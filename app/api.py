"""
REST API for the translator.

Endpoints:
    POST /translate         -> translate a single string
    POST /translate/batch   -> translate a list of strings
    GET  /health            -> liveness check

Run with: python -m app.api
"""

from flask import Flask, request, jsonify

from .translator import Translator, TranslationError
from .agent import TranslationAgent

app = Flask(__name__)
translator = Translator()

# NOTE: a single shared agent means all API callers share one conversation
# history — fine for local/demo use, not for multi-user production (where
# you'd key a dict of agents by session/user id instead).
chat_agent = TranslationAgent()


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/translate")
def translate_single():
    """
    Request body:
        {"text": "Bonjour le monde", "target_language": "English"}

    Response:
        {"source_text": "...", "translated_text": "...",
         "detected_source_language": "French", "target_language": "English"}
    """
    body = request.get_json(silent=True) or {}
    text = body.get("text")
    target_language = body.get("target_language")

    if not text or not target_language:
        return jsonify({"error": "Both 'text' and 'target_language' are required"}), 400

    try:
        result = translator.translate(text, target_language)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except TranslationError as e:
        return jsonify({"error": f"Translation failed: {e}"}), 502

    return jsonify(result.to_dict())


@app.post("/translate/batch")
def translate_batch():
    """
    Request body:
        {"texts": ["Hola", "Adios"], "target_language": "English"}

    Response:
        {"results": [ {...}, {...} ]}
    """
    body = request.get_json(silent=True) or {}
    texts = body.get("texts")
    target_language = body.get("target_language")

    if not isinstance(texts, list) or not texts or not target_language:
        return jsonify({"error": "'texts' (non-empty list) and 'target_language' are required"}), 400

    results = []
    for text in texts:
        try:
            results.append(translator.translate(text, target_language).to_dict())
        except (ValueError, TranslationError) as e:
            results.append({"source_text": text, "error": str(e)})

    return jsonify({"results": results})


@app.post("/chat")
def chat():
    """
    Multi-turn conversational translation. Maintains history server-side
    across requests (see NOTE above re: single shared agent).

    Request body:
        {"message": "Translate 'good morning' to French"}
        then later:
        {"message": "Now make it more formal"}

    Response:
        {"reply": "..."}
    """
    body = request.get_json(silent=True) or {}
    message = body.get("message")

    if not message:
        return jsonify({"error": "'message' is required"}), 400

    try:
        reply = chat_agent.send(message)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"reply": reply})


@app.post("/chat/reset")
def chat_reset():
    """Clear the shared chat agent's conversation history."""
    chat_agent.reset()
    return jsonify({"status": "conversation reset"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
