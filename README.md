# Document Search Service

Full-text document search powered by **FastAPI**, **PostgreSQL**, and **Elasticsearch**.

## Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.115 + Uvicorn |
| Database | PostgreSQL 16 (async via asyncpg + SQLAlchemy 2) |
| Search index | Elasticsearch 8.16 |
| Containerisation | Docker + Docker Compose |
| Tests | pytest + pytest-asyncio + httpx |

---

## Quick start (Docker — recommended)

### 1. Clone and configure

```bash
git clone <repo-url>
cd document_search
cp .env.example .env
```

### 2. Start all services

```bash
docker compose up --build -d
```

This starts three containers:

- `document_search_app` — FastAPI on **http://localhost:8000**
- `document_search_postgres` — PostgreSQL on port 5432
- `document_search_es` — Elasticsearch on port 9200

The app waits for both dependencies to pass their health checks before starting.

### 3. Load test data

Put the CSV file somewhere accessible (e.g. `data/test_data.csv`) and run:

```bash
docker compose exec app python scripts/load_data.py --file data/test_data.csv
```

Or locally (see "Local setup" below):

```bash
python scripts/load_data.py --file data/test_data.csv
```

### 4. Verify

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok", "elasticsearch": "ok"}
```

---

## Local setup (without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL 16 running locally
- Elasticsearch 8.x running locally on port 9200

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env — set POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD etc.
```

### Run

```bash
uvicorn app.main:app --reload
```

---

## API Reference

Interactive docs are available at:

| URL | Format |
|---|---|
| http://localhost:8000/api/v1/docs | Swagger UI |
| http://localhost:8000/api/v1/redoc | ReDoc |
| http://localhost:8000/api/v1/openapi.json | Raw OpenAPI JSON |

A static copy is saved in `docs.json`.

### Endpoints

#### `POST /api/v1/documents/search`

Full-text search. Returns up to 20 documents ordered by `created_date` DESC.

**Request body:**
```json
{
  "query": "климатические изменения арктика"
}
```

**Response:**
```json
{
  "total": 3,
  "documents": [
    {
      "id": 42,
      "rubrics": ["Наука", "Экология"],
      "text": "Арктика нагревается в четыре раза быстрее...",
      "created_date": "2024-03-15T10:20:00+00:00"
    }
  ]
}
```

---

#### `DELETE /api/v1/documents/{id}`

Delete a document from PostgreSQL and the Elasticsearch index.

**Response:**
```json
{
  "id": 42,
  "message": "Document successfully deleted."
}
```

Returns `404` if the document does not exist.

---

#### `GET /api/v1/health`

Service health check. Returns Elasticsearch connectivity status.

---

## Running tests

```bash
# Install test deps if not already done
pip install -r requirements.txt

# Run all tests
pytest -v

# Run only functional tests
pytest tests/functional/ -v

# Run only unit tests
pytest tests/unit/ -v

# With coverage report
pytest --cov=app --cov-report=term-missing
```

Tests use an **in-memory SQLite** database and a **mocked Elasticsearch** client — no external services required.

---

## Project structure

```
document_search/
├── app/
│   ├── api/v1/
│   │   ├── documents.py      # Search and delete endpoints
│   │   ├── health.py         # Health check endpoint
│   │   └── router.py         # Router aggregator
│   ├── core/
│   │   ├── config.py          # Settings (pydantic-settings + .env)
│   │   ├── exceptions.py      # Domain exceptions
│   │   ├── lifespan.py        # Startup / shutdown hooks
│   │   └── logging_config.py  # Logging configuration
│   ├── db/
│   │   ├── postgres.py             # Async engine, session factory, Base
│   │   └── elasticsearch_client.py # ES client + index mapping
│   ├── models/
│   │   ├── document_model.py # SQLAlchemy Document model
│   │   └── types.py          # Cross-dialect StringArray column type
│   ├── repositories/
│   │   ├── document_repo.py  # PostgreSQL queries
│   │   └── search_repo.py    # Elasticsearch queries
│   ├── schemas/
│   │   └── document_schemas.py  # Pydantic request/response models
│   ├── services/
│   │   └── document_service.py  # Business logic
│   └── main.py               # App factory
├── scripts/
│   └── load_data.py          # CSV → PostgreSQL + Elasticsearch loader
├── tests/
│   ├── conftest.py           # Fixtures (test DB, mock ES, HTTP client)
│   ├── factories.py          # Test data builders
│   ├── functional/           # End-to-end endpoint tests
│   └── unit/                 # Repository unit tests
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── docs.json                 # OpenAPI spec (static copy)
├── pyproject.toml
└── requirements.txt
```

---

## Design decisions

- **Repository pattern** — DB and ES access is separated into `DocumentRepository` and `SearchRepository`. The service layer orchestrates both without knowing their internals.
- **Delete consistency** — DB is deleted first. If the DB delete fails, ES is left untouched. If ES delete fails after a successful DB delete, it is logged as a warning (ES can be re-indexed; the source of truth is PostgreSQL).
- **Russian language support** — The Elasticsearch index uses a custom analyser with `russian_stop` and `russian_stemmer` filters for better search quality on Russian-language documents.
- **Async-first** — All I/O (DB queries, ES calls) uses `async/await`. The app can handle many concurrent requests on a single process.