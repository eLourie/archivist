import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.db.postgres import get_db_session
from app.schemas import DeleteResponse, SearchRequest, SearchResponse, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = logging.getLogger(__name__)


def get_document_service(
    session: AsyncSession = Depends(get_db_session),
) -> DocumentService:
    return DocumentService(session)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Full-text search over documents",
    description=(
        "Accepts an arbitrary text query, searches the Elasticsearch index, "
        "and returns up to 20 matching documents with all fields ordered by "
        "creation date (newest first)."
    ),
    status_code=status.HTTP_200_OK,
)
async def search_documents(
    payload: SearchRequest,
    service: DocumentService = Depends(get_document_service),
) -> SearchResponse:
    documents = await service.search(payload.query)
    return SearchResponse(
        total=len(documents),
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
    )


@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
    summary="Delete a document by id",
    description=(
        "Permanently removes the document from PostgreSQL and the "
        "Elasticsearch index. Returns 404 if the document does not exist."
    ),
    status_code=status.HTTP_200_OK,
)
async def delete_document(
    document_id: int,
    service: DocumentService = Depends(get_document_service),
) -> DeleteResponse:
    try:
        await service.delete(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return DeleteResponse(id=document_id)