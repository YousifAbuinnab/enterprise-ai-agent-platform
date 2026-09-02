from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


def create_document(db: Session, filename: str, content_type: str, file_path: str) -> Document:
    """Insert a new document metadata row."""
    document = Document(filename=filename, content_type=content_type, file_path=file_path)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session) -> list[Document]:
    """Return all documents ordered by id."""
    return list(db.scalars(select(Document).order_by(Document.id)))


def get_document(db: Session, document_id: int) -> Document | None:
    """Return a single document by id, or None if not found."""
    return db.get(Document, document_id)


def update_processing_result(db: Session, document: Document, status: str, parsed_text: str | None) -> Document:
    """Store the outcome of text extraction (status + extracted text, if any) for a document."""
    document.processing_status = status
    document.parsed_text = parsed_text
    db.commit()
    db.refresh(document)
    return document
