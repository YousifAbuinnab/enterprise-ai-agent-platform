from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.crud import document_chunk as chunk_crud
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.embeddings import embed_texts


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


def _create_document(db: Session, filename: str = "integration_test.txt") -> Document:
    document = Document(
        filename=filename,
        content_type="text/plain",
        file_path=f"uploads/{filename}",
        processing_status="processed",
        parsed_text="placeholder",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def _cleanup(db: Session, document: Document) -> None:
    db.query(type(document)).filter_by(id=document.id).delete()
    db.commit()


def test_create_chunks_persists_chunks_with_embeddings(db_session: Session) -> None:
    """create_chunks should insert one row per chunk, preserving order and embedding values."""
    document = _create_document(db_session)
    texts = ["first chunk of text", "second chunk of text"]
    embeddings = embed_texts(texts)

    try:
        chunks = chunk_crud.create_chunks(db_session, document.id, texts, embeddings)

        assert len(chunks) == 2
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[0].chunk_text == "first chunk of text"
        assert len(chunks[0].embedding) == len(embeddings[0])
    finally:
        _cleanup(db_session, document)


def test_search_similar_chunks_returns_most_similar_first(db_session: Session) -> None:
    """search_similar_chunks should rank the semantically closest chunk first."""
    document = _create_document(db_session)
    texts = ["The cat sat on the mat", "Quantum physics explains subatomic particles"]
    embeddings = embed_texts(texts)
    chunk_crud.create_chunks(db_session, document.id, texts, embeddings)

    try:
        query_embedding = embed_texts(["a small cat resting on a mat"])[0]
        results = chunk_crud.search_similar_chunks(db_session, query_embedding, limit=1)

        assert len(results) == 1
        chunk, filename, distance = results[0]
        assert "cat" in chunk.chunk_text
        assert filename == document.filename
        assert distance < 1.0
    finally:
        _cleanup(db_session, document)
