import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rag import RagAnswer, RagAskRequest
from app.services import rag as rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask", response_model=RagAnswer)
def ask(request: RagAskRequest, db: Session = Depends(get_db)) -> RagAnswer:
    """Answer a question using retrieval-augmented generation over uploaded documents."""
    return rag_service.answer_question(db, request.question, request.top_k)
