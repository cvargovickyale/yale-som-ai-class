"""Build a human-readable January income-statement HTML report."""

import argparse
import html
import json
from pathlib import Path


def money(value: float) -> str:
    return f"${value:,.2f}"


def cell(value: object) -> str:
    return html.escape(str(value))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an HTML income-statement summary.")
    parser.add_argument("--json-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    json_dir = args.json_dir
    statement = json.loads((json_dir / "income_statement_jan2026.json").read_text())
    reconciliation = json.loads((json_dir / "reconciliation_log.json").read_text())
    judgement_calls = json.loads((json_dir / "judement_calls.json").read_text())

    excluded = [row for row in reconciliation if row.get("included_in_income_statement") == "no"]
    expense_rows = "".join(
        f"<tr><td>{cell(line['label'])}</td><td>{cell(line['category'])}</td><td>{money(line['amount_usd'])}</td></tr>"
        for line in statement["expense_lines"]
    )
    excluded_rows = "".join(
        f"<tr><td>{cell(row['id'])}</td><td>{money(row['amount_used_in_income_statement'])}</td>"
        f"<td>{cell(row['resolution'])}</td></tr>"
        for row in excluded
    )
    judgement_rows = "".join(
        f"<tr><td>{cell(row['transaction_id'])}</td><td>{cell(row['included_in_income_statement'])}</td>"
        f"<td>{money(row['amount_used_in_income_statement'])}</td><td>{cell(row['confidence'])}</td>"
        f"<td><ul>{''.join(f'<li>{cell(item.lstrip("- "))}</li>' for item in row['evidence_for'])}</ul></td></tr>"
        for row in judgement_calls
    )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spoke &amp; Wrench — January 2026 Income Statement</title>
<style>
body{{margin:0;background:#008080;color:#111;font:14px Tahoma,Arial,sans-serif}}
.window{{max-width:1050px;margin:28px auto;background:#c0c0c0;border:3px outset #eee;padding:8px}}
.title{{background:#000080;color:#fff;font-weight:bold;padding:7px 10px}}
.panel{{background:#eee;border:2px inset #fff;margin:12px 0;padding:12px}}
.summary{{display:flex;gap:12px;flex-wrap:wrap}} .metric{{background:#fff;border:2px inset #ddd;padding:12px;min-width:180px}}
.metric strong{{display:block;font-size:22px;margin-top:5px}} table{{width:100%;border-collapse:collapse;background:#fff}}
th,td{{border:1px solid #888;padding:7px;text-align:left;vertical-align:top}} th{{background:#000080;color:#fff}}
tr:nth-child(even){{background:#e8e8e8}} ul{{margin:0;padding-left:18px}} .note{{font-size:12px}}
</style></head><body><main class="window">
<div class="title">SPOKE &amp; WRENCH — JANUARY 2026 INCOME STATEMENT</div>
<section class="panel"><h2>January income statement</h2><div class="summary">
<div class="metric">Revenue<strong>{money(statement['revenue_usd'])}</strong></div>
<div class="metric">Expenses<strong>{money(statement['total_expenses_usd'])}</strong></div>
<div class="metric">Net income<strong>{money(statement['net_income_usd'])}</strong></div>
</div></section>
<section class="panel"><h2>Expense lines</h2><table><tr><th>Label</th><th>Category</th><th>Amount</th></tr>{expense_rows}</table></section>
<section class="panel"><h2>Excluded from income statement</h2><p class="note">These rows remain in the reconciliation log but are excluded from January revenue and expenses.</p>
<table><tr><th>Transaction</th><th>Used amount</th><th>Resolution</th></tr>{excluded_rows}</table></section>
<section class="panel"><h2>Judgement calls</h2><table><tr><th>Transaction</th><th>Included</th><th>Amount used</th><th>Confidence</th><th>Evidence</th></tr>{judgement_rows}</table></section>
</main></body></html>"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page)
    print(f"Wrote report to {args.out}")


if __name__ == "__main__":
    main()
