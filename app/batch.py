import json
from pathlib import Path
from typing import List

from .translator import Translator, TranslationResult


def translate_lines(
    translator: Translator,
    lines: List[str],
    target_language: str,
) -> List[TranslationResult]:
    """Translate a list of strings, skipping blank lines (returned as-is)."""
    results = []
    for line in lines:
        if not line.strip():
            results.append(
                TranslationResult(
                    source_text=line,
                    translated_text=line,
                    detected_source_language="n/a (blank line)",
                    target_language=target_language,
                )
            )
            continue
        results.append(translator.translate(line, target_language))
    return results


def translate_text_file(
    translator: Translator,
    input_path: str,
    output_path: str,
    target_language: str,
) -> List[TranslationResult]:
    """Translate a .txt file line-by-line and write the result to output_path."""
    lines = Path(input_path).read_text(encoding="utf-8").splitlines()
    results = translate_lines(translator, lines, target_language)

    Path(output_path).write_text(
        "\n".join(r.translated_text for r in results), encoding="utf-8"
    )
    return results


def translate_json_values(
    translator: Translator,
    input_path: str,
    output_path: str,
    target_language: str,
) -> dict:
    """
    Translate every string value in a flat JSON object (e.g. a UI strings: {"welcome_message": "Hello!", "logout_button": "Log out"}).
    Keys are left untouched; only values are translated. Non-string values pass through unchanged.
    """
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))

    translated = {}
    for key, value in data.items():
        if isinstance(value, str) and value.strip():
            translated[key] = translator.translate(value, target_language).translated_text
        else:
            translated[key] = value

    Path(output_path).write_text(
        json.dumps(translated, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return translated
