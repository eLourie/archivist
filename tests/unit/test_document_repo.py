import pytest
from datetime import datetime, timezone, timedelta

from app.repositories.document_repo import DocumentRepository
from tests.factories import make_document


@pytest.mark.asyncio
async def test_get_by_id_returns_document(db_session):
    doc = make_document(text="Hello world")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    repo = DocumentRepository(db_session)
    result = await repo.get_by_id(doc.id)

    assert result is not None
    assert result.id == doc.id
    assert result.text == "Hello world"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing(db_session):
    repo = DocumentRepository(db_session)
    result = await repo.get_by_id(99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_ids_ordered_by_date(db_session):
    now = datetime.now(tz=timezone.utc)
    older = make_document(text="Older", created_date=now - timedelta(days=2))
    newer = make_document(text="Newer", created_date=now)
    db_session.add_all([older, newer])
    await db_session.commit()
    await db_session.refresh(older)
    await db_session.refresh(newer)

    repo = DocumentRepository(db_session)
    results = await repo.get_by_ids_ordered_by_date([older.id, newer.id])

    assert len(results) == 2
    assert results[0].id == newer.id


@pytest.mark.asyncio
async def test_delete_by_id_removes_document(db_session):
    doc = make_document()
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    repo = DocumentRepository(db_session)
    deleted = await repo.delete_by_id(doc.id)

    assert deleted is True
    assert await repo.get_by_id(doc.id) is None


@pytest.mark.asyncio
async def test_delete_by_id_returns_false_for_missing(db_session):
    repo = DocumentRepository(db_session)
    deleted = await repo.delete_by_id(99999)
    assert deleted is False


@pytest.mark.asyncio
async def test_get_by_ids_returns_empty_for_empty_list(db_session):
    repo = DocumentRepository(db_session)
    results = await repo.get_by_ids_ordered_by_date([])
    assert results == []
