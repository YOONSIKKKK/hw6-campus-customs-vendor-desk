r"""Problem 4 - run all 12 practice documents with and without prompt caching.

    .\.venv\Scripts\python.exe run_cache_test.py

Writes output/cache_test.json, one entry per *model call* (not per document),
recording the setup, the document, every token count the API reported, and the
dollar cost from data/prices.json. Also keeps appending to output/usage_log.json
and output/audit_trail.json, as every run does.

The uncached setup is run first so that it cannot benefit from anything the cached
setup leaves warm.
"""

from __future__ import annotations

import json
from pathlib import Path

import agent as vendor_agent
import tools

ROOT = Path(__file__).resolve().parent
PRACTICE_DIR = ROOT / "data" / "practice_docs"
KEY_PATH = ROOT / "data" / "practice_key.json"
CACHE_TEST_PATH = ROOT / "output" / "cache_test.json"
SUMMARY_PATH = ROOT / "output" / "cache_test_summary.json"

SETUPS = ("uncached", "cached")


def practice_docs() -> list[Path]:
    return sorted(PRACTICE_DIR.iterdir())


def score(assessment, expected: dict) -> dict:
    """Compare one assessment against the practice key, field by field."""
    if assessment is None:
        return {"fields_correct": 0, "fields_total": 6, "decision_correct": False}
    got = assessment.model_dump()
    fields = ["vendor", "sku", "unit_price", "lead_time_days", "min_order", "decision"]
    correct = sum(1 for f in fields if got.get(f) == expected.get(f))
    return {
        "fields_correct": correct,
        "fields_total": len(fields),
        "decision_correct": got.get("decision") == expected.get("decision"),
        "mismatches": {
            f: {"got": got.get(f), "expected": expected.get(f)}
            for f in fields
            if got.get(f) != expected.get(f)
        },
    }


def main() -> None:
    key = {entry["file"]: entry for entry in json.loads(KEY_PATH.read_text(encoding="utf-8"))}
    docs = practice_docs()

    CACHE_TEST_PATH.write_text("[]", encoding="utf-8")

    call_records: list[dict] = []
    run_records: list[dict] = []

    for setup in SETUPS:
        print(f"\n########## setup: {setup} ##########", flush=True)
        for position, doc in enumerate(docs, start=1):
            run = vendor_agent.run_on_doc(str(doc), cache_mode=setup, log=True)
            if run["error"]:
                print(f"  [{position:2}/{len(docs)}] {doc.name}: FAILED {run['error']}", flush=True)

            accuracy = score(run["assessment"], key.get(doc.name, {}))

            for call in run["calls"]:
                record = {
                    "setup": setup,
                    "doc": doc.name,
                    "doc_position_in_setup": position,
                    "model": vendor_agent.MODEL_NAME,
                    **call,
                }
                call_records.append(record)

            run_records.append(
                {
                    "setup": setup,
                    "doc": doc.name,
                    "doc_position_in_setup": position,
                    "model_calls": len(run["calls"]),
                    "usage": run["usage"].model_dump(),
                    "cost": run["cost"].model_dump(),
                    "decision": None if run["assessment"] is None else run["assessment"].decision,
                    "accuracy": accuracy,
                    "error": run["error"],
                }
            )

            u = run["usage"]
            print(
                f"  [{position:2}/{len(docs)}] {doc.name:30} "
                f"calls={len(run['calls'])} in={u.input_tokens:6} "
                f"fresh={u.fresh_input_tokens:6} read={u.cache_read_tokens:6} "
                f"write={u.cache_write_tokens:6} out={u.output_tokens:4} "
                f"${run['cost'].total_usd:.6f}",
                flush=True,
            )

    CACHE_TEST_PATH.write_text(json.dumps(call_records, indent=2), encoding="utf-8")

    summary = build_summary(run_records, call_records, len(docs))
    SUMMARY_PATH.write_text(
        json.dumps({"summary": summary, "runs": run_records}, indent=2), encoding="utf-8"
    )
    print("\n" + json.dumps(summary, indent=2), flush=True)


def build_summary(run_records: list[dict], call_records: list[dict], n_docs: int) -> dict:
    summary: dict = {"documents": n_docs, "by_setup": {}}

    for setup in SETUPS:
        runs = [r for r in run_records if r["setup"] == setup]
        calls = [c for c in call_records if c["setup"] == setup]

        total_cost = sum(r["cost"]["total_usd"] for r in runs)
        summary["by_setup"][setup] = {
            "documents": len(runs),
            "model_calls": len(calls),
            "input_tokens": sum(r["usage"]["input_tokens"] for r in runs),
            "fresh_input_tokens": sum(r["usage"]["fresh_input_tokens"] for r in runs),
            "cache_read_tokens": sum(r["usage"]["cache_read_tokens"] for r in runs),
            "cache_write_tokens": sum(r["usage"]["cache_write_tokens"] for r in runs),
            "output_tokens": sum(r["usage"]["output_tokens"] for r in runs),
            "total_cost_usd": total_cost,
            "avg_cost_per_doc_usd": total_cost / len(runs) if runs else 0.0,
            "calls_reporting_cache_reads": sum(
                1 for c in calls if c["usage"]["cache_read_tokens"] > 0
            ),
            "decisions_correct": sum(1 for r in runs if r["accuracy"]["decision_correct"]),
            "fields_correct": sum(r["accuracy"]["fields_correct"] for r in runs),
            "fields_total": sum(r["accuracy"]["fields_total"] for r in runs),
        }

    uncached = summary["by_setup"]["uncached"]
    cached = summary["by_setup"]["cached"]
    summary["savings_usd"] = uncached["total_cost_usd"] - cached["total_cost_usd"]
    summary["savings_pct"] = (
        summary["savings_usd"] / uncached["total_cost_usd"] * 100
        if uncached["total_cost_usd"]
        else 0.0
    )
    # The control check the assignment demands: an uncached call must never report
    # a cache read.
    summary["uncached_is_clean"] = uncached["calls_reporting_cache_reads"] == 0

    # 1,000 docs/day for 30 days.
    for setup in SETUPS:
        s = summary["by_setup"][setup]
        s["projection_1000_per_day_30_days_usd"] = s["avg_cost_per_doc_usd"] * 1000 * 30

    return summary


if __name__ == "__main__":
    main()
