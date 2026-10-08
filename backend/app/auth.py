import json
import uuid
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.db import SessionDep
from app.models import User

bearer = HTTPBearer(auto_error=False)


@lru_cache
def jwks_client(issuer: str):
    return jwt.PyJWKClient(issuer + "/.well-known/jwks.json")


async def current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    settings = get_settings()
    if not settings.auth_configured:
        raise HTTPException(503, "Authentication is not configured")
    if not credentials:
        raise HTTPException(401, "Sign in required", headers={"WWW-Authenticate": "Bearer"})
    try:
        token = credentials.credentials
        if settings.cognito_jwks:
            kid = jwt.get_unverified_header(token).get("kid")
            keys = json.loads(settings.cognito_jwks)["keys"]
            key = jwt.PyJWK.from_dict(next(k for k in keys if k["kid"] == kid)).key
        else:
            signing = await run_in_threadpool(
                jwks_client(settings.cognito_issuer).get_signing_key_from_jwt, token
            )
            key = signing.key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=settings.cognito_issuer,
            options={"require": ["exp", "iss", "aud", "sub", "token_use"]},
        )
        if claims["token_use"] != "id":
            raise ValueError("Invalid token use")
        sub, email = claims["sub"], claims["email"]
    except (jwt.PyJWTError, ValueError, KeyError, StopIteration) as exc:
        raise HTTPException(401, "Invalid or expired session") from exc
    # Concurrent first requests cannot create duplicate users.
    await session.execute(
        insert(User)
        .values(
            id=uuid.uuid4(),
            cognito_sub=sub,
            email=email,
            name=claims.get("name") or email.split("@")[0],
        )
        .on_conflict_do_nothing(index_elements=["cognito_sub"])
    )
    return (await session.execute(select(User).where(User.cognito_sub == sub))).scalar_one()


CurrentUser = Annotated[User, Depends(current_user)]
