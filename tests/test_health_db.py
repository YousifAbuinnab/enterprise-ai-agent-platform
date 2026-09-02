from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.main import app

client = TestClient(app)


class _FakeSessionOk:
    """Fake DB session that succeeds on execute(), simulating a healthy database."""

    def execute(self, _statement: object) -> None:
        return None


class _FakeSessionFailing:
    """Fake DB session that raises on execute(), simulating a database outage."""

    def execute(self, _statement: object) -> None:
        raise SQLAlchemyError("simulated connection failure")


@pytest.fixture(autouse=True)
def _clear_overrides() -> Generator[None, None, None]:
    """Ensure dependency overrides don't leak between tests."""
    yield
    app.dependency_overrides.clear()


def test_health_db_returns_ok_when_database_reachable() -> None:
    """/health/db should return 200 when the database query succeeds."""

    def _override() -> Generator[_FakeSessionOk, None, None]:
        yield _FakeSessionOk()

    app.dependency_overrides[get_db] = _override

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_returns_503_when_database_unreachable() -> None:
    """/health/db should return 503 when the database query fails."""

    def _override() -> Generator[_FakeSessionFailing, None, None]:
        yield _FakeSessionFailing()

    app.dependency_overrides[get_db] = _override

    response = client.get("/health/db")

    assert response.status_code == 503
