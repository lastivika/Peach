import json
import sys
import types
from datetime import datetime
from email import message_from_bytes
from email.policy import default
from zoneinfo import ZoneInfo

import pytest

from app.services.weekly_report import previous_completed_week
from app.weekly_report import delivery, worker


def test_last_completed_week_handles_iso_year_boundary_in_kyiv():
    monday = datetime(2021, 1, 4, 0, 5, tzinfo=ZoneInfo("Europe/Kyiv"))
    assert previous_completed_week(monday) == "2020-W53"


def test_delivery_reads_csv_and_sends_attachment_and_private_link(monkeypatch):
    class S3:
        def get_object(self, *, Bucket, Key):
            assert Bucket == "weekly-report"
            assert Key == "reports/2026-W39/weekly-meetings.csv"

            class Body:
                def read(self):
                    return b"meeting_count,title\n1,Planning\n"

            return {"Body": Body()}

        def generate_presigned_url(self, operation, *, Params, ExpiresIn):
            assert operation == "get_object"
            assert Params == {
                "Bucket": "weekly-report",
                "Key": "reports/2026-W39/weekly-meetings.csv",
            }
            assert ExpiresIn == 604800
            return "https://private.example/report"

    class SES:
        sent = None

        def send_email(self, **kwargs):
            self.sent = kwargs

    ses = SES()
    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setenv("REPORT_SENDER", "verified@example.test")
    monkeypatch.setenv("REPORT_RECIPIENT", "authorized@example.test")
    monkeypatch.setattr(delivery, "_s3_client", lambda: S3())
    monkeypatch.setattr(delivery, "_ses_client", lambda: ses)

    result = delivery.handler(
        {
            "Records": [
                {
                    "detail": {
                        "bucket": {"name": "weekly-report"},
                        "object": {"key": "reports/2026-W39/weekly-meetings.csv"},
                    }
                }
            ]
        },
        None,
    )
    assert result == {"processed": 1}
    assert ses.sent["Destination"] == {"ToAddresses": ["authorized@example.test"]}
    raw = message_from_bytes(ses.sent["Content"]["Raw"]["Data"], policy=default)
    email_body = raw.get_body(preferencelist=("plain",)).get_content()
    assert "https://private.example/report" in email_body
    assert "intended to work for up to 7 days" in email_body
    assert "may expire sooner when the signing credentials expire" in email_body
    attachments = list(raw.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "weekly-meetings-2026-W39.csv"
    assert attachments[0].get_content() == "meeting_count,title\n1,Planning\n"


def test_delivery_accepts_native_s3_eventbridge_event(monkeypatch, caplog):
    caplog.set_level("INFO")
    class S3:
        def get_object(self, *, Bucket, Key):
            assert Bucket == "weekly-report"
            assert Key == "reports/2026-W43/weekly-meetings.csv"

            class Body:
                def read(self):
                    return b"meeting_count\n0\n"

            return {"Body": Body()}

        def generate_presigned_url(self, *_args, **_kwargs):
            return "https://private.example/report"

    class SES:
        sent = None

        def send_email(self, **kwargs):
            self.sent = kwargs

    ses = SES()
    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setenv("REPORT_SENDER", "verified@example.test")
    monkeypatch.setenv("REPORT_RECIPIENT", "authorized@example.test")
    monkeypatch.setattr(delivery, "_s3_client", lambda: S3())
    monkeypatch.setattr(delivery, "_ses_client", lambda: ses)

    event = {
        "version": "0",
        "id": "event-id",
        "detail-type": "Object Created",
        "source": "aws.s3",
        "detail": {
            "bucket": {"name": "weekly-report"},
            "object": {"key": "reports/2026-W43/weekly-meetings.csv"},
        },
    }
    assert delivery.handler(event, None) == {"processed": 1}
    assert ses.sent["Destination"] == {"ToAddresses": ["authorized@example.test"]}
    assert "trigger=s3 outcome=received week=2026-W43" in caplog.text
    assert "trigger=s3 outcome=accepted_by_ses week=2026-W43" in caplog.text


def test_delivery_accepts_sqs_records_wrapping_eventbridge_event(monkeypatch):
    class S3:
        def get_object(self, *, Bucket, Key):
            assert Bucket == "weekly-report"
            assert Key == "reports/2026-W43/weekly-meetings.csv"

            class Body:
                def read(self):
                    return b"meeting_count\n0\n"

            return {"Body": Body()}

        def generate_presigned_url(self, *_args, **_kwargs):
            return "https://private.example/report"

    class SES:
        sent = 0

        def send_email(self, **_kwargs):
            self.sent += 1

    ses = SES()
    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setenv("REPORT_SENDER", "verified@example.test")
    monkeypatch.setenv("REPORT_RECIPIENT", "authorized@example.test")
    monkeypatch.setattr(delivery, "_s3_client", lambda: S3())
    monkeypatch.setattr(delivery, "_ses_client", lambda: ses)
    eventbridge_event = {
        "detail-type": "Object Created",
        "source": "aws.s3",
        "detail": {
            "bucket": {"name": "weekly-report"},
            "object": {"key": "reports/2026-W43/weekly-meetings.csv"},
        },
    }
    wrapped = {"Records": [{"body": json.dumps(eventbridge_event)}]}

    assert delivery.handler(wrapped, None) == {"processed": 1}
    assert ses.sent == 1


def test_delivery_ignores_invalid_event_payload(monkeypatch):
    class FailIfCalled:
        def __getattr__(self, _name):
            raise AssertionError("unexpected AWS client call")

    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setenv("REPORT_SENDER", "verified@example.test")
    monkeypatch.setenv("REPORT_RECIPIENT", "authorized@example.test")
    monkeypatch.setattr(delivery, "_s3_client", lambda: FailIfCalled())
    monkeypatch.setattr(delivery, "_ses_client", lambda: FailIfCalled())

    assert delivery.handler(None, None) == {"processed": 0}
    assert delivery.handler({"Records": [{"body": "not-json"}]}, None) == {"processed": 0}
    assert delivery.handler({"detail": None}, None) == {"processed": 0}


def test_delivery_ignores_other_bucket(monkeypatch):
    class FailIfCalled:
        def __getattr__(self, _name):
            raise AssertionError("unexpected client call")

    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setenv("REPORT_SENDER", "verified@example.test")
    monkeypatch.setenv("REPORT_RECIPIENT", "authorized@example.test")
    monkeypatch.setattr(delivery, "_s3_client", lambda: FailIfCalled())
    monkeypatch.setattr(delivery, "_ses_client", lambda: FailIfCalled())
    assert delivery.handler(
        {"Records": [{"detail": {"bucket": {"name": "other"}, "object": {"key": "x"}}}]}, None
    ) == {"processed": 1}


def test_repeated_s3_event_can_send_duplicate_email(monkeypatch):
    class S3:
        reads = 0

        def get_object(self, *, Bucket, Key):
            self.reads += 1

            class Body:
                def read(self):
                    return b"meeting_count\n0\n"

            return {"Body": Body()}

        def generate_presigned_url(self, *_args, **_kwargs):
            return "https://private.example/report"

    class SES:
        sends = 0

        def send_email(self, **_kwargs):
            self.sends += 1

    s3, ses = S3(), SES()
    event = {
        "Records": [
            {
                "detail": {
                    "bucket": {"name": "weekly-report"},
                    "object": {"key": "reports/2026-W39/weekly-meetings.csv"},
                }
            }
        ]
    }
    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setenv("REPORT_SENDER", "verified@example.test")
    monkeypatch.setenv("REPORT_RECIPIENT", "authorized@example.test")
    monkeypatch.setattr(delivery, "_s3_client", lambda: s3)
    monkeypatch.setattr(delivery, "_ses_client", lambda: ses)

    assert delivery.handler(event, None) == {"processed": 1}
    assert delivery.handler(event, None) == {"processed": 1}
    assert s3.reads == 2
    assert ses.sends == 2


def test_worker_writes_utf8_csv_and_is_idempotent(monkeypatch):
    class S3:
        objects = {}

        def list_objects_v2(self, *, Bucket, Prefix, MaxKeys):
            assert MaxKeys == 1
            return {
                "Contents": [
                    {"Key": key}
                    for bucket, key in self.objects
                    if bucket == Bucket and key.startswith(Prefix)
                ]
            }

        def put_object(self, **kwargs):
            assert kwargs["IfNoneMatch"] == "*"
            self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    s3 = S3()
    built = []
    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.ClientError = RuntimeError
    botocore.exceptions = exceptions
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions)

    async def build(week):
        built.append(week)
        return "мітинг,title\n".encode()

    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setattr(worker, "_s3_client", lambda: s3)
    monkeypatch.setattr(worker, "build_weekly_report", build)
    monkeypatch.setattr(worker, "previous_completed_week", lambda: "2026-W41")
    event = {"Records": [{"body": "{}"}]}
    assert worker.handler(event, None) == {"processed": 1}
    assert worker.handler(event, None) == {"processed": 1}
    assert built == ["2026-W41"]
    assert s3.objects[("weekly-report", "reports/2026-W41/weekly-meetings.csv")].startswith(
        b"\xd0\xbc"
    )


