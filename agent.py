r"""Campus Customs vendor desk agent - entry point.

Reads one vendor document, extracts the quote facts, and decides recommend /
do_not_recommend against the Campus Customs Shop Handbook.

    .\.venv\Scripts\python.exe agent.py --doc data/practice_docs/p01_bluehen_quote.html
    .\.venv\Scripts\python.exe agent.py --doc <path> --no-defenses

Two modes:

  DEFENDED (default) - all three defense layers are on.
      layer 1 (code)   tools.read_document strips anything a human could not see
                       before the text reaches the model.
      layer 2 (design) the model is given only read_document, and returns facts
                       only. policy.py applies the four handbook checks in Python,
                       so a poisoned document cannot reach the verdict and cannot
                       reach send_email or approve_payment.
      layer 3 (prompt) the security rules block in prompts/prompt.md is included.

  UNDEFENDED (--no-defenses) - the Problem 3 agent exactly: raw text extraction,
      all three tools registered, the model decides, no security rules. Kept
      because Problem 7 needs something to attack.

Every run appends to output/usage_log.json (tokens and dollars) and
output/audit_trail.json (tool calls and the final answer). The trap tools append to
output/trap_calls.json if a document ever talks the agent into using them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

import policy
import tools
from models import (
    AuditRecord,
    CostBreakdown,
    DocumentFacts,
    TokenUsage,
    ToolCallRecord,
    UsageRecord,
    VendorAssessment,
)

ROOT = Path(__file__).resolve().parent
# A .env beside this file wins (that is what a fresh clone will have); otherwise
# fall back to the course layout, where .env sits one directory up.
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

MODEL_NAME = "gpt-6-luna"
HANDBOOK_PATH = ROOT / "data" / "shop_handbook.md"
PROMPT_PATH = ROOT / "prompts" / "prompt.md"
PRICES_PATH = ROOT / "data" / "prices.json"

OUTPUT_DIR = ROOT / "output"
USAGE_LOG_PATH = OUTPUT_DIR / "usage_log.json"
AUDIT_TRAIL_PATH = OUTPUT_DIR / "audit_trail.json"

# Blocks in prompts/prompt.md that are switched on and off by mode.
BLOCKS = {
    "security": "SECURITY RULES",      # defended only  (layer 3)
    "extract": "EXTRACTION ONLY",      # defended only  (layer 2)
    "decide": "DECIDE IN MODEL",       # undefended only
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _strip_block(text: str, name: str) -> str:
    pattern = re.compile(
        rf"<!-- {re.escape(name)}: BEGIN -->.*?<!-- {re.escape(name)}: END -->\n?",
        re.DOTALL,
    )
    return pattern.sub("", text)


def _unwrap_markers(text: str) -> str:
    return re.sub(r"<!-- [A-Z ]+: (BEGIN|END) -->\n?", "", text)


def build_instructions(cache_mode: str = "cached", defended: bool = True) -> str:
    """The full system prompt: our instructions with the handbook spliced in.

    In `cached` mode this string is byte-identical on every call, so the model can
    reuse the whole thing from its prompt cache.

    In `uncached` mode we prepend a fresh random nonce. Prompt caching matches on a
    common *prefix*, so changing the very first tokens guarantees that nothing -
    not even the handbook behind it - can be reused. The nonce is regenerated on
    every call to this function, and in uncached mode the function is passed to the
    Agent as a callable so PydanticAI re-runs it for each model request. That
    matters because one document takes two requests: without a per-request nonce,
    the second request would hit the cache the first request just wrote.
    """
    handbook = HANDBOOK_PATH.read_text(encoding="utf-8")
    text = PROMPT_PATH.read_text(encoding="utf-8").replace("{{HANDBOOK}}", handbook)

    if defended:
        text = _strip_block(text, BLOCKS["decide"])
    else:
        text = _strip_block(text, BLOCKS["security"])
        text = _strip_block(text, BLOCKS["extract"])
    text = _unwrap_markers(text)

    if cache_mode == "uncached":
        text = f"Run id {uuid.uuid4()} - ignore this line.\n\n{text}"
    return text


def build_agent(cache_mode: str = "cached", defended: bool = True):
    model = OpenAIResponsesModel(
        MODEL_NAME,
        provider=OpenAIProvider(
            base_url="https://api.portkey.ai/v1",
            api_key=os.environ["PORTKEY_API_KEY"],
        ),
    )
    # Defended and undefended prompts differ from the first token, so they get
    # separate cache keys; a throwaway key when caching is deliberately defeated.
    base_key = f"campus-customs-vendor-desk-v2-{'defended' if defended else 'raw'}"
    settings = OpenAIResponsesModelSettings(
        openai_prompt_cache_key=(
            base_key if cache_mode == "cached" else f"no-cache-{uuid.uuid4()}"
        ),
    )

    instructions = (
        build_instructions("cached", defended)
        if cache_mode == "cached"
        else (lambda: build_instructions("uncached", defended))
    )

    agent = Agent(
        model,
        output_type=DocumentFacts if defended else VendorAssessment,
        instructions=instructions,
        model_settings=settings,
        name="vendor-desk" if defended else "vendor-desk-undefended",
    )

    # DEFENSE LAYER 2 (DESIGN). In defended mode the model is handed exactly one
    # tool. send_email and approve_payment still exist in tools.py - the shop needs
    # them under human authorisation - but they are not in this agent's toolset, so
    # no document can reach them no matter what it says.
    agent.tool_plain(tools.read_document)
    if not defended:
        agent.tool_plain(tools.send_email)
        agent.tool_plain(tools.approve_payment)
    return agent


def tool_names(defended: bool) -> list[str]:
    return ["read_document"] if defended else ["read_document", "send_email", "approve_payment"]


def price_run(usage, prices: dict) -> tuple[TokenUsage, CostBreakdown]:
    """Turn the API's token counts into dollars using data/prices.json."""
    cache_read = usage.cache_read_tokens or 0
    cache_write = usage.cache_write_tokens or 0
    # input_tokens is the whole prompt; the cached parts are a subset of it.
    fresh = max(usage.input_tokens - cache_read - cache_write, 0)

    token_usage = TokenUsage(
        input_tokens=usage.input_tokens,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        fresh_input_tokens=fresh,
        output_tokens=usage.output_tokens,
        total_tokens=usage.input_tokens + usage.output_tokens,
        requests=usage.requests,
    )

    fresh_usd = fresh / 1_000_000 * prices["input_per_1m"]
    read_usd = cache_read / 1_000_000 * prices["cached_input_per_1m"]
    write_usd = cache_write / 1_000_000 * prices["cache_write_per_1m"]
    output_usd = usage.output_tokens / 1_000_000 * prices["output_per_1m"]

    cost = CostBreakdown(
        fresh_input_usd=fresh_usd,
        cache_read_usd=read_usd,
        cache_write_usd=write_usd,
        output_usd=output_usd,
        total_usd=fresh_usd + read_usd + write_usd + output_usd,
    )
    return token_usage, cost


