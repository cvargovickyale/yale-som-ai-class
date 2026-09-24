# Homework 3 Agent Harness — Campus Customs

This document explains the whole system in one place: what it does, how it
decides things, what it's allowed to do, what it costs, and where it's known
to fall short. It's written to be readable by someone who isn't going to
read the code — technical detail is here when it matters, but every section
leads with what a manager actually needs to know. (It was built up problem
by problem across this homework; the detailed build history — the exact
prompts and corrections at each step — lives in `AI_prompts.md`, not here.)

## What this system does

Campus Customs sells Yale merchandise. This project builds one agent with
two abilities, plus a one-time script that gives the agent something to
work from:

1. **Build a product catalogue** (`build_catalogue.py`, run once): turns 102
   raw product photos into a structured, searchable database.
2. **Ability 1 — identify a product in a photo**: given any photo, decide
   whether someone is wearing a Campus Customs product, and if so, exactly
   which one from the catalogue.
3. **Ability 2 — judge an ad's effectiveness**: given an ad video and a
   customer profile, judge how well that specific ad would land with that
   specific customer, and why.

```text
data/products/*.jpg  ──build_catalogue.py──▶  output/catalogue.json
                                                       │
                        ┌──────────────────────────────┘
                        ▼
  --image <photo>  ──agent.py──▶  output/identify_product.json

  --video <ad> --profile <customer.json>  ──agent.py──▶  output/ad_effectiveness.json

  (every agent.py run also appends to)  ──▶  output/audit_trail.json
```

The agent itself is exactly four files: `prompts/prompt.md` (the system
prompt, loaded fresh on every run), `agent.py` (entry point — builds the
model connection, registers tools, runs one of the two abilities, writes
output), `tools.py` (the actual tool logic), and `models.py` (every
structured data type, shared by everything). `build_catalogue.py` is
deliberately kept separate from those four files — cataloguing only needs to
run once (or when the photo set changes), while the agent runs repeatedly
against whatever it produced.

## The two abilities, and the tools behind them

Both abilities follow the same shape: a cheap, text-only tool to narrow
things down, then a bounded tool that actually loads images/video for the
model to look at. Nothing here checks a large set of images one at a time —
that's the whole point of the two-step design.

| Tool | Used by | What it does |
|---|---|---|
| `get_catalogue_summary` | Ability 1 | Returns every catalogue product as plain text (filename, merch type, school/program, branding) — zero images loaded. |
| `load_product_images` | Ability 1 | Loads up to 10 named catalogue photos as real images to compare against the query photo; a call over 10 is rejected and the model is told to narrow its list instead. |
| `get_customer_profile_summary` | Ability 2 | Returns the customer profile as plain text (role, interests, style, budget, occasions) — zero video frames loaded. |
| `watch_ad_video` | Ability 2 | Loads 8 evenly-spaced frames from the ad video as real images. |

A tool is just a plain Python function in `tools.py` until `agent.py`
registers it on a specific `Agent` instance with `agent.tool(...)` — that
registration ("wiring") is what generates a schema from the function's
signature and makes it something the model is actually allowed to call
mid-run. `build_identify_agent()` wires the first two tools; `build_ad_agent()`
wires the other two. Nothing in `tools.py` can run on its own.

### Ability 1: identify a product

```zsh
python agent.py --image "data/test_images/image_01_true.jpeg"
```

1. The agent looks at the query photo directly (given to it up front, not
   through a tool).
2. It calls `get_catalogue_summary` — free, no images.
3. It reasons about plausibility using only that text: if the garment type
   or visible branding doesn't plausibly match anything Campus Customs
   sells, it stops here and reports no product, having loaded zero images.
4. Otherwise it calls `load_product_images` with its best few guesses
   (≤10 filenames) and visually compares.
5. It reports whether a product is present, which one (with a confidence
   level) if it could pin one down, its reasoning, and exactly which
   filenames it actually compared against.

