from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.agent import run_agent

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
def run(request: AgentRunRequest, db: Session = Depends(get_db)) -> AgentRunResponse:
    """Run the company assistant with access to its bounded set of tools."""
    return run_agent(db, request.message)