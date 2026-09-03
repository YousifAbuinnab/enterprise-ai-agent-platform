import json
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.schemas.agent import AgentRunResponse, ToolUse
from app.services import tools
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


def execute_tool(db: Session, name: str, raw_arguments: str) -> ToolUse:
    """Validate and execute a single agent tool call without exposing internal errors."""
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return ToolUse(name=name, arguments={}, result="Tool call rejected: arguments must be valid JSON.")

    tool_registry: dict[str, tuple[type[BaseModel], Any]] = {
        "search_company_documents": (tools.SearchDocumentsArgs, tools.search_documents),
        "get_customer_by_id": (tools.GetCustomerArgs, tools.get_customer_by_id),
        "list_customers": (tools.ListCustomersArgs, tools.list_customers),
    }
    tool = tool_registry.get(name)
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
