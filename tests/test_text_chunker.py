from app.services.text_chunker import chunk_text


def test_chunk_text_returns_empty_list_for_empty_input() -> None:
    """Empty (or whitespace-only) text should produce no chunks."""
    assert chunk_text("   ") == []
    assert chunk_text("") == []


def test_chunk_text_returns_single_chunk_for_short_text() -> None:
    """Text shorter than chunk_size should come back as a single chunk."""
    chunks = chunk_text("hello world", chunk_size=500, overlap=50)

    assert chunks == ["hello world"]


def test_chunk_text_splits_long_text_into_overlapping_chunks() -> None:
    """Long text should be split into multiple chunks that overlap by the given amount."""
    text = "a" * 120
    chunks = chunk_text(text, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    # every chunk except possibly the last should be exactly chunk_size long
    assert all(len(c) == 50 for c in chunks[:-1])
    # consecutive chunks should share `overlap` characters at the boundary
    assert chunks[0][-10:] == chunks[1][:10]
