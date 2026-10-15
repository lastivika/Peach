"""SQS consumer that queries Peach meetings and stores a private CSV in S3."""

import asyncio
import json
import logging
import os
import re
from functools import lru_cache

from app.services.weekly_report import build_weekly_report, previous_completed_week

_WEEK = re.compile(r"^\d{4}-W\d{2}$")
_LOG = logging.getLogger(__name__)


@lru_cache
def _s3_client():
    import boto3

    return boto3.client("s3")


def _already_reported(bucket: str, key: str) -> bool:
    response = _s3_client().list_objects_v2(
        Bucket=bucket,
        Prefix=key,
        MaxKeys=1,
    )
    return any(item.get("Key") == key for item in response.get("Contents", []))


def handler(event, context):
    bucket = os.environ["REPORT_BUCKET"]
    for record in event.get("Records", []):
        try:
            payload = json.loads(record["body"])
        except (KeyError, json.JSONDecodeError):
            _LOG.error("trigger=sqs origin=unknown outcome=invalid_message")
            raise
        if not isinstance(payload, dict):
            _LOG.error("trigger=sqs origin=unknown outcome=invalid_message")
            raise ValueError("SQS message body must be a JSON object")
        origin = "schedule" if payload.get("source") == "schedule" else "manual"
        _LOG.info("trigger=sqs origin=%s outcome=received", origin)
        if origin == "schedule":
            _LOG.info("trigger=schedule outcome=queued")
        week = payload.get("week") or previous_completed_week()
        if not isinstance(week, str) or not _WEEK.fullmatch(week):
            _LOG.error("trigger=sqs origin=%s outcome=invalid_week", origin)
            raise ValueError("SQS message must contain an ISO week in YYYY-Www format")
        key = f"reports/{week}/weekly-meetings.csv"
        if _already_reported(bucket, key):
            _LOG.info("trigger=sqs origin=%s outcome=already_exists week=%s", origin, week)
            continue
        from botocore.exceptions import ClientError

        try:
            report = asyncio.run(build_weekly_report(week))
        except Exception:
            _LOG.error("trigger=sqs origin=%s outcome=failed week=%s", origin, week)
            raise
        try:
            _s3_client().put_object(
                Bucket=bucket,
                Key=key,
                Body=report,
                ContentType="text/csv; charset=utf-8",
                ServerSideEncryption="AES256",
                IfNoneMatch="*",
            )
        except ClientError as error:
            status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 412 and _already_reported(bucket, key):
                _LOG.info(
                    "trigger=sqs origin=%s outcome=already_exists week=%s", origin, week
                )
                continue
            _LOG.error("trigger=sqs origin=%s outcome=failed week=%s", origin, week)
            raise
        except Exception:
            _LOG.error("trigger=sqs origin=%s outcome=failed week=%s", origin, week)
            raise
        _LOG.info("trigger=sqs origin=%s outcome=created week=%s", origin, week)
    return {"processed": len(event.get("Records", []))}