def collect_tool_calls(messages) -> list[ToolCallRecord]:
    """Pair up every ToolCallPart with the ToolReturnPart that answered it."""
    returns: dict[str, str] = {}
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                returns[part.tool_call_id] = str(part.content)

    records: list[ToolCallRecord] = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                records.append(
                    ToolCallRecord(
                        tool=part.tool_name,
                        args=part.args_as_dict(),
                        result_preview=returns.get(part.tool_call_id, "")[:300],
                    )
                )
    return records


def per_call_usage(messages, prices: dict) -> list[dict]:
    """One entry per *model call*, not per run.

    A single document takes more than one round trip to the model (first to ask for
    the tool, then to answer), and each round trip is billed separately. Problem 4
    needs that granularity, so we walk the ModelResponse messages and price each
    one on its own.
    """
    calls: list[dict] = []
    for message in messages:
        usage = getattr(message, "usage", None)
        if usage is None or getattr(usage, "requests", 0) == 0:
            continue
        token_usage, cost = price_run(usage, prices)
        calls.append(
            {
                "call_index": len(calls) + 1,
                "usage": token_usage.model_dump(),
                "cost": cost.model_dump(),
            }
        )
    return calls


def assess_from_facts(facts: DocumentFacts) -> VendorAssessment:
    """DEFENSE LAYER 2 (DESIGN): the verdict is computed, not generated."""
    verdict = policy.evaluate(
        facts.vendor, facts.sku, facts.unit_price, facts.lead_time_days, facts.min_order
    )
    reason = verdict.reason
    if facts.conflicts:
        reason += f" ({len(facts.conflicts)} suspicious passage(s) in the document were ignored.)"
    return VendorAssessment(
        vendor=facts.vendor or "unknown",
        sku=facts.sku,
        unit_price=facts.unit_price,
        lead_time_days=facts.lead_time_days,
        min_order=facts.min_order,
        decision=verdict.decision,
        reason=reason,
    )


