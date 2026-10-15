import csv
import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Meeting, User
from app.services import weekly_report
from app.services.weekly_report import build_weekly_report, week_bounds


def test_week_bounds_handles_iso_year_boundary_and_kyiv_timezone():
    label, start, end = week_bounds("2021-W01")
    assert label == "2021-W01"
    assert start.isoformat() == "2021-01-03T22:00:00+00:00"
    assert end.isoformat() == "2021-01-10T22:00:00+00:00"
    prior_label, prior_start, _ = week_bounds("2020-W53")
    assert prior_label == "2020-W53"
    assert prior_start < start


def test_missing_week_uses_current_iso_week_in_kyiv(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2021, 1, 4, 0, 5, tzinfo=tz)

    monkeypatch.setattr(weekly_report, "datetime", FixedDateTime)
    assert week_bounds()[0] == "2021-W01"


@pytest.mark.parametrize("value", ["2026-W00", "2026-W54", "2026-39", "2026-W3"])
def test_week_bounds_rejects_invalid_iso_weeks(value):
    with pytest.raises(ValueError):
        week_bounds(value)


async def test_build_weekly_report_uses_database_groups_owners_and_escapes_csv(session):
    owner_one = User(cognito_sub=f"report-{uuid.uuid4()}", email="one@example.com", name="One")
    owner_two = User(cognito_sub=f"report-{uuid.uuid4()}", email="two@example.com", name="Two")
    session.add_all([owner_one, owner_two])
    await session.flush()

    async def add_meeting(owner, title, start, hours):
        session.add(
            Meeting(
                owner_id=owner.id,
                title=title,
                start_at=start,
                end_at=start + timedelta(hours=hours),
            )
        )

    # Europe/Kyiv Monday 2026-09-21 begins at 2026-09-20 21:00 UTC.
    week_start = datetime(2026, 9, 20, 21, tzinfo=UTC)
    await add_meeting(owner_one, 'Planning, "North"', week_start + timedelta(hours=1), 2)
    await add_meeting(owner_one, "Review", week_start + timedelta(hours=4), 1)
    await add_meeting(owner_two, "Prior week", week_start - timedelta(days=1), 3)
    await session.flush()

    report = await build_weekly_report("2026-W39", session=session)
    assert isinstance(report, bytes)
    rows = list(csv.DictReader(io.StringIO(report.decode("utf-8"))))

    summary = next(row for row in rows if row["record_type"] == "week_summary")
    assert summary["meeting_count"] == "2"
    assert summary["total_duration_hours"] == "3.00"
    assert summary["previous_meeting_count"] == "1"
    assert summary["previous_total_duration_hours"] == "3.00"
    organizers = [row for row in rows if row["record_type"] == "organizer_summary"]
    assert len(organizers) == 2
    owner_one_row = next(row for row in organizers if row["organizer_id"] == str(owner_one.id))
    owner_two_row = next(row for row in organizers if row["organizer_id"] == str(owner_two.id))
    assert owner_one_row["meeting_count"] == "2"
    assert owner_one_row["previous_meeting_count"] == "0"
    assert owner_two_row["meeting_count"] == "0"
    assert owner_two_row["previous_meeting_count"] == "1"
    top_meeting = next(row for row in rows if row["record_type"] == "longest_meeting")
    assert top_meeting["meeting_title"] == 'Planning, "North"'
    assert top_meeting["duration_hours"] == "2.00"


async def test_build_weekly_report_limits_top_meetings_to_five(session):
    owner = User(cognito_sub=f"report-{uuid.uuid4()}", email="owner@example.com", name="Owner")
    session.add(owner)
    await session.flush()
    _, start, _ = week_bounds("2026-W39")
    for index in range(6):
        session.add(
            Meeting(
                owner_id=owner.id,
                title=f"Meeting {index}",
                start_at=start + timedelta(hours=index),
                end_at=start + timedelta(hours=index + index + 1),
            )
        )
    await session.flush()
    rows = list(
        csv.DictReader(
            io.StringIO((await build_weekly_report("2026-W39", session=session)).decode("utf-8"))
        )
    )
    longest = [row for row in rows if row["record_type"] == "longest_meeting"]
    assert len(longest) == 5
    assert [int(row["meeting_rank"]) for row in longest] == [1, 2, 3, 4, 5]
