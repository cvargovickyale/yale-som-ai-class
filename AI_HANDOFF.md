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
`gpt-6-luna` by default (since HW5, 2026-10; HW1–HW4 code defaults to
`gpt-5.6-luna` — don't copy that default forward), but this is not a course-wide requirement: a lecture
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

Update (HW5, 2026-10-12): HW5 requires **only `gpt-6-luna`** for every agent
and deducts points if any other model shows up in code or runs. Verified via
Portkey; responses report the dated snapshot `gpt-6-luna-2026-09-22`, so check
the reported model name with a prefix match, not exact equality.

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

### New-homework kickoff (established HW4, 2026-10-05)

Christopher works through homeworks **one problem at a time, to learn along
the way** — he leads, types each problem in his own words, and says "P5"
meaning Problem 5. Before any building:

1. **Plan backward from the submission problem** (usually the last one). Read
   its required file tree and submission method first (zip vs. public GitHub
   repo, and which files must never be committed), so every earlier problem
   builds toward the right files in the right places.
2. **Write `hw/hw_0N/WORKPLAN.md`**: a P-number → problem name → what gets
   built → which final-tree files it produces table, plus open decisions and
   the submission mechanics. Keep it outside the deliverable folder so the
   submitted tree matches the spec exactly. `hw/hw_04/WORKPLAN.md` is the
   template.
3. **Walk him through the app's gist** (architecture, data flow, what's
   deterministic code vs. what's the LLM), then give a **mid-level quiz** and
   wait for his answers before starting the first build problem.
4. **Prompt log scope:** the prompt-log problem (P1 in HW3/HW4) only sets up
   the convention. Kickoff/background conversation is *not* logged;
   `AI_prompts.md` entries start with the first real build problem (P2 in
   HW4).
5. Then go one problem at a time — finish, verify, log the prompt, and stop
   for him to lead the next one. Don't run ahead into later problems.

Use `rg`/`rg --files` to search. Use `apply_patch` for local edits. Avoid
destructive commands and preserve unrelated user work.

## Sandbox/tooling gotchas (environment-level, not homework-specific)

**Which environment are you in?** The first three bullets below describe an
earlier restricted sandbox (Codex/Cowork-style). They did **not** apply in
the Claude Code desktop app used for HW4 (2026-10): there, `pip install`,
`npm install`, and deleting files all worked normally. Test once (e.g. a
quick `pip install` into the project venv) before assuming either way, and
don't tell Christopher to run installs himself unless they actually fail.

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
- `hw/hw_04/`: **built and published (2026-10-06); Christopher submits the
  repo URL on Canvas.** Campus Customs website: React + Vite TS frontend,
  FastAPI backend, PydanticAI agent ("Handsome Dan") over
  `campus_customs.db`. Submitted as a **public GitHub repo**:
  https://github.com/cvargovickyale/campus-customs-hw4 (root contains only
  `hw4/`). Edit in `hw/hw_04/hw4/`, commit to the private workspace repo,
  then republish with `hw/hw_04/publish_hw4.sh "message"` (exports only
  git-tracked files, refuses `.env`/db/data/node_modules; local clone at
  `../campus-customs-hw4`). `hw/hw_04/WORKPLAN.md` has the P1–P13 map;
  `hw4/output/harness.md` section 0 is the system overview. Treat it as
  frozen once graded, like HW1–HW3.
- `hw/hw_05/`: **built and published (2026-10-14); Christopher submits the
  repo URL on Canvas.** Campus Customs multi-agent operations: FastMCP
  server (`mcp_server/server.py`, the only DB access), FastAPI +
  five PydanticAI agents on `gpt-6-luna` with bounded delegation
  (`backend/main.py`), React/Vite/TS board (`frontend/`). Public repo
  https://github.com/cvargovickyale/campus-customs-hw5 (root = `hw5/`, both
  DBs committed by rule). Edit in `hw/hw_05/hw5/`, commit, republish with
  `hw/hw_05/publish_hw5.sh "message"`. `hw/hw_05/WORKPLAN.md` has the P1–P11
  map; `hw5/output/harness.md` §0 is the system overview. Treat as frozen
  once graded.
- `hw/hw_06/`: future homework slot; don't assume requirements or create
  content until the user provides the assignment.

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

Homework 4 (public repo `cvargovickyale/campus-customs-hw4`) is the current
reference for a **React + Vite + TS frontend / FastAPI backend / PydanticAI
agent** app. Start with `hw/hw_04/hw4/output/harness.md` section 0 (system
overview), then reuse:

- **Contract-first agent output:** the agent returns IDs plus a flag
  (`AgentReply{reply, product_ids, results_label}`); code looks up every
  fact (prices, images) from the DB, and unknown IDs are dropped. The model
  picks, code states facts.
