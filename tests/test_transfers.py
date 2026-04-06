import pytest
from httpx import AsyncClient


def make_event(event_id="E1", station_id="S1", amount=100.0, status="approved", created_at="2026-02-19T10:00:00Z"):
    return {
        "event_id": event_id,
        "station_id": station_id,
        "amount": amount,
        "status": status,
        "created_at": created_at,
    }


@pytest.mark.asyncio
async def test_batch_insert_returns_correct_counts(client: AsyncClient):
    """Batch insert should return correct inserted and duplicates counts."""
    events = [make_event(event_id=f"E{i}") for i in range(5)]
    resp = await client.post("/transfers", json={"events": events})

    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 5
    assert data["duplicates"] == 0
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_duplicate_events_are_counted(client: AsyncClient):
    """Submitting the same events twice should count duplicates correctly."""
    events = [make_event(event_id="E1"), make_event(event_id="E2")]

    resp1 = await client.post("/transfers", json={"events": events})
    assert resp1.json()["inserted"] == 2

    resp2 = await client.post("/transfers", json={"events": events})
    data = resp2.json()
    assert data["inserted"] == 0
    assert data["duplicates"] == 2


@pytest.mark.asyncio
async def test_partial_accept_valid_and_invalid(client: AsyncClient):
    """Valid events are inserted, invalid ones reported in errors (partial accept)."""
    events = [
        make_event(event_id="E1", amount=50.0),
        {"event_id": "E2", "station_id": "S1", "amount": -10, "status": "approved", "created_at": "2026-02-19T10:00:00Z"},
        {"event_id": "E3", "station_id": "S1", "amount": 30.0, "status": "approved", "created_at": "not-a-date"},
    ]
    resp = await client.post("/transfers", json={"events": events})

    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 1
    assert data["duplicates"] == 0
    assert len(data["errors"]) == 2


@pytest.mark.asyncio
async def test_missing_required_fields(client: AsyncClient):
    """Events missing required fields should be reported as errors."""
    events = [
        {"station_id": "S1", "amount": 10, "status": "approved", "created_at": "2026-02-19T10:00:00Z"},  # missing event_id
    ]
    resp = await client.post("/transfers", json={"events": events})

    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 0
    assert len(data["errors"]) == 1


@pytest.mark.asyncio
async def test_malformed_body_returns_400(client: AsyncClient):
    """Completely invalid JSON structure should return 400."""
    resp = await client.post("/transfers", content="not json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_missing_events_key_returns_400(client: AsyncClient):
    """Body without 'events' key should return 400."""
    resp = await client.post("/transfers", json={"data": []})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_empty_batch_returns_zeros(client: AsyncClient):
    """An empty events list should return all zeros."""
    resp = await client.post("/transfers", json={"events": []})

    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted"] == 0
    assert data["duplicates"] == 0
    assert data["errors"] == []