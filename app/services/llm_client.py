from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings


@dataclass
class AgentToolCall:
    """A normalized function call returned by an LLM provider."""

    id: str
    name: str
    arguments: str


@dataclass
class AgentResponse:
    """A normalized agent turn containing text and optional function calls."""

    content: str | None
    tool_calls: list[AgentToolCall]

    def as_assistant_message(self) -> dict[str, Any]:
        """Return the OpenAI-compatible assistant message required for tool-result follow-up."""
        return {
            "role": "assistant",
            "content": self.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in self.tool_calls
            ],
        }


def generate_answer(prompt: str) -> str:
    """Generate a completion for the given prompt using the configured LLM provider."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        return _generate_openai(prompt, settings.llm_api_key, settings.llm_model)

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def generate_agent_response(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AgentResponse:
    """Request an answer or tool calls from the configured LLM provider."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.llm_api_key)
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
        )
        message = response.choices[0].message
        return AgentResponse(
            content=message.content,
            tool_calls=[
                AgentToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
                for call in message.tool_calls or []
            ],
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def _generate_openai(prompt: str, api_key: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content or ""
