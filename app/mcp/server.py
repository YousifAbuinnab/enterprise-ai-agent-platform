"""Minimal MCP server exposing a subset of the platform's existing tools.

Kept separate from the FastAPI routes and the agent service (app/services/agent.py).
Both callers share the same business/database logic via app.services.tools, so nothing
is duplicated here - this module only adapts that logic to the MCP tool protocol.
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.db.session import SessionLocal
from app.services import tools

mcp = FastMCP("enterprise-ai-agent-platform")


@mcp.tool()
def search_documents(
    query: Annotated[str, Field(min_length=1, description="The document search query.")],
    limit: Annotated[int, Field(ge=1, le=10, description="Maximum number of chunks to return.")] = 5,
) -> str:
    """Search uploaded company documents for semantically relevant text chunks."""
    db = SessionLocal()
    try:
        return tools.search_documents(db, tools.SearchDocumentsArgs(query=query, limit=limit))
    finally:
        db.close()


@mcp.tool()
def get_customer_by_id(
    customer_id: Annotated[int, Field(ge=1, description="The numeric ID of the customer to look up.")],
) -> str:
    """Retrieve one customer by its numeric ID."""
    db = SessionLocal()
    try:
        return tools.get_customer_by_id(db, tools.GetCustomerArgs(customer_id=customer_id))
    finally:
        db.close()


@mcp.tool()
def list_customers() -> str:
    """List all customers with their basic details."""
    db = SessionLocal()
    try:
        return tools.list_customers(db, tools.ListCustomersArgs())
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
