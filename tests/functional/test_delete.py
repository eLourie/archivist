import pytest
from httpx import AsyncClient

from tests.factories import make_document


@pytest.mark.asyncio
async def test_delete_existing_document(client: AsyncClient, db_session, mock_es):
    doc = make_document(text="Документ для удаления")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    response = await client.delete(f"/api/v1/documents/{doc.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc.id
    assert data["message"] == "Document successfully deleted."


@pytest.mark.asyncio
async def test_delete_nonexistent_document_returns_404(client: AsyncClient):
    response = await client.delete("/api/v1/documents/99999")
    assert response.status_code == 404
    assert "99999" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_calls_es_delete(client: AsyncClient, db_session, mock_es):
    doc = make_document(text="ES удаление")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    await client.delete(f"/api/v1/documents/{doc.id}")

    mock_es.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_twice_returns_404_second_time(
    client: AsyncClient, db_session, mock_es
):
    doc = make_document(text="Двойное удаление")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    first = await client.delete(f"/api/v1/documents/{doc.id}")
    assert first.status_code == 200

    second = await client.delete(f"/api/v1/documents/{doc.id}")
    assert second.status_code == 404