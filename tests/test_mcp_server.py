"""Tests for the MCP server: use FastMCP's in-process list_tools/call_tool API as a
minimal MCP client/test harness, avoiding the need for a separate transport (stdio/SSE).
"""

import asyncio
import json
from dataclasses import dataclass

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from app.mcp.server import mcp
from app.services import tools


@dataclass
class _FakeChunk:
    id: int
    document_id: int
    chunk_text: str


@dataclass
class _FakeCustomer:
    id: int
    name: str
    email: str
    company: str | None


def _run(coro):
    return asyncio.run(coro)


def test_discover_tools_lists_expected_tools_with_schemas() -> None:
    """Tool discovery should expose exactly the three required tools with descriptions and schemas."""
    discovered = _run(mcp.list_tools())

    names = {tool.name for tool in discovered}
    assert names == {"search_documents", "get_customer_by_id", "list_customers"}
    for tool in discovered:
        assert tool.description
        assert tool.inputSchema["type"] == "object"


def test_search_documents_tool_executes_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling search_documents should reuse the shared retrieval logic and return matching chunks."""
    monkeypatch.setattr(tools, "embed_query", lambda query: [0.0] * 384)
    monkeypatch.setattr(
        tools.chunk_crud,
        "search_similar_chunks",
        lambda db, embedding, limit: [
            (_FakeChunk(id=1, document_id=5, chunk_text="Refunds within 30 days."), "policy.txt", 0.1)
        ],
    )

    result = _run(mcp.call_tool("search_documents", {"query": "refund policy"}))

    body = json.loads(result[0].text)
    assert body[0]["filename"] == "policy.txt"
    assert body[0]["chunk_text"] == "Refunds within 30 days."


def test_get_customer_by_id_tool_executes_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling get_customer_by_id should reuse the existing customer CRUD logic."""
    monkeypatch.setattr(
        tools.customer_crud,
        "get_customer",
        lambda db, customer_id: _FakeCustomer(1, "Ada Lovelace", "ada@example.com", "Analytical Co"),
    )

    result = _run(mcp.call_tool("get_customer_by_id", {"customer_id": 1}))

    body = json.loads(result[0].text)
    assert body["found"] is True
    assert body["name"] == "Ada Lovelace"


def test_list_customers_tool_executes_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling list_customers should reuse the existing customer CRUD logic."""
    customer = _FakeCustomer(1, "Ada Lovelace", "ada@example.com", None)
    monkeypatch.setattr(tools.customer_crud, "list_customers", lambda db: [customer])

    result = _run(mcp.call_tool("list_customers", {}))

    body = json.loads(result[0].text)
    assert body == [{"id": 1, "name": "Ada Lovelace", "email": "ada@example.com", "company": None}]


def test_call_unknown_tool_raises_tool_error() -> None:
    """Requesting a tool that doesn't exist should raise a clear ToolError, not crash the server."""
    with pytest.raises(ToolError, match="Unknown tool"):
        _run(mcp.call_tool("delete_all_customers", {}))


def test_call_tool_with_invalid_parameters_raises_tool_error() -> None:
    """Invalid parameters (wrong type, out-of-range) should be rejected via schema validation."""
    with pytest.raises(ToolError):
        _run(mcp.call_tool("get_customer_by_id", {"customer_id": "not-a-number"}))

    with pytest.raises(ToolError):
        _run(mcp.call_tool("get_customer_by_id", {"customer_id": 0}))

    with pytest.raises(ToolError):
        _run(mcp.call_tool("search_documents", {"query": ""}))
