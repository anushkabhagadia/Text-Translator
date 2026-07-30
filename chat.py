#!/usr/bin/env python3
"""
Interactive multi-turn translation chat.

Run with:
    python chat.py

Then just type naturally:
    > Translate "good morning" to French
    > Now make it more formal
    > Actually, do that in Japanese instead
    > exit

Type 'reset' to clear history and start a new conversation,
or 'exit' / 'quit' to leave.
"""

from app.agent import TranslationAgent


def main():
    print("Translation Agent — multi-turn chat")
    print("Type a translation request, then follow-up instructions naturally.")
    print("Commands: 'reset' to clear history, 'exit' to quit.\n")

    agent = TranslationAgent()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        if user_input.lower() == "reset":
            agent.reset()
            print("(conversation history cleared)\n")
            continue

        try:
            reply = agent.send(user_input)
            print(f"\n{reply}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
