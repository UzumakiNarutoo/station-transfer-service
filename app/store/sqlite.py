import logging

from sqlalchemy import case, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.db import TransferEvent
from app.models.domain import TransferEventInput
from app.store.protocol import InsertResult, StationSummary

logger = logging.getLogger(__name__)


class SQLiteTransferStore:
    """SQLite-backed implementation of TransferStore."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def insert_events(self, events: list[TransferEventInput]) -> InsertResult:
        """Batch insert using INSERT ... ON CONFLICT DO NOTHING."""
        if not events:
            return InsertResult()

        rows = [
            {
                "event_id": e.event_id,
                "station_id": e.station_id,
                "amount": e.amount,
                "status": e.status,
                "created_at": e.created_at,
            }
            for e in events
        ]

        async with self._session_factory() as session:
            stmt = insert(TransferEvent).values(rows).on_conflict_do_nothing(index_elements=["event_id"])
            result = await session.execute(stmt)
            await session.commit()

            inserted = result.rowcount
            duplicates = len(events) - inserted

            logger.debug("Batch insert: %d inserted, %d duplicates", inserted, duplicates)
            return InsertResult(inserted=inserted, duplicates=duplicates)

    async def get_station_summary(self, station_id: str) -> StationSummary | None:
        """Aggregate summary: count all events, sum only approved amounts."""
        async with self._session_factory() as session:
            query = select(
                func.count().label("events_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (TransferEvent.status == "approved", TransferEvent.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("total_approved_amount"),
            ).where(TransferEvent.station_id == station_id)

            result = await session.execute(query)
            row = result.one()

            if row.events_count == 0:
                return None

            return StationSummary(
                station_id=station_id,
                total_approved_amount=round(float(row.total_approved_amount), 2),
                events_count=row.events_count,
            )