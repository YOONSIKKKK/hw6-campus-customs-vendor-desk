r"""Problem 6 - rerun the 12 practice documents with all three defenses on.

    .\.venv\Scripts\python.exe run_defense_test.py

Same output shape as Problem 5's attack_results.json, plus the token counts and
dollar cost for each document, plus what defense layer 1 stripped and what the
model flagged in `conflicts`.

Writes output/defense_results.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import agent as vendor_agent
import tools
from run_attack_test import KEY_FIELDS, inspect_answer

ROOT = Path(__file__).resolve().parent
PRACTICE_DIR = ROOT / "data" / "practice_docs"
KEY_PATH = ROOT / "data" / "practice_key.json"
RESULTS_PATH = ROOT / "output" / "defense_results.json"


def main() -> None:
    key = {e["file"]: e for e in json.loads(KEY_PATH.read_text(encoding="utf-8"))}
    docs = sorted(PRACTICE_DIR.iterdir())

    tools.TRAP_CALLS_PATH.write_text("[]", encoding="utf-8")

    results = []
    for position, doc in enumerate(docs, start=1):
        run = vendor_agent.run_on_doc(str(doc), cache_mode="cached", defended=True, log=True)
        assessment = run["assessment"]
        expected = key.get(doc.name, {})
        got = assessment.model_dump() if assessment else {}

        fields = {
            f: {"got": got.get(f), "expected": expected.get(f), "match": got.get(f) == expected.get(f)}
            for f in KEY_FIELDS
        }
        decision_match = got.get("decision") == expected.get("decision")
        all_fields_match = all(fr["match"] for fr in fields.values())

        traps = json.loads(tools.TRAP_CALLS_PATH.read_text(encoding="utf-8"))
        traps_for_doc = [t for t in traps if t.get("doc") == doc.name]

        usage, cost = run["usage"], run["cost"]
        entry = {
            "doc": doc.name,
            "defended": True,
            "all_fields_matched": all_fields_match,
            "decision_matched": decision_match,
            "fooled": not (all_fields_match and decision_match),
            "blank_fields": [f for f in KEY_FIELDS if got.get(f) in (None, "", "unknown")],
            "trap_tool_called": bool(traps_for_doc),
            "trap_calls": traps_for_doc,
            "fields": fields,
            "decision": {
                "got": got.get("decision"),
                "expected": expected.get("decision"),
                "match": decision_match,
            },
            "reason": got.get("reason"),
            "answer_inspection": inspect_answer(assessment),
            "tools_offered": vendor_agent.tool_names(True),
            "tools_used": [t.tool for t in run["tool_calls"]],
            "sanitization": {
                "removed_count": run["sanitization"].get("removed_count", 0),
                "removed": run["sanitization"].get("removed", []),
            },
            "conflicts_flagged": list(run["facts"].conflicts) if run["facts"] else [],
            "input_tokens": usage.input_tokens,
            "cached_tokens": usage.cache_read_tokens,
            "cache_write_tokens": usage.cache_write_tokens,
            "fresh_input_tokens": usage.fresh_input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": cost.total_usd,
            "error": run["error"],
        }
        results.append(entry)

        flag = "FOOLED" if entry["fooled"] else "ok    "
        print(
            f"  [{position:2}/{len(docs)}] {doc.name:30} {flag} "
            f"decision={got.get('decision'):17} stripped={entry['sanitization']['removed_count']} "
            f"flagged={len(entry['conflicts_flagged'])} ${cost.total_usd:.6f}",
            flush=True,
        )

    traps_all = json.loads(tools.TRAP_CALLS_PATH.read_text(encoding="utf-8"))
    summary = {
        "documents": len(results),
        "defended": True,
        "fooled": sum(1 for r in results if r["fooled"]),
        "decision_correct": sum(1 for r in results if r["decision_matched"]),
        "all_fields_correct": sum(1 for r in results if r["all_fields_matched"]),
        "field_matches": sum(1 for r in results for f in r["fields"].values() if f["match"]),
        "field_total": len(results) * len(KEY_FIELDS),
        "trap_tools_called": len(traps_all),
        "docs_with_blank_fields": [r["doc"] for r in results if r["blank_fields"]],
        "passages_stripped": sum(r["sanitization"]["removed_count"] for r in results),
        "conflicts_flagged": sum(len(r["conflicts_flagged"]) for r in results),
        "input_tokens": sum(r["input_tokens"] for r in results),
        "output_tokens": sum(r["output_tokens"] for r in results),
        "total_cost_usd": sum(r["cost_usd"] for r in results),
        "avg_cost_per_doc_usd": sum(r["cost_usd"] for r in results) / len(results),
    }

    RESULTS_PATH.write_text(
        json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8"
    )
    print("\n" + json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
