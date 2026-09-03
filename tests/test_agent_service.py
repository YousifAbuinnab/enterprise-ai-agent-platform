import json
from dataclasses import dataclass

import pytest

from app.services import agent
from app.services.llm_client import AgentResponse, AgentToolCall


@dataclass
class _FakeCustomer:
    id: int
    name: str
    email: str
    company: str | None


def _tool_call(name: str, arguments: dict[str, object], call_id: str = "call_1") -> AgentToolCall:
    return AgentToolCall(id=call_id, name=name, arguments=json.dumps(arguments))


def test_run_agent_answers_without_a_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """A final LLM response without tool calls should be returned directly."""
    monkeypatch.setattr(
        agent, "generate_agent_response", lambda messages, tools: AgentResponse("Hello.", [])
    )

    result = agent.run_agent(db=None, message="Hello")

    assert result.answer == "Hello."
    assert result.tools_used == []


def test_run_agent_uses_document_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent should execute a requested document search and send its result back to the LLM."""
    responses = iter(
        [
            AgentResponse(None, [_tool_call("search_company_documents", {"query": "refund policy"})]),
            AgentResponse("Refunds are available within 30 days.", []),
        ]
    )
    monkeypatch.setattr(agent, "generate_agent_response", lambda messages, tools: next(responses))
    monkeypatch.setattr(agent, "embed_query", lambda query: [0.0] * 384)
    monkeypatch.setattr(
        agent.chunk_crud,
        "search_similar_chunks",
        lambda db, embedding, limit: [
            (type("Chunk", (), {"id": 7, "document_id": 3, "chunk_text": "Refunds within 30 days."})(), "policy.txt", 0.1)
        ],
    )

    result = agent.run_agent(db=None, message="What is the refund policy?")

    assert result.answer == "Refunds are available within 30 days."
    assert result.tools_used[0].name == "search_company_documents"
    assert "policy.txt" in result.tools_used[0].result


def test_run_agent_uses_customer_lookup_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent should execute a requested customer lookup using existing customer CRUD."""
    responses = iter(
        [
            AgentResponse(None, [_tool_call("get_customer_by_id", {"customer_id": 42})]),
            AgentResponse("Customer 42 is Ada Lovelace.", []),
        ]
    )
    monkeypatch.setattr(agent, "generate_agent_response", lambda messages, tools: next(responses))
    monkeypatch.setattr(
        agent.customer_crud, "get_customer", lambda db, customer_id: _FakeCustomer(42, "Ada Lovelace", "ada@example.com", "Analytical Co")
    )

    result = agent.run_agent(db=None, message="Who is customer 42?")

    assert result.answer == "Customer 42 is Ada Lovelace."
    assert result.tools_used[0].name == "get_customer_by_id"
    assert '"id": 42' in result.tools_used[0].result


def test_run_agent_handles_multiple_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent should execute several requested tools before returning its final answer."""
    responses = iter(
        [
            AgentResponse(
                None,
                [
                    _tool_call("list_customers", {}, "call_1"),
                    _tool_call("get_customer_by_id", {"customer_id": 1}, "call_2"),
                ],
            ),
            AgentResponse("There is one customer: Ada Lovelace.", []),
        ]
    )
    monkeypatch.setattr(agent, "generate_agent_response", lambda messages, tools: next(responses))
    customer = _FakeCustomer(1, "Ada Lovelace", "ada@example.com", None)
    monkeypatch.setattr(agent.customer_crud, "list_customers", lambda db: [customer])
    monkeypatch.setattr(agent.customer_crud, "get_customer", lambda db, customer_id: customer)

    result = agent.run_agent(db=None, message="List customers and inspect customer 1")

    assert result.answer == "There is one customer: Ada Lovelace."
    assert [tool.name for tool in result.tools_used] == ["list_customers", "get_customer_by_id"]


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        ("unknown_tool", "{}", "unknown tool"),
        ("get_customer_by_id", "not-json", "arguments must be valid JSON"),
        ("get_customer_by_id", '{"customer_id": 0}', "invalid arguments"),
    ],
)
def test_execute_tool_rejects_unknown_or_invalid_requests(
    name: str, arguments: str, expected: str
) -> None:
    """Unknown names and malformed/invalid parameters should be safely rejected."""
    result = agent.execute_tool(db=None, name=name, raw_arguments=arguments)

    assert expected in result.result


def test_run_agent_stops_at_iteration_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated tool calls should stop at MAX_TOOL_ITERATIONS rather than looping indefinitely."""
    calls = 0

    def request_tool(messages: list[dict[str, object]], tools: list[dict[str, object]]) -> AgentResponse:
        nonlocal calls
        calls += 1
        return AgentResponse(None, [_tool_call("list_customers", {}, f"call_{calls}")])

    monkeypatch.setattr(agent, "generate_agent_response", request_tool)
    monkeypatch.setattr(agent.customer_crud, "list_customers", lambda db: [])

    result = agent.run_agent(db=None, message="Keep searching")

    assert calls == agent.MAX_TOOL_ITERATIONS
    assert len(result.tools_used) == agent.MAX_TOOL_ITERATIONS
    assert "tool-call limit" in result.answer
