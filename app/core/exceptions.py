class DocumentNotFoundError(Exception):
    """Raised when a document is not found by the given id."""

    def __init__(self, document_id: int) -> None:
        self.document_id = document_id
        super().__init__(f"Document with id={document_id} not found.")


class SearchServiceError(Exception):
    """Raised when Elasticsearch query fails."""


class DatabaseError(Exception):
    """Raised on unexpected database errors."""