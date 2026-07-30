#!/usr/bin/env python3
import argparse
import sys

from app.translator import Translator, TranslationError
from app.batch import translate_text_file, translate_json_values


def main():
    parser = argparse.ArgumentParser(description="Translate text using Groq (Llama 3.3).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_single = subparsers.add_parser("translate", help="Translate a single string")
    p_single.add_argument("text", help="Text to translate")
    p_single.add_argument("--to", required=True, dest="target_language", help="Target language")

    p_file = subparsers.add_parser("translate-file", help="Translate a .txt file line by line")
    p_file.add_argument("input_path")
    p_file.add_argument("output_path")
    p_file.add_argument("--to", required=True, dest="target_language")

    p_json = subparsers.add_parser("translate-json", help="Translate string values in a JSON file")
    p_json.add_argument("input_path")
    p_json.add_argument("output_path")
    p_json.add_argument("--to", required=True, dest="target_language")

    args = parser.parse_args()
    translator = Translator()

    try:
        if args.command == "translate":
            result = translator.translate(args.text, args.target_language)
            print(f"Detected source language: {result.detected_source_language}")
            print(f"Translation ({args.target_language}): {result.translated_text}")

        elif args.command == "translate-file":
            results = translate_text_file(
                translator, args.input_path, args.output_path, args.target_language
            )
            print(f"Translated {len(results)} lines -> {args.output_path}")

        elif args.command == "translate-json":
            translated = translate_json_values(
                translator, args.input_path, args.output_path, args.target_language
            )
            print(f"Translated {len(translated)} values -> {args.output_path}")

    except (ValueError, TranslationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
