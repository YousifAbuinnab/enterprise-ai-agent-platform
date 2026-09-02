def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping character-based chunks for embedding.

    A simple sliding window is used: each chunk is `chunk_size` characters, and
    consecutive chunks overlap by `overlap` characters so context isn't lost at chunk boundaries.
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += step
    return chunks
