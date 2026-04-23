import os
import anthropic

API_KEY = os.getenv("ANTHROPIC_API_KEY", "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")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

client = anthropic.Anthropic(api_key=API_KEY)


def ask_claude(prompt: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.content[0].text


def list_available_models():
    return client.models.list()