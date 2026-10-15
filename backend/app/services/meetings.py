import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Meeting
from app.schemas.meeting import MeetingCreate, MeetingUpdate


async def list_meetings(session: AsyncSession, owner_id: uuid.UUID, start: datetime, end: datetime):
    where = (Meeting.owner_id == owner_id, Meeting.start_at < end, Meeting.end_at > start)
    total = await session.scalar(select(func.count()).select_from(Meeting).where(*where)) or 0
    result = await session.scalars(select(Meeting).where(*where).order_by(Meeting.start_at))
    return list(result), total


async def get_meeting(session: AsyncSession, owner_id: uuid.UUID, meeting_id: uuid.UUID):
    return await session.scalar(
        select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == owner_id)
    )


async def create_meeting(session: AsyncSession, owner_id: uuid.UUID, payload: MeetingCreate):
    meeting = Meeting(owner_id=owner_id, **payload.model_dump())
    session.add(meeting)
    await session.flush()
    await session.refresh(meeting)
    return meeting


async def update_meeting(session: AsyncSession, meeting: Meeting, payload: MeetingUpdate):
    values = payload.model_dump(exclude_unset=True)
    start = values.get("start_at", meeting.start_at)
    end = values.get("end_at", meeting.end_at)
    if start is not None and end is not None and end <= start:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="End time must be later than start time")
    for field, value in values.items():
        setattr(meeting, field, value)
    await session.flush()
    await session.refresh(meeting)
    return meeting


async def delete_meeting(session: AsyncSession, meeting: Meeting):
    await session.delete(meeting)
    await session.flush()
