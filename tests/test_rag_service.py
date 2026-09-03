from dataclasses import dataclass

import pytest

from app.services import rag as rag_service


@dataclass
class _FakeChunk:
    id: int
    document_id: int
    chunk_text: str


def test_answer_question_returns_no_answer_when_no_chunks_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """With zero retrieved chunks, the service should return the 'don't know' message without calling the LLM."""
    monkeypatch.setattr(rag_service.chunk_crud, "search_similar_chunks", lambda db, embedding, limit: [])
    called = []
    monkeypatch.setattr(rag_service, "generate_answer", lambda prompt: called.append(prompt) or "should not happen")
    monkeypatch.setattr(rag_service, "embed_query", lambda text: [0.0] * 384)

    result = rag_service.answer_question(db=None, question="What is X?", top_k=5)

    assert result.answer == rag_service.NO_ANSWER_MESSAGE
    assert result.sources == []
    assert result.chunks == []
    assert called == []


def test_answer_question_returns_no_answer_when_similarity_too_low(monkeypatch: pytest.MonkeyPatch) -> None:
    """With only weakly-similar chunks, the service should decline to answer without calling the LLM."""
    fake_rows = [(_FakeChunk(id=1, document_id=1, chunk_text="irrelevant text"), "doc.txt", 0.95)]
    monkeypatch.setattr(rag_service.chunk_crud, "search_similar_chunks", lambda db, embedding, limit: fake_rows)
    called = []
    monkeypatch.setattr(rag_service, "generate_answer", lambda prompt: called.append(prompt) or "should not happen")
    monkeypatch.setattr(rag_service, "embed_query", lambda text: [0.0] * 384)

    result = rag_service.answer_question(db=None, question="What is X?", top_k=5)

    assert result.answer == rag_service.NO_ANSWER_MESSAGE
    assert len(result.chunks) == 1
    assert called == []


def test_answer_question_generates_answer_from_relevant_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """With relevant chunks, the service should build a prompt, call the (mocked) LLM, and format the response."""
    fake_rows = [
        (_FakeChunk(id=1, document_id=10, chunk_text="Refunds are available within 30 days."), "policy.txt", 0.1),
        (_FakeChunk(id=2, document_id=10, chunk_text="Contact support for help."), "policy.txt", 0.3),
    ]
    monkeypatch.setattr(rag_service.chunk_crud, "search_similar_chunks", lambda db, embedding, limit: fake_rows)
    monkeypatch.setattr(rag_service, "embed_query", lambda text: [0.0] * 384)

    captured_prompts = []

    def fake_generate_answer(prompt: str) -> str:
        captured_prompts.append(prompt)
        return "You can request a refund within 30 days."

    monkeypatch.setattr(rag_service, "generate_answer", fake_generate_answer)

    result = rag_service.answer_question(db=None, question="What is the refund policy?", top_k=5)

    assert result.answer == "You can request a refund within 30 days."
    assert result.sources == ["policy.txt"]
    assert len(result.chunks) == 2
    assert result.chunks[0].chunk_id == 1
    assert result.chunks[0].similarity_score == pytest.approx(0.9)
    assert len(captured_prompts) == 1
    assert "What is the refund policy?" in captured_prompts[0]
    assert "Refunds are available within 30 days." in captured_prompts[0]