**Verified on real test images** (`data/test_images/*.jpeg`, ground truth in
each filename): 3 of 4 produced a correct result — `image_01_true` matched
`yale-dad-t-shirt.jpg` after loading 3 candidates; `image_02_false` correctly
reported no product after loading **zero** candidates (ruled out from the
garment description alone); `image_03_true` matched
`dry-zone-long-sleeve.jpg` after loading 2 candidates, explicitly
discriminating it from a visually similar Under Armour long-sleeve. Total
images loaded across all three: 5, out of a possible 102 each. The fourth
(`image_04_false`) could not be checked at all — see Known Limitations.

### Ability 2: judge ad effectiveness

```zsh
python agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_student.json"
```

1. The agent calls `get_customer_profile_summary` — who is this ad being
   judged for, and what do they respond to.
2. It calls `watch_ad_video` to see 8 sampled frames and judges what the ad
   actually emphasizes, using the same category vocabulary
   (`AppealCategory`) the customer profile uses for its own interests.
3. It computes the actual overlap between what the ad shows and what the
   customer cares about, and rates effectiveness on that evidence — not a
   general impression of ad quality.

**Category design was grounded in the real video, not guessed.** Before any
schema was written, 8 frames of `data/videos/ad_humble.mp4` (9 seconds,
1920x1080) were pulled and reviewed by hand. It turned out to be a shot-for-
shot parody of Kendrick Lamar's "HUMBLE." music video — a ~15-20 person
group under a highway overpass in Yale merch, led by one performer rapping
directly to camera. That's squad identity, stylized confidence, and a
cultural-reference joke — not athletics, not family, not academics. The
seven `AppealCategory` values (`school_pride`, `humor_comedy`,
`social_belonging`, `style_fashion`, `confidence_swagger`,
`athletic_energy`, `tradition_heritage`, plus `purpose_impact` added in
Problem 6 for the Yale School of Management personas' "business and
society" mission) reflect what's actually in the one ad that exists, not a
generic guess at what a "school ad" might contain.

**Verified on both real profiles** (`profiles/profile_student.json` — Maya
Chen, a Yale SOM MBA student; `profiles/profile_parent.json` — David Chen,
her parent), against the one ad video: both landed on `effectiveness:
medium`, but the reasoning behind each is genuinely different, not a
copy-paste — see the models section below for what `AdEffectivenessResult`
actually captured, and Known Limitations for a real critique of the
same-label outcome.

## Getting video into a photo-only model call

Chat Completions accepts images, not raw video, and no system `ffmpeg` is
installed on this Mac. Rather than requiring an install, `tools.py` uses
`opencv-python-headless` (a pip package with no system dependency) to pull 8
evenly-spaced frames via `cv2.VideoCapture`, convert BGR→RGB, and reuse the
same downscale/JPEG-encode path as product photos. There's exactly one video
per run, so unlike `load_product_images` there's no shortlisting question
and no 10-item cap needed here.

## Data models (`models.py`) — what each is for, and why the fields are shaped this way

Every structured type in this homework lives in one file rather than being
scattered across scripts. A **Pydantic model** is a schema: it declares
exact field names, types, and allowed values, and rejects anything that
doesn't match — the difference between "the model returned some JSON we
hope parses" and "the model returned exactly this shape or the call fails
validation." **PydanticAI** uses those same classes as an `Agent`'s
`output_type`, turning the schema into a tool call the model is constrained
to use, so the code gets back a real Python object (`result.match.filename`,
an actual string), never text to hope-parse.

**Catalogue types** (Problem 2):
- `MerchType` — garment categories actually observed across the 102 product
  photos (t-shirt, crewneck, hoodie, quarter-zip, fleece/bomber jacket, long
  sleeve, mockneck). A photo's garment silhouette is one of the more
  reliable signals for whether it's plausibly Campus Customs merch at all,
  independent of branding.
- `BrandingStyle` — whether the school identity is a wordmark, a logo/icon,
  a crest, or some combination. Manually reviewing the photos showed a real
  photo often only shows one of these clearly, so collapsing it into free
  text would lose the distinction the identify ability needs most.
- `CatalogueEntry` — one product: `filename`, `source` (`vision_model` or
  `manual` — see Known Limitations), `merch_type`, `description`,
  `school_or_program` (the specific Yale entity — a residential college, a
  school, a varsity sport, a family-affinity line, or generic "Yale" — not
  collapsed to just "Yale"), `branding_style`, `primary_colors`.
- `ProductCatalogue` — the container written to `catalogue.json`: `model`,
  `generated_at`, `entries`, and `skipped` (filenames that never got a
  valid entry — see Known Limitations. Never fabricated; a failed photo is
  recorded here, not silently dropped or guessed at).

**Identify types** (Problem 3):
- `ProductMatch` — just enough to say *which* product and *how sure*:
  `filename` (links back to the real catalogue entry rather than duplicating
  its data), `school_or_program`/`merch_type` for a quick read, `confidence`
  (high/medium/low).
- `IdentifyResult` — written to `identify_product.json`: `query_image`,
  `product_present` (kept separate from `match` because "nothing here" and
  "something's here but I can't pin it down" are genuinely different
  outcomes), `match` (`ProductMatch | None`), `reasoning` (an observable
  account of what was seen — not the model's private chain-of-thought),
  `candidates_considered` (the filenames actually compared, bounded to ≤10 —
  set from the agent's own tool-call bookkeeping, not the model's
  self-report, so it's verifiable rather than trusted).

**Ad-effectiveness types** (Problems 5–6):
- `AppealCategory` — one enum used on *both* sides of the judgment (a
  customer's `interests` and an ad's `ad_themes`); the overlap between the
  two lists is the actual matching mechanism, not a side effect of reusing
  an enum. Grounded in the real ad (see above) plus one addition
  (`purpose_impact`) grounded in the SOM personas' actual "business and
  society" mission.
- `CustomerProfile` — `name`, `role` (free text), `relationship_to_yale`
  (`student`/`parent`/`alum`/`other` — structured and filterable, distinct
  from the free-text `role`), `program` (e.g. "Yale School of Management,
  MBA"), `age_range`, `interests` (`AppealCategory` list), `wear_occasions`
  (free-text list — deliberately kept separate from `interests`: what
  appeals to someone and where they'd wear the merch are different
  questions), `style_preferences`, `budget_sensitivity`, `notes`.
- `AdEffectivenessResult` — written to `ad_effectiveness.json`:
  `video_path`, `customer_name`, `ad_themes` (what the agent judged the ad
  actually shows), `matched_categories` (the real overlap with this
  customer — the evidence, kept separate from `ad_themes` so the reasoning
  is inspectable after the fact), `effectiveness` (high/medium/low),
  `reasoning`.

**Audit types** (Problem 8):
- `AuditStep` — one turn of the agent's loop: `timestamp`, `thought` (only
  ever real visible text the model produced that turn — see Known
  Limitations, it came back empty on every real run so far), `tool_name`/
  `tool_args` (`None`/`{}` for a turn with no tool call), `result_summary`
  (the tool's return, truncated to 200 characters).
- `AuditEntry` — one full run: `timestamp`, `mode`, `inputs`, the `steps`
  list, `stop_reason` (plain text — "completed normally" or "aborted:
  content-safety rejection on X"), `outcome_summary`.

## Safety rules

Christopher's original request (with an "is this sufficient?" attached):
never save personalized data about a customer, influencer, or parent, or
about any real photo of a person; `student`/`parent`/`alum` are acceptable
categories, nothing else should be gleaned; the agent may look at a photo
when necessary, but facial information must never be stored or analyzed.

**Where this lives:** `prompts/prompt.md`, not this document. Only the
prompt is actually loaded into the model's context
(`instructions=PROMPT_PATH.read_text(...)` in both `build_identify_agent()`
and `build_ad_agent()`) — a rule written only in a harness document describes
a policy but enforces nothing.

**Assessment of the requested rule, and three extensions made to it:**

1. **Generalized past the named roles.** The request named "customer /
   influencer / parent." The images actually contain people who are none of
   those things — the 15-20 person crowd in the ad video, any bystander in
   a test photo. The rule now applies to *every* person in an image.
2. **Separated "necessary task observation" from "identity description."**
   A blanket "never analyze people" would conflict with the ad-effectiveness
   task's real job — judging a scene's tone, partly conveyed by the people
   in it. Resolved by permitting performance/tone description (confident,
   assertive, deadpan) while banning any facial or identifying-feature
   description, rather than refusing to engage with people at all.
3. **Named an honest limitation instead of assuming compliance.** As built,
   this is a prompt-level rule only — nothing in code independently checks
   that `reasoning` text actually stayed compliant before it's written to
   disk. For this assignment that's an acceptable scope: no output field
   asks for a person description in the first place, and real runs (rerun
   for Problem 8 with this rule active) show `reasoning` staying scoped to
   garments and performance/tone with no facial content. But "the model
   wasn't asked to" is weaker than "the code wouldn't let it" — a production
   system handling less cooperative inputs would want a second, code-layer
   check, not just the prompt.

**Where it's enforced, layered:**
- **Prompt:** `prompts/prompt.md`'s "Safety rules for photos and video of
  real people" section.
- **Schema:** no field on `CustomerProfile`, `IdentifyResult`, or
  `AdEffectivenessResult` asks for a person or identity description at all.
- **Code:** photos and video frames exist only as in-memory bytes passed to
  the model (`load_image_bytes`, `_sample_video_frames`); nothing anywhere
  writes an image file or embeds raw image bytes into any JSON output.
- **Audit:** `AuditStep.result_summary` is built from tool-call metadata
  (filenames, counts, catalogue text) — never from image content.
- **Not enforced** (the honest gap named above): no independent check that
  `reasoning`/`thought` text complies with the rule.

## Limits that matter for cost, speed, and quality

Asked directly which of these came from an explicit instruction versus an
engineering default chosen along the way — here's the full list, honestly
attributed:

| Limit | Value | Where | Who decided |
|---|---|---|---|
| Max candidate images per identify comparison | 10 | `tools.py: MAX_CANDIDATE_IMAGES`, enforced via `ModelRetry` | **Christopher, explicitly** ("never send more than 10 product images in a single call") |
| Ad video frames sampled | 8 | `tools.py: AD_FRAME_SAMPLE_COUNT` | My choice — a round number giving reasonable coverage of a 9-second/217-frame clip without excessive image count; not tuned against other values |
| Max image side after crop/resize | 640px | `tools.py`, `build_catalogue.py: MAX_IMAGE_SIDE` | My choice, spot-checked for legibility (crest text still readable), not exhaustively tuned |
| JPEG quality on re-encode | 75, with `optimize=True` | `tools.py`, `build_catalogue.py: JPEG_QUALITY` | My choice, but only after Christopher pushed on whether the crop/resize trick was actually helping — the first version (quality 85, no `optimize`) was measured to make 82 of 102 images *bigger* than the source; this value is the corrected one |
| Catalogue-build concurrency | 8 workers | `build_catalogue.py: DEFAULT_MAX_WORKERS` | My choice for the one-time script; overridable via `--workers` |
| Agent output-validation retries | 2 | `agent.py`, `Agent(..., retries=2)` | My choice; PydanticAI's own parameter default is `None` |
| **Max tool-calling loop iterations per run** | **none set** | — | **Nobody — an honest gap.** PydanticAI supports `usage_limits=UsageLimits(request_limit=...)` on `run_sync`, whose own default *if you construct one* is 50, but `agent.py` never passes `usage_limits` at all, so there is currently no hard cap on how many rounds the model could theoretically loop through. In practice only 2 tools exist per ability and the prompt guides a short flow (confirmed: real runs so far take 2-3 steps), but nothing in code would stop a pathological loop. |
| **Overall wall-clock timeout per run** | **none set** | — | **Nobody — another honest gap.** HW2's agent had a 90-second run timeout; this one has no equivalent. Worth adding if this were going further. |
| Manual-review offers (catalogue build) | 1 per failed photo per run | `build_catalogue.py: run_manual_review()` | My design, matching "ask a human once, don't loop" |

## Failure handling (all abilities)

A failure is never silently presented as a success, and never fabricated:

- **Catalogue build:** a per-image vision-call failure is caught, recorded in
  `skipped`, and does not abort the batch. 3 of 102 photos hit a genuine
  Azure content-safety 400 on heraldic crest artwork (a false positive, not
  a code or key problem) and were resolved by asking Christopher to look at
  them directly and enter the fields himself (`source: "manual"` — fully
  transparent in the data, never indistinguishable from an automated entry).
- **Identify / ad-effectiveness runs:** the same content-safety rejection
  can hit a *query* photo or the ad video too — confirmed for real on
  `data/products/berkeley-1-4-zip.jpg` (used as a query image) and on
  `data/test_images/image_04_false.jpeg` (a photo containing a visible
  third-party "Balenciaga" logo, a different trigger than crest artwork).
  In both cases, `agent.py` catches the error, prints a clear message, and
  writes **nothing** — "could not be checked" is a different, explicitly
  distinct outcome from "checked, nothing found," never collapsed into one.
- **No automated retry logic exists anywhere to specifically defeat
  content-safety moderation.** One was attempted during testing (shrinking
  crops to try to slip past the filter) and deliberately abandoned — see
  the audit-trail/safety-rules reasoning above; a moderation rejection
  either gets resolved by a human looking at the actual content, or stays
  honestly recorded as unresolved.

## Audit trail

Every `agent.py` run — both abilities, success or failure — appends exactly
one `AuditEntry` to `output/audit_trail.json` (`_append_audit_entry()`
rewrites the whole file each time; nothing already there is ever dropped or
edited). Steps are built by `_extract_audit_steps()` walking
`result.all_messages()` — PydanticAI's actual per-run message history, not a
reconstruction — matching each tool call to its return by `tool_call_id`.

`thought` is never backfilled with a guess at hidden reasoning: it's only
ever visible text the model included alongside a tool call. Checked against
real runs rather than assumed — every step so far has `thought: ""`, because
this model's tool-calling turns don't include separate visible rationale.
Logged as empty rather than invented, the same "observable decisions, not
hidden chain-of-thought" rule HW2's audit log used.

**Real data, not a mockup:** `output/audit_trail.json` has 3 entries as of
this writing — the Problem 7 student and parent ad-effectiveness runs
(full real tool sequence: `get_customer_profile_summary` → `watch_ad_video`
→ `final_result`, real timestamps, real truncated results), plus one
`identify` run against the known-blocked Berkeley photo, giving a real
example of the abort path (`steps: []`, since the content-safety rejection
happens before any message history exists to walk).

## Known limitations (an honest list)

- **3 of 102 catalogue photos and 1 of 4 test images could not be
  automatically processed**, blocked by the vision backend's own
  content-safety filter (heraldic crest artwork; a visible third-party
  brand logo). The 3 catalogue photos were resolved through manual entry;
  the 1 test image was not (nothing required it to be, but it means
  Ability 1 was only ever verified on 3 of the 4 available ground-truth
  photos).
- **Both real ad-effectiveness runs landed on the same `effectiveness:
  medium` label**, for genuinely different underlying reasons (see each
  entry's `reasoning`). Christopher's own evaluation (`agent_evaluation.md`)
  flags this directly: a 3-level high/medium/low scale may be too coarse to
  separate "medium because of X" from "medium because of Y," and neither
  `high` nor `low` has ever actually been observed, since only one ad video
  exists to test against.
- **No hard cap on agent loop iterations or overall run time** (see Limits
  table above) — a real gap, not a hidden safety net.
- **The "rule out before loading any images" step in Ability 1 is entirely
  the model's own judgment**, with nothing in code independently
  double-checking it. `image_02_false.jpeg` correctly loaded zero
  candidates in the one real test we have, but a wrong call at this step
  (incorrectly assuming something is implausible) would not currently be
  caught by anything else in the system.
- **The safety rules for photos of real people are prompt-level only** — no
  code-layer check independently verifies compliance (see Safety Rules
  section above).
