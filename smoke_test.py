"""Smoke test: confirm the Portkey -> gpt-6-luna path works from this project."""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
load_dotenv(HERE.parent / ".env")

MODEL = "gpt-6-luna"

client = OpenAI(
    api_key=os.environ["PORTKEY_API_KEY"],
    base_url="https://api.portkey.ai/v1",
)

response = client.responses.create(
    model=MODEL,
    input="Reply with exactly: vendor desk online",
)

print(response.output_text)
print("usage:", response.usage)
