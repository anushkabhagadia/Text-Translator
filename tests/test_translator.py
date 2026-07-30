"""
Tests use a mocked Groq client so they run without hitting the real
API or needing a key set (important for CI and for anyone cloning the repo
to try it without using their free-tier quota).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.translator import Translator, TranslationError


def _mock_response(detected_language: str, translated_text: str):
    """Build a fake Groq response object shaped like the real SDK's."""
    mock_message = MagicMock()
    mock_message.content = json.dumps(
        {"detected_source_language": detected_language, "translated_text": translated_text}
    )
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@patch("app.translator.Groq")
def test_translate_returns_expected_fields(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response("French", "Hello world")
    mock_groq_cls.return_value = mock_client

    translator = Translator(api_key="fake-key-for-test")
    result = translator.translate("Bonjour le monde", "English")

    assert result.translated_text == "Hello world"
    assert result.detected_source_language == "French"
    assert result.target_language == "English"
    assert result.source_text == "Bonjour le monde"


@patch("app.translator.Groq")
def test_translate_strips_markdown_code_fences(mock_groq_cls):
    mock_message = MagicMock()
    mock_message.content = (
        '```json\n{"detected_source_language": "Spanish", "translated_text": "Goodbye"}\n```'
    )
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_cls.return_value = mock_client

    translator = Translator(api_key="fake-key-for-test")
    result = translator.translate("Adios", "English")

    assert result.translated_text == "Goodbye"


@patch("app.translator.Groq")
def test_translate_strips_echoed_delimiters(mock_groq_cls):
    """
    Regression test: Llama 3.3 was observed echoing the prompt's text
    delimiters back inside translated_text (e.g. "---\nHello world\n---").
    The delimiter markers should never appear in the returned translation.
    """
    mock_message = MagicMock()
    mock_message.content = json.dumps(
        {
            "detected_source_language": "French",
            "translated_text": "TEXT_TO_TRANSLATE_START\nHello world\nTEXT_TO_TRANSLATE_END",
        }
    )
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_cls.return_value = mock_client

    translator = Translator(api_key="fake-key-for-test")
    result = translator.translate("Bonjour le monde", "English")

    assert result.translated_text == "Hello world"
    assert "TEXT_TO_TRANSLATE_START" not in result.translated_text
    assert "TEXT_TO_TRANSLATE_END" not in result.translated_text


def test_translate_rejects_empty_text():
    translator = Translator(api_key="fake-key-for-test")
    with pytest.raises(ValueError):
        translator.translate("", "English")


def test_translate_rejects_empty_target_language():
    translator = Translator(api_key="fake-key-for-test")
    with pytest.raises(ValueError):
        translator.translate("Hello", "")


@patch("app.translator.Groq")
def test_translate_raises_on_malformed_json(mock_groq_cls):
    mock_message = MagicMock()
    mock_message.content = "this is not json"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq_cls.return_value = mock_client

    translator = Translator(api_key="fake-key-for-test")
    with pytest.raises(TranslationError):
        translator.translate("Hello", "French")
