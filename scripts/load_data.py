#!/usr/bin/env python
"""
Load documents from a CSV file into PostgreSQL and Elasticsearch.

Usage:
    python scripts/load_data.py --file data/test_data.csv

CSV format expected:
    id,rubrics,text,created_date
    1,"['Культура', 'Спорт']","Текст документа...",2020-01-01 00:00:00
"""
import asyncio
import ast
import csv
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Make sure app imports resolve
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.postgres import Base
from app.db.elasticsearch_client import es_client, ensure_index
from app.models.document_model import Document
from app.repositories.document_repo import DocumentRepository
from app.repositories.search_repo import SearchRepository

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def parse_rubrics(value: str) -> list[str]:
    """Parse rubrics field which may be a Python list literal or JSON array."""
    value = value.strip()
    if not value or value in ("[]", "null", ""):
        return []
    try:
        result = ast.literal_eval(value)
        if isinstance(result, list):
            return [str(r) for r in result]
    except (ValueError, SyntaxError):
        pass
    # Fallback: treat as a single rubric string
    return [value]


def parse_date(value: str) -> datetime:
    """Try several common date formats."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {value!r}")


async def load(file_path: Path) -> None:
    setup_logging()

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await ensure_index()

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    logger.info("Loaded %d rows from %s", total, file_path)

    for batch_start in range(0, total, BATCH_SIZE):
        batch_rows = rows[batch_start : batch_start + BATCH_SIZE]
        db_docs: list[Document] = []
        es_docs: list[dict] = []

        for row in batch_rows:
            doc = Document(
                rubrics=parse_rubrics(row.get("rubrics", "")),
                text=row["text"].strip(),
                created_date=parse_date(row["created_date"]),
            )
            db_docs.append(doc)

        async with session_factory() as session:
            doc_repo = DocumentRepository(session)
            await doc_repo.bulk_insert(db_docs)
            await session.commit()
            # Refresh to get auto-assigned ids
            for doc in db_docs:
                await session.refresh(doc)
            es_docs = [{"id": doc.id, "text": doc.text} for doc in db_docs]

        search_repo = SearchRepository(es_client)
        await search_repo.bulk_index(es_docs)

        logger.info(
            "Processed batch %d/%d",
            min(batch_start + BATCH_SIZE, total),
            total,
        )

    await es_client.close()
    await engine.dispose()
    logger.info("Done. %d documents indexed.", total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load CSV data into the service.")
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to the CSV file",
    )
    args = parser.parse_args()
    asyncio.run(load(args.file))