import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.crud import customer as customer_crud
from app.crud import document_chunk as chunk_crud
from app.schemas.agent import AgentRunResponse, ToolUse
from app.services.embeddings import embed_query
from app.services.llm_client import generate_agent_response

MAX_TOOL_ITERATIONS = 5

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_company_documents",
            "description": "Search uploaded company documents for semantically relevant text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The document search query."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_by_id",
            "description": "Retrieve one customer by its numeric ID.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "integer", "minimum": 1}},
                "required": ["customer_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_customers",
            "description": "List all customers with their basic details.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


class SearchDocumentsArgs(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


class GetCustomerArgs(BaseModel):
    customer_id: int = Field(ge=1)


class ListCustomersArgs(BaseModel):
    pass


def _search_company_documents(db: Session, arguments: SearchDocumentsArgs) -> str:
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


def _get_customer_by_id(db: Session, arguments: GetCustomerArgs) -> str:
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


def _list_customers(db: Session, _: ListCustomersArgs) -> str:
    customers = customer_crud.list_customers(db)
    return json.dumps(
        [
            {"id": customer.id, "name": customer.name, "email": customer.email, "company": customer.company}
            for customer in customers
        ]
    )


def execute_tool(db: Session, name: str, raw_arguments: str) -> ToolUse:
    """Validate and execute a single agent tool call without exposing internal errors."""
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return ToolUse(name=name, arguments={}, result="Tool call rejected: arguments must be valid JSON.")

    tools: dict[str, tuple[type[BaseModel], Any]] = {
        "search_company_documents": (SearchDocumentsArgs, _search_company_documents),
        "get_customer_by_id": (GetCustomerArgs, _get_customer_by_id),
        "list_customers": (ListCustomersArgs, _list_customers),
    }
    tool = tools.get(name)
    if tool is None:
        return ToolUse(name=name, arguments=arguments, result="Tool call rejected: unknown tool.")

    schema, handler = tool
    try:
        validated_arguments = schema.model_validate(arguments)
    except ValidationError:
        return ToolUse(name=name, arguments=arguments, result="Tool call rejected: invalid arguments.")

    return ToolUse(name=name, arguments=validated_arguments.model_dump(), result=handler(db, validated_arguments))


def run_agent(db: Session, message: str) -> AgentRunResponse:
    """Run a bounded tool-calling loop and return the final model answer plus tool trace."""
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": "You are an internal company assistant. Use tools when company documents or customer data are needed. "
            "Do not invent tool results.",
        },
        {"role": "user", "content": message},
    ]
    tools_used: list[ToolUse] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = generate_agent_response(messages, TOOL_DEFINITIONS)
        if not response.tool_calls:
            return AgentRunResponse(answer=response.content or "I don't know.", tools_used=tools_used)

        messages.append(response.as_assistant_message())
        for tool_call in response.tool_calls:
            tool_use = execute_tool(db, tool_call.name, tool_call.arguments)
            tools_used.append(tool_use)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_use.result})

    return AgentRunResponse(
        answer="I could not complete the request because the tool-call limit was reached.", tools_used=tools_used
    )
