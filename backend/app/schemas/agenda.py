from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgendaItem(StrictModel):
    topic: str = Field(min_length=1, max_length=1000)
    owner: str | None = Field(default=None, max_length=320)
    minutes: int | None = Field(default=None, ge=1, le=480, strict=True)


class ActionItem(StrictModel):
    task: str = Field(min_length=1, max_length=2000)
    owner: str | None = Field(default=None, max_length=320)
    due: date | None = None


class ParsedAgenda(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    starts_at: str | None = Field(default=None, max_length=50)
    duration_minutes: int | None = Field(default=None, ge=1, le=600, strict=True)
    items: list[AgendaItem] = Field(max_length=50)
    action_items: list[ActionItem] = Field(default_factory=list, max_length=50)
    language: str = Field(min_length=2, max_length=10, pattern=r"^[a-z]{2,3}(-[A-Za-z]+)?$")

    @field_validator("starts_at")
    @classmethod
    def offset_required(cls, value):
        if value is not None:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError("starts_at must include a UTC offset")
        return value


class AISuggestion(StrictModel):
    agenda: ParsedAgenda
    model: str = Field(min_length=1, max_length=200)
    prompt_version: str = Field(min_length=1, max_length=100)


class AgendaSave(StrictModel):
    agenda: ParsedAgenda
    ai_suggestion: AISuggestion | None = None
