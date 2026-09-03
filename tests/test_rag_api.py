from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.services import rag as rag_service

client = TestClient(app)


@dataclass
class _FakeChunk:
    id: int
    document_id: int
    chunk_text: str


@pytest.fixture(autouse=True)
def _override_get_db() -> Generator[None, None, None]:
    """The DB session isn't actually used once search_similar_chunks is mocked, so a dummy is enough."""
    app.dependency_overrides[get_db] = lambda: iter([None])
    yield
    app.dependency_overrides.clear()


def test_rag_ask_returns_answer_with_sources_and_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /rag/ask should return the generated answer, sources, and chunk references."""
    fake_rows = [
        (_FakeChunk(id=1, document_id=10, chunk_text="Refunds are available within 30 days."), "policy.txt", 0.1),
    ]
    monkeypatch.setattr(rag_service.chunk_crud, "search_similar_chunks", lambda db, embedding, limit: fake_rows)
    monkeypatch.setattr(rag_service, "embed_query", lambda text: [0.0] * 384)
    monkeypatch.setattr(rag_service, "generate_answer", lambda prompt: "You can request a refund within 30 days.")

    response = client.post("/rag/ask", json={"question": "What is the refund policy?", "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "You can request a refund within 30 days."
    assert body["sources"] == ["policy.txt"]
    assert len(body["chunks"]) == 1
    assert body["chunks"][0]["chunk_id"] == 1
    assert body["chunks"][0]["filename"] == "policy.txt"


def test_rag_ask_returns_no_answer_message_when_no_chunks_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /rag/ask should return the 'don't know' message when nothing relevant is retrieved."""
    monkeypatch.setattr(rag_service.chunk_crud, "search_similar_chunks", lambda db, embedding, limit: [])
    monkeypatch.setattr(rag_service, "embed_query", lambda text: [0.0] * 384)

    response = client.post("/rag/ask", json={"question": "What is the meaning of life?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == rag_service.NO_ANSWER_MESSAGE
    assert body["sources"] == []
    assert body["chunks"] == []
