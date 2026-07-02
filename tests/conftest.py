"""
Shared pytest fixtures.

Functional tests use an in-process FastAPI test client (httpx + anyio) backed by:
  - A real PostgreSQL test database (or SQLite for CI speed)
  - A mocked Elasticsearch client

Run with:  pytest -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, MagicMock

from app.db.postgres import Base, get_db_session
from app.db.elasticsearch_client import es_client as real_es_client
from app.main import app
from app.models.document_model import Document
from tests.factories import make_document



# Database fixtures

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()



# Elasticsearch mock

@pytest.fixture
def mock_es():
    mock = AsyncMock()
    mock.search.return_value = {"hits": {"hits": []}}
    mock.index.return_value = {"result": "created"}
    mock.delete.return_value = {"result": "deleted"}
    mock.bulk.return_value = {"errors": False, "items": []}
    mock.ping.return_value = True
    return mock



# HTTP client fixture

@pytest_asyncio.fixture
async def client(db_session, mock_es, monkeypatch):
    """
    Fully wired async test client:
    - Overrides DB session with the in-memory SQLite session
    - Patches the ES client used by SearchRepository
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    monkeypatch.setattr("app.repositories.search_repo.AsyncElasticsearch", lambda **kw: mock_es)
    monkeypatch.setattr("app.services.document_service.es_client", mock_es)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()



# Data helpers

@pytest_asyncio.fixture
async def sample_document(db_session) -> Document:
    doc = make_document(text="Арктика климатические изменения")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc