from pathlib import Path

from pypdf import PdfReader


def extract_text(file_path: Path, extension: str) -> str:
    """Extract plain text from a .txt or .pdf file. Raises on unsupported types or parse failures."""
    if extension == ".txt":
        return _extract_txt(file_path)
    if extension == ".pdf":
        return _extract_pdf(file_path)
    raise ValueError(f"Unsupported file type for parsing: {extension}")


def _extract_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def _extract_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
