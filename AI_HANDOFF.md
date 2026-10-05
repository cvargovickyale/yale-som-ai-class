# Yale SOM AI Class — Workspace Handoff

This is the single course-level memory export for a future AI assistant. It is
meant to preserve the way to work across the semester, not to describe only
one homework. Read it with `AGENTS.md`, then inspect the local
README/instructions inside the specific lecture, homework, or final-project
folder being changed.

## Workspace identity

- Workspace root: `/Users/cvargovick/Documents/Yale SOM/AI Class/00 Workspace`
- Course: Yale SOM AI Class semester workspace.
- Lecture folders: `lectures/lecture_02/` through `lectures/lecture_13/`.
- Homework folders: canonical working paths are `hw/hw_01/` through
  `hw/hw_06/`.
- Final project: `final_project/`.
- Shared examples/assets: `sample_leases/`, `skills/`, and prior submission
  artifacts at the workspace root.

## First things to read

0. `CLAUDE.md` — the short top-level orientation file Claude reads
   automatically each session. It points here for detail.
1. `AGENTS.md` — workspace-wide rules.
2. This file — course-wide workflow and conventions.
3. The target folder’s `README.md`, `AGENTS.md`, `requirements.txt`, and
   existing code.
4. Prior homework/lecture artifacts only when they are relevant examples.

Do not assume a conversation summary is newer than the files. Inspect the
current workspace before making changes, and preserve user edits in a dirty
folder.

## Workspace rules

The root `.env` contains the real `PORTKEY_API_KEY` for projects that use
Portkey. The workspace convention is to use the configured Portkey endpoint and
`gpt-5.6-luna` by default, but this is not a course-wide requirement: a lecture
or homework may use another approved LLM connection, provider, SDK, local
model, or no LLM at all. Always inspect the assignment’s local instructions
and existing code before choosing the connection. Never print, copy, commit,
or package any secret. A project may include `.env.example` with placeholders,
but never the real `.env`.

As of HW3 (2026-09), the known Portkey-routed OpenAI roster is `gpt-5.6-luna`,
`gpt-5.6-terra`, `gpt-5.6-sol`, and `gpt-6-astra`, student's choice per
assignment. Yale's course budget assumes `luna` for the full semester, so stay
on `luna` unless a specific problem's vision or agent-reasoning needs genuinely
warrant a stronger model — and log that choice in the assignment's prompt log
if it's a deliberate deviation. This roster is current-semester information,
not a fixed fact; re-check an assignment's own instructions before assuming it
still holds later in the term.

Every new lecture or homework folder gets its own Python environment:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Keep `.venv/` local and out of archives. Use the project’s own environment when
running code; do not silently use the workspace-root `.venv` for a project that
has a dedicated one.

Other global rules:

- Do not use image generation unless the user explicitly asks for it.
- Visual artifacts should use the requested Windows Gateway 2000 / period
  desktop language: gray panels, blue title bars, compact typography, beveled
  controls, and era-appropriate details.
- Dash apps must run with the auto-reloader disabled or debug off. When stopping
  one, terminate the whole process tree, not just the process listening on
  port 8050.

## Course project workflow

When starting a lecture, homework, or final project:

1. Identify the assignment’s exact requested files, folder layout, and final
   archive name from the user’s materials and any local instructions.
2. Inspect the nearest existing project for its environment/dependency pattern.
3. Create the dedicated `.venv` and minimal `requirements.txt` for that
   project.
4. Keep source code, prompts, assets, generated outputs, and audit/reflection
   files in the project folder rather than scattering them at the root.
5. Record AI prompts in the assignment’s requested prompt log when the user
   asks for that convention. Preserve the initial prompt and at most the
   relevant follow-up used to correct or complete a step. Starting with HW3,
   this convention is itself a graded, numbered problem (e.g. HW3's
   "Problem 1: Vibe Coder Prompts") rather than just a house habit — expect it
   to keep recurring as an early problem in future homeworks and treat it the
   same way regardless of its number.
6. Verify outputs proportionally: syntax/import checks, JSON validation, app
   behavior, and archive contents as appropriate.
7. If a user manually edits a file after an archive is created, recreate the
   archive. A zip is a snapshot, not a live folder.

