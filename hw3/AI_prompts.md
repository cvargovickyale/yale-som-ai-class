# Homework 3 AI Prompts

Records the prompt used for each problem, plus at most one follow-up when a
correction or clarification was needed. Follows the HW1/HW2 logging
convention.

## Setup

**Prompt:** Start HW3 (Campus Customs) as a readiness check — scaffold the
folder like previous homeworks, confirm Node/git are irrelevant here (this is
the Python/vision homework), and wait for Problem 1 to be typed before writing
any solution code.

**Notes:**

- `hw/hw_03/.venv` created with `python3 -m venv --copies` (not the default
  symlink layout) after the default `venv` layout hit a sandbox-specific
  permission wall — see `hw_03_broken_venv_do_not_use/` left one level up in
  `hw/` as inert debris from that failed first attempt. Safe to delete by hand
  in Finder; the assistant's sandbox cannot delete it itself.
- Package installation (`pip install -r requirements.txt`) must be run by
  Christopher locally — this sandbox has no PyPI network access.

## Problem 2 — Build the product catalogue

**Prompt:** Build `build_catalogue.py` that produces a one-time structured
catalogue entry for each product photo: merch type (hoodie, t-shirt, etc.), a
text description, and other fields for later matching, especially what
branding/school is shown and whether it's a logo, the name, both, or a crest.
The catalogue entry type belongs in `models.py` as a Pydantic/PydanticAI
model, written to `output/catalogue.json`. Also write `output/harness.md`
(same category structure as HW2's harness), covering how the image
cataloguing was sped up and why those particular merch-type/branding/school
fields were chosen (I manually reviewed the product photos before picking
them). Speed it up clearly beyond a plain sequential loop — ideas on the
table: downscaling images (risks losing readability) and cropping the
whitespace/blackspace margin most (not all) product photos have around the
garment before resizing.

**Follow-up prompt used:** "Is the cropping/resizing trick actually helping?
And build a manual workaround for the 3 crest photos the vision model
refuses — flag what can't be answered automatically and ask me to look at
those images and make the calls myself."

**Notes:**

- The previous session's `hw_03/.venv` was built inside a Linux sandbox and
  its Python binary couldn't run on this Mac; rebuilt natively with
  `python3 -m venv .venv` and a real `pip install -r requirements.txt`, which
  worked over the Mac's own network.
- 99 of 102 product photos catalogued automatically; 3
  (`berkeley-1-4-zip.jpg`, `benjamin-franklin-t-shirt.jpg`,
  `timothy-dwight-college-crewneck.jpg`) fail every retry with a genuine 400
  content-safety rejection from the vision backend on heraldic crest artwork
  — a false positive, not a code or key problem.
- Checking the size-reduction claim (asked, not assumed) found the original
  preprocessing was actually making 82 of 102 images *bigger* than the raw
  source file (missing `optimize=True`); fixed with `optimize=True` and
  quality 75, giving a real ~15% reduction. Concurrency, not crop/resize, was
  confirmed as the actual speed lever.
- Built a manual-review fallback (`run_manual_review()` /
  `prompt_manual_entry()` in `build_catalogue.py`, gated on
  `sys.stdin.isatty()`) instead of writing an automated bypass for the
  content-safety block. For today's 3, since there was no live terminal to
  prompt, Christopher described each photo directly in conversation and
  those answers were validated through the same `CatalogueEntry` schema and
  merged in with `"source": "manual"`. Current state: 102/102 catalogued, 0
  skipped. Full writeup in `output/harness.md`.

**Completed artifacts:** `models.py`, `build_catalogue.py`,
`output/catalogue.json`, `output/harness.md`.

## Problem 3 — Product-identify agent

**Prompt:** Build the four-file Campus Customs agent
(`prompts/prompt.md`, `agent.py`, `tools.py`, `models.py`) that decides
whether a Campus Customs product is visible in a given photo, and which one
if possible. Never check the catalogue one image at a time, and never send
more than 10 product images in a single model call — consider using the
catalogue's own fields (merch type, school/program) to rule out implausible
matches before loading any images. New structured return type goes in
`models.py`. CLI: `python agent.py --image "<path>"`; writes
`output/identify_product.json`. Update `output/harness.md` with the
identification/efficiency approach and the field rationale, and explain (in
`models.py`'s docstring and in chat) what "Pydantic/PydanticAI structured
types" and "wiring a tool from agent.py" actually mean.

**Follow-up prompt used:** None needed for the build itself. Testing turned
up a real failure mode: the first test image chosen
(`data/products/berkeley-1-4-zip.jpg`, one of the 3 manually-catalogued crest
photos) hit the same Azure content-safety 400 as a *query* photo, crashing
with a raw traceback. Fixed by catching `ModelHTTPError` in `agent.py` and
failing cleanly with no fabricated `identify_product.json`, then re-tested
successfully against `data/test_images/image_01_true.jpeg`.

**Notes:**

- Added `pydantic-ai-slim[openai]>=1.0.0` to `requirements.txt` (installed:
  `pydantic_ai` 2.46.0), matching the version convention already used in
  `hw/hw_02` and the lecture folders.
- Real run against `image_01_true.jpeg`: `get_catalogue_summary` (0 images)
  then `load_product_images` with exactly 3 filenames (the "Yale Dad"
  family), matched `yale-dad-t-shirt.jpg` at high confidence — consistent
  with the photo's own `_true` ground truth. 3 of 102 catalogue images
  loaded, well under the 10-image ceiling.
- Full design writeup (field rationale, tool wiring, efficiency evidence,
  the query-image failure mode) is in `output/harness.md`.

**Completed artifacts:** `prompts/prompt.md`, `agent.py`, `tools.py`,
`models.py` (added `ProductMatch`/`IdentifyResult`),
`output/identify_product.json`, `output/harness.md`.

## Problem 4 — Test identify on four images

**Prompt:** Run the identify agent against all four `data/test_images/*.jpeg`
photos; collect all four results in `output/identify_product.json`, each
validating against `IdentifyResult`.

**Follow-up prompt used:** None needed for the build. `agent.py` previously
overwrote `identify_product.json` with a single object per run; changed it to
accumulate a JSON list (one entry per photo, replacing only that photo's own
entry on rerun) so all four results could coexist.

**Notes:**

- 3 of 4 produced a result and all 3 matched their filename's ground truth:
  `image_01_true.jpeg` -> `yale-dad-t-shirt.jpg` (high confidence, 3
  candidates loaded); `image_02_false.jpeg` -> no product, 0 candidates
  loaded (ruled out from the garment description alone); `image_03_true.jpeg`
  -> `dry-zone-long-sleeve.jpg` (high confidence, 2 candidates loaded,
  correctly discriminated against a visually similar Under Armour
  long-sleeve).
- `image_04_false.jpeg` could not be checked at all — a different
  content-safety 400 (this one looks triggered by a visible third-party
  "Balenciaga" logo in the photo, not heraldry) blocked the query photo
  itself before the agent could reason about it. Left out of
  `identify_product.json` rather than guessed at; a real, currently
  unresolved gap, not a reasoning mistake by the agent. See
  `output/harness.md` for the full writeup.

**Completed artifacts:** `agent.py` (list-accumulating output),
`output/identify_product.json`, `output/harness.md`.

## Problem 5 — Ad-effectiveness ability

**Prompt:** Add a second ability to the agent: given an ad video and a
customer profile JSON, judge how effective the ad would be at convincing
that customer to shop with Campus Customs. New tool code in `tools.py`,
prompt updated (added to, not overwritten) to describe the new ability, new
structured result type in `models.py` (added to, not overwritten). CLI:
`python agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_student.json"`,
output in `output/ad_effectiveness.json` matching the new model. Create
different ad-effectiveness categories, and use customer-profile fields to
identify what the customer is interested in so it can be matched against
what's derived from the video. One profile is enough to test for now.
Update `output/harness.md` with the tools this problem adds (one line each).

**Follow-up prompt used:** None needed.

**Notes:**

- Watched the actual ad first (8 sampled frames via OpenCV, reviewed by
  hand) rather than guessing at categories blind: it's a parody of Kendrick
  Lamar's "HUMBLE." video — a squad in Yale merch under a highway overpass.
  Informed the `AppealCategory` vocabulary (`school_pride`, `humor_comedy`,
  `social_belonging`, `style_fashion`, `confidence_swagger`,
  `athletic_energy`, `tradition_heritage`), shared between
  `CustomerProfile.interests` and `AdEffectivenessResult.ad_themes` so their
  overlap is the actual matching mechanism.
- No system `ffmpeg` on this Mac; used `opencv-python-headless` (pip
  package, no system binary needed) to pull 8 evenly-spaced video frames
  instead.
- Created `profiles/profile_student.json` (a price-sensitive Yale undergrad
  who responds to social/style/confidence themes, not sport/tradition) since
  P6 hasn't been reached yet and one profile is enough for this problem.
- Real run result: `effectiveness: medium` (not `high`) for the student
  profile against `ad_humble.mp4` — 3 of 4 detected ad themes matched the
  customer's interests, but the reasoning explicitly downgraded because the
  ad has no price/value messaging for a highly price-sensitive customer.
  Full writeup in `output/harness.md`.

**Completed artifacts:** `models.py` (added `AppealCategory`,
`CustomerProfile`, `AdEffectivenessResult`), `tools.py` (added
`get_customer_profile_summary`, `watch_ad_video`), `agent.py` (added
`--video`/`--profile` mode), `prompts/prompt.md` (added ad-effectiveness
instructions), `profiles/profile_student.json`,
`output/ad_effectiveness.json`, `output/harness.md`,
`requirements.txt` (added `opencv-python-headless`).

## Problem 6 — Student and parent profiles (Yale SOM)

**Prompt:** Create `profiles/profile_student.json` and
`profiles/profile_parent.json` describing typical Yale students/parents,
focused on the School of Management and its "business & society" mission.
Add useful fields to `CustomerProfile` in `models.py` for judging ad fit.
Discuss field choices and flag uncertainty before finalizing; add the
rationale to `output/harness.md` once decided.

**Follow-up prompt used:** Four open questions were raised before writing
any files (new `AppealCategory` for the SOM mission? a separate
"professional identity" category vs. a distinct "where worn" field? scope
the parent profile to SOM specifically? a separate mission-alignment
field?). Christopher's answers: add the new category; keep "what they like"
and "where they wear it" as two distinct fields, not one category; yes,
scope the parent to SOM; no separate mission field needed.

**Notes:**

- Added `AppealCategory.PURPOSE_IMPACT` to the shared vocabulary (used by
  both `CustomerProfile.interests` and `AdEffectivenessResult.ad_themes`).
- Added `CustomerProfile.wear_occasions` (list[str]), deliberately separate
  from `interests` — what appeals to a customer and where they'd wear the
  merch are different questions.
- Added `CustomerProfile.relationship_to_yale`
  (student/parent/alum/other) and `program` as structured fields alongside
  the existing free-text `role`.
- Considered and rejected: a separate "professional identity" appeal
  category (folded into `wear_occasions` instead) and a standalone
  mission-alignment field (redundant once `PURPOSE_IMPACT` existed as a real
  category).
- This intentionally overwrites P5's original `profile_student.json` (a
  generic Yale College undergrad); P5's harness section is left as a
  historical record of that specific run, not a description of the current
  file.

**Completed artifacts:** `models.py` (extended `AppealCategory` and
`CustomerProfile`), `tools.py` (`get_customer_profile_summary` updated for
the new fields), `prompts/prompt.md` (ad-effectiveness instructions updated),
`profiles/profile_student.json` (Maya Chen, SOM MBA student),
`profiles/profile_parent.json` (David Chen, parent of a SOM MBA student),
`output/harness.md`.

## Problem 7 — Run ad judgment for both profiles

**Prompt:** Run `agent.py` against `data/videos/ad_humble.mp4` for both
`profiles/profile_student.json` and `profiles/profile_parent.json`; save
both structured results to `output/ad_effectiveness.json` via
`AdEffectivenessResult`. Show the resulting file and set up
`output/agent_evaluation.md` for Christopher's own judgment of the output.

**Follow-up prompt used:** None needed.

**Notes:**

- Removed a stale "Jordan" entry from `output/ad_effectiveness.json` — a
  leftover from P5's original (since-replaced) generic student profile, no
  longer corresponding to any file in `profiles/`.
- Both runs landed on `effectiveness: medium`, for genuinely different
  reasons per profile (style mismatch + missing `purpose_impact` for Maya;
  missing `purpose_impact` + tone mismatch for David) — not a copy-pasted
  result. Neither matched on `purpose_impact`, consistent with Problem 5's
  finding that the ad itself never shows anything mission/impact-oriented.
- Appended a "Problem 7" section to the existing `output/agent_evaluation.md`
  (which already held Christopher's own P4 writeup) rather than overwriting
  or creating a second file — same blank-structure-only convention as P4.

**Completed artifacts:** `output/ad_effectiveness.json`,
`output/agent_evaluation.md` (P7 section scaffolded), `output/harness.md`.

## Problem 8 — Safety rules and audit trail

**Prompt:** Add safety rules for image processing that the agent loads as
its system prompt (asked whether these belong in `output/harness.md` or
`prompts/prompt.md`): no personalized data on customers, influencers,
parents, or any real photo of a person; `student`/`parent`/`alum` are
acceptable categories, nothing else should be gleaned; the agent may review
an image when necessary but facial information must never be stored or
analyzed (asked for an assessment of whether this rule is sufficient).
Append to `output/audit_trail.json` on every run from here on, with a new
`AuditEntry` Pydantic model in `models.py`; each loop iteration needs
thought, time, tool name, args, a short result, and the run needs a reason
it stopped. Document the audit fields in `output/harness.md`. Populate the
log with real data, from memory or a fresh run.

**Follow-up prompt used:** None needed.

**Notes:**

- Recommended (and implemented) the rules in `prompts/prompt.md`, since
  that's the only file actually loaded as the agent's instructions;
  `output/harness.md` documents and explains them instead, mirroring HW2's
  guardrail/enforcement split.
- Extended the requested rule in three ways, explained in
  `output/harness.md`: generalized it to every person in an image (not just
  named "customer/influencer/parent" roles), explicitly separated
  task-necessary tone/performance observation from identity/face
  description (rather than banning all engagement with people), and flagged
  as an honest limitation that this is currently prompt-level only — no
  code-layer check independently verifies the model's `reasoning` text
  actually stayed compliant.
- `AuditStep`/`AuditEntry` built from `result.all_messages()` (PydanticAI's
  real per-run message history), not reconstructed by hand. `thought` only
  ever holds text the model actually produced visibly in a turn — checked
  against a real run rather than assumed, and it came back empty every
  time, since this model's tool-calling turns don't include separate
  visible rationale. Left empty rather than invented, per HW2's
  "observable decisions, not hidden chain-of-thought" rule.
- Populated with real data: reran both Problem 7 ad-effectiveness commands
  with the new logging attached (2 entries, full real tool-call sequences),
  plus one deliberate rerun of `--image data/products/berkeley-1-4-zip.jpg`
  to produce a real example of the abort-path entry (`steps: []`,
  `stop_reason` describing the content-safety rejection). 3 real entries
  total, not a mockup.

**Completed artifacts:** `models.py` (added `AuditStep`, `AuditEntry`),
`agent.py` (audit extraction/append wired into both success and
content-safety-abort paths), `prompts/prompt.md` (safety rules section),
`output/audit_trail.json` (3 real entries), `output/harness.md`.

## Problem 9 — Finish the harness

**Prompt:** Rewrite `output/harness.md` so a less-technical manager could
understand the system: verify it covers every tool and both abilities
(identify a product, find the specific match, judge an ad for a customer
profile), every Pydantic/PydanticAI model in `models.py` and why its fields
are shaped that way, the Problem 8 safety rules, and other limiting specs
(max loop iterations, video frames sampled, image size, JPEG quality,
concurrency, retries) — explicitly distinguishing which limits were
requested versus which are my own engineering defaults versus untouched
library defaults. Keep all earlier sections' substance (catalogue
speedup/field choices, efficiency findings, profile fields, video tooling);
this problem is a coherent cleanup, not new capability.

**Follow-up prompt used:** None needed.

**Notes:**

- Rewrote `harness.md` from a per-problem changelog structure (`## Problem
  N — ...` headers) into one topical document: what the system does, the two
  abilities with their real verified results, all four tools, every
  `models.py` type with field rationale, safety rules, a limits table, failure
  handling, the audit trail, and an honest "known limitations" section.
  Problem-by-problem build history stays in this file (`AI_prompts.md`), not
  duplicated there.
- Directly answered (in chat and in the new "Limits" table): 8 video frames
  sampled (my choice, not requested); 640px max image side and JPEG quality
  75 (my choices, the latter corrected after Christopher's own push on
  Problem 2); 10-image identify cap (Christopher's explicit instruction);
  8-worker catalogue concurrency and `retries=2` (my choices). Named two
  real gaps rather than glossing over them: no hard cap on agent
  tool-calling loop iterations (`usage_limits` never set), and no overall
  run-time timeout (unlike HW2's 90-second budget).
- Verified all four tools, all two abilities, and all eleven `models.py`
  types (`MerchType`, `BrandingStyle`, `CatalogueEntry`, `ProductMatch`,
  `IdentifyResult`, `ProductCatalogue`, `AppealCategory`, `CustomerProfile`,
  `AdEffectivenessResult`, `AuditStep`, `AuditEntry`) are represented in the
  rewritten document; none were dropped in the consolidation.

**Completed artifacts:** `output/harness.md` (rewritten, ~360 lines, topical
structure).
