# Station Transfer Service

A microservice that ingests station transfer events and exposes per-station reconciliation summaries. Built with idempotency and concurrency safety as first-class concerns.

## Tech Stack

- **Language**: Python 3.12
- **Framework**: FastAPI
- **Database**: SQLite (via SQLAlchemy async + aiosqlite)
- **Validation**: Pydantic v2
- **Testing**: pytest + httpx
- **Dependency Management**: uv
- **Containerization**: Docker + Docker Compose

## Prerequisites

### Local

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Docker

- Docker
- Docker Compose

## Getting Started

### Local

```bash
# Install dependencies
make install

# Run the server (http://localhost:8000)
make run

# Run tests
make test
```

### Docker

```bash
# Build and run
docker compose up --build

# Run tests
docker compose run --rm app test
```

## API Reference

### POST /transfers

Ingest a batch of transfer events.

**Request:**

```bash
curl -X POST http://localhost:8000/transfers \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_id": "E1",
        "station_id": "S1",
        "amount": 100.50,
        "status": "approved",
        "created_at": "2026-02-19T10:00:00Z"
      },
      {
        "event_id": "E2",
        "station_id": "S1",
        "amount": 200.00,
        "status": "pending",
        "created_at": "2026-02-19T11:00:00Z"
      }
    ]
  }'
```

**Response (200):**

```json
{
  "inserted": 2,
  "duplicates": 0,
  "errors": []
}
```

Submitting the same batch again:

```json
{
  "inserted": 0,
  "duplicates": 2,
  "errors": []
}
```

**Response with validation errors (200 — partial accept):**

```json
{
  "inserted": 1,
  "duplicates": 0,
  "errors": [
    {
      "event_id": "E3",
      "error": "amount must be a non-negative number"
    }
  ]
}
```

**Response (400):** Malformed request body (not valid JSON or missing `events` key).

### GET /stations/{station_id}/summary

Get reconciliation summary for a station.

**Request:**

```bash
curl http://localhost:8000/stations/S1/summary
```

**Response (200):**

```json
{
  "station_id": "S1",
  "total_approved_amount": 100.50,
  "events_count": 2
}
```

**Response (404):** Station has no events.

## Design Notes

### Idempotency Strategy

Every event has a globally unique `event_id`. The database enforces a **unique constraint** on `event_id`. When a batch is ingested, each event is inserted individually within a transaction. If an `IntegrityError` is raised (duplicate `event_id`), the event is silently skipped and counted as a duplicate. The first write wins — subsequent submissions of the same `event_id` are discarded regardless of payload differences.

### Concurrency Strategy

Concurrency safety is achieved through **SQLite's unique constraint + transactional inserts**:

- Each event insert is attempted inside a transaction.
- If two concurrent requests try to insert the same `event_id`, the database's unique constraint guarantees exactly one succeeds. The other receives an `IntegrityError` and counts it as a duplicate.
- SQLite is configured with **WAL (Write-Ahead Logging)** mode, which allows concurrent readers while a write is in progress.

This approach mirrors how a production PostgreSQL setup would work — the database is the single source of truth for uniqueness, not application-level locking.

### Batch Validation: Partial Accept

This service uses a **partial-accept** strategy:

- Each event in the batch is validated independently.
- Valid events are inserted; invalid events are skipped and reported in the `errors` array.
- This ensures one malformed event doesn't block the rest of the batch.
- If the request body itself is malformed (e.g., not valid JSON), the entire request is rejected with a 400.

### `events_count` Definition

`events_count` counts **all stored events** for a station regardless of status. This includes approved, pending, rejected, and any unknown statuses. Only `total_approved_amount` filters by `status == "approved"`.

### Store Abstraction

The storage layer is defined as a Python `Protocol` class (`TransferStore`), making the implementation swappable. The current implementation uses SQLite, but it can be replaced with PostgreSQL, DynamoDB, or any other backend by implementing the same interface.

### Tradeoffs

- **SQLite vs. PostgreSQL**: SQLite is chosen for simplicity and zero-config setup. It handles the concurrency requirements of this assignment well with WAL mode. For production with high write throughput, PostgreSQL would be the better choice due to its superior concurrency model.
- **Partial-accept vs. fail-fast**: Partial-accept adds slight response complexity (the `errors` array) but is more practical — a single bad event in a batch of thousands shouldn't invalidate the entire submission.
- **On-demand aggregation vs. pre-computed summaries**: Summaries are computed on every request via a SQL aggregation query. This is simple and always consistent. For production at large scale, a hybrid approach could be used: maintain a pre-aggregated summary table updated periodically (e.g., via a background job every N minutes), and at query time merge the pre-aggregated snapshot with a live delta query over only the recently ingested events. This reduces read latency while preserving correctness.

## Project Structure

```
station-transfer-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, logging setup
│   ├── config.py            # Application settings
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoint handlers
│   ├── models/
│   │   ├── __init__.py
│   │   ├── domain.py        # Pydantic request/response schemas
│   │   └── db.py            # SQLAlchemy ORM model
│   └── store/
│       ├── __init__.py
│       ├── protocol.py      # TransferStore Protocol (interface)
│       └── sqlite.py        # SQLite implementation
├── tests/
│   ├── conftest.py          # Test fixtures
│   ├── test_transfers.py    # POST /transfers tests
│   ├── test_summary.py      # GET /stations/{id}/summary tests
│   └── test_concurrency.py  # Concurrent ingestion tests
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── openapi.json
└── README.md
```
