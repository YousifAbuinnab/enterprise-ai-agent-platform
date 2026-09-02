from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.services.document_parser import extract_text


def test_extract_text_from_txt_file(tmp_path: Path) -> None:
    """extract_text should return the exact contents of a .txt file."""
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello world", encoding="utf-8")

    result = extract_text(file_path, ".txt")

    assert result == "hello world"


def test_extract_text_from_pdf_file(tmp_path: Path) -> None:
    """extract_text should successfully parse a valid (if textless) PDF without raising."""
    file_path = tmp_path / "report.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with file_path.open("wb") as f:
        writer.write(f)

    result = extract_text(file_path, ".pdf")

    assert result == ""


def test_extract_text_raises_for_invalid_pdf(tmp_path: Path) -> None:
    """extract_text should raise when the PDF content is corrupt/unreadable."""
    file_path = tmp_path / "broken.pdf"
    file_path.write_bytes(b"this is not a real pdf")

    with pytest.raises(Exception):
        extract_text(file_path, ".pdf")


def test_extract_text_raises_for_unsupported_extension(tmp_path: Path) -> None:
    """extract_text should raise ValueError for extensions other than .txt/.pdf."""
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"fake")

    with pytest.raises(ValueError):
        extract_text(file_path, ".png")
