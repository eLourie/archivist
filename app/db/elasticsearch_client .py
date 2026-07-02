import logging

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.core.config import settings

logger = logging.getLogger(__name__)

es_client = AsyncElasticsearch(
    hosts=[settings.ELASTICSEARCH_URL],
    retry_on_timeout=True,
    max_retries=3,
)

# Index mapping: only id and text are needed for search
INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "russian_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "russian_stop", "russian_stemmer"],
                }
            },
            "filter": {
                "russian_stop": {
                    "type": "stop",
                    "stopwords": "_russian_",
                },
                "russian_stemmer": {
                    "type": "stemmer",
                    "language": "russian",
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "text": {
                "type": "text",
                "analyzer": "russian_analyzer",
                "search_analyzer": "russian_analyzer",
            },
        }
    },
}


async def ensure_index() -> None:
    """Create the index with mapping if it does not already exist."""
    index = settings.ELASTICSEARCH_INDEX
    exists = await es_client.indices.exists(index=index)
    if not exists:
        await es_client.indices.create(index=index, body=INDEX_MAPPING)
        logger.info("Created Elasticsearch index '%s'.", index)
    else:
        logger.info("Elasticsearch index '%s' already exists.", index)