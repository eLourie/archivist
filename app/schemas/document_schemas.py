from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Full document representation returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    rubrics: list[str]
    text: str
    created_date: datetime


class SearchRequest(BaseModel):
    """Payload for the full-text search endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Arbitrary text query to search documents by.",
        examples=["климатические изменения арктика"],
    )


class SearchResponse(BaseModel):
    """Paginated search result."""

    total: int = Field(description="Number of documents returned (max 20).")
    documents: list[DocumentResponse]


class DeleteResponse(BaseModel):
    """Confirmation of document deletion."""

    id: int
    message: str = "Document successfully deleted."