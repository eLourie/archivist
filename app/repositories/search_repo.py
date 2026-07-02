import logging

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchRepository:
    """All Elasticsearch operations."""

    def __init__(self, client: AsyncElasticsearch) -> None:
        self._client = client
        self._index = settings.ELASTICSEARCH_INDEX

    async def search(self, query: str, limit: int = 20) -> list[int]:
        """
        Full-text search. Returns a list of document ids (up to `limit`).
        Uses multi_match to search across the text field with BM25 ranking.
        """
        body = {
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
        }
        response = await self._client.search(index=self._index, body=body)
        hits = response["hits"]["hits"]
        return [int(hit["_source"]["id"]) for hit in hits]

    async def index_document(self, document_id: int, text: str) -> None:
        await self._client.index(
            index=self._index,
            id=str(document_id),
            document={"id": document_id, "text": text},
        )

    async def delete_document(self, document_id: int) -> bool:
        """Delete a document from the index. Returns False if it didn't exist."""
        try:
            await self._client.delete(
                index=self._index, id=str(document_id)
            )
            return True
        except NotFoundError:
            logger.warning(
                "Document id=%d not found in Elasticsearch index.", document_id
            )
            return False

    async def bulk_index(self, documents: list[dict]) -> None:
        """
        Index multiple documents at once using the bulk API.
        Each dict must have 'id' and 'text'.
        """
        if not documents:
            return

        operations: list[dict] = []
        for doc in documents:
            operations.append(
                {"index": {"_index": self._index, "_id": str(doc["id"])}}
            )
            operations.append({"id": doc["id"], "text": doc["text"]})

        response = await self._client.bulk(operations=operations)
        if response.get("errors"):
            failed = [
                item
                for item in response["items"]
                if item.get("index", {}).get("error")
            ]
            logger.error("Bulk index had %d failures.", len(failed))
        else:
            logger.info("Bulk indexed %d documents.", len(documents))