"""Build privacy-aware weekly meeting statistics from the meetings table."""

import csv
import io
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionFactory
from app.models import Meeting

REPORT_TIMEZONE = ZoneInfo("Europe/Kyiv")
_WEEK_FORMAT = re.compile(r"^(\d{4})-W(\d{2})$")
CSV_COLUMNS = (
    "record_type",
    "week",
    "organizer_id",
    "meeting_count",
    "total_duration_hours",
    "previous_meeting_count",
    "previous_total_duration_hours",
    "meeting_count_change",
    "duration_hours_change",
    "meeting_rank",
    "meeting_id",
    "meeting_title",
    "start_at_utc",
    "end_at_utc",
    "duration_hours",
)


@dataclass(frozen=True, slots=True)
class ReportMeeting:
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    start_at: datetime
    end_at: datetime


def week_bounds(week: str | None = None) -> tuple[str, datetime, datetime]:
    """Return the ISO week label and UTC [start, end) bounds."""
    if week is None:
        local_today = datetime.now(REPORT_TIMEZONE).date()
        iso = local_today.isocalendar()
        year, week_number = iso.year, iso.week
    else:
        match = _WEEK_FORMAT.fullmatch(week)
        if match is None:
            raise ValueError("week must use ISO format YYYY-Www, for example 2026-W39")
        year, week_number = map(int, match.groups())

    try:
        monday = date.fromisocalendar(year, week_number, 1)
    except ValueError as exc:
        raise ValueError(f"invalid ISO week: {year}-W{week_number:02d}") from exc

    start_local = datetime.combine(monday, time.min, tzinfo=REPORT_TIMEZONE)
    end_local = datetime.combine(monday + timedelta(days=7), time.min, tzinfo=REPORT_TIMEZONE)
    return (
        f"{year}-W{week_number:02d}",
        start_local.astimezone(UTC),
        end_local.astimezone(UTC),
    )


def previous_completed_week(now: datetime | None = None) -> str:
    """Return the last complete ISO week in Europe/Kyiv."""
    local_now = now or datetime.now(REPORT_TIMEZONE)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=REPORT_TIMEZONE)
    else:
        local_now = local_now.astimezone(REPORT_TIMEZONE)
    monday = local_now.date() - timedelta(days=local_now.isoweekday() - 1)
    previous_monday = monday - timedelta(days=7)
    iso = previous_monday.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _duration_hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


async def _query_meetings(
    session: AsyncSession, start: datetime, end: datetime
) -> list[ReportMeeting]:
    result = await session.execute(
        select(Meeting.id, Meeting.owner_id, Meeting.title, Meeting.start_at, Meeting.end_at)
        .where(Meeting.start_at >= start, Meeting.start_at < end)
        .order_by(Meeting.owner_id, Meeting.start_at, Meeting.id)
    )
    return [ReportMeeting(*row) for row in result.all()]


async def _build(session: AsyncSession, week: str | None) -> bytes:
    label, start, end = week_bounds(week)
    previous_end = start
    monday = date.fromisocalendar(int(label[:4]), int(label[-2:]), 1)
    previous_iso = (monday - timedelta(days=7)).isocalendar()
    previous_label = f"{previous_iso.year}-W{previous_iso.week:02d}"
    _, previous_start, _ = week_bounds(previous_label)
    current_meetings = await _query_meetings(session, start, end)
    previous_meetings = await _query_meetings(session, previous_start, previous_end)

    current_by_owner: dict[str, list[ReportMeeting]] = defaultdict(list)
    previous_by_owner: dict[str, list[ReportMeeting]] = defaultdict(list)
    for meeting in current_meetings:
        current_by_owner[str(meeting.owner_id)].append(meeting)
    for meeting in previous_meetings:
        previous_by_owner[str(meeting.owner_id)].append(meeting)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()

    current_hours = sum(_duration_hours(m.start_at, m.end_at) for m in current_meetings)
    previous_hours = sum(_duration_hours(m.start_at, m.end_at) for m in previous_meetings)
    writer.writerow(
        {
            "record_type": "week_summary",
            "week": label,
            "meeting_count": len(current_meetings),
            "total_duration_hours": f"{current_hours:.2f}",
            "previous_meeting_count": len(previous_meetings),
            "previous_total_duration_hours": f"{previous_hours:.2f}",
            "meeting_count_change": len(current_meetings) - len(previous_meetings),
            "duration_hours_change": f"{current_hours - previous_hours:.2f}",
        }
    )

    for owner_id in sorted(current_by_owner.keys() | previous_by_owner.keys()):
        current_owner = current_by_owner[owner_id]
        previous_owner = previous_by_owner[owner_id]
        owner_hours = sum(_duration_hours(m.start_at, m.end_at) for m in current_owner)
        previous_owner_hours = sum(_duration_hours(m.start_at, m.end_at) for m in previous_owner)
        writer.writerow(
            {
                "record_type": "organizer_summary",
                "week": label,
                "organizer_id": owner_id,
                "meeting_count": len(current_owner),
                "total_duration_hours": f"{owner_hours:.2f}",
                "previous_meeting_count": len(previous_owner),
                "previous_total_duration_hours": f"{previous_owner_hours:.2f}",
                "meeting_count_change": len(current_owner) - len(previous_owner),
                "duration_hours_change": f"{owner_hours - previous_owner_hours:.2f}",
            }
        )

    longest = sorted(
        current_meetings,
        key=lambda meeting: (
            -_duration_hours(meeting.start_at, meeting.end_at),
            meeting.start_at,
            str(meeting.id),
        ),
    )[:5]
    for rank, meeting in enumerate(longest, start=1):
        writer.writerow(
            {
                "record_type": "longest_meeting",
                "week": label,
                "organizer_id": str(meeting.owner_id),
                "meeting_rank": rank,
                "meeting_id": str(meeting.id),
                "meeting_title": meeting.title,
                "start_at_utc": _utc_text(meeting.start_at),
                "end_at_utc": _utc_text(meeting.end_at),
                "duration_hours": f"{_duration_hours(meeting.start_at, meeting.end_at):.2f}",
            }
        )

    return output.getvalue().encode("utf-8")


async def build_weekly_report(
    week: str | None = None, *, session: AsyncSession | None = None
) -> bytes:
    """Return UTF-8 CSV bytes for an ISO week using persisted meeting records."""
    if session is not None:
        return await _build(session, week)
    async with SessionFactory() as owned_session:
        return await _build(owned_session, week)
