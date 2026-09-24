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
- `lectures/lecture_06/` through `lecture_13/`: folders exist but are empty as
  of 2026-09-21; read their actual contents before planning anything.

### Homeworks

- `hw/hw_01/`: canonical working folder for the prior Spoke & Wrench homework;
  useful as a reference for prompt logs, scripts, JSON outputs, HTML artifacts,
  and submission packaging.
- `hw/hw_02/`: completed Sanford & Hawley sales-agent homework. Read its
  `HARNESS.md` for the detailed agent architecture. (It has no folder-level
  `AI_HANDOFF.md`; this root file is the only one.)
- `hw/hw_03/`: in progress — Campus Customs vision/agent homework. Its own
  `README.md` and `AI_prompts.md` are the source of truth for its scenario,
  10-problem list, and Problem 10's exact submission layout; that detail is
  homework-specific and deliberately not duplicated here. Course-level facts
  learned while working on it (model roster, sandbox gotchas, zip artifacts)
  are folded into the relevant general sections above instead.
- `hw/hw_04/` through `hw/hw_06/`: future/homework slots; do not assume their
  requirements or create content until the user provides the assignment.

**HW1 and HW2 are submitted work and are frozen.** Do not modify `hw/hw_01/`,
`hw/hw_02/`, root-level `hw1/`, `hw2/`, `hw1.zip`, or `hw2.zip`. Read them as
reference patterns only; ask before touching anything under those paths. Known
cosmetic quirks in them are intentional leftovers, not bugs to fix: `hw/hw_01/`
lacks a `README.md` and `requirements.txt` (the root `hw1/` copy has both),
`hw/hw_01/output/judement_calls.json` is misspelled relative to the correctly
named `hw1/output/judgment_calls.json`, and the filenames under
`hw/hw_01/hw1_spoke_and_wrench/` contain literal backslashes from a
Windows-created archive.

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
