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
async def test_summary_approved_only_totals(client: AsyncClient):
    """total_approved_amount should only sum approved events."""
    events = [
        make_event("E1", amount=100.0, status="approved"),
        make_event("E2", amount=200.0, status="approved"),
        make_event("E3", amount=50.0, status="pending"),
        make_event("E4", amount=75.0, status="rejected"),
    ]
    await client.post("/transfers", json={"events": events})

    resp = await client.get("/stations/S1/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_approved_amount"] == 300.0
    assert data["events_count"] == 4


@pytest.mark.asyncio
async def test_summary_per_station(client: AsyncClient):
    """Each station should have its own independent summary."""
    events = [
        make_event("E1", station_id="S1", amount=100.0),
        make_event("E2", station_id="S2", amount=200.0),
        make_event("E3", station_id="S1", amount=50.0),
    ]
    await client.post("/transfers", json={"events": events})

    resp_s1 = await client.get("/stations/S1/summary")
    assert resp_s1.json()["total_approved_amount"] == 150.0
    assert resp_s1.json()["events_count"] == 2

    resp_s2 = await client.get("/stations/S2/summary")
    assert resp_s2.json()["total_approved_amount"] == 200.0
    assert resp_s2.json()["events_count"] == 1


@pytest.mark.asyncio
async def test_summary_station_not_found(client: AsyncClient):
    """Summary for a non-existent station should return 404."""
    resp = await client.get("/stations/UNKNOWN/summary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_does_not_change_totals(client: AsyncClient):
    """Re-submitting the same event should not alter the summary."""
    event = make_event("E1", amount=100.0)
    await client.post("/transfers", json={"events": [event]})

    resp1 = await client.get("/stations/S1/summary")
    assert resp1.json()["total_approved_amount"] == 100.0
    assert resp1.json()["events_count"] == 1

    # Submit same event again
    await client.post("/transfers", json={"events": [event]})

    resp2 = await client.get("/stations/S1/summary")
    assert resp2.json()["total_approved_amount"] == 100.0
    assert resp2.json()["events_count"] == 1


@pytest.mark.asyncio
async def test_out_of_order_arrival_same_totals(client: AsyncClient):
    """Events arriving in different order should produce the same summary."""
    events_batch1 = [
        make_event("E3", amount=50.0, created_at="2026-02-19T12:00:00Z"),
        make_event("E1", amount=100.0, created_at="2026-02-19T10:00:00Z"),
    ]
    events_batch2 = [
        make_event("E2", amount=200.0, created_at="2026-02-19T11:00:00Z"),
    ]

    await client.post("/transfers", json={"events": events_batch1})
    await client.post("/transfers", json={"events": events_batch2})

    resp = await client.get("/stations/S1/summary")
    data = resp.json()
    assert data["total_approved_amount"] == 350.0
    assert data["events_count"] == 3