import logging
from collections.abc import Sequence

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_model import Document

logger = logging.getLogger(__name__)


class DocumentRepository:
    """All database operations for the Document model."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: int) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids_ordered_by_date(
        self, ids: list[int]
    ) -> Sequence[Document]:
        """Fetch multiple documents by ids, sorted by created_date DESC."""
        if not ids:
            return []
        result = await self._session.execute(
            select(Document)
            .where(Document.id.in_(ids))
            .order_by(Document.created_date.desc())
        )
        return result.scalars().all()

    async def delete_by_id(self, document_id: int) -> bool:
        """Delete a document. Returns True if a row was deleted."""
        result = await self._session.execute(
            delete(Document).where(Document.id == document_id)
        )
        return result.rowcount > 0

    async def bulk_insert(self, documents: list[Document]) -> None:
        self._session.add_all(documents)
        await self._session.flush()
        logger.info("Bulk inserted %d documents.", len(documents))