"""Shared, reusable tool implementations backed by existing business/database logic.

Both the agent service (app/services/agent.py) and the MCP server (app/mcp/server.py) call
these functions so the retrieval/customer logic is defined exactly once.
"""

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.crud import customer as customer_crud
from app.crud import document_chunk as chunk_crud
from app.services.embeddings import embed_query


class SearchDocumentsArgs(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


class GetCustomerArgs(BaseModel):
    customer_id: int = Field(ge=1)


class ListCustomersArgs(BaseModel):
    pass


def search_documents(db: Session, arguments: SearchDocumentsArgs) -> str:
    """Search uploaded company documents for semantically relevant text chunks."""
    rows = chunk_crud.search_similar_chunks(db, embed_query(arguments.query), arguments.limit)
    results = [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "filename": filename,
            "chunk_text": chunk.chunk_text,
            "similarity_score": round(1 - distance, 4),
        }
        for chunk, filename, distance in rows
    ]
    return json.dumps(results)


def get_customer_by_id(db: Session, arguments: GetCustomerArgs) -> str:
    """Retrieve one customer by its numeric ID."""
    customer = customer_crud.get_customer(db, arguments.customer_id)
    if customer is None:
        return json.dumps({"found": False, "message": "Customer not found"})
    return json.dumps(
        {
            "found": True,
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "company": customer.company,
        }
    )


def list_customers(db: Session, _: ListCustomersArgs) -> str:
    """List all customers with their basic details."""
    customers = customer_crud.list_customers(db)
    return json.dumps(
        [
            {"id": customer.id, "name": customer.name, "email": customer.email, "company": customer.company}
            for customer in customers
        ]
    )
