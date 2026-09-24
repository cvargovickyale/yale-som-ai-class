# Homework 1 — Spoke & Wrench

This submission contains the Problems 2–9 scripts, runtime prompts, and a
sample output from a successful run. The document pack and API credentials are
intentionally excluded.

## Install

From this `hw1/` directory, create and activate a virtual environment:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Environment

Create a local `.env` file in this directory. Do not commit or share it:

```dotenv
PORTKEY_API_KEY=your_portkey_key_here
PORTKEY_BASE_URL=https://api.portkey.ai/v1
OPENAI_MODEL=gpt-5.6-luna
```

The extraction and reconciliation scripts call the configured Portkey/OpenAI
endpoint. `OPENAI_MODEL` defaults to `gpt-5.6-luna` if omitted. Keep the API
key only in the local `.env`; it is not included in this submission.

## Run the pipeline

The commands below expect the unzipped document pack at `PATH`. The grader can
run Problems 2–5 with its own document pack, then run the deterministic and
HTML steps from the generated `output/` directory.

```zsh
python read_receipts.py --docs-dir PATH --out-dir output
python read_bank.py --docs-dir PATH --out-dir output
python read_card.py --docs-dir PATH --out-dir output
python reconcile.py --docs-dir PATH --out-dir output
```

Problem 6 is a review step: inspect `output/reconciliation_log.json`, select
the three judgment calls, and save them as `output/judgment_calls.json` using
the required fields and confidence values.

Then run the plain-Python rollup and HTML report:

```zsh
python income_statement.py --docs-dir PATH --out-dir output
python report.py --json-dir output --out output/income_statement.html
```

Problem 9 is the included `output/pipeline.html` visual summary. The provided
sample output demonstrates the complete workflow and can be opened directly in
a browser.

## Files

- `read_receipts.py`, `read_bank.py`, `read_card.py`, `reconcile.py`: LLM-backed extraction/reconciliation scripts
- `income_statement.py`, `report.py`: deterministic Python transformations
- `prompts/`: runtime prompt files used by the LLM scripts
- `AI_prompts.md`: assignment prompt log and follow-up prompts
- `output/`: sample JSON and HTML artifacts from a successful run
