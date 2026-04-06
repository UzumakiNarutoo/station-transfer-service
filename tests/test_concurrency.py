import asyncio

import pytest
from httpx import AsyncClient


def make_event(event_id, station_id="S1", amount=100.0, status="approved", created_at="2026-02-19T10:00:00Z"):
    return {
        "event_id": event_id,
        "station_id": station_id,
        "amount": amount,
        "status": status,
        "created_at": created_at,
    }


@pytest.mark.asyncio
async def test_concurrent_same_event_id_no_double_insert(client: AsyncClient):
    """Concurrent POSTs with the same event_id must not double-insert."""
    event = make_event("CONCURRENT-1", amount=100.0)

    # Fire 10 concurrent requests all trying to insert the same event
    tasks = [
        client.post("/transfers", json={"events": [event]})
        for _ in range(10)
    ]
    responses = await asyncio.gather(*tasks)

    total_inserted = sum(r.json()["inserted"] for r in responses)
    total_duplicates = sum(r.json()["duplicates"] for r in responses)

    assert total_inserted == 1
    assert total_duplicates == 9

    # Verify summary reflects exactly one event
    resp = await client.get("/stations/S1/summary")
    data = resp.json()
    assert data["total_approved_amount"] == 100.0
    assert data["events_count"] == 1


@pytest.mark.asyncio
async def test_concurrent_different_events_all_inserted(client: AsyncClient):
    """Concurrent POSTs with different event_ids should all insert."""
    tasks = [
        client.post("/transfers", json={"events": [make_event(f"C-{i}", amount=10.0)]})
        for i in range(20)
    ]
    responses = await asyncio.gather(*tasks)

    total_inserted = sum(r.json()["inserted"] for r in responses)
    assert total_inserted == 20

    resp = await client.get("/stations/S1/summary")
    data = resp.json()
    assert data["total_approved_amount"] == 200.0
    assert data["events_count"] == 20


@pytest.mark.asyncio
async def test_concurrent_overlapping_batches(client: AsyncClient):
    """Concurrent batches with overlapping event_ids should not double-count."""
    batch1 = [make_event("O-1", amount=10.0), make_event("O-2", amount=20.0)]
    batch2 = [make_event("O-2", amount=20.0), make_event("O-3", amount=30.0)]
    batch3 = [make_event("O-1", amount=10.0), make_event("O-3", amount=30.0)]

    tasks = [
        client.post("/transfers", json={"events": batch1}),
        client.post("/transfers", json={"events": batch2}),
        client.post("/transfers", json={"events": batch3}),
    ]
    responses = await asyncio.gather(*tasks)

    total_inserted = sum(r.json()["inserted"] for r in responses)
    total_duplicates = sum(r.json()["duplicates"] for r in responses)

    # 3 unique events across all batches (6 total submissions)
    assert total_inserted == 3
    assert total_duplicates == 3

    resp = await client.get("/stations/S1/summary")
    data = resp.json()
    assert data["total_approved_amount"] == 60.0
    assert data["events_count"] == 3