def test_worker_treats_conditional_put_conflict_as_duplicate(monkeypatch):
    key = ("weekly-report", "reports/2026-W41/weekly-meetings.csv")

    class S3:
        objects = {}
        list_calls = 0

        def list_objects_v2(self, *, Bucket, Prefix, MaxKeys):
            self.list_calls += 1
            assert MaxKeys == 1
            return {
                "Contents": [
                    {"Key": key}
                    for bucket, key in self.objects
                    if bucket == Bucket and key.startswith(Prefix)
                ]
            }

        def put_object(self, **kwargs):
            assert kwargs["IfNoneMatch"] == "*"
            self.objects[(kwargs["Bucket"], kwargs["Key"])] = b"other invocation won"
            error = RuntimeError("object already exists")
            error.response = {
                "Error": {"Code": "PreconditionFailed"},
                "ResponseMetadata": {"HTTPStatusCode": 412},
            }
            raise error

    s3 = S3()
    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.ClientError = RuntimeError
    botocore.exceptions = exceptions
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions)

    async def build(_week):
        return b"meeting_count\n0\n"

    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setattr(worker, "_s3_client", lambda: s3)
    monkeypatch.setattr(worker, "build_weekly_report", build)
    monkeypatch.setattr(worker, "previous_completed_week", lambda: "2026-W41")

    assert worker.handler({"Records": [{"body": "{}"}]}, None) == {"processed": 1}
    assert s3.objects[key] == b"other invocation won"


