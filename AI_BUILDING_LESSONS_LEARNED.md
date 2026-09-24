# AI Building Lessons Learned

Personal notes for Christopher's Chief-of-Staff-in-AI job search — "cowork"
side of the pitch. Each build in this course is a source of concrete,
source-able examples of what actually makes AI-building efforts succeed
organizationally, not framework trivia.

**Why this file exists:** the point isn't "I can code an agent." It's
demonstrating the judgment that translates to a non-engineering leadership
role — coordination, verification discipline, and reuse of institutional
knowledge. Add a new dated entry after any future lecture/homework build
that produces a clear "why did this work (or break)" moment.

---

## Lecture 07 — Yale SOM course-explorer app, 2026-09-22

Built a course-catalog UI (React + Vite + TS) with a chat agent
(`search_courses` + native OpenAI `web_search` tool via pydantic-ai, routed
through Portkey) over Yale SOM's course JSON. Worked end-to-end on the first
live run after two quick fixes. Distilled lessons:

1. **Contract-first coordination** — locking `run_agent(message) ->
   {reply, tools_used}` as an exact interface before either side (frontend,
   backend, agent internals) was fully built let all three pieces get built
   in parallel and snap together on the first try. *CoS translation:*
   define the interface between two workstreams precisely, then let them
   move independently.

2. **Verify against the live system, not memory** — the AI SDK
   (pydantic-ai) had renamed key classes between versions (e.g. web search
   moved to a `NativeTool`/`WebSearchTool` concept, and requires the
   Responses API model, not Chat Completions). Checking the *installed*
   package's actual API before writing code — instead of pattern-matching
   on remembered docs — avoided a whole class of silent-wrong-wiring bugs.
   *CoS translation:* in fast-moving AI tooling, "verify against ground
   truth" beats "trust what I read last."

3. **Cheap verification before expensive verification** — ran imports,
   type-checks, and pure-function tests (free, instant) before any real LLM
   call (slow, costs quota). When the live call did fail, the failure
   surface was tiny because everything else was already proven. *CoS
   translation:* sequence cheap checks before expensive ones — it shrinks
   the space you have to debug later.

4. **Reuse institutional knowledge instead of re-deriving it** — when the
   live call 401'd on a Portkey auth issue, the fix was finding an
   already-working pattern in a sibling lecture folder (`lecture_04/agent.py`)
   and copying it, rather than guessing further. This was the single
   highest-leverage move in the session. *CoS translation:* assume someone
   (or something) already solved this; route to it before re-solving from
   scratch.

5. **Observability built in, not bolted on** — an append-only audit trail
   (timestamp, message, tool calls, errors) meant a live failure produced a
   precise, diagnosable record instead of a vague "it broke." *CoS
   translation:* insist on this kind of logging *before* something breaks,
   not after.

**Soundbite:** "The reliability came from contracts and verification
discipline — not from picking React."

---

## Homework 3 — Campus Customs merch-identify + ad-effectiveness agent, 2026-09-22

Built a two-ability PydanticAI agent (product-identify from a photo,
ad-effectiveness judged against a customer profile) plus a one-time
vision-based catalogue builder, over ten sequential problems. Several real
failures and a few deliberate stop/escalate moments produced clearer
lessons than the parts that just worked.

1. **A plausible optimization story is not evidence — measure it.** The
   crop/resize preprocessing was assumed to speed things up because the
   *mechanism* sounded right (less background, smaller payload). When
   actually measured (only because asked directly, "is this actually
   helping?"), the real version was making 82 of 102 images *bigger* than
   the source file, not smaller — a missing `optimize=True` flag, invisible
   until checked. *CoS translation:* "here's why this should be faster/
   cheaper" is a hypothesis, not a result. Ask for the before/after number
   before it goes in the deck.

2. **Diagnose whether the failure is in the system or in your own
   instrumentation before drawing a conclusion.** A string of confusing
   401 errors during debugging turned out to be a bug in the debugging
   script itself (a missing fallback default for an environment variable),
   completely unrelated to the real, separate, reproducible failure (3
   catalogue photos genuinely blocked by the vision vendor's content-safety
   filter). Two different problems, easy to collapse into one wrong story
   if you stop at the first plausible-sounding explanation. *CoS
   translation:* when a system "flakes," rule out your own tooling before
   you write the incident report about the vendor.

3. **Some blockers should be escalated to a person, not engineered around.**
   When the vision model refused certain (entirely legitimate) product
   photos, the natural engineering instinct was to keep iterating past it —
   tighter crops, retries. That instinct got flagged and stopped mid-task:
   repeatedly reshaping a request specifically to slip past a safety/
   moderation control is the wrong kind of persistence, even when the
   underlying content is obviously fine. The right move was a human
   decision (manual review), not a cleverer bypass. *CoS translation:*
   "I can probably find a way around this" is exactly the moment to check
   whether the obstacle is a bug (fix it) or a control (escalate it) —
   conflating the two is how well-intentioned teams end up defending a
   workaround instead of a decision.

4. **Make human-resolved exceptions permanently, structurally visible —
   never let them look like automation succeeded.** Every catalogue entry
   and audit record carries a `source`/provenance field distinguishing
   "the model produced this" from "a person entered this by hand." When
   ~3% of a pipeline can't be automated, that's fine — as long as nobody
   downstream can mistake the patched-over 3% for verified machine output a
   year from now. *CoS translation:* build the "how do we know this was a
   human override" answer into the data itself, not into someone's memory
   of the exception.

5. **Escalate real design forks with the tradeoffs named, especially ones
   that get reused everywhere downstream.** Before adding a new shared
   category to a vocabulary used by both sides of a matching system (an ad's
   themes and a customer's interests), the fork was surfaced explicitly —
   "I could add a category here, or handle it as a separate field instead,
   here's what each implies" — rather than silently picking one. That
   vocabulary got reused in every subsequent run; a silently-wrong default
   would have propagated everywhere instead of costing one conversation
   turn. *CoS translation:* the cost of asking is fixed and small; the cost
   of a silently-wrong foundational decision compounds with everything
   built on top of it. Ask before the fork gets load-bearing.

6. **When asked about one constraint, volunteer the adjacent one nobody
   asked about.** Directly asked to report the cost/quality limits already
   in place (image size, retry counts, worker concurrency), the review also
   surfaced — unprompted — that there was no cap at all on the agent's
   tool-calling loop length or overall run time. That gap was real and
   would only have surfaced later, expensively, in production. *CoS
   translation:* a status report that only answers the literal question
   asked is incomplete by design. The valuable version says "and here's a
   related risk you didn't ask about."

**Soundbite:** "Nothing here failed because of bad code. The moments that
mattered were catching a claim I hadn't actually measured, and knowing which
blockers were mine to fix versus a person's to decide."
