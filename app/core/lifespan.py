import logging

from app.core.logging import setup_logging
from app.db.postgres import engine, Base
from app.db.elasticsearch_client import es_client, ensure_index

logger = logging.getLogger(__name__)


async def init_resources() -> None:
    setup_logging()
    logger.info("Initializing application resources...")

    # Create all tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL tables ready.")

    # Ensure Elasticsearch index exists with proper mapping
    await ensure_index()
    logger.info("Elasticsearch index ready.")

    logger.info("Application startup complete.")


async def close_resources() -> None:
    logger.info("Shutting down application resources...")
    await engine.dispose()
    await es_client.close()
    logger.info("Resources released.")