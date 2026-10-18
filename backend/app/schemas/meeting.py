import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.agenda import AISuggestion, ParsedAgenda


class MeetingFields(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    location: str | None = Field(default=None, max_length=1000)
    purpose: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("Meeting times must include a timezone")
        if self.end_at <= self.start_at:
            raise ValueError("End time must be later than start time")
        return self


class MeetingCreate(MeetingFields):
    pass


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    location: str | None = Field(default=None, max_length=1000)
    purpose: str | None = Field(default=None, max_length=5000)


class MeetingRead(MeetingFields):
    agenda: ParsedAgenda | None = None
    ai_suggestion: AISuggestion | None = None
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MeetingList(BaseModel):
    meetings: list[MeetingRead]
    total: int
