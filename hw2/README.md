# Homework 2 — Sanford & Hawley Sales Agent

## Install

From this directory:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

The workspace root `.env` supplies the real Portkey key. For a submission,
include `.env.example` only; never include `.env` or `.venv/`.

## Problem 4 run

```zsh
python sales_agent.py "Build a profile of this company." --url https://sanhaw.com/
```

Outputs:

- `assets/company_profile.json`
- `output/audit_log.json`

## Problem 5 run

First build a broad candidate list:

```zsh
python sales_agent.py "Find up to 20 plausible Sanford & Hawley customer candidates in Connecticut and western Massachusetts." \
  --profile assets/company_profile.json --discover
```

This writes `output/candidate_list.json` without crawling candidate sites.
Then qualify the list and draft outreach:

```zsh
python sales_agent.py "Find 3 good customer targets for this company and draft outreach emails." \
  --profile assets/company_profile.json --candidates output/candidate_list.json
```

Outputs:

- `output/targets.json`
- `output/emails.json`
- `output/audit_log.json` (appended, not replaced)

The agent evaluates no more than twenty candidates, uses public web evidence,
and drafts emails only. It never sends them.

Use `--max-pages` and `--timeout-seconds` for bounded individual agent runs.
The default agent run allows up to eight pages and 90 seconds; development,
debugging, and verification work outside the run is not subject to that limit.
