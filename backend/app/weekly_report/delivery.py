"""Email a report attachment and time-limited private link after S3 creation."""

import json
import logging
import os
import re
from email.message import EmailMessage
from email.policy import SMTP
from functools import lru_cache
from urllib.parse import unquote_plus

_LOG = logging.getLogger(__name__)


@lru_cache
def _s3_client():
    import boto3

    return boto3.client("s3")


@lru_cache
def _ses_client():
    import boto3

    return boto3.client("sesv2")


def _event_records(event):
    """Normalize EventBridge, legacy Records, and SQS-wrapped events."""
    if not isinstance(event, dict):
        return []
    if isinstance(event.get("detail"), dict):
        return [event]

    records = event.get("Records")
    if not isinstance(records, list):
        return []

    normalized = []
    for record in records:
        if not isinstance(record, dict):
            continue
        if isinstance(record.get("detail"), dict):
            normalized.append(record)
            continue
        body = record.get("body")
        if isinstance(body, str):
            try:
                nested_event = json.loads(body)
            except json.JSONDecodeError:
                continue
            if isinstance(nested_event, dict) and isinstance(nested_event.get("detail"), dict):
                normalized.append(nested_event)
    return normalized


def handler(event, context):
    expected_bucket = os.environ["REPORT_BUCKET"]
    sender = os.environ["REPORT_SENDER"]
    recipient = os.environ["REPORT_RECIPIENT"]
    records = _event_records(event)
    for record in records:
        detail = record.get("detail", {})
        bucket_detail = detail.get("bucket")
        object_detail = detail.get("object")
        if not isinstance(bucket_detail, dict) or not isinstance(object_detail, dict):
            continue
        bucket = bucket_detail.get("name")
        encoded_key = object_detail.get("key")
        if not isinstance(encoded_key, str):
            continue
        key = unquote_plus(encoded_key)
        match = re.fullmatch(r"reports/(\d{4}-W\d{2})/weekly-meetings\.csv", key)
        if bucket != expected_bucket or match is None:
            continue
        week = match.group(1)
        year, week_number = map(int, (week[:4], week[-2:]))
        try:
            from datetime import date

            date.fromisocalendar(year, week_number, 1)
        except ValueError:
            continue
        _LOG.info("trigger=s3 outcome=received week=%s", week)
        try:
            report = _s3_client().get_object(Bucket=bucket, Key=key)["Body"].read()
            url = _s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=604800,
            )
            message = EmailMessage()
            message["Subject"] = f"Peach weekly meetings report: {week}"
            message["From"] = sender
            message["To"] = recipient
            message.set_content(
                f"The Peach meetings report for {week} is attached. "
                "The private download link is intended to work for up to 7 days, "
                "but may expire sooner when the signing credentials expire:\n"
                f"{url}"
            )
            message.add_attachment(
                report,
                maintype="text",
                subtype="csv",
                filename=f"weekly-meetings-{week}.csv",
            )
            _ses_client().send_email(
                FromEmailAddress=sender,
                Destination={"ToAddresses": [recipient]},
                Content={"Raw": {"Data": message.as_bytes(policy=SMTP)}},
            )
        except Exception:
            _LOG.exception("trigger=s3 outcome=failed week=%s", week)
            raise
        _LOG.info("trigger=s3 outcome=accepted_by_ses week=%s", week)
    return {"processed": len(records)}
