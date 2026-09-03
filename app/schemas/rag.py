from pydantic import BaseModel, Field


class RagAskRequest(BaseModel):
    """A question to be answered using retrieval-augmented generation."""

    question: str
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkReference(BaseModel):
    """A chunk that was used as context for an answer, with its similarity score."""

    chunk_id: int
    document_id: int
    filename: str
    similarity_score: float


class RagAnswer(BaseModel):
    """A generated answer along with the sources and chunks it was based on."""

    answer: str
    sources: list[str]
    chunks: list[ChunkReference]
