r"""Defense layer 2 (design) - the purchasing decision, made in Python.

The model's job in defended mode is to read a document and report what it says.
It does not get to decide anything. This module parses the handbook's own tables
and applies the four section 4 checks in ordinary Python, so a document that lies
its way past the extractor still has to get past arithmetic it cannot talk to.

Nothing here calls a model. It is deterministic and unit-testable:

    .\.venv\Scripts\python.exe policy.py        # self-check against the practice key
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HANDBOOK_PATH = ROOT / "data" / "shop_handbook.md"

MAX_LEAD_TIME_DAYS = 21
MAX_MIN_ORDER_UNITS = 600


@dataclass(frozen=True)
class CatalogueItem:
    sku: str
    item: str
    retail: float
    max_unit_cost: float
    usual_vendor: str


@dataclass(frozen=True)
class Handbook:
    approved_vendors: dict[str, str]  # normalised name -> display name
    blocked_vendors: dict[str, str]  # normalised name -> reason
    catalogue: dict[str, CatalogueItem]


def normalise(name: str | None) -> str:
    """Lowercase, strip punctuation and legal suffixes, collapse spaces.

    So 'Ivy Print Co.', 'IVY PRINT CO' and 'Ivy  Print Co' all collapse together -
    a vendor cannot slip past the blocked list on punctuation alone.
    """
    if not name:
        return ""
    text = re.sub(r"[^a-z0-9 ]+", " ", name.lower())
    text = re.sub(r"\b(inc|llc|ltd|co|corp|company|the)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _money(cell: str) -> float:
    return float(re.sub(r"[^0-9.]", "", cell))


def _rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):  # separator row
            continue
        rows.append(cells)
    return rows


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    nxt = text.find("\n## ", start + 1)
    return text[start : nxt if nxt != -1 else len(text)]


@lru_cache(maxsize=1)
def load_handbook() -> Handbook:
    text = HANDBOOK_PATH.read_text(encoding="utf-8")

    approved: dict[str, str] = {}
    for cells in _rows(_section(text, "## 5. Approved vendors"))[1:]:
        approved[normalise(cells[1])] = cells[1]

    blocked: dict[str, str] = {}
    for cells in _rows(_section(text, "## 6. Removed and pending vendors"))[1:]:
        blocked[normalise(cells[0])] = cells[1]

    catalogue: dict[str, CatalogueItem] = {}
    for cells in _rows(_section(text, "## 9. Product catalogue"))[1:]:
        catalogue[cells[0].upper()] = CatalogueItem(
            sku=cells[0].upper(),
            item=cells[1],
            retail=_money(cells[3]),
            max_unit_cost=_money(cells[4]),
            usual_vendor=cells[5],
        )

    return Handbook(approved, blocked, catalogue)


@dataclass
class Check:
    name: str
    passed: bool | None  # None = could not be evaluated (missing fact)
    detail: str


@dataclass
class Verdict:
    decision: str  # "recommend" | "do_not_recommend"
    reason: str
    checks: list[Check]


def evaluate(
    vendor: str | None,
    sku: str | None,
    unit_price: float | None,
    lead_time_days: int | None,
    min_order: int | None,
) -> Verdict:
    """Apply handbook section 4. Any failure, or any missing fact, is a refusal."""
    hb = load_handbook()
    key = normalise(vendor)
    checks: list[Check] = []

    # 1. Approved vendor - the blocked list is checked first and wins outright.
    if not vendor:
        checks.append(Check("approved_vendor", None, "no vendor name in the document"))
    elif key in hb.blocked_vendors:
        checks.append(
            Check(
                "approved_vendor",
                False,
                f"{vendor} is on the removed/pending list: {hb.blocked_vendors[key]}",
            )
        )
    elif key in hb.approved_vendors:
        checks.append(Check("approved_vendor", True, f"{vendor} is on the approved list"))
    else:
        checks.append(
            Check("approved_vendor", False, f"{vendor} is not on the approved vendor list")
        )

    # 2. Price against the catalogue maximum for that SKU.
    item = hb.catalogue.get((sku or "").upper())
    if item is None:
        checks.append(
            Check("price", None, f"SKU {sku!r} is not in the catalogue, so no max unit cost")
        )
    elif unit_price is None:
        checks.append(Check("price", None, "the document does not state a unit price"))
    elif unit_price <= item.max_unit_cost:
        checks.append(
            Check(
                "price",
                True,
                f"${unit_price:.2f} is at or below the ${item.max_unit_cost:.2f} max for {item.sku}",
            )
        )
    else:
        checks.append(
            Check(
                "price",
                False,
                f"${unit_price:.2f} is above the ${item.max_unit_cost:.2f} max for {item.sku}",
            )
        )

    # 3. Lead time.
    if lead_time_days is None:
        checks.append(Check("lead_time", None, "the document does not state a lead time"))
    elif lead_time_days <= MAX_LEAD_TIME_DAYS:
        checks.append(
            Check("lead_time", True, f"{lead_time_days} days is within the {MAX_LEAD_TIME_DAYS}-day limit")
        )
    else:
        checks.append(
            Check("lead_time", False, f"{lead_time_days} days exceeds the {MAX_LEAD_TIME_DAYS}-day limit")
        )

    # 4. Minimum order.
    if min_order is None:
        checks.append(Check("min_order", None, "the document does not state a minimum order"))
    elif min_order <= MAX_MIN_ORDER_UNITS:
        checks.append(
            Check("min_order", True, f"{min_order} units is within the {MAX_MIN_ORDER_UNITS}-unit limit")
        )
    else:
        checks.append(
            Check("min_order", False, f"{min_order} units exceeds the {MAX_MIN_ORDER_UNITS}-unit limit")
        )

    failed = [c for c in checks if c.passed is False]
    unknown = [c for c in checks if c.passed is None]

    if failed:
        return Verdict("do_not_recommend", f"The {failed[0].name} check fails: {failed[0].detail}.", checks)
    if unknown:
        return Verdict(
            "do_not_recommend",
            f"The {unknown[0].name} check cannot be completed because {unknown[0].detail}.",
            checks,
        )
    return Verdict(
        "recommend",
        "All four purchasing checks pass: " + "; ".join(c.detail for c in checks) + ".",
        checks,
    )


def _self_check() -> None:
    """Feed the practice key's own facts through the engine and compare decisions."""
    key = json.loads((ROOT / "data" / "practice_key.json").read_text(encoding="utf-8"))
    bad = 0
    for row in key:
        v = evaluate(
            row["vendor"], row["sku"], row["unit_price"], row["lead_time_days"], row["min_order"]
        )
        ok = v.decision == row["decision"]
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {row['file']:30} {v.decision:17} {v.reason[:90]}")
    hb = load_handbook()
    print(
        f"\n{len(key) - bad}/{len(key)} decisions reproduced "
        f"({len(hb.approved_vendors)} approved vendors, {len(hb.blocked_vendors)} blocked, "
        f"{len(hb.catalogue)} catalogue SKUs)"
    )


if __name__ == "__main__":
    _self_check()
