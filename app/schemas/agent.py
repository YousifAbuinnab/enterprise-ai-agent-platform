from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    """A request for the company assistant agent."""

    message: str = Field(min_length=1)


class ToolUse(BaseModel):
    """A tool invocation and the safe result returned to the client."""

    name: str
    arguments: dict[str, Any]
    result: str


class AgentRunResponse(BaseModel):
    """The agent's final answer and its tool-use trace."""

    answer: str
    tools_used: list[ToolUse]
