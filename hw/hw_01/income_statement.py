"""Build the January 2026 income statement from the reconciliation log."""

import argparse
import json
import re
from pathlib import Path


REVENUE_TERMS = ("revenue", "deposit", "invoice", "service")
CATEGORY_TERMS = {
    "rent": ("rent",),
    "utilities": ("utility", "utilities", "electric", "internet", "aws"),
    "cogs_parts": ("parts", "bike parts", "tubes", "brake", "chain"),
    "shipping": ("shipping", "courier", "delivery"),
    "tools_equipment": ("tool", "equipment", "repair stand"),
    "insurance": ("insurance",),
    "office_supplies": ("office", "staples"),
    "shop_supplies": ("shop", "home depot", "bins", "broom"),
}


def category_for(row: dict) -> str:
    text = f"{row['id']} {row['resolution']}".lower()
    for category, terms in CATEGORY_TERMS.items():
        if any(term in text for term in terms):
            return category
    return "other"


def is_revenue(row: dict) -> bool:
    text = row["resolution"].lower()
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in REVENUE_TERMS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Roll reconciliation decisions into an income statement.")
    parser.add_argument("--docs-dir", type=Path, required=True, help="Accepted for a consistent homework command format.")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    reconciliation_path = args.out_dir / "reconciliation_log.json"
    if not reconciliation_path.exists():
        raise SystemExit(f"Required input is missing: {reconciliation_path}")
    rows = json.loads(reconciliation_path.read_text())
    included = [row for row in rows if row.get("included_in_income_statement") == "yes"]

    revenue = sum(row["amount_used_in_income_statement"] for row in included if is_revenue(row))
    expense_lines = [
        {
            "label": row["id"],
            "amount_usd": row["amount_used_in_income_statement"],
            "category": category_for(row),
            "sources": row["sources"],
        }
        for row in included
        if not is_revenue(row)
    ]
    total_expenses = sum(line["amount_usd"] for line in expense_lines)
    statement = {
        "period": "2026-01",
        "revenue_usd": round(revenue, 2),
        "expense_lines": expense_lines,
        "total_expenses_usd": round(total_expenses, 2),
        "net_income_usd": round(revenue - total_expenses, 2),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.out_dir / "income_statement_jan2026.json"
    output_path.write_text(json.dumps(statement, indent=2) + "\n")
    print(f"Wrote January income statement to {output_path}")


if __name__ == "__main__":
    main()
