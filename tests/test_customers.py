from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# In-memory SQLite gives each test run a fresh, isolated database without needing Postgres.
# StaticPool keeps a single shared connection so the in-memory DB persists across sessions.
engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _test_db() -> Generator[None, None, None]:
    """Create fresh tables for each test and override the app's DB dependency."""
    Base.metadata.create_all(bind=engine)

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_create_customer_returns_201() -> None:
    """POST /customers should create a customer and return it with an id and created_at."""
    response = client.post(
        "/customers", json={"name": "Ada Lovelace", "email": "ada@example.com", "company": "Analytical Co"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert body["id"] is not None
    assert body["created_at"] is not None


def test_create_customer_duplicate_email_returns_409() -> None:
    """POST /customers with an email that already exists should return 409, not 500."""
    payload = {"name": "Ada Lovelace", "email": "ada@example.com", "company": "Analytical Co"}
    client.post("/customers", json=payload)

    response = client.post("/customers", json=payload)

    assert response.status_code == 409


def test_list_customers_returns_created_customers() -> None:
    """GET /customers should return all previously created customers."""
    client.post("/customers", json={"name": "Ada Lovelace", "email": "ada@example.com"})
    client.post("/customers", json={"name": "Alan Turing", "email": "alan@example.com"})

    response = client.get("/customers")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {c["email"] for c in body} == {"ada@example.com", "alan@example.com"}


def test_get_customer_by_id_returns_customer() -> None:
    """GET /customers/{id} should return the matching customer."""
    created = client.post("/customers", json={"name": "Ada Lovelace", "email": "ada@example.com"}).json()

    response = client.get(f"/customers/{created['id']}")

    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


def test_get_customer_not_found_returns_404() -> None:
    """GET /customers/{id} should return 404 when no customer has that id."""
    response = client.get("/customers/999999")

    assert response.status_code == 404
