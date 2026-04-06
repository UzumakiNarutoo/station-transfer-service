from dataclasses import dataclass
from typing import Protocol

from app.models.domain import TransferEventInput


@dataclass
class InsertResult:
    """Result of a batch insert operation."""

    inserted: int = 0
    duplicates: int = 0


@dataclass
class StationSummary:
    """Aggregated summary for a station."""

    station_id: str
    total_approved_amount: float
    events_count: int


class TransferStore(Protocol):
    """Interface for transfer event storage. Implementations must be concurrency-safe."""

    async def insert_events(self, events: list[TransferEventInput]) -> InsertResult:
        """Insert events, skipping duplicates by event_id. Returns insert/duplicate counts."""
        ...

    async def get_station_summary(self, station_id: str) -> StationSummary | None:
        """Return aggregated summary for a station, or None if station has no events."""
        ...