def test_worker_message_can_be_replayed_after_three_failures_are_fixed(monkeypatch):
    class S3:
        objects = {}

        def list_objects_v2(self, *, Bucket, Prefix, MaxKeys):
            assert MaxKeys == 1
            return {
                "Contents": [
                    {"Key": key}
                    for bucket, key in self.objects
                    if bucket == Bucket and key.startswith(Prefix)
                ]
            }

        def put_object(self, **kwargs):
            assert kwargs["IfNoneMatch"] == "*"
            self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    s3 = S3()
    botocore = types.ModuleType("botocore")
    exceptions = types.ModuleType("botocore.exceptions")
    exceptions.ClientError = RuntimeError
    botocore.exceptions = exceptions
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exceptions)
    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setattr(worker, "_s3_client", lambda: s3)

    async def failing_build(_week):
        raise RuntimeError("temporary database failure")

    monkeypatch.setattr(worker, "build_weekly_report", failing_build)
    event = {"Records": [{"body": '{"week":"2026-W41"}'}]}
    for _ in range(3):
        with pytest.raises(RuntimeError, match="temporary database failure"):
            worker.handler(event, None)

    async def fixed_build(_week):
        return b"meeting_count\n0\n"

    monkeypatch.setattr(worker, "build_weekly_report", fixed_build)
    assert worker.handler(event, None) == {"processed": 1}
    assert s3.objects[("weekly-report", "reports/2026-W41/weekly-meetings.csv")] == (
        b"meeting_count\n0\n"
    )


def test_worker_logs_scheduled_origin(monkeypatch, caplog):
    caplog.set_level("INFO")
    class S3:
        def list_objects_v2(self, **_kwargs):
            return {"Contents": [{"Key": "reports/2026-W41/weekly-meetings.csv"}]}

    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    monkeypatch.setattr(worker, "_s3_client", lambda: S3())

    assert worker.handler(
        {"Records": [{"body": '{"week":"2026-W41","source":"schedule"}'}]}, None
    ) == {"processed": 1}
    assert "trigger=sqs origin=schedule outcome=received" in caplog.text
    assert "trigger=schedule outcome=queued" in caplog.text


@pytest.mark.parametrize("body", ["[]", "null", '"text"'])
def test_worker_rejects_non_object_message_body(monkeypatch, body):
    monkeypatch.setenv("REPORT_BUCKET", "weekly-report")
    with pytest.raises(ValueError, match="JSON object"):
        worker.handler({"Records": [{"body": body}]}, None)
