import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import document_chunk as chunk_crud
from app.db.session import get_db
from app.schemas.search import SearchRequest, SearchResult
from app.services.embeddings import embed_query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


@router.post("/search", response_model=list[SearchResult])
def semantic_search(request: SearchRequest, db: Session = Depends(get_db)) -> list[SearchResult]:
    """Return the chunks most semantically similar to the query, across all documents."""
    query_embedding = embed_query(request.query)
    rows = chunk_crud.search_similar_chunks(db, query_embedding, request.limit)

    results = []
    for chunk, filename, distance in rows:
        # cosine_distance = 1 - cosine_similarity, so similarity = 1 - distance
        results.append(
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                similarity_score=1 - distance,
            )
        )
    return results
