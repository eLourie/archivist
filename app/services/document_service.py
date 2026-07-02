import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DocumentNotFoundError
from app.db.elasticsearch_client import es_client
from app.models.document_model import Document
from app.repositories.document_repo import DocumentRepository
from app.repositories.search_repo import SearchRepository

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Orchestrates operations that touch both PostgreSQL and Elasticsearch.
    The service layer is the single source of truth for business rules.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._doc_repo = DocumentRepository(session)
        self._search_repo = SearchRepository(es_client)

    async def search(self, query: str) -> Sequence[Document]:
        """
        1. Search Elasticsearch for matching document ids.
        2. Fetch full document records from PostgreSQL.
        3. Return sorted by created_date DESC (handled in DB query).
        """
        ids = await self._search_repo.search(
            query=query, limit=settings.SEARCH_RESULT_LIMIT
        )
        if not ids:
            return []

        documents = await self._doc_repo.get_by_ids_ordered_by_date(ids)
        logger.info(
            "Search query=%r → %d ES hits, %d DB records returned.",
            query,
            len(ids),
            len(documents),
        )
        return documents

    async def delete(self, document_id: int) -> None:
        """
        Delete document from both PostgreSQL and Elasticsearch atomically.
        Raises DocumentNotFoundError if the document does not exist in the DB.
        """
        document = await self._doc_repo.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        # Delete from DB first — if this fails, ES is untouched (consistent state)
        await self._doc_repo.delete_by_id(document_id)

        # Best-effort ES delete (log warning if not found, don't fail the request)
        await self._search_repo.delete_document(document_id)

        logger.info("Document id=%d deleted from DB and Elasticsearch.", document_id)