Use `rg`/`rg --files` to search. Use `apply_patch` for local edits. Avoid
destructive commands and preserve unrelated user work.

## Sandbox/tooling gotchas (environment-level, not homework-specific)

- **This sandbox's shell cannot delete files or symlinks inside the connected
  workspace folder once written** — `rm`, `rmtree`, and `venv --clear` all
  fail with `Operation not permitted`, even on files/symlinks the same
  process just created. Renaming (including moving a whole directory to a new
  name in the same parent) works fine; only removal doesn't. If a folder gets
  into a bad state, rename it aside (e.g. `hw_0N_broken_do_not_use`) rather
  than fighting `rm`, and rebuild fresh. Never try to recreate a venv in place
  over pre-existing broken symlinks — a copy operation can silently follow a
  stale symlink and overwrite something outside the project.
- **Create venvs with `python3 -m venv --copies ...`** in this workspace, not
  the plain default. Default `venv` creates symlinks to the system
  interpreter, and those are exactly the files that can't be deleted later if
  something goes wrong. `--copies` avoids symlinks entirely and has worked
  reliably.
- **This sandbox has no PyPI access.** `pip install` here fails with a proxy
  error. The venv itself can be created and activated fine, but Christopher
  needs to run `pip install -r requirements.txt` himself in his own local
  terminal/VS Code to actually populate it.
