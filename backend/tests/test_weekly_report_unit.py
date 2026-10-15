import csv
import io
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.dialects import postgresql

from app.services.weekly_report import CSV_COLUMNS, ReportMeeting, build_weekly_report


class Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class Session:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return Result(next(self.results))


@pytest.mark.asyncio
async def test_report_queries_iso_week_and_previous_week_and_writes_csv():
    owner_id = uuid.uuid4()
    meeting = ReportMeeting(
        id=uuid.uuid4(),
        owner_id=owner_id,
        title='Planning, "North"',
        start_at=datetime(2026, 9, 20, 22, tzinfo=UTC),
        end_at=datetime(2026, 9, 21, 0, tzinfo=UTC),
    )
    session = Session(
        [[(meeting.id, meeting.owner_id, meeting.title, meeting.start_at, meeting.end_at)], []]
    )

    report = await build_weekly_report("2026-W39", session=session)

    sql = [str(statement.compile(dialect=postgresql.dialect())) for statement in session.statements]
    assert len(sql) == 2
    assert all("FROM meetings" in statement for statement in sql)
    assert all("meetings.start_at >=" in statement for statement in sql)
    assert all("meetings.start_at <" in statement for statement in sql)
    assert all(
        "ORDER BY meetings.owner_id, meetings.start_at, meetings.id" in statement
        for statement in sql
    )
    rows = list(csv.DictReader(io.StringIO(report.decode("utf-8"))))
    assert tuple(rows[0].keys()) == CSV_COLUMNS
    summary, organizer, longest = rows
    assert summary["week"] == "2026-W39"
    assert summary["meeting_count"] == "1"
    assert summary["total_duration_hours"] == "2.00"
    assert organizer["organizer_id"] == str(owner_id)
    assert longest["meeting_title"] == 'Planning, "North"'
    assert longest["start_at_utc"] == "2026-09-20T22:00:00Z"


@pytest.mark.asyncio
async def test_empty_report_contains_header_and_zero_summary():
    session = Session([[], []])

    report = await build_weekly_report("2026-W39", session=session)

    reader = csv.DictReader(io.StringIO(report.decode("utf-8")))
    assert tuple(reader.fieldnames) == CSV_COLUMNS
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["record_type"] == "week_summary"
    assert rows[0]["meeting_count"] == "0"
    assert rows[0]["total_duration_hours"] == "0.00"
    assert rows[0]["previous_meeting_count"] == "0"
