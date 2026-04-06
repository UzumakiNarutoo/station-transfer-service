import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models.domain import (
    EventError,
    StationSummaryResponse,
    TransferBatchResponse,
    TransferEventInput,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transfers", response_model=TransferBatchResponse)
async def ingest_transfers(request: Request) -> TransferBatchResponse | JSONResponse:
    """Ingest a batch of transfer events with partial-accept validation."""
    # Parse raw JSON — reject malformed bodies with 400
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})

    if not isinstance(body, dict) or "events" not in body:
        return JSONResponse(status_code=400, content={"detail": "Missing required field: events"})

    raw_events = body["events"]
    if not isinstance(raw_events, list):
        return JSONResponse(status_code=400, content={"detail": "'events' must be a list"})

    # Validate each event individually (partial-accept)
    valid_events: list[TransferEventInput] = []
    errors: list[EventError] = []

    for raw in raw_events:
        try:
            event = TransferEventInput.model_validate(raw)
            valid_events.append(event)
        except ValidationError as e:
            event_id = raw.get("event_id") if isinstance(raw, dict) else None
            msg = "; ".join(err["msg"] for err in e.errors())
            errors.append(EventError(event_id=event_id, error=msg))

    # Insert valid events into the store
    store = request.app.state.store
    result = await store.insert_events(valid_events)

    return TransferBatchResponse(
        inserted=result.inserted,
        duplicates=result.duplicates,
        errors=errors,
    )


@router.get("/stations/{station_id}/summary", response_model=StationSummaryResponse)
async def get_station_summary(station_id: str, request: Request) -> StationSummaryResponse | JSONResponse:
    """Return reconciliation summary for a station."""
    store = request.app.state.store
    summary = await store.get_station_summary(station_id)

    if summary is None:
        return JSONResponse(status_code=404, content={"detail": f"No events found for station '{station_id}'"})

    return StationSummaryResponse(
        station_id=summary.station_id,
        total_approved_amount=summary.total_approved_amount,
        events_count=summary.events_count,
    )