# Yale SOM AI Class — workspace guide for Claude

Read this first, every session. Then read `AGENTS.md` (workspace rules) and
`AI_HANDOFF.md` (full course-level handoff, folder map, and prior-work
patterns). Finally read the local `README.md` / instructions inside whichever
lecture, homework, or final-project folder you are actually touching.

**The files are the truth, not a conversation summary.** Inspect the current
state of the workspace before changing anything, and preserve user edits.

## Layout

- `lectures/lecture_02/` … `lecture_13/` — one folder per lecture (`06`–`13`
  are empty as of 2026-09-21).
- `hw/hw_01/` … `hw/hw_06/` — canonical homework working folders
  (`03`–`06` are empty as of 2026-09-21).
- `final_project/` — empty as of 2026-09-21.
- `skills/` — reusable skills (currently `chatbot_dash`).
- `sample_leases/`, root-level `hw1/`, `hw2/`, `hw1.zip`, `hw2.zip` — reference
  and submission copies.

## Hard rules

1. **Do not modify `hw1/`, `hw2/`, `hw/hw_01/`, `hw/hw_02/`, `hw1.zip`, or
   `hw2.zip`.** HW1 and HW2 are submitted. Read them as reference patterns
   only. Ask before touching anything under those paths.
2. **Secrets.** The root `.env` holds the real `PORTKEY_API_KEY`. Never print,
   copy, commit, or package it. Ship `.env.example` with placeholders instead.
3. **Model default.** Portkey endpoint with `gpt-5.6-luna` is the workspace
   convention, not a course requirement. An assignment may call for a different
   provider, SDK, local model, or no LLM at all — check the local instructions
   and existing code first.
4. **One venv per project folder.** `python3 -m venv .venv` inside the lecture
   or homework folder; never silently borrow the root `.venv`.
5. **No image generation** unless Christopher explicitly asks.
6. **Visual style:** Windows Gateway 2000 / period desktop — gray panels, blue
   title bars, beveled controls, compact system typography. See
   `skills/chatbot_dash/SKILL.md` for the full treatment.
7. **Dash apps:** run with `use_reloader=False` or debug off. To stop one, kill
   the whole process tree, not just the PID on port 8050.
8. **Never send email, submit forms, or submit coursework** on his behalf
   without explicit, separate authorization.

## How work gets done here

1. Pin down the assignment's exact requested files, folder layout, and archive
   name from the assignment materials.
2. Copy the environment/dependency pattern from the nearest existing project.
3. Keep source, prompts, assets, generated outputs, and audit/reflection files
   inside the project folder.
4. Log prompts in `AI_prompts.md` when the assignment asks for it: the initial
   prompt per problem, plus at most one follow-up if a correction was needed.
5. Verify proportionally — imports, JSON validity, app behavior, archive
   contents.
6. Zips are snapshots. If a file is edited after packaging, rebuild the zip and
   check it with `unzip -l`. Exclude `.env`, `.venv/`, caches, `__pycache__`.

## Working with Christopher

Lead with the outcome. State assumptions when they matter. Implement and verify
change requests; for a diagnosis or review request, report — do not silently
fix. Assignment instructions are constraints; Christopher is the authority on
choices. **Reflections and analysis stay in his voice** — prepare blank
structures on request, never write the reflection for him.
