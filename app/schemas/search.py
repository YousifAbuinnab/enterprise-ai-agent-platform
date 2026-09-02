from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """A semantic search query."""

    query: str
    limit: int = Field(default=5, ge=1, le=50)


class SearchResult(BaseModel):
    """A single matching chunk returned by semantic search."""

    chunk_id: int
    document_id: int
    filename: str
    chunk_index: int
    chunk_text: str
    similarity_score: float
