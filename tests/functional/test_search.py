import pytest
from httpx import AsyncClient

from tests.factories import make_document


@pytest.mark.asyncio
async def test_search_returns_200(client: AsyncClient, db_session, mock_es):
    doc = make_document(text="Арктика климатические изменения")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    # Mock ES to return this document's id
    mock_es.search.return_value = {
        "hits": {"hits": [{"_source": {"id": doc.id, "text": doc.text}}]}
    }

    response = await client.post(
        "/api/v1/documents/search",
        json={"query": "Арктика"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["documents"][0]["id"] == doc.id
    assert data["documents"][0]["text"] == doc.text


@pytest.mark.asyncio
async def test_search_empty_result(client: AsyncClient, mock_es):
    mock_es.search.return_value = {"hits": {"hits": []}}

    response = await client.post(
        "/api/v1/documents/search",
        json={"query": "несуществующий запрос"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["documents"] == []


@pytest.mark.asyncio
async def test_search_returns_max_20_documents(client: AsyncClient, db_session, mock_es):
    docs = [make_document(text=f"Document number {i}") for i in range(25)]
    db_session.add_all(docs)
    await db_session.commit()
    for doc in docs:
        await db_session.refresh(doc)

    # ES mock returns 20 ids (service asks for 20 max)
    mock_es.search.return_value = {
        "hits": {
            "hits": [{"_source": {"id": doc.id, "text": doc.text}} for doc in docs[:20]]
        }
    }

    response = await client.post(
        "/api/v1/documents/search",
        json={"query": "Document"},
    )

    assert response.status_code == 200
    assert response.json()["total"] <= 20


@pytest.mark.asyncio
async def test_search_validates_empty_query(client: AsyncClient):
    response = await client.post(
        "/api/v1/documents/search",
        json={"query": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_validates_missing_query(client: AsyncClient):
    response = await client.post("/api/v1/documents/search", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_response_has_required_fields(client: AsyncClient, db_session, mock_es):
    doc = make_document(text="Проверка полей ответа", rubrics=["тест"])
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    mock_es.search.return_value = {
        "hits": {"hits": [{"_source": {"id": doc.id, "text": doc.text}}]}
    }

    response = await client.post(
        "/api/v1/documents/search",
        json={"query": "Проверка"},
    )

    assert response.status_code == 200
    document = response.json()["documents"][0]
    assert "id" in document
    assert "rubrics" in document
    assert "text" in document
    assert "created_date" in document