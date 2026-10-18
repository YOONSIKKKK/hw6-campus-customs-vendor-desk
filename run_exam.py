r"""Problem 8 - run the fully defended agent over data/exam_docs/.

    .\.venv\Scripts\python.exe run_exam.py

Writes output/exam_results.json: a plain JSON list with exactly one entry per exam
document, in the field order the assignment specifies. Nothing in this file is
hand-edited; rerunning this script regenerates it from scratch.
"""

from __future__ import annotations

import json
from pathlib import Path

import agent as vendor_agent
import tools

ROOT = Path(__file__).resolve().parent
EXAM_DIR = ROOT / "data" / "exam_docs"
RESULTS_PATH = ROOT / "output" / "exam_results.json"


def main() -> None:
    docs = sorted(EXAM_DIR.iterdir())
    before = json.loads(tools.TRAP_CALLS_PATH.read_text(encoding="utf-8"))
    seen_traps = len(before)

    results = []
    for position, doc in enumerate(docs, start=1):
        run = vendor_agent.run_on_doc(str(doc), cache_mode="cached", defended=True, log=True)
        a = run["assessment"]
        usage, cost = run["usage"], run["cost"]

        traps = json.loads(tools.TRAP_CALLS_PATH.read_text(encoding="utf-8"))
        fired = len(traps) > seen_traps
        seen_traps = len(traps)

        entry = {
            "file": doc.name,
            "vendor": a.vendor if a else None,
            "sku": a.sku if a else None,
            "unit_price": a.unit_price if a else None,
            "lead_time_days": a.lead_time_days if a else None,
            "min_order": a.min_order if a else None,
            "decision": a.decision if a else "do_not_recommend",
            "reason": a.reason if a else f"Processing failed: {run['error']}",
            "trap_tool_called": fired,
            "input_tokens": usage.input_tokens,
            "cached_tokens": usage.cache_read_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd": cost.total_usd,
        }
        results.append(entry)

        stripped = run["sanitization"].get("removed_count", 0)
        flagged = len(run["facts"].conflicts) if run["facts"] else 0
        print(
            f"  [{position:2}/{len(docs)}] {doc.name:18} {entry['decision']:17} "
            f"{str(entry['vendor'])[:24]:24} {entry['sku']} ${entry['unit_price']} "
            f"{entry['lead_time_days']}d min{entry['min_order']} "
            f"stripped={stripped} flagged={flagged} ${cost.total_usd:.6f}",
            flush=True,
        )

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(
        f"\n{len(results)} documents | "
        f"{sum(1 for r in results if r['decision'] == 'recommend')} recommend / "
        f"{sum(1 for r in results if r['decision'] == 'do_not_recommend')} do_not_recommend | "
        f"traps fired: {sum(1 for r in results if r['trap_tool_called'])} | "
        f"total ${sum(r['cost_usd'] for r in results):.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
