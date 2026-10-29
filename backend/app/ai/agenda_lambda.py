"""Authenticated function URL. It can suggest, but cannot access the database."""

import base64
import json
import logging
import os
import time
from datetime import date
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import jwt
from anthropic import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.ai.agenda import PROMPT_VERSION, AgendaParseError, cost_usd, model_id, parse_agenda

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@lru_cache
def keys(issuer):
    return jwt.PyJWKClient(issuer + "/.well-known/jwks.json", timeout=3)


def verify_cognito_token(authorization):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ValueError("Missing bearer token")
    region = os.environ["COGNITO_REGION"]
    issuer = f"https://cognito-idp.{region}.amazonaws.com/{os.environ['COGNITO_USER_POOL_ID']}"
    claims = jwt.decode(
        token,
        keys(issuer).get_signing_key_from_jwt(token).key,
        algorithms=["RS256"],
        audience=os.environ["COGNITO_CLIENT_ID"],
        issuer=issuer,
        options={"require": ["exp", "iss", "aud", "sub", "token_use"]},
    )
    if claims["token_use"] != "id":
        raise ValueError("Wrong token use")
    return claims["sub"]


class ParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=10_000)
    today: date
    tz: str = Field(min_length=1, max_length=100)

    @field_validator("tz")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use a valid IANA time zone") from exc
        return value


def response(code, body):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if event.get("requestContext", {}).get("http", {}).get("method") != "POST":
        return response(405, {"error": "Use POST."})
    try:
        user = verify_cognito_token(headers.get("authorization", ""))
    except jwt.PyJWTError, ValueError, KeyError:
        return response(401, {"error": "Sign in again to parse an agenda."})
    raw = event.get("body") or ""
    if len(raw) > 100_000:
        return response(413, {"error": "Text is too long. Maximum: 10,000 characters."})
    try:
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        body = json.loads(raw)
        if (
            isinstance(body, dict)
            and isinstance(body.get("text"), str)
            and len(body["text"]) > 10_000
        ):
            return response(413, {"error": "Text is too long. Maximum: 10,000 characters."})
        request = ParseRequest.model_validate(body)
    except ValueError, ValidationError:
        return response(400, {"error": "Provide text, today's ISO date, and an IANA time zone."})
    started = time.monotonic()
    usage = {"input_tokens": 0, "output_tokens": 0}
    outcome = "error"
    try:
        agenda, usage = parse_agenda(request.text, request.today, request.tz)
        outcome = "success"
        return response(
            200,
            {
                "agenda": agenda.model_dump(mode="json"),
                "model": model_id(),
                "prompt_version": PROMPT_VERSION,
                "usage": usage,
                "cost_usd": cost_usd(usage),
                "latency_ms": int((time.monotonic() - started) * 1000),
            },
        )
    except AgendaParseError as exc:
        usage = exc.usage
        return response(422, {"error": str(exc)})
    except RateLimitError as exc:
        usage = getattr(exc, "agenda_usage", usage)
        return response(
            429, {"error": "The AI service is busy. Try again shortly or type manually."}
        )
    except ClientError as exc:
        usage = getattr(exc, "agenda_usage", usage)
        code = exc.response.get("Error", {}).get("Code")
        if code == "ThrottlingException":
            return response(
                429, {"error": "The AI service is busy. Try again shortly or type manually."}
            )
        return response(
            503, {"error": "The AI service is unavailable. You can still type manually."}
        )
    except (APIConnectionError, APITimeoutError, APIStatusError, BotoCoreError) as exc:
        usage = getattr(exc, "agenda_usage", usage)
        return response(
            503, {"error": "The AI service is unavailable. You can still type manually."}
        )
    finally:
        log.info(
            json.dumps(
                {
                    "event": "agenda_parsed",
                    "user": user,
                    "model": model_id(),
                    "prompt_version": PROMPT_VERSION,
                    **usage,
                    "outcome": outcome,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "cost_usd": cost_usd(usage),
                }
            )
        )
