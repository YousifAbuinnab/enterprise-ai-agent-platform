import logging

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.api.routes.customers import router as customers_router
from app.api.routes.documents import router as documents_router

settings = get_settings()

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

app.include_router(customers_router)
app.include_router(documents_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic liveness check used by monitoring, load balancers, and CI."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)) -> dict[str, str]:
    """Verify the application can connect to and query PostgreSQL."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Database health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}
