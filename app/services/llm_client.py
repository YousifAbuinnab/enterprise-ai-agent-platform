from app.core.config import get_settings


def generate_answer(prompt: str) -> str:
    """Generate a completion for the given prompt using the configured LLM provider."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        return _generate_openai(prompt, settings.llm_api_key, settings.llm_model)

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
