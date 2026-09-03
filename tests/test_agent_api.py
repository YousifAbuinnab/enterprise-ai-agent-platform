from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.api.routes import agent as agent_route
from app.db.session import get_db
from app.main import app
from app.schemas.agent import AgentRunResponse, ToolUse

client = TestClient(app)


@pytest.fixture(autouse=True)
def _override_get_db() -> Generator[None, None, None]:
    """Supply a dummy session because the agent service is mocked in this route test."""
    app.dependency_overrides[get_db] = lambda: iter([None])
    yield
    app.dependency_overrides.clear()


def test_agent_run_returns_answer_and_tool_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /agent/run should expose the final answer and safe tool-use summary."""
    expected = AgentRunResponse(
        answer="Ada Lovelace is customer 1.",
        tools_used=[
            ToolUse(
                name="get_customer_by_id",
                arguments={"customer_id": 1},
                result='{"found": true, "id": 1, "name": "Ada Lovelace"}',
            )
        ],
    )
    monkeypatch.setattr(agent_route, "run_agent", lambda db, message: expected)

    response = client.post("/agent/run", json={"message": "Who is customer 1?"})

    assert response.status_code == 200
    assert response.json() == expected.model_dump()


def test_agent_run_rejects_blank_message() -> None:
    """POST /agent/run should reject an empty request message before calling the service."""
    response = client.post("/agent/run", json={"message": ""})

    assert response.status_code == 422