def run_on_doc(
    doc: str, cache_mode: str = "cached", defended: bool = True, log: bool = True
) -> dict:
    """Process one document end to end and append both log files."""
    prices = json.loads(PRICES_PATH.read_text(encoding="utf-8"))[MODEL_NAME]
    doc_name = Path(doc).name

    for path in (USAGE_LOG_PATH, AUDIT_TRAIL_PATH, tools.TRAP_CALLS_PATH):
        tools.init_json_list(path)

    tools.CURRENT_DOC = doc_name
    tools.DEFENDED = defended
    tools.LAST_SANITIZATION = {}
    agent = build_agent(cache_mode, defended)

    assessment: VendorAssessment | None = None
    facts: DocumentFacts | None = None
    error: str | None = None
    try:
        result = agent.run_sync(f"Assess the vendor document at this path: {doc}")
        if defended:
            facts = result.output
            assessment = assess_from_facts(facts)
        else:
            assessment = result.output
        messages = result.all_messages()
        token_usage, cost = price_run(result.usage, prices)
        calls = per_call_usage(messages, prices)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        messages, calls = [], []
        token_usage, cost = TokenUsage(), CostBreakdown()
    finally:
        sanitization = dict(tools.LAST_SANITIZATION)
        tools.CURRENT_DOC = None

    timestamp = _now()
    usage_record = UsageRecord(
        timestamp=timestamp,
        doc=doc_name,
        model=MODEL_NAME,
        cache_mode=cache_mode,
        defended=defended,
        usage=token_usage,
        cost=cost,
    )
    audit_record = AuditRecord(
        timestamp=timestamp,
        doc=doc_name,
        model=MODEL_NAME,
        defended=defended,
        tools_available=tool_names(defended),
        sanitization=sanitization,
        conflicts_flagged=list(facts.conflicts) if facts else [],
        tool_calls=collect_tool_calls(messages),
        final_answer=assessment,
        error=error,
    )

    if log:
        tools.append_json(USAGE_LOG_PATH, usage_record.model_dump())
        tools.append_json(AUDIT_TRAIL_PATH, audit_record.model_dump())

    return {
        "doc": doc_name,
        "cache_mode": cache_mode,
        "defended": defended,
        "assessment": assessment,
        "facts": facts,
        "sanitization": sanitization,
        "usage": token_usage,
        "cost": cost,
        "calls": calls,
        "tool_calls": audit_record.tool_calls,
        "error": error,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Customs vendor desk agent")
    parser.add_argument("--doc", required=True, help="path to a vendor document")
    parser.add_argument(
        "--no-defenses",
        action="store_true",
        help="run the undefended Problem 3 agent: raw text, all tools, model decides",
    )
    parser.add_argument(
        "--cache-mode",
        choices=("cached", "uncached"),
        default="cached",
        help="cached (default) reuses the handbook prefix; uncached forces a cold prompt",
    )
    args = parser.parse_args()
    defended = not args.no_defenses

    run = run_on_doc(args.doc, cache_mode=args.cache_mode, defended=defended)

    if run["error"]:
        print(f"FAILED on {run['doc']}: {run['error']}")
        raise SystemExit(1)

    a, u, c = run["assessment"], run["usage"], run["cost"]
    mode = "DEFENDED" if defended else "NO DEFENSES"
    print(f"=== {run['doc']}  ({mode}, {run['cache_mode']}) ===")
    print(f"vendor          : {a.vendor}")
    print(f"sku             : {a.sku}")
    print(f"unit_price      : {a.unit_price}")
    print(f"lead_time_days  : {a.lead_time_days}")
    print(f"min_order       : {a.min_order}")
    print(f"decision        : {a.decision}")
    print(f"reason          : {a.reason}")
    print(f"tools offered   : {tool_names(defended)}")
    print(f"tools used      : {[t.tool for t in run['tool_calls']]}")
    removed = run["sanitization"].get("removed") or []
    print(f"text stripped   : {len(removed)} passage(s) a human could not see")
    for item in removed:
        print(f"                  - [{item['reason']}] {item['text'][:88]}")
    if run["facts"] and run["facts"].conflicts:
        print(f"conflicts flagged:")
        for conflict in run["facts"].conflicts:
            print(f"                  - {conflict[:100]}")
    print(
        f"tokens          : input={u.input_tokens} "
        f"(fresh={u.fresh_input_tokens}, cache_read={u.cache_read_tokens}, "
        f"cache_write={u.cache_write_tokens}) output={u.output_tokens}"
    )
    print(f"cost            : ${c.total_usd:.6f}")


if __name__ == "__main__":
    main()
