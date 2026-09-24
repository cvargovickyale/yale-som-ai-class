# Homework 3 — Campus Customs

Scaffolded ahead of the actual problem statements so setup is ready to go.
Problem-specific scripts, prompts, and outputs get added as Christopher types
each problem to the assistant (per course policy: typed in his own words, not
screenshotted or pasted as the page URL).

## Scenario

Campus Customs sells Yale merch. The agent helps with two growth questions:

1. Is someone in a photo wearing a Campus Customs product (possible outreach
   target)?
2. Would a Campus Customs ad video land with a given customer profile (e.g. a
   Yale student vs. a parent)?

Not a partnership with the actual shop — a local class setting.

## Install

From this directory:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The workspace root `.env` supplies the real `PORTKEY_API_KEY`. Copy
`.env.example` if a local override is ever needed; never commit the real
`.env`.

## Model

Course-approved OpenAI-via-Portkey options: `gpt-5.6-luna`, `gpt-5.6-terra`,
`gpt-5.6-sol`, `gpt-6-astra`. Default is `luna` (what the course budget
assumes for the semester); switch to a stronger model only if a specific
problem's vision or agent reasoning needs it, and note the choice in
`AI_prompts.md`.

## Data

Unzip the course `data.zip` into `data/` so this folder contains:

- `data/products/` — Campus Customs product catalogue photos
- `data/test_images/` — four influencer-style photos; filenames indicate
  ground truth (`true`/`false`) for whether a Campus Customs product appears
- `data/videos/ad_humble.mp4` — the Campus Customs ad video

## Problems

Filled in one at a time as each is typed and solved. See `AI_prompts.md` for
the prompt log.

1. P1 — Vibe Coder Prompts
2. P2 — Build the product catalogue
3. P3 — Product-identify agent
4. P4 — Test identify on four images
5. P5 — Ad video + profile ability
6. P6 — Student and parent profiles
7. P7 — Run ad for both profiles
8. P8 — Safety rules + audit trail
9. P9 — Finish the harness
10. P10 — Submit zip (4 pts)

## Target submission layout (Problem 10)

The final `hw3.zip` wraps a `hw3/` folder built fresh at submission time —
it is not simply a zip of this working folder:

```text
hw3/
├── AI_prompts.md
├── requirements.txt
├── .env.example
├── agent.py
├── tools.py
├── build_catalogue.py
├── models.py
├── prompts/
│   └── prompt.md
├── profiles/
│   ├── profile_student.json
│   └── profile_parent.json
└── output/
    ├── catalogue.json
    ├── harness.md
    ├── identify_product.json
    ├── agent_evaluation.md
    ├── ad_effectiveness.json
    └── audit_trail.json
```

The agent itself is exactly four files: `prompts/prompt.md`, `agent.py`,
`tools.py`, `models.py`. `models.py` holds every Pydantic/PydanticAI
structured type used in the homework (catalogue entry, identify result, ad
result, profile, audit entry, etc.). No real `.env`; `.env.example` carries
placeholders only. The course `data/` pack stays alongside the project while
working but is not re-zipped into `hw3.zip` unless asked.

This working folder currently also has an `assets/` directory and a
`data/` folder from setup — `assets/` is unused debris (an artifact of this
sandbox not being able to delete an empty folder) and won't be part of the
final `hw3/` submission structure above.
