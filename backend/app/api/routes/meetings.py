import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.db import SessionDep
from app.models import User
from app.schemas.agenda import AgendaSave
from app.schemas.meeting import MeetingCreate, MeetingList, MeetingRead, MeetingUpdate
from app.services import meetings as service

router = APIRouter(prefix="/meetings", tags=["meetings"])


async def get_or_404(session: AsyncSession, user: User, meeting_id: uuid.UUID):
    meeting = await service.get_meeting(session, user.id, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("", response_model=MeetingList)
async def list_meetings(
    session: SessionDep,
    user: CurrentUser,
    start: Annotated[datetime, Query(alias="start")],
    end: Annotated[datetime, Query(alias="end")],
):
    if end <= start:
        raise HTTPException(status_code=422, detail="End must be later than start")
    meetings, total = await service.list_meetings(session, user.id, start, end)
    return MeetingList(meetings=[MeetingRead.model_validate(m) for m in meetings], total=total)


@router.post("", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
async def create_meeting(payload: MeetingCreate, session: SessionDep, user: CurrentUser):
    return MeetingRead.model_validate(await service.create_meeting(session, user.id, payload))


@router.get("/{meeting_id}", response_model=MeetingRead)
async def read_meeting(meeting_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    return MeetingRead.model_validate(await get_or_404(session, user, meeting_id))


@router.patch("/{meeting_id}", response_model=MeetingRead)
async def update_meeting(
    meeting_id: uuid.UUID, payload: MeetingUpdate, session: SessionDep, user: CurrentUser
):
    meeting = await get_or_404(session, user, meeting_id)
    return MeetingRead.model_validate(await service.update_meeting(session, meeting, payload))


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(meeting_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    await service.delete_meeting(session, await get_or_404(session, user, meeting_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{meeting_id}/agenda", response_model=MeetingRead)
async def save_agenda(
    meeting_id: uuid.UUID, payload: AgendaSave, session: SessionDep, user: CurrentUser
):
    meeting = await get_or_404(session, user, meeting_id)
    meeting.agenda = payload.agenda.model_dump(mode="json")
    meeting.ai_suggestion = (
        payload.ai_suggestion.model_dump(mode="json") if payload.ai_suggestion else None
    )
    await session.flush()
    await session.refresh(meeting)
    return MeetingRead.model_validate(meeting)
