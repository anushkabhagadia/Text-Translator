import json
from unittest.mock import MagicMock, patch

from app.translator import Translator, TranslationResult
from app.batch import translate_lines, translate_text_file, translate_json_values


def _fake_translate(self, text, target_language, preserve_formatting=True):
    """Monkeypatched translate() that just uppercases input — deterministic, no API call."""
    return TranslationResult(
        source_text=text,
        translated_text=text.upper(),
        detected_source_language="English",
        target_language=target_language,
    )


@patch.object(Translator, "translate", _fake_translate)
def test_translate_lines_skips_blank_lines():
    translator = Translator(api_key="fake-key")
    results = translate_lines(translator, ["hello", "", "world"], "French")

    assert results[0].translated_text == "HELLO"
    assert results[1].translated_text == ""  # blank line passed through untouched
    assert results[2].translated_text == "WORLD"


@patch.object(Translator, "translate", _fake_translate)
def test_translate_text_file(tmp_path):
    input_file = tmp_path / "in.txt"
    output_file = tmp_path / "out.txt"
    input_file.write_text("hello\nworld", encoding="utf-8")

    translator = Translator(api_key="fake-key")
    results = translate_text_file(translator, str(input_file), str(output_file), "French")

    assert len(results) == 2
    assert output_file.read_text(encoding="utf-8") == "HELLO\nWORLD"


@patch.object(Translator, "translate", _fake_translate)
def test_translate_json_values_preserves_keys_and_non_strings(tmp_path):
    input_file = tmp_path / "in.json"
    output_file = tmp_path / "out.json"
    input_file.write_text(
        json.dumps({"greeting": "hello", "count": 5, "empty": ""}), encoding="utf-8"
    )

    translator = Translator(api_key="fake-key")
    translated = translate_json_values(translator, str(input_file), str(output_file), "French")

    assert translated["greeting"] == "HELLO"
    assert translated["count"] == 5  # non-string passed through
    assert translated["empty"] == ""  # empty string passed through

    on_disk = json.loads(output_file.read_text(encoding="utf-8"))
    assert on_disk == translated
