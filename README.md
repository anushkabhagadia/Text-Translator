# LLM Text Translator

A translation tool built on the Groq API (running Llama 3.3 70B, an open
model) instead of a dedicated translation service — an upgrade of an
earlier rule-based translator project, built to practice real LLM API
integration: prompt design, structured output parsing, and error handling
around a non-deterministic API. Groq's free tier means this can be run
and demoed at no cost.

## Why an LLM instead of a translation API?

Dedicated translation APIs (Google Translate, DeepL) are faster and cheaper
per request. I used an LLM instead, deliberately, because:

- **Auto-detection is free.** One prompt both detects the source language
  and translates — no separate language-ID library or step.
- **Instructions travel with the text.** "Preserve markdown formatting" or
  "keep this tone formal" are prompt instructions, not API parameters — this
  is straightforward for an LLM and awkward-to-impossible for a rule-based
  translation API.
- **The point of the project was LLM integration practice**, not building
  the most cost-efficient translator possible. That trade-off is stated
  here rather than hidden.

## What it does

- Translates a single string, auto-detecting the source language
- **Batch-translates a whole `.txt` file**, line by line
- **Batch-translates a JSON file's string values** (e.g. a UI strings /
  i18n file), leaving keys and non-string values untouched
- **Multi-turn conversational translation** (`chat.py` / `/chat` endpoint):
  holds conversation history so follow-ups like "make it more formal" or
  "now do that in Japanese instead" are understood in context, without
  re-supplying the original text
- Exposes both a **CLI** and a **REST API (Flask)** — same underlying logic,
  multiple interfaces
- Handles the model returning malformed JSON or wrapping output in markdown
  code fences (both observed in testing) without crashing

## One-shot vs. conversational: two different interaction patterns

This repo intentionally contains both, to show the distinction clearly:

| | `Translator` (translator.py) | `TranslationAgent` (agent.py) |
|---|---|---|
| Interaction | One request per response | Multi-turn, holds history |
| Use case | Batch jobs, API integrations | Interactive back-and-forth |
| "Make it more formal" | Needs the full text resent | Understood from context |
| State | Stateless | Stateful (in-memory per session) |

Same model, same API — the difference is entirely in how the conversation
is structured and what context is carried forward.

## What's in here

```
text-translator/
├── app/
│   ├── translator.py    # core Translator class, wraps the Groq API
│   ├── batch.py          # batch file / JSON translation
│   ├── agent.py           # multi-turn conversational agent
│   └── api.py              # Flask REST API (translate + chat endpoints)
├── cli.py                  # command-line interface
├── chat.py                 # interactive multi-turn chat CLI
├── tests/
│   ├── test_translator.py  # mocked-API unit tests
│   ├── test_batch.py
│   └── test_agent.py
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com) — no credit
card required, generous free-tier rate limits.

## Usage

**CLI:**
```bash
# Single string
python cli.py translate "Bonjour tout le monde" --to English

# Whole text file, line by line
python cli.py translate-file input.txt output.txt --to Spanish

# JSON i18n-style file (translates values, keeps keys)
python cli.py translate-json strings.json strings_fr.json --to French
```

**Multi-turn chat (CLI):**
```bash
python chat.py
```
```
> Translate "good morning" to French
Bonjour (detected source: English, target: French)

> Now make it more formal
Bonjour, et bonne journée à vous

> Actually, do that in Japanese instead
おはようございます
```
Type `reset` to clear history, `exit` to quit.

**REST API:**
```bash
python -m app.api
# then, in another terminal:

curl -X POST http://localhost:5000/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour le monde", "target_language": "English"}'

curl -X POST http://localhost:5000/translate/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hola", "Adios"], "target_language": "English"}'

# Multi-turn chat endpoint (server holds conversation state):
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Translate good morning to French"}'

curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Now make it more formal"}'

# Clear chat history:
curl -X POST http://localhost:5000/chat/reset
```

## Tests

Tests mock the Groq client, so the suite runs without a real API key
or making real (paid) API calls:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

13 tests covering: successful translation, markdown-code-fence stripping,
empty-input validation, malformed-JSON handling, blank-line skipping in
batch mode, file I/O round-trips, and — for the conversational agent —
that follow-up turns actually send full history to the API (the core
agentic behavior), history reset, and transcript formatting.

## Known limitations / next steps

- No retry/backoff on API rate limits yet — a production version would need
  this, since a single 429 currently fails the whole batch call.
- Batch translation calls the API once per line/value sequentially; for
  large files this could be parallelized (with rate-limit handling added
  first).
- No caching — translating the same string twice makes two API calls.
- The chat agent's history is in-memory only (lost on restart) and, via the
  REST `/chat` endpoint, shared across all callers rather than per-user —
  fine for local/demo use, not multiple simultaneous users. A real version
  would key conversations by session ID and persist them.
- The agent has memory but no tools — it reasons over conversation history
  but can't look anything up or take actions. Adding tools (e.g. a glossary
  lookup, a translation-memory database) is the natural next step toward a
  fuller agentic system.
