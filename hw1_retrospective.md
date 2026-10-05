# HW1 Retrospective: Spoke & Wrench Pipeline

## Executive summary

HW1 earned 86/100. The submission successfully implemented the document
pipeline, generated sample outputs, created the HTML report and pipeline visual,
and packaged the work without the document pack or API key. The main losses
were interface-contract errors in Problems 5 and 7 and incorrect accounting
classification in the income-statement rollup.

## What I explicitly asked for

### Cross-assignment requirements

- Keep `AI_prompts.md` updated with at least one prompt and follow-up for each
  Problem 2–9.
- Use one script per scripted problem.
- Keep runtime prompts in `prompts/` and generated artifacts in `output/`.
- At the end, package everything in a top-level `hw1/` folder and zip it.
- Include scripts, runtime prompts, `requirements.txt`, a README, `AI_prompts.md`,
  sample outputs, and `pipeline.html`.
- Exclude the document pack, `.env`, API key, and virtual environment.

### Problem-specific requirements

- **P2:** `read_receipts.py`; extract receipt PDFs with an LLM into
  `output/receipts.json`.
- **P3:** `read_bank.py`; extract January bank lines into
  `output/bank_transactions.json`, including business/personal classification,
  direction, accounting label, and expense type.
- **P4:** `read_card.py`; extract January card charges into
  `output/credit_card_transactions.json`, with personal expense categories set
  to null.
- **P5:** `reconcile.py`; reconcile duplicates, mixed deposits, and supporting
  emails/memos into `output/reconciliation_log.json`.
- **P6:** identify uncertain decisions, explain evidence and confidence, and
  save three final judgment calls.
- **P7:** `income_statement.py`; read the reconciliation log and roll included
  rows into revenue and expenses in `output/income_statement_jan2026.json`.
- **P8:** `report.py`; read the JSON files and create
  `output/income_statement.html`.
- **P9:** create `output/pipeline.html` showing inputs, scripts, outputs,
  arrows, and Luna calls.
- **P10:** create a Canvas-ready `hw1.zip`.

## What was actually built

- P2–P5 scripts using Portkey/OpenAI structured extraction/reconciliation.
- P6 review artifact with REI, mixed Square, and Home Depot judgment calls.
- P7 plain-Python rollup.
- P8 static HTML report.
- P9 static pipeline diagram.
- P10 package with README, requirements, prompts, scripts, sample outputs, and
  no secrets/document pack.

## Working style observed

- You worked iteratively: implement one problem, run it, inspect the output,
  then move to the next problem.
- You preferred executable progress over long upfront planning and often asked
  to run the result immediately.
- You relied on the LLM for document interpretation, then personally reviewed
  ambiguous business judgments.
- You explicitly authorized sensitive-data runs before bank, card, and
  reconciliation calls.
- You frequently refined requirements during implementation: command formats,
  filename spelling, prompt logging, packaging contents, and visual design.
- You switched contexts between HW1 and lecture projects, which made explicit
  project-scope checks important.
- You accepted reasonable assumptions when details were unclear, but the
  assignment’s exact grader interface contract was not always checked first.

## What went wrong and how to prevent it

### P5: `wrong_cli` (-3)

The grader reported that `reconcile.py` did not implement the required CLI.
We used the command format discussed in chat:

```zsh
python reconcile.py --docs-dir PATH --out-dir output
```

The lesson is that “same command format” is not enough when a rubric defines
exact flag names. Before implementing a script, copy the assignment’s required
CLI literally into a contract checklist and test it with `--help` plus the
grader’s exact invocation. Do not add compatibility flags only by inference.

### P7: `wrong_cli` (-2)

The same issue occurred in `income_statement.py`. It accepted
`--docs-dir` and `--out-dir`, with `--docs-dir` unused, because the chat request
said to use the same command format. A cleaner design would have used the exact
reconciliation-input flag required by the rubric, or explicitly supported both
the rubric command and the convenience command.

### P7: revenue was too high (-5)

Our rollup reported `$9,125.58`; the grader’s gold value was `$8,150.00`.
The root cause was a fragile text heuristic in `income_statement.py`:

```python
REVENUE_TERMS = ("revenue", "deposit", "invoice", "service")
```

It treated purchase rows containing words like `invoice`, `service`, or related
descriptions as revenue. In particular, purchase/expense rows such as the NHBP
counter invoice, NHBP restock, and bank service fee were pulled into revenue.

Prevention: the reconciliation schema should have included an explicit
`statement_section` or `accounting_label` with allowed values such as
`revenue` and `expense`. P7 should then filter on that field, never infer the
section from prose. A pre-submission assertion should have checked that revenue
equals the independently reviewed revenue rows.

### P7: expenses were too low (-4)

Our expenses were `$3,501.64`; the gold value was `$4,566.22`. The same rows
misclassified as revenue were omitted from expenses, so the error flowed through
both totals. The net income was therefore also unreliable even though the
arithmetic itself was correct.

Prevention: reconcile the complete included-row partition before writing the
statement:

```text
included rows = revenue rows + expense rows
excluded rows = everything marked no
no included row may be unclassified
```

Then compare category totals and row counts against the reconciliation log.

## Process improvements for future assignments

1. Read the rubric and extract exact filenames, flags, schemas, and required
   values before writing code.
2. Put those requirements in a machine-checkable checklist.
3. Make schemas explicit rather than deriving accounting meaning from prose.
4. Test every script with the exact grader command, not only a convenient local
   command.
5. Add validation assertions for row coverage, allowed labels, totals, and
   output filenames.
6. Run a clean-room test from the packaged folder before submission.
7. Preserve a short “assumptions and unresolved judgments” section for anything
   supported only by a memo or owner statement.

## Key study takeaway

The pipeline’s biggest conceptual weakness was not Python arithmetic. It was
letting natural-language resolution text carry accounting structure. LLMs are
useful for extracting and explaining evidence, but downstream financial math
should consume explicit, validated fields—not infer revenue versus expense from
words appearing in a sentence.
