import logging

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic liveness check used by monitoring, load balancers, and CI."""
    return {"status": "ok", "environment": settings.environment}
