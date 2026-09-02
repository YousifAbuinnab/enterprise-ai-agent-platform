from app.services.embeddings import EMBEDDING_DIM, embed_query, embed_texts


def test_embed_texts_returns_correct_dimension() -> None:
    """Each embedding should have the model's expected dimensionality."""
    embeddings = embed_texts(["hello world", "another sentence"])

    assert len(embeddings) == 2
    assert all(len(vec) == EMBEDDING_DIM for vec in embeddings)


def test_embed_query_returns_single_vector() -> None:
    """embed_query should return one embedding vector for a single string."""
    embedding = embed_query("what is the capital of France?")

    assert len(embedding) == EMBEDDING_DIM


def test_similar_texts_have_higher_similarity_than_dissimilar_texts() -> None:
    """Embeddings of semantically similar sentences should be closer than dissimilar ones."""
    import numpy as np

    base = embed_query("The cat sat on the mat")
    similar = embed_query("A cat is sitting on a mat")
    different = embed_query("Quantum physics explains subatomic particles")

    def cosine_similarity(a: list[float], b: list[float]) -> float:
        a_arr, b_arr = np.array(a), np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

    assert cosine_similarity(base, similar) > cosine_similarity(base, different)
