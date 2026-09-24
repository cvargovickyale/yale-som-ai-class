# Homework 1 AI Prompts

This file records the prompts used with AI for each homework problem. It will be
updated as the work progresses. Reusable extraction commands follow this form:

```zsh
python <script>.py --docs-dir PATH --out-dir output
```

## Problem 2 — Read Receipts

**Prompt:** Extract one structured JSON row per purchase receipt PDF. For each
row, return `vendor`, `date`, `description`, `amount_usd`, `category`,
`source_file`, and `fields_not_found`. Use only facts present in the receipt,
do not invent missing values, and save the JSON array to `output/receipts.json`.
The full reusable prompt is in `prompts/receipts_extract.md`.

**Follow-up needed:** If the first response does not identify the relevant
business documents, assumptions, and required output clearly, ask AI to cite
the source documents and revise the result in the required format.

## Problem 3 — Read Bank Statement

**Prompt:** Extract every January bank-statement transaction into one JSON row
per line with `date`, `description`, positive `amount_usd`, `classification`,
`direction`, `accounting_label`, `expense_type`, `source_file`, and
`fields_not_found`. Use the LLM prompt in `prompts/bank_extract.md` and save the
array to `output/bank_transactions.json`. Run with:

```zsh
python read_bank.py --docs-dir PATH --out-dir output
```

**Follow-up needed:** If the first extraction misses lines or misclassifies a
transaction, ask AI to reconcile the output against every statement line,
preserve positive amounts, and explain or correct each disputed classification.

**Follow-up prompt used:** Run the bank extraction now using the configured LLM
endpoint and save the resulting JSON to `output/bank_transactions.json`.

## Upcoming problems

- Problem 4: Read credit card statement
- Problem 5: Reconciliation log
- Problem 6: Judgement calls
- Problem 7: January income statement
- Problem 8: Income statement webpage
- Problem 9: Process flow diagram
- Problem 10: Zip the completed HW1 package

## Problem 4 — Read Credit Card Statement

**Prompt:** Extract every January credit-card charge into one JSON row per
charge with `date`, `merchant`, `amount_usd`, `classification`,
`expense_category`, `source_file`, and `fields_not_found`. Set
`expense_category` to null for personal charges and use the preliminary business
categories from Problem 3 for business charges. Save the array to
`output/credit_card_transactions.json` using:

```zsh
python read_card.py --docs-dir PATH --out-dir output
```

The full reusable prompt is in `prompts/card_extract.md`.

**Follow-up needed:** If the first extraction misses a charge or assigns a
questionable category, ask AI to reconcile every statement line and preserve
personal charges with a null expense category; Problem 5 will handle overlap
and reconciliation with receipts.

## Problem 5 — Reconciliation Log

**Prompt:** Reconcile the receipt, bank, and credit-card JSON datasets together
with relevant emails, memos, and other supporting documents. Return one row per
duplicate, ambiguous, or decision-needed real-world amount—not every raw line.
Each row must include `id`, `sources`, `amounts_seen`,
`included_in_income_statement`, `amount_used_in_income_statement`, and a plain
English `resolution`. Avoid double counting and explain decisions.
The full prompt is in `prompts/reconcile.md`. Run with:

```zsh
python reconcile.py --docs-dir PATH --out-dir output
```

Output: `output/reconciliation_log.json`.

**Follow-up needed:** If the first reconciliation omits a duplicate, mixes a
personal and business amount, or lacks support for a decision, ask AI to audit
each source document and revise the affected reconciliation rows.

## Problem 6 — Judgement Calls

**Prompt:** Review the reconciliation log and nominate the five rows where it
was hardest to decide whether the amount belongs in the January income
statement or what amount should be used. For each, provide `transaction_id`,
`included_in_income_statement`, `amount_used_in_income_statement`, an
`evidence_for` bullet list of document names, and confidence (`high`, `medium`,
or `low`), including at least one low-confidence call. The required final file
will be `output/judement_calls.json`; after review, narrow the five candidates
to the top three objects.

**Follow-up needed:** After reviewing the five candidates, identify the top
three and revise `output/judement_calls.json` to contain only those three.

## Problem 7 — January Income Statement

**Prompt:** Roll every reconciliation-log row with
`included_in_income_statement = yes` into January revenue and expense lines.
Use plain Python only; read the reconciliation log rather than hardcoding
amounts. Save `period`, `revenue_usd`, `expense_lines` with `label`,
`amount_usd`, `category`, and `sources`, plus `total_expenses_usd` and
`net_income_usd` to `output/income_statement_jan2026.json`.

Run with:

```zsh
python income_statement.py --docs-dir PATH --out-dir output
```

**Follow-up needed:** If the rollup misclassifies a reconciliation row or the
totals do not tie to the included source amounts, ask AI to audit the revenue
and expense classification and recalculate from the reconciliation log.

## Problem 8 — Income Statement Webpage

**Prompt:** Build a one-page HTML summary from the JSON files in `output`.
Show the January revenue, expenses, net income, excluded personal and business
rows, and the three judgment calls with confidence. Use the exact numbers from
`income_statement_jan2026.json`; do not hand-edit totals. Save the page to
`output/income_statement.html` with:

```zsh
python report.py --json-dir output --out output/income_statement.html
```

**Follow-up needed:** If the webpage totals differ from the JSON, ask AI to
trace every displayed amount back to its source file and correct the rendering.

## Problem 9 — Process Flow Diagram

**Prompt:** Build `output/pipeline.html`, a one-page visual block diagram of
the HW1 data pipeline for Problems 2–8. Show the document pack, each script,
the script inputs and outputs, arrows through the workflow, which steps call
Luna, and the path to `income_statement.html`. Include text explainers for
each step.

**Follow-up needed:** If any script, artifact, Luna call, or dependency is
missing from the diagram, ask AI to compare it against the actual files and
update the pipeline.
