from unittest.mock import MagicMock, patch

import pytest

from app.agent import TranslationAgent, Turn


def _mock_response(text: str):
    mock_message = MagicMock()
    mock_message.content = text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@patch("app.agent.Groq")
def test_send_appends_to_history(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response("Bonjour")
    mock_groq_cls.return_value = mock_client

    agent = TranslationAgent(api_key="fake-key")
    reply = agent.send("Translate 'hello' to French")

    assert reply == "Bonjour"
    assert len(agent.history) == 2
    assert agent.history[0] == Turn(role="user", content="Translate 'hello' to French")
    assert agent.history[1] == Turn(role="assistant", content="Bonjour")


@patch("app.agent.Groq")
def test_follow_up_sends_full_history_to_api(mock_groq_cls):
    """The key agentic behavior: a follow-up turn must include prior turns as context."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _mock_response("Bonjour"),
        _mock_response("Bonjour, comment allez-vous"),
    ]
    mock_groq_cls.return_value = mock_client

    agent = TranslationAgent(api_key="fake-key")
    agent.send("Translate 'hi' to French")
    agent.send("Make it more formal")

    second_call_kwargs = mock_client.chat.completions.create.call_args_list[1].kwargs
    messages_sent = second_call_kwargs["messages"]

    # System prompt + all 3 prior turns (user, assistant, new user) should be sent.
    assert len(messages_sent) == 4
    assert messages_sent[0]["role"] == "system"
    assert messages_sent[1]["content"] == "Translate 'hi' to French"
    assert messages_sent[2]["content"] == "Bonjour"
    assert messages_sent[3]["content"] == "Make it more formal"


@patch("app.agent.Groq")
def test_reset_clears_history(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response("Hola")
    mock_groq_cls.return_value = mock_client

    agent = TranslationAgent(api_key="fake-key")
    agent.send("Translate 'hi' to Spanish")
    assert len(agent.history) == 2

    agent.reset()
    assert agent.history == []


def test_send_rejects_empty_message():
    agent = TranslationAgent(api_key="fake-key")
    with pytest.raises(ValueError):
        agent.send("")


@patch("app.agent.Groq")
def test_transcript_formats_readable_output(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response("Hola")
    mock_groq_cls.return_value = mock_client

    agent = TranslationAgent(api_key="fake-key")
    agent.send("Translate 'hi' to Spanish")

    transcript = agent.transcript()
    assert "You: Translate 'hi' to Spanish" in transcript
    assert "Agent: Hola" in transcript
