import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# In-memory SQLite gives each test run a fresh, isolated database without needing Postgres.
engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

client = TestClient(app)

TEST_UPLOAD_DIR = Path("test_uploads")


@pytest.fixture(autouse=True)
def _test_db_and_uploads() -> Generator[None, None, None]:
    """Create fresh tables and an isolated upload directory for each test."""
    Base.metadata.create_all(bind=engine)
    get_settings().upload_dir = str(TEST_UPLOAD_DIR)

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
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)


def _make_valid_pdf_bytes() -> bytes:
    """Build a minimal valid (blank) PDF for use in tests."""
    import io

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_upload_txt_document_is_processed_successfully() -> None:
    """Uploading a .txt file should succeed, extract its text, and mark it 'processed'."""
    response = client.post(
        "/documents/upload", files={"file": ("notes.txt", b"hello world", "text/plain")}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["content_type"] == "text/plain"
    assert body["processing_status"] == "processed"
    assert Path(body["file_path"]).exists()


def test_upload_valid_pdf_document_is_processed_successfully() -> None:
    """Uploading a well-formed .pdf file should succeed and be marked 'processed'."""
    response = client.post(
        "/documents/upload",
        files={"file": ("report.pdf", _make_valid_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "report.pdf"
    assert body["processing_status"] == "processed"


def test_upload_corrupt_pdf_is_marked_failed_but_still_created() -> None:
    """A corrupt .pdf should still create the document record, marked 'failed'."""
    response = client.post(
        "/documents/upload", files={"file": ("broken.pdf", b"not a real pdf", "application/pdf")}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "failed"


def test_upload_unsupported_file_type_returns_400() -> None:
    """Uploading a file type other than .txt/.pdf should return 400 with a clear message."""
    response = client.post(
        "/documents/upload", files={"file": ("image.png", b"fake image bytes", "image/png")}
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_list_documents_returns_uploaded_documents() -> None:
    """GET /documents should return all previously uploaded documents."""
    client.post("/documents/upload", files={"file": ("a.txt", b"a", "text/plain")})
    client.post("/documents/upload", files={"file": ("b.txt", b"b", "text/plain")})

    response = client.get("/documents")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {d["filename"] for d in body} == {"a.txt", "b.txt"}


def test_get_document_by_id_returns_document() -> None:
    """GET /documents/{id} should return the matching document's metadata."""
    created = client.post(
        "/documents/upload", files={"file": ("a.txt", b"a", "text/plain")}
    ).json()

    response = client.get(f"/documents/{created['id']}")

    assert response.status_code == 200
    assert response.json()["filename"] == "a.txt"


def test_get_document_not_found_returns_404() -> None:
    """GET /documents/{id} should return 404 when no document has that id."""
    response = client.get("/documents/999999")

    assert response.status_code == 404


def test_get_document_content_returns_extracted_text() -> None:
    """GET /documents/{id}/content should return the extracted text for a processed document."""
    created = client.post(
        "/documents/upload", files={"file": ("a.txt", b"hello world", "text/plain")}
    ).json()

    response = client.get(f"/documents/{created['id']}/content")

    assert response.status_code == 200
    body = response.json()
    assert body["processing_status"] == "processed"
    assert body["parsed_text"] == "hello world"


def test_get_document_content_not_found_returns_404() -> None:
    """GET /documents/{id}/content should return 404 when no document has that id."""
    response = client.get("/documents/999999/content")

    assert response.status_code == 404
