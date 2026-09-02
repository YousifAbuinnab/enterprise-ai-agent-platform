from functools import lru_cache

from sentence_transformers import SentenceTransformer

# Small (~80MB), well-known sentence-transformers model - good accuracy/speed trade-off for a portfolio project
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache
def _get_model() -> SentenceTransformer:
    """Load and cache the embedding model so it's only loaded once per process."""
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True).tolist()


def embed_query(text: str) -> list[float]:
    """Generate an embedding for a single query string."""
    return embed_texts([text])[0]
