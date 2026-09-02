import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.crud import document as document_crud
from app.db.session import get_db
from app.schemas.document import DocumentContent, DocumentRead
from app.services.document_parser import extract_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".txt", ".pdf"}


@router.post("/upload", response_model=DocumentRead, status_code=201)
def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> DocumentRead:
    """Upload a .txt or .pdf file and store its metadata. Returns 400 for unsupported file types."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Prefix with a UUID to avoid collisions between uploads with the same filename
    stored_name = f"{uuid.uuid4()}{extension}"
    file_path = upload_dir / stored_name
    with file_path.open("wb") as out_file:
        out_file.write(file.file.read())

    content_type = file.content_type or "application/octet-stream"
    document = document_crud.create_document(
        db, filename=file.filename, content_type=content_type, file_path=str(file_path)
    )

    try:
        parsed_text = extract_text(file_path, extension)
    except Exception:
        logger.exception("Failed to extract text from document %s", document.id)
        document = document_crud.update_processing_result(db, document, status="failed", parsed_text=None)
    else:
        document = document_crud.update_processing_result(db, document, status="processed", parsed_text=parsed_text)

    return DocumentRead.model_validate(document)


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentRead]:
    """List all uploaded documents."""
    documents = document_crud.list_documents(db)
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentRead:
    """Retrieve a single document's metadata by id. Returns 404 if not found."""
    document = document_crud.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead.model_validate(document)


@router.get("/{document_id}/content", response_model=DocumentContent)
def get_document_content(document_id: int, db: Session = Depends(get_db)) -> DocumentContent:
    """Retrieve the extracted text for a document. Returns 404 if not found."""
    document = document_crud.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentContent.model_validate(document)
