from datetime import datetime, timezone

from app.models.document_model import Document


def make_document(
    text: str = "Sample document text",
    rubrics: list[str] | None = None,
    created_date: datetime | None = None,
) -> Document:
    return Document(
        rubrics=rubrics or ["general"],
        text=text,
        created_date=created_date or datetime.now(tz=timezone.utc),
    )