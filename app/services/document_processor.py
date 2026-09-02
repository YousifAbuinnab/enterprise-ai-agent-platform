import logging

from sqlalchemy.orm import Session

from app.crud import document_chunk as chunk_crud
from app.models.document import Document
from app.services.embeddings import embed_texts
from app.services.text_chunker import chunk_text

logger = logging.getLogger(__name__)


def chunk_and_embed_document(db: Session, document: Document) -> None:
    """Split a document's extracted text into chunks, embed them, and persist the chunks.

    No-op if the document has no parsed text. Exceptions are left to the caller to handle,
    since embedding failure should not silently hide from callers relying on chunks existing.
    """
    if not document.parsed_text:
        return

    chunks = chunk_text(document.parsed_text)
    if not chunks:
        return

    embeddings = embed_texts(chunks)
    chunk_crud.create_chunks(db, document.id, chunks, embeddings)
