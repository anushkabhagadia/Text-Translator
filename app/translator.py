"""
Core translation logic.

Uses the Groq API (running Llama 3.3 70B, an open model) as the translation
engine instead of a dedicated translation API. Trade-off, stated plainly:

  + Handles idiom, tone, and formatting instructions ("keep it formal",
    "preserve markdown") that rule-based translation APIs can't.
  + One call can auto-detect the source language AND translate, so no
    separate language-detection step/library is needed.
  + Groq's free tier makes this viable to run and demo without cost.
  - Slower and more expensive per-request than a dedicated translation
    API (e.g. Google Translate) for pure high-volume, no-context text.

This is a deliberate choice to demonstrate LLM API integration, not a
claim that this is the "best" approach for every production translation
use case.
"""

import os
import json
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads a local .env file, if present, into os.environ

MODEL = "llama-3.3-70b-versatile"


class TranslationError(Exception):
    """Raised when the API call succeeds but the response can't be used."""


@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    detected_source_language: str
    target_language: str

    def to_dict(self) -> dict:
        return {
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "detected_source_language": self.detected_source_language,
            "target_language": self.target_language,
        }


class Translator:
    """Thin wrapper around the Groq API for translation tasks."""

    def __init__(self, api_key: Optional[str] = None):
        # Falls back to the GROQ_API_KEY env var if not passed explicitly.
        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))

    def translate(
        self,
        text: str,
        target_language: str,
        preserve_formatting: bool = True,
    ) -> TranslationResult:
        """
        Translate `text` into `target_language`, auto-detecting the source
        language. Returns a TranslationResult, not just a string, so callers
        (CLI, API, tests) get the detected source language for free instead
        of running a second detection step.
        """
        if not text or not text.strip():
            raise ValueError("text must be a non-empty string")
        if not target_language or not target_language.strip():
            raise ValueError("target_language must be a non-empty string")

        formatting_note = (
            "Preserve all original formatting exactly (line breaks, markdown, "
            "punctuation style, capitalization conventions)."
            if preserve_formatting
            else "Formatting does not need to be preserved."
        )

        prompt = f"""Translate the following text into {target_language}.

{formatting_note}

Respond with ONLY a JSON object in exactly this shape, and nothing else:
{{"detected_source_language": "<language name>", "translated_text": "<translation>"}}

The "translated_text" field must contain ONLY the translation itself — do
not include any delimiters, labels, or the original text in that field.

TEXT_TO_TRANSLATE_START
{text}
TEXT_TO_TRANSLATE_END"""

        response = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content.strip()
        # Model sometimes wraps JSON in code fences despite instructions; strip defensively.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise TranslationError(f"Could not parse model response as JSON: {raw[:200]}") from e

        if "translated_text" not in parsed or "detected_source_language" not in parsed:
            raise TranslationError(f"Model response missing expected keys: {parsed}")

        translated_text = parsed["translated_text"].strip()
        # Defensive cleanup: if the model echoed our delimiters despite instructions,
        # strip them rather than failing the whole translation.
        for marker in ("TEXT_TO_TRANSLATE_START", "TEXT_TO_TRANSLATE_END", "---"):
            translated_text = translated_text.replace(marker, "").strip()

        return TranslationResult(
            source_text=text,
            translated_text=translated_text,
            detected_source_language=parsed["detected_source_language"],
            target_language=target_language,
        )

