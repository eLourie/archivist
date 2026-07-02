# Archivist

Full-text document search service powered by **FastAPI**, **PostgreSQL**, and **Elasticsearch**.

## Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.115 + Uvicorn |
| Database | PostgreSQL 16 (async via asyncpg + SQLAlchemy 2) |
| Search index | Elasticsearch 8.16 |
| Containerisation | Docker + Docker Compose |
| Tests | pytest + pytest-asyncio + httpx |

---

## Quickstart with Docker

### 1. Clone the repository

```bash
git clone https://github.com/eLourie/archivist.git
cd archivist
```

### 2. Create the environment file

```bash
cp .env.example .env
```

The default values work out of the box — no changes needed.

### 3. Start all services

```bash
docker compose up --build -d
```

This builds and starts three containers:

| Container | Description | Port |
|---|---|---|
| `document_search_app` | FastAPI application | 8000 |
| `document_search_postgres` | PostgreSQL database | 5432 |
| `document_search_es` | Elasticsearch search index | 9200 |

The app waits for both PostgreSQL and Elasticsearch to pass their health checks before starting. On first run this can take up to 60 seconds.

### 4. Check the service is up

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{"status": "ok", "elasticsearch": "ok"}
```

### 5. Load data

The sample dataset is already included in `data/posts.csv`. Copy it into the running container and run the loader:

```bash
docker compose cp data/posts.csv app:/app/data/posts.csv
docker compose exec app python scripts/load_data.py --file data/posts.csv
```

Expected output:

```
INFO - Loaded 1500 rows from data/posts.csv
INFO - Processed batch 500/1500
INFO - Processed batch 1000/1500
INFO - Processed batch 1500/1500
INFO - Done. 1500 documents indexed.
```

The loader writes every document to PostgreSQL and simultaneously indexes its text in Elasticsearch.

### 6. Verify search is working

```bash
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "россия"}'
```

---

## API Reference

Interactive documentation is available at:

| URL | Format |
|---|---|
| http://localhost:8000/api/v1/docs | Swagger UI |
| http://localhost:8000/api/v1/redoc | ReDoc |
| http://localhost:8000/api/v1/openapi.json | Raw OpenAPI JSON |

A static copy of the OpenAPI spec is saved in `docs.json`.

### `POST /api/v1/documents/search`

Full-text search over all documents. Returns up to 20 results ordered by `created_date` DESC.

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

### `DELETE /api/v1/documents/{id}`

Permanently removes a document from PostgreSQL and the Elasticsearch index.

**Response:**
```json
{
  "id": 42,
  "message": "Document successfully deleted."
}
```

Returns `404` if the document does not exist.

### `GET /api/v1/health`

Returns service status and Elasticsearch connectivity.

**Response:**
```json
{"status": "ok", "elasticsearch": "ok"}
```

---

## Running tests

Tests run locally without Docker — they use an in-memory SQLite database and a mocked Elasticsearch client so no external services are required.

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run all tests
PYTHONPATH=. pytest -v

# Run only functional tests
PYTHONPATH=. pytest tests/functional/ -v

# Run only unit tests
PYTHONPATH=. pytest tests/unit/ -v

# Run with coverage report
PYTHONPATH=. pytest --cov=app --cov-report=term-missing
```

Expected result: **17 passed**.

---

## Project structure

```
archivist/
├── app/
│   ├── api/v1/
│   │   ├── documents.py          # Search and delete endpoints
│   │   ├── health.py             # Health check endpoint
│   │   └── router.py             # Router aggregator
│   ├── core/
│   │   ├── config.py             # Settings via pydantic-settings + .env
│   │   ├── exceptions.py         # Domain exceptions
│   │   ├── lifespan.py           # Startup / shutdown hooks
│   │   └── logging_config.py     # Logging configuration
│   ├── db/
│   │   ├── postgres.py           # Async engine, session factory, Base
│   │   └── elasticsearch_client.py  # ES client + index mapping
│   ├── models/
│   │   ├── document_model.py     # SQLAlchemy Document model
│   │   └── types.py              # Cross-dialect StringArray column type
│   ├── repositories/
│   │   ├── document_repo.py      # PostgreSQL queries
│   │   └── search_repo.py        # Elasticsearch queries
│   ├── schemas/
│   │   └── document_schemas.py   # Pydantic request/response models
│   ├── services/
│   │   └── document_service.py   # Business logic
│   └── main.py                   # FastAPI app factory
├── data/
│   └── posts.csv                 # Sample dataset (1500 documents)
├── scripts/
│   └── load_data.py              # CSV → PostgreSQL + Elasticsearch loader
├── tests/
│   ├── conftest.py               # Fixtures: test DB, mock ES, HTTP client
│   ├── factories.py              # Test data builders
│   ├── functional/               # End-to-end endpoint tests
│   └── unit/                     # Repository unit tests
├── .env.example                  # Environment variable template
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── docs.json                     # OpenAPI spec (static copy)
├── pyproject.toml                # pytest + ruff configuration
└── requirements.txt
```

---

## Design decisions

**Repository pattern** — database and Elasticsearch access is separated into `DocumentRepository` and `SearchRepository`. The service layer orchestrates both without knowing their internals, making each layer independently testable.

**Delete consistency** — the document is deleted from PostgreSQL first. If that fails, Elasticsearch is left untouched. If the ES delete fails after a successful DB delete, it is logged as a warning — PostgreSQL is the source of truth, Elasticsearch can always be re-indexed from it.

**Russian language support** — the Elasticsearch index is configured with a custom analyser using `russian_stop` and `russian_stemmer` filters, which significantly improves search quality for Russian-language documents compared to the default analyser.

**Async-first** — all I/O (database queries, Elasticsearch calls) uses `async/await` throughout. The service can handle many concurrent requests on a single process without blocking.

**Cross-dialect column type** — the `rubrics` field uses a custom `StringArray` type that maps to native `ARRAY(Text)` on PostgreSQL and falls back to `JSON` on SQLite. This allows the test suite to run against a fast in-memory database without requiring a real PostgreSQL instance.