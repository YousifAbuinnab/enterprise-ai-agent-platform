from sqlalchemy import select
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


def create_chunks(
    db: Session, document_id: int, chunks: list[str], embeddings: list[list[float]]
) -> list[DocumentChunk]:
    """Insert chunk rows (with their embeddings) for a document, in order."""
    rows = [
        DocumentChunk(document_id=document_id, chunk_index=index, chunk_text=chunk, embedding=embedding)
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def search_similar_chunks(
    db: Session, query_embedding: list[float], limit: int
) -> list[Row[tuple[DocumentChunk, str, float]]]:
    """Return the chunks most similar to query_embedding (cosine distance), joined with filename."""
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(DocumentChunk, Document.filename, distance.label("distance"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .order_by(distance)
        .limit(limit)
    )
    return db.execute(stmt).all()