- **Static + dynamic instructions:** `prompt.md` is re-read on every run
  (`uvicorn --reload` ignores `.md` edits; a stale prompt cost an hour of
  wrong debugging in P8), and a `dynamic_context(ctx)` function writes
  per-message context (who's chatting, what page they're on) from
  `AgentDeps`. Page context arrives as an untrusted URL path and is
  validated against the DB in `main.py`.
- **Per-message lookup record** (`MessageLookups` in deps): tools read
  through it, so each DB fact is read once per message and nothing carries
  across messages. History replies are time-stamped "may be out of date" so
  old prices are never reused.
- **Append-only audit trail v2** (`hw4/backend/agent.py`): HW3's
  message-history approach, plus `capture_run_messages()` so failed or
  timed-out runs are logged too; fixed `stop_reason` list; per-tool timing,
  shortened args, and readable result summaries; masks card numbers, emails,
  and "password is …"; atomic temp-file writes; an unreadable file is moved
  aside, never overwritten.
- **Cost controls:** sliding-window rate limits checked *before* the agent
  runs (guest/customer/site-wide), `UsageLimits`, a timeout, and a
  one-line-per-message cost log (round trips, tokens, DB queries). Measure
  tokens per message before optimizing; the instructions are re-sent on
  every round trip, so round trips are the main cost lever.
- **PydanticAI 2.54 API notes** (verified against the installed package):
  `result.usage` is a property, not a method; set
  `PYDANTIC_AI_NO_BANNER=1`; use `TestModel(call_tools=[])` for offline
  instruction checks (the default calls every tool with junk args);
  `ModelRetry` from a tool lets the model self-correct (logged as `retry`).
  Azure (behind Portkey) has a content filter that blocks jailbreak-style
  messages; handle it gracefully and never try to get around it.
- **Public-repo submission:** keep the source in the private workspace,
  and publish with `hw/hw_04/publish_hw4.sh` (git-archive of tracked files
  only → a separate local clone → push; refuses `.env`/db/data/
  node_modules). Confirm the repo name with Christopher before creating a
  public repo, then grader-test a fresh clone end to end. Copy this
  script for future public-repo homeworks.
- **Screenshots for an `app_check.html`:** `playwright-core` installed in
  the session scratchpad (not the project), driving the system Chrome at
  `/Applications/Google Chrome.app/...`, headless, `reducedMotion: 'reduce'`,
  1920×1080 so side panels don't cover content. The preview tool's
  screenshots are compressed and can't hover. Verify the HTML via a
  `file://` load at 1280/840/375 px.
- **Preview-server quirks:** the desktop app stops preview servers when
  idle (just restart them); other sessions may already hold ports 8000/5173
  (HW4's Vite reads `HW4_BACKEND` for an alternate port); the venv's
  `uvicorn` script can be blocked, so launch with `.venv/bin/python -m
  uvicorn` in `.claude/launch.json`.
- **Verification habits that caught real bugs:** compare every number
  against SQL on the DB; for layout, measure overlap (not just horizontal
  overflow) across a sweep of widths (375–1440); when a fix "should" work,
  confirm it's actually live before judging it.

Homework 5 (public repo `cvargovickyale/campus-customs-hw5`) is the
reference for an **MCP server + multi-agent team + approval dashboard**.
Start with `hw/hw_05/hw5/output/harness.md` §0, then reuse:

- **MCP as the only data layer.** FastMCP serves agent tools (stdio for
  Claude Code via `.mcp.json`, `--http` for the backend). Human-only tools
  (approve/reset) are registered in HTTP mode only, and each agent sees an
  allowlisted subset (`toolset.filtered`).
- **Propose → approve → execute.** Agents write *pending* records (payment,
  reprint, hold, draft, decision); only a human route executes. Rules (cash
  floor, vendor block, dedupe, ticket link) live in the tool.
- **Bounded delegation:** a `delegate` tool with depth cap, no revisits,
  same ticket, a shared `UsageLimits` budget, timeouts, and a per-agent
  append-only audit (`run_id`/`parent_run_id`/chain).
- **gpt-6-luna gotchas (Portkey/Azure):** tools need the Responses API
  (Chat Completions rejects tools with reasoning on); force
  `x-portkey-cache-force-refresh` (cache hits return IDs Azure rejects on
  rerun); retry intermittent `401 Jwt verification fails` on both
  `request` and `request_stream` (the event hook makes runs stream).
- **Verification:** throwaway DB copies via `CAMPUS_CUSTOMS_DB` for tests;
  a read-only Playwright watcher for screenshots (never click run/approve
  buttons in checks: one stray click cost ~41k tokens in P8).

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
