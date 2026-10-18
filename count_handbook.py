r"""Problem 2 - measure the Campus Customs handbook and price it.

Two independent measurements:
  1. Offline, with tiktoken (o200k_base, the encoding the GPT-4o/5/6 family uses).
  2. Empirical, by asking the real gpt-6-luna endpoint to count it for us: we send
     one call with the handbook and one identical call without it, and take the
     difference in reported input_tokens. That difference is the handbook's true
     billable size, free of any per-request overhead.

Writes output/handbook_tokens.json. Run from the project root:
    .\.venv\Scripts\python.exe count_handbook.py
"""

import json
import os
from pathlib import Path

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

MODEL = "gpt-6-luna"
HANDBOOK = ROOT / "data" / "shop_handbook.md"
PRICES = ROOT / "data" / "prices.json"
OUT = ROOT / "output" / "handbook_tokens.json"

# Identical in both probe calls, so it cancels out in the subtraction.
PROBE_TASK = "Reply with the single word: ok"


def offline_counts(text: str) -> dict:
    counts = {}
    for encoding_name in ("o200k_base", "cl100k_base"):
        enc = tiktoken.get_encoding(encoding_name)
        counts[encoding_name] = len(enc.encode(text))
    return counts


def empirical_count(client: OpenAI, text: str) -> dict:
    """input_tokens(handbook + task) - input_tokens(task) = handbook tokens."""
    with_handbook = client.responses.create(
        model=MODEL,
        input=f"{text}\n\n{PROBE_TASK}",
        max_output_tokens=16,
    )
    without_handbook = client.responses.create(
        model=MODEL,
        input=PROBE_TASK,
        max_output_tokens=16,
    )
    return {
        "input_tokens_with_handbook": with_handbook.usage.input_tokens,
        "input_tokens_without_handbook": without_handbook.usage.input_tokens,
        "handbook_tokens": (
            with_handbook.usage.input_tokens - without_handbook.usage.input_tokens
        ),
    }


def price_table(tokens: int, prices: dict) -> dict:
    """Cost of sending `tokens` input tokens, under each billing rate."""
    per_million = tokens / 1_000_000
    uncached_one = per_million * prices["input_per_1m"]
    cached_one = per_million * prices["cached_input_per_1m"]
    write_one = per_million * prices["cache_write_per_1m"]

    # Realistic caching: call 1 writes the cache, calls 2..1000 read it.
    cached_1000_realistic = write_one + cached_one * 999

    return {
        "uncached_1_call": uncached_one,
        "uncached_1000_calls": uncached_one * 1000,
        "cache_write_1_call": write_one,
        "cached_read_1_call": cached_one,
        "cached_1000_calls_realistic": cached_1000_realistic,
        "cached_1000_calls_all_hits": cached_one * 1000,
        "savings_1000_calls": uncached_one * 1000 - cached_1000_realistic,
    }


def main() -> None:
    text = HANDBOOK.read_text(encoding="utf-8")
    prices = json.loads(PRICES.read_text(encoding="utf-8"))[MODEL]

    client = OpenAI(
        api_key=os.environ["PORTKEY_API_KEY"],
        base_url="https://api.portkey.ai/v1",
    )

    result = {
        "model": MODEL,
        "handbook_file": str(HANDBOOK.relative_to(ROOT)).replace("\\", "/"),
        "raw_size": {
            "characters": len(text),
            "whitespace_words": len(text.split()),
            "lines": text.count("\n") + 1,
        },
        "tiktoken": offline_counts(text),
        "empirical": empirical_count(client, text),
        "prices_per_1m": prices,
    }

    # Price using the empirical count - that is what we are actually billed for.
    result["cost_usd"] = price_table(result["empirical"]["handbook_tokens"], prices)

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
