from app.services.rag import build_prompt


def test_build_prompt_includes_question_and_context() -> None:
    """The prompt should contain the question and every chunk's text and filename."""
    prompt = build_prompt(
        "What is the refund policy?",
        [("policy.txt", "Refunds are available within 30 days."), ("faq.txt", "Contact support for help.")],
    )

    assert "What is the refund policy?" in prompt
    assert "Refunds are available within 30 days." in prompt
    assert "[Source: policy.txt]" in prompt
    assert "Contact support for help." in prompt
    assert "[Source: faq.txt]" in prompt


def test_build_prompt_instructs_context_only_answering() -> None:
    """The prompt must instruct the model to answer only from the provided context."""
    prompt = build_prompt("anything", [("a.txt", "some text")])

    assert "ONLY the context below" in prompt
    assert "I don't know based on the available documents." in prompt
