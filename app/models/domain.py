from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class TransferEventInput(BaseModel):
    """Single event in a batch request."""

    event_id: str
    station_id: str
    amount: float = Field(ge=0)
    status: str
    created_at: datetime

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("event_id", "station_id", "status")
    @classmethod
    def must_be_non_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v


class TransferBatchRequest(BaseModel):
    """POST /transfers request body."""

    events: list[TransferEventInput]


class EventError(BaseModel):
    """Validation error for a single event."""

    event_id: str | None = None
    error: str


class TransferBatchResponse(BaseModel):
    """POST /transfers response."""

    inserted: int = 0
    duplicates: int = 0
    errors: list[EventError] = []


class StationSummaryResponse(BaseModel):
    """GET /stations/{station_id}/summary response."""

    station_id: str
    total_approved_amount: float
    events_count: int