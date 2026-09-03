import logging

from sqlalchemy.orm import Session

from app.crud import document_chunk as chunk_crud
from app.schemas.rag import ChunkReference, RagAnswer
from app.services.embeddings import embed_query
from app.services.llm_client import generate_answer

logger = logging.getLogger(__name__)

# Below this similarity, retrieved chunks are considered too weak to answer from - skip the LLM call entirely.
MIN_SIMILARITY_THRESHOLD = 0.2

NO_ANSWER_MESSAGE = "I don't know based on the available documents."


def build_prompt(question: str, context_chunks: list[tuple[str, str]]) -> str:
    """Build a strict, context-only prompt from the question and (filename, chunk_text) pairs."""
    context = "\n\n".join(f"[Source: {filename}]\n{text}" for filename, text in context_chunks)
    return (
        "You are an internal company assistant. Answer the question using ONLY the context below.\n"
        "Do not use any outside knowledge. "
        f'If the context does not contain enough information to answer, respond exactly with: "{NO_ANSWER_MESSAGE}"\n\n'
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )


def answer_question(db: Session, question: str, top_k: int) -> RagAnswer:
    """Retrieve relevant chunks, build a prompt, and generate an answer grounded in those chunks."""
    query_embedding = embed_query(question)
    rows = chunk_crud.search_similar_chunks(db, query_embedding, top_k)

    if not rows:
        return RagAnswer(answer=NO_ANSWER_MESSAGE, sources=[], chunks=[])

    chunk_refs = [
        ChunkReference(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=filename,
            similarity_score=1 - distance,
        )
        for chunk, filename, distance in rows
    ]
    best_similarity = max(ref.similarity_score for ref in chunk_refs)

    if best_similarity < MIN_SIMILARITY_THRESHOLD:
        logger.info("Best similarity %.3f below threshold; skipping LLM call", best_similarity)
        return RagAnswer(answer=NO_ANSWER_MESSAGE, sources=[], chunks=chunk_refs)

    context_chunks = [(filename, chunk.chunk_text) for chunk, filename, _ in rows]
    prompt = build_prompt(question, context_chunks)
    answer_text = generate_answer(prompt)

    sources = sorted({ref.filename for ref in chunk_refs})
    return RagAnswer(answer=answer_text, sources=sources, chunks=chunk_refs)
