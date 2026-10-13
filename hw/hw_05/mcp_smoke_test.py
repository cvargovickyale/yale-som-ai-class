"""P4 smoke test: call every MCP tool over stdio using hw5/.mcp.json; compare to SQL."""
import asyncio, json, sqlite3, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path
from fastmcp import Client

HW5 = Path(sys.argv[1]); OUT = HW5 / "output" / "mcp_smoke.json"
DB = HW5 / "data" / "campus_customs_new.db"
PROMPT = sys.argv[2]
db = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True); db.row_factory = sqlite3.Row
q = lambda sql, *a: [dict(r) for r in db.execute(sql, a)]
today = q("select date_today from desk")[0]["date_today"]

def sql_stock(sku, size, need):
    rows = q("select size, qty from inventory where sku=? order by rowid", sku)
    on = next(r["qty"] for r in rows if r["size"] == size)
    return {"sizes": rows, "total_on_hand": sum(r["qty"] for r in rows),
            "qty_on_hand": on, "shortfall": max(0, need - on)}
def sql_price(sku, qty):
    p = q("select unit_cost, list_price from pricing where sku=?", sku)[0]
    return {"unit_cost": p["unit_cost"], "list_price": p["list_price"],
            "margin_pct_at_list": round((p["list_price"]-p["unit_cost"])/p["list_price"]*100, 1),
            "order_revenue": p["list_price"]*qty, "order_cost": p["unit_cost"]*qty,
            "order_profit": (p["list_price"]-p["unit_cost"])*qty,
            "cash_balance": q("select balance from cash_accounts where name='checking'")[0]["balance"]}
def sql_ticket(tid):
    t = q("select * from tickets where id=?", tid)[0]; e = {"ticket": t}
    if t["invoice_id"]:
        e["invoice"] = q("""select i.id, i.amount, i.due_date, v.name vendor_name, v.lead_days,
            cast(julianday(?) - julianday(i.due_date) as int) days_overdue
            from invoices i join vendors v on v.id=i.vendor_id where i.id=?""", today, t["invoice_id"])[0]
    if t["lease_id"]:
        e["lease"] = q("""select landlord, monthly_rent, next_due,
            cast(julianday(next_due) - julianday(?) as int) days_until_due from leases where id=?""", today, t["lease_id"])[0]
    return e

def matches(tool, out, exp):
    if tool == "check_stock":
        r = out["requested"]
        return (out["sizes"] == exp["sizes"] and out["total_on_hand"] == exp["total_on_hand"]
                and r["qty_on_hand"] == exp["qty_on_hand"] and r["shortfall"] == exp["shortfall"])
    if tool == "price_and_margin":
        return all(out[k] == exp[k] for k in ["unit_cost","list_price","margin_pct_at_list","order_revenue","order_cost","order_profit"]) \
            and out["cash_accounts"][0]["balance"] == exp["cash_balance"]
    if tool == "get_ticket":
        ok = out["ticket"] == exp["ticket"]
        if "invoice" in exp:
            i = out["linked_invoice"]; x = exp["invoice"]
            ok &= all(i[k] == x[k] for k in ["id","amount","due_date","vendor_name","lead_days","days_overdue"])
        if "lease" in exp:
            l = out["linked_lease"]; x = exp["lease"]
            ok &= all(l[k] == x[k] for k in ["landlord","monthly_rent","next_due","days_until_due"])
        ok &= ("linked_invoice" in out) == ("invoice" in exp) and ("linked_lease" in out) == ("lease" in exp)
        return ok

CASES = [
  ("check_stock", {"sku":"CC-TEE-WHITE","size":"S","qty_needed":1}, "Ticket 101: can we fill 1 white tee in S?", lambda: sql_stock("CC-TEE-WHITE","S",1)),
  ("check_stock", {"sku":"CC-HOOD-NAVY","size":"M","qty_needed":20}, "Ticket 103: can we fill 20 navy hoodies in M?", lambda: sql_stock("CC-HOOD-NAVY","M",20)),
  ("price_and_margin", {"sku":"CC-HOOD-NAVY","qty":20,"discount_pct":0}, "Ticket 103: cost, revenue, margin for 20 hoodies at list", lambda: sql_price("CC-HOOD-NAVY",20)),
  ("price_and_margin", {"sku":"CC-HOOD-NAVY","qty":12,"discount_pct":0}, "Ticket 103: cost of reprinting the 12-hoodie shortfall", lambda: sql_price("CC-HOOD-NAVY",12)),
  ("get_ticket", {"ticket_id":101}, "Ticket 101: requester + linked invoice", lambda: sql_ticket(101)),
  ("get_ticket", {"ticket_id":102}, "Ticket 102: requester + linked lease", lambda: sql_ticket(102)),
  ("get_ticket", {"ticket_id":103}, "Ticket 103: requester + request, nothing linked", lambda: sql_ticket(103)),
]
ERRORS = [
  ("check_stock", {"sku":"CC-NOPE"}, "Unknown SKU must error, not invent stock"),
  ("check_stock", {"sku":"CC-TEE-WHITE","size":"XXL"}, "Unknown size must error"),
  ("price_and_margin", {"sku":"CC-NOPE","qty":1}, "Unknown SKU must error, not invent a price"),
  ("get_ticket", {"ticket_id":999}, "Unknown ticket must error"),
]

async def main():
    sha_before = hashlib.sha1(DB.read_bytes()).hexdigest()
    cfg = json.loads((HW5/".mcp.json").read_text())
    tests, errors = [], []
    async with Client(cfg) as c:
        listed = [{"name": t.name, "description": t.description, "inputs": t.inputSchema,
                   "read_only": t.annotations.readOnlyHint if t.annotations else None}
                  for t in await c.list_tools()]
        for tool, args, purpose, exp_fn in CASES:
            res = await c.call_tool(tool, args)
            out = res.structured_content.get("result", res.structured_content)
            exp = exp_fn()
            tests.append({"tool": tool, "purpose": purpose, "arguments": args, "output": out,
                          "expected_from_sql": exp, "matches_db": matches(tool, out, exp)})
        for tool, args, purpose in ERRORS:
            res = await c.call_tool(tool, args, raise_on_error=False)
            errors.append({"tool": tool, "purpose": purpose, "arguments": args,
                           "is_error": res.is_error, "message": res.content[0].text,
                           "pass": res.is_error})
    sha_after = hashlib.sha1(DB.read_bytes()).hexdigest()
    report = {
      "problem": "P4 — Add the MCP server to the vibe coder and test each tool",
      "prompt": PROMPT,
      "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "how": ("Claude Code launched the server from hw5/.mcp.json (stdio: .venv/bin/python mcp_server/server.py) "
              "and called each tool over the MCP protocol with FastMCP's Client. No LLM involved. Each output is "
              "compared to an independent SQL query on the same database."),
      "server": "campus-customs", "database": "data/campus_customs_new.db", "date_today": today,
      "tools_listed": listed, "tests": tests, "error_checks": errors,
      "database_unchanged": {"sha1_before": sha_before, "sha1_after": sha_after, "unchanged": sha_before == sha_after},
      "summary": {"tests_passed": sum(t["matches_db"] for t in tests), "tests_total": len(tests),
                  "error_checks_passed": sum(e["pass"] for e in errors), "error_checks_total": len(errors)},
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"]), "db unchanged:", report["database_unchanged"]["unchanged"])
    for t in tests: print(t["matches_db"], t["tool"], t["arguments"])
    for e in errors: print(e["pass"], e["tool"], e["arguments"], "->", e["message"])
asyncio.run(main())