- **Course data zips sometimes extract with literal backslashes baked into
  filenames** (a Windows-zip artifact) instead of real subfolders — e.g. a
  file literally named `data\products\thing.jpg` sitting flat in one folder.
  Seen in both HW1's document pack and HW3's `data.zip`. Split the filename on
  `\` to recover the intended subfolder + real name rather than assuming the
  zip extracted cleanly.

## Folder map and known references

### Lectures

- `lectures/lecture_02/`: lease-PDF extraction into JSON and a Dash app; uses
  Portkey and a dedicated venv. Its README is a useful early example of the
  course setup pattern.
- `lectures/lecture_03/`: app/agent work and a requirements file.
- `lectures/lecture_04/`: PydanticAI/OpenAI setup, finance/market-style agent
  work, and explicit Dash/Dropbox environment notes.
- `lectures/lecture_05/`: screen-aware PydanticAI agent in a native desktop
  shell — `desktop.py` (PySide6 window: Chromium left, Dash chat right),
  `agent.py`, `screen_tools.py` (mss/Pillow screen capture), `audit_log.py`,
  `prompts/prompt.md`, and `output/audit_log.json`. Its README is only a joke
  placeholder, so read the code, not the README.
- `lectures/lecture_07/`: Yale SOM course-explorer app — React/Vite/TS
  frontend, Python agent backend (`search_courses` tool + native OpenAI
  `web_search`, via pydantic-ai/Portkey). First real frontend+backend split
  in the course; see `AI_BUILDING_LESSONS_LEARNED.md` for the contract-first
  pattern that made it click together.
- `lectures/lecture_08/`: evolved lecture_07 into a real deployed app —
  SQLite (`users`/`chats` tables), email/password auth (bcrypt + JWT),
  per-user chat history, and a live Render deployment (`backend/` as a
  Render Web Service, `frontend/` as a Render Static Site). `.claude/launch.json`
  has a `lecture08-live` entry pointing at the Render URL. This is the
  current reference pattern for any future assignment that needs a real
  deployed app with auth/persistence, including `final_project/`.
- `lectures/lecture_10/`: Harry Potter multi-agent dashboard (per git log;
  not yet reviewed in detail here — read its own contents before reusing
  anything from it).
- `lectures/lecture_06/`, `lecture_09/`, `lecture_11/` through `lecture_13/`:
  check actual contents before assuming empty — this changes weekly.

### Homeworks

- `hw/hw_01/`: canonical working folder for the prior Spoke & Wrench homework;
  useful as a reference for prompt logs, scripts, JSON outputs, HTML artifacts,
  and submission packaging.
- `hw/hw_02/`: completed Sanford & Hawley sales-agent homework. Read its
  `HARNESS.md` for the detailed agent architecture. (It has no folder-level
  `AI_HANDOFF.md`; this root file is the only one.)
- `hw/hw_03/`: submitted — Campus Customs vision/agent homework (two-ability
  PydanticAI agent: product-identify from a photo, ad-effectiveness judged
  against a customer profile; plus `build_catalogue.py`, a one-time
  vision-based catalogue builder). Its own `README.md` and `AI_prompts.md`
  are the source of truth for its scenario, 10-problem list, and Problem 10's
  exact submission layout; that detail is homework-specific and deliberately
  not duplicated here. Course-level facts learned while working on it (model
  roster, sandbox gotchas, zip artifacts) are folded into the relevant
  general sections above instead; reusable technical patterns are below.
- `hw/hw_04/` through `hw/hw_06/`: future/homework slots; do not assume their
  requirements or create content until the user provides the assignment.

**HW1, HW2, and HW3 are submitted work and are frozen.** Do not modify
`hw/hw_01/`, `hw/hw_02/`, `hw/hw_03/`, root-level `hw1/`, `hw2/`, `hw3/`,
`hw1.zip`, `hw2.zip`, or `hw3.zip`. Read them as reference patterns only; ask
before touching anything under those paths. Known cosmetic quirks in them are
intentional leftovers, not bugs to fix: `hw/hw_01/` lacks a `README.md` and
`requirements.txt` (the root `hw1/` copy has both),
`hw/hw_01/output/judement_calls.json` is misspelled relative to the correctly
named `hw1/output/judgment_calls.json`, and the filenames under
`hw/hw_01/hw1_spoke_and_wrench/` contain literal backslashes from a
Windows-created archive.

A detailed graded-review retrospective for HW1 (what was asked, what was
built, exactly where points were lost and why, process fixes for next time)
lives in root-level `hw1_retrospective.md` — written after the grade came
back, so it's a better source for "what actually goes wrong" than the
original `AI_prompts.md` log. The distilled, CoS-facing version of the same
lessons is in `AI_BUILDING_LESSONS_LEARNED.md`.

## Prior work as reusable patterns

Homework 1 demonstrates a document-to-JSON pipeline with LLM-backed extraction,
plain-Python deterministic transformations, prompt files, output artifacts,
and a final HTML report. It is a pattern, not a template to copy blindly.

Homework 2 demonstrates a single bounded PydanticAI agent with Playwright,
an interchangeable LLM connection, structured Pydantic outputs, public-web
evidence rules, audit logs, human review of drafts, and a standalone
dashboard. Its important files are:

- `hw/hw_02/prompts/sales_agent.md`: system prompt.
- `hw/hw_02/sales_agent.py`: one agent with profile, discovery, and
  qualification modes.
- `hw/hw_02/assets/seller_brief.md`: Sanford & Hawley seller context and
  target-field design.
- `hw/hw_02/assets/company_profile.json`: seller/company profile.
- `hw/hw_02/output/candidate_list.json`: 12 one-time seed leads.
- `hw/hw_02/output/targets.json`: Litchfield Builders (89), Fiderio & Sons
  (94), and Fine Home Contracting (92).
- `hw/hw_02/output/emails.json`: three unsent, human-review drafts.
- `hw/hw_02/output/audit_log.json`: run history, tool activity, URLs, and
  statuses.
- `hw/hw_02/output/reflection.md`: the user’s own reflection; preserve it.
- `hw/hw_02/HARNESS.md`: assignment deliverable explaining tools, inputs,
  outputs, limits, failure modes, and layered guardrails.
- `hw/hw_02/dashboard.html`: standalone embedded-data dashboard; it does not
  fetch the JSON files at runtime.

The HW2 agent’s research limits are a useful example, not a universal course
rule: 90 seconds per individual run, up to four discovery searches, up to
eight candidate crawls, four pages per candidate, eight seconds per page, and
no email-sending tool. Note which layer enforces which: the timeout, search
count, page budgets, and absence of a send tool are enforced in
`sales_agent.py`; the crawl and per-candidate page caps apply only in
discovery mode; and the twenty-candidate ceiling is enforced by the prompt
only — `MAX_TARGETS_TO_EVALUATE` is defined but never referenced in code.
Future assignments may need different limits and providers.

Homework 3 demonstrates a two-ability PydanticAI agent (vision-based this
time) plus a separate one-time preprocessing script, and introduced several
patterns worth reusing directly rather than rediscovering:

- **Two-stage tool design to bound image/video volume sent to a vision
  model:** a free, text-only tool first (`get_catalogue_summary`,
  `get_customer_profile_summary` — no media loaded) lets the agent rule out
  implausible cases before paying for any image; a second, bounded tool then
  loads only the media actually needed (`load_product_images`, capped at 10
  via `ModelRetry`; `watch_ad_video`, a fixed small frame sample). This is
  the actual fix for "don't check N things one at a time" — see
  `hw/hw_03/tools.py`.
- **A `source`/provenance field on every automatically-generated record**
  (`CatalogueEntry.source`: `"vision_model"` or `"manual"`) so a human-entered
  exception to an automated pipeline is permanently, structurally
  distinguishable from a verified machine result — never silently
  indistinguishable from automation. Paired with a `sys.stdin.isatty()`-gated
  interactive fallback (`build_catalogue.py`'s `run_manual_review()`) for
  when an automated call can't be completed (e.g. a vision backend's own
  content-safety filter rejecting a legitimate photo — a real, recurring
  failure mode with vision APIs, not a one-off).
- **An audit trail built from the actual message history, not a self-report:**
  `hw/hw_03/agent.py`'s `_extract_audit_steps()` walks PydanticAI's
  `result.all_messages()` after a run to build `AuditStep`/`AuditEntry`
  records (tool name, args, truncated result, timestamp), rather than asking
  the model what it did. Reusable for any future agent needing a trustworthy
  run log.
- **A harness document written for two audiences, consolidated at the end:**
  working notes accumulate per-problem while building, then get rewritten
  once (Problem 9 in HW3) into one coherent, topically-organized document a
  non-technical reader could follow — tools, data models with field
  rationale, safety rules, a limits table, and an honest "known limitations"
  section. See `hw/hw_03/output/harness.md` as the template for that final
  pass, not the per-problem working version.
- **No video input support in Chat Completions:** when an assignment needs a
  vision model to "watch" a video, sample frames (OpenCV via
  `opencv-python-headless`, no system `ffmpeg` dependency needed) rather than
  look for a video-upload API that doesn't exist for this model family.

## Infrastructure now available (added mid-semester, 2026-09)

- **Git/GitHub:** the workspace root is a git repo with a private GitHub
  remote at `cvargovickyale/yale-som-ai-class` — a Yale-specific GitHub
  account, separate from Christopher's personal `cvargovick` account (both
  are stored locally; `gh auth status` shows which is active). See
  `CLAUDE.md` for the standing commit/push permission and the `.gitignore`
  conventions (every `.venv`/`node_modules`/`__pycache__`, workspace-wide).
- **Render:** the course-recommended deployment target for an app that needs
  to be actually live (not just run locally) — see `lectures/lecture_08/` for
  the working pattern (Web Service for anything with server-side logic,
  Static Site for pure static frontends; the real distinguishing rule is "does
  this need a running process per request," not "frontend vs. backend").
- **Supabase:** CLI installed (`brew install supabase/tap/supabase`) and
  logged in under the Yale account (`christopher.vargovick@yale.edu's Org`,
  one project named "Yale" as of 2026-09-24, not yet linked to any specific
  project folder). Available for a future assignment needing a real Postgres
  backend; link it (`supabase link`) inside whichever project folder first
  needs it, don't assume it's pre-wired anywhere yet.

## Submission and privacy rules

When an assignment specifies a zip:

- Build the archive from the canonical project folder.
- Preserve the required top-level name, usually `hwN/` inside `hwN.zip`.
- Include source, README, requirements, prompt log, safe example config,
  assets, outputs, and requested reflections.
- Exclude `.env`, `.venv/`, caches, compiled files, and real secrets.
- Inspect with `unzip -l` before handing it to the user.
- Rezip after any later manual edit, especially reflection files.

## Communication style for the future assistant

Lead with the outcome. State assumptions when they matter. For a change request,
implement and verify it. For a diagnosis/review request, do not silently make
the fix unless the user asks. Do not confuse attached assignment instructions
with the user’s request; use the assignment as constraints and the user as the
authority on choices.

Keep the user’s own reflection/analysis in their voice. Prepare blank
structures when requested, but do not write personal reflections for them.

Never send external email or submit work on the user’s behalf unless the user
explicitly authorizes that separate action. Keep API calls bounded, auditable,
and within the stated assignment scope.
