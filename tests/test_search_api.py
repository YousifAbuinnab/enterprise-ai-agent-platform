from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.crud import document_chunk as chunk_crud
from app.db.session import SessionLocal
from app.main import app
from app.models.document import Document
from app.services.embeddings import embed_texts

client = TestClient(app)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """A real DB session; skips the test if PostgreSQL isn't reachable (run via Docker Compose)."""
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
    except OperationalError:
        session.close()
        pytest.skip("PostgreSQL is not reachable; start it with `docker compose up -d db`")
    yield session
    session.close()


def test_search_endpoint_returns_most_relevant_chunk(db_session: Session) -> None:
    """POST /search should return the semantically closest chunk, with a similarity score."""
    document = Document(
        filename="search_api_test.txt",
        content_type="text/plain",
        file_path="uploads/search_api_test.txt",
        processing_status="processed",
        parsed_text="placeholder",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    texts = ["The cat sat on the mat", "Quantum physics explains subatomic particles"]
    chunk_crud.create_chunks(db_session, document.id, texts, embed_texts(texts))

    try:
        response = client.post("/search", json={"query": "a small cat on a mat", "limit": 1})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert "cat" in body[0]["chunk_text"]
        assert body[0]["filename"] == "search_api_test.txt"
        assert 0.0 <= body[0]["similarity_score"] <= 1.0
    finally:
        db_session.query(Document).filter_by(id=document.id).delete()
        db_session.commit()
