from fastapi import APIRouter
from pydantic import BaseModel

from app.db.elasticsearch_client import es_client

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    elasticsearch: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
async def health_check() -> HealthResponse:
    try:
        es_ok = await es_client.ping()
        es_status = "ok" if es_ok else "unavailable"
    except Exception:
        es_status = "unavailable"

    return HealthResponse(
        status="ok",
        elasticsearch=es_status,
    )