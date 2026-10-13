# Homework 5 AI Prompts

Records the prompt used for each problem, plus at most one follow-up when a
correction or clarification was needed. Each prompt is typed in my own words,
one problem at a time. Other decisions made while working a problem are
recorded in that problem's notes. Coding assistant: Claude Code.

## Problem 2 — Study the Campus Customs database

**Prompt:** P2 study the database and set up the working copy
data/campus_customs_new.db - later problems will update this. we already
looked through the db. start a new harness.md in output that lists fields and
one line on why the table matters for each agent (if it does)

**Follow-up prompt used:** none.

**Notes:**

- No LLM was used. The database was studied with direct SQL (`sqlite3`),
  opened read-only.
- Placed the data at `hw5/data/` and made the working copy
  `campus_customs_new.db` as a byte-for-byte copy of `campus_customs.db`
  (same SHA-1). Both files are committed, per the submission rules; only
  SQLite's temporary `-journal`/`-wal`/`-shm` files are gitignored.
- Started `output/harness.md`. Section 1 (Data) lists every table and field
  and says why each table matters to each agent.
- Findings that shape later problems:
  - Today is `desk.date_today` = 2026-08-31. Cash is $3,400 in checking.
    No payments yet.
  - Invoice 501 ($840, Bulldog Print Co) is 3 days overdue, so that vendor
    can't ship. Rent ($2,400) is due in 2 days. Paying both leaves $160.
  - Ticket 101 needs a tee in S (0 in stock). Ticket 103 wants 20 hoodies
    in M (8 in stock, 12 short; 12 × $22 = $264). Both reprints are apparel
    from the blocked vendor (5-day lead time).
  - There's no SKU → vendor link (only the `specialty` text), and no table
    for pending approvals or reprint orders. Those will need new tools in P5.
  - The links are clean: every ticket's SKU/size, invoice, and lease exists.
