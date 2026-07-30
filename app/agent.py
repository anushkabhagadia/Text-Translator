import os
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads a local .env file, if present, into os.environ

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a translation assistant having a multi-turn conversation with a user.

Rules:
- When given text to translate, translate it and state the detected source language and target language plainly.
- When given a follow-up instruction (e.g. "make it more formal", "now in Japanese instead", "shorter"), apply it to the most recent translation in context — don't ask the user to repeat the original text.
- If a follow-up is ambiguous (e.g. unclear which prior translation it refers to), ask ONE clarifying question rather than guessing.
- Keep responses concise: the translation/result first, then at most one short line of explanation if genuinely useful.
- Never invent content that wasn't in the source text or a prior turn."""


@dataclass
class Turn:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class TranslationAgent:
    """
    Holds conversation state across multiple translation requests.

    Usage:
        agent = TranslationAgent()
        print(agent.send("Translate 'good morning' to French"))
        print(agent.send("Now make it more formal"))
        print(agent.send("Actually, do that in Japanese instead"))
    """

    api_key: Optional[str] = None
    history: List[Turn] = field(default_factory=list)
    client: Groq = field(init=False, repr=False)

    def __post_init__(self):
        self.client = Groq(api_key=self.api_key or os.environ.get("GROQ_API_KEY"))

    def send(self, message: str) -> str:
        """Send one conversational turn and return the agent's reply, updating history."""
        if not message or not message.strip():
            raise ValueError("message must be a non-empty string")

        self.history.append(Turn(role="user", content=message))

        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
            {"role": t.role, "content": t.content} for t in self.history
        ]

        response = self.client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            messages=api_messages,
        )

        reply = response.choices[0].message.content.strip()
        self.history.append(Turn(role="assistant", content=reply))
        return reply

    def reset(self) -> None:
        """Clear conversation history, starting a fresh session."""
        self.history = []

    def transcript(self) -> str:
        """Return the full conversation so far as a readable string (useful for debugging/logging)."""
        lines = []
        for turn in self.history:
            speaker = "You" if turn.role == "user" else "Agent"
            lines.append(f"{speaker}: {turn.content}")
        return "\n".join(lines)
