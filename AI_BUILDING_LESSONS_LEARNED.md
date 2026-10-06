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

## Lecture 08 — SQLite-backed course explorer with auth + chat history, 2026-09-24

Migrated the Lecture 07 app to a real database (SQLite, `users`/`chats`
tables added), email/password login (bcrypt + JWT), per-user chat history, a
public GitHub repo, and a live Render deployment (Web Service backend +
Static Site frontend). It all worked end-to-end, but getting there ran
through several real missteps worth keeping — most of them mine, not
Christopher's.

1. **Interruptions don't queue themselves — unfinished work has to be
   explicitly re-surfaced.** A git commit got left at "dry-run only" while a
   string of Render dashboard questions arrived back-to-back. Nothing forced
   a return to finish it, so it silently stayed undone. Render's "root
   directory doesn't exist" error then looked like a deploy-config problem;
   the real cause was an entire folder that had simply never been pushed.
   *CoS translation:* when work gets interrupted repeatedly, say out loud
   what's still pending before moving on to the next thing — don't assume
   you'll remember to circle back.
2. **Public-exposure risk is about what's stored in plaintext, not password
   strength.** A throwaway password is fully protected by bcrypt even if
   it's weak — that's the whole point of the hash. The signup *email*,
   though, sits in the database as plaintext, and once that database is
   committed to a public repo it's permanently, publicly linked to whoever's
   email is in it. The real risk question is "what's hashed vs. what's
   plaintext," not "is my password strong enough." *CoS translation:* "low
   stakes because it's a throwaway password" can hide a completely different
   exposure sitting one field over.
3. **In a monorepo, every path is relative to the repo root, not to the
   folder you're mentally standing in.** Typing `backend` instead of
   `lectures/lecture_08/backend` into Render's Root Directory field produced
   an error that read like a bigger problem than it was. *CoS translation:*
   when a system spans multiple nested projects, state paths in
   root-relative terms — "the folder" is ambiguous the moment there's more
   than one.
4. **When reasoning from indirect evidence, say so — don't present one
   plausible mechanism as the fix.** An unchanged rebuilt JS bundle got
   explained as "you clicked the wrong deploy button" — a specific,
   confident-sounding claim that was never checked against an actual build
   log, and turned out not to be the real cause at all (a typo'd env var key
   was). The right move once a first fix doesn't work is to flag the
   previous explanation as unconfirmed, not layer a second confident guess
   on top. *CoS translation:* state a diagnosis's confidence level honestly
   — "my best guess is X" and "X is what's wrong" should never sound
   identical.
5. **Verify against the actual deployed artifact, not a report that an
   action was taken.** "It's wired right, I did your check" (a passing
   health check) still left the frontend silently pointed at localhost in
   production. What actually confirmed the fix was curling the live JS
   bundle and grepping for the real backend URL baked into it. *CoS
   translation:* a status report ("I did the thing") is a claim, not
   evidence — check the artifact itself before declaring something fixed.
6. **A fix can introduce a new failure mode — re-verify with real metrics,
   not a glance at the top of the screen.** Fixing mobile crowding by
   setting a container to `height: auto` looked fine in a screenshot of the
   top of the page, but silently broke the internal scroll-clipping chain
   beneath it, rendering all 234 course cards unclipped (a 39,575px-tall
   element). Only checking the actual `scrollHeight` number caught it. *CoS
   translation:* "it looks right in the screenshot" and "it's actually
   right" are different claims — check a number, not just an impression.
7. **A comfortable heuristic works right up until it doesn't — know the
   real underlying rule.** "Static Site = frontend, Web Service = backend"
   was correct for this app, but only because the frontend has zero
   server-side logic. The actual line Render draws is "does this need a
   running process per request," not "frontend vs. backend" — a framework
   with server-side rendering (e.g. Next.js) would need a Web Service for
   its "frontend" too. *CoS translation:* know *why* a rule of thumb holds,
   not just that it happened to hold this time — that's the difference
   between it generalizing and it quietly failing on the next project.

**Soundbite:** "Every real bug today was upstream of the code — an
unfinished task, a wrong assumption stated with too much confidence, or a
path typed relative to the wrong root."

## Homework 1 — Spoke & Wrench financial pipeline (graded review), 2026-09-24

Built 2026-09-08 with Codex: LLM extraction of receipts, bank, and card
statements, an LLM reconciliation log, then a plain-Python income statement
and HTML report. Graded 86/100. Every lost point traced to a handoff between
steps, not to the LLM misreading a document. Revenue was overstated by
exactly $975.58 (three expense rows counted as revenue) and expenses
understated by that plus one dropped $89 charge.

1. **Hand off decisions as structure, not prose.** The bank-extraction step
   correctly tagged every line `revenue` or `expense`. The reconciliation
   step's output format had no field for it, so the label survived only
   inside a plain-English sentence. The income statement then guessed by
   searching that sentence for words like "invoice" and "service" — which
   flagged a parts invoice *received* and a bank "service fee" as revenue,
   even where the sentence literally said "expense." *CoS translation:* a
   decision made upstream but recorded only in an email is a decision the
   next team will re-make, differently.
2. **Every gap in a spec is a decision the AI makes silently.** The prompt
   said "roll rows into revenue and expense" but never said how to tell
   which. Codex filled the gap with a keyword heuristic and never surfaced
   it as a choice. *CoS translation:* when delegating, ask "what judgment
   calls did you make that I didn't specify?" — it costs ten seconds.
3. **Tie out to an independent control total.** The eight business deposits
   on the bank statement sum to $8,150 — exactly the grader's revenue. A
   30-second cross-check would have caught the error before submission.
   *CoS translation:* don't review the logic, reconcile the output against
   a number that was produced a different way.
4. **Agree on what each step assumes about its input.** Reconciliation was
   prompted to list only items needing a decision; the income statement
   treated that list as the complete ledger. A clean, single-source $89
   printing charge fell through the seam. The CLI deductions were the same
   failure: the rubric defined exact flags, and the build used convenient
   ones. *CoS translation:* two individually reasonable workstreams can
   still break where they meet — the interface is someone's job.
5. **A contingency plan needs a trigger.** The prompt log said "if the
   rollup misclassifies a row, ask AI to audit" — but nothing ever checked
   whether it had. *CoS translation:* turn every "if X goes wrong" into a
   check that actually runs.

**Soundbite:** "The AI did the hard part — reading messy documents —
correctly. The points were lost at the handoffs, where nobody owned the
contract between steps."

## Lecture 08 — mobile layout fixes (follow-up), 2026-09-29

One bug report — "mobile is crowded, make it scrollable" — turned into
three sequential rounds of fixes on the live Render deployment, each one
exposing the next real problem underneath rather than being the end of it.

1. **A layout fix can silently break the thing it depends on — verify with
   numbers, not a screenshot.** Making the mobile container scrollable via
   `height: auto` looked fine in a screenshot of the top of the page, but it
   unbounded the flex chain every internal list relies on to clip and
   scroll — the course list rendered all 234 cards unclipped (a
   39,575px-tall element) instead of a scrollable few. Only reading
   `scrollHeight` numerically caught it; nothing about the screenshot looked
   wrong. *CoS translation:* for layout/rendering bugs specifically, "looks
   right in a screenshot" and "is actually right" are different claims —
   check a number.
2. **`flex: 1` only produces a finite, scrollable area when every ancestor
   up to the true scroll boundary is itself bounded.** Re-flowing a
   side-by-side desktop layout into a stacked mobile one broke that chain
   silently — nothing errored, content just stopped clipping. *CoS
   translation:* when you re-flow a system for a new context (desktop →
   mobile, wide → narrow), re-check the sizing assumptions the whole system
   depends on, not just the piece you're changing.
3. **A UI pattern that works at one size can be structurally wrong at
   another, not just "too small."** ~25 category chips wrapping to 9+ rows
   on a phone wasn't a spacing problem to fix with more room — it was the
   wrong interaction pattern for that viewport. The fix was changing the
   pattern (a single swipeable row) rather than resizing the container
   around it. *CoS translation:* "make it bigger" is sometimes the wrong
   ask — the right fix is recognizing when a pattern itself doesn't
   transfer to a new context.
4. **A positioning strategy that works in the simple case can break in a
   nested/scrolled one.** `position: sticky` for a "stay at the bottom"
   taskbar is a reasonable first instinct, but it's unreliable specifically
   inside a custom scroll container sized with vh/% units on real mobile
   browsers, where the visible viewport itself changes as the address bar
   collapses. `position: fixed` — anchored to the real screen, not a scroll
   container — was the actually-robust choice, and checking for it exposed
   a second, related bug: a popup menu positioned relative to that same
   scroll container, which needed the identical fix. *CoS translation:*
   when a reasonable-sounding technical choice breaks in one specific
   environment, check whether something else built on the same assumption
   is quietly broken too.
5. **One bug report is rarely one bug — budget for the next layer, don't
   declare victory after the first fix.** "Crowded" → chips consuming the
   whole window → taskbar not sticking → popup menu misplaced were four
   distinct root causes, each surfaced only by testing after fixing the
   previous one, not predicted upfront. *CoS translation:* a symptom-level
   report ("this feels off") is the start of a debugging thread, not a
   single ticket — the fix that resolves the stated symptom is often just
   the first domino.

**Soundbite:** "Every fix this round passed the screenshot test and failed
the numbers test — the bugs were all in dimensions a picture doesn't show."

## Homework 4 — Campus Customs website + chatbot (kickoff), 2026-10-05

Kickoff only: planning, the architecture walkthrough, and a quiz before any
code. The quiz review alone surfaced design principles worth keeping. More
entries to come as the build proceeds.

1. **Show the facts that matter most with code, not the model.** Giving the
   agent a database tool for price and stock doesn't make a wrong answer
   impossible. The model can still misquote what the tool returned. What the
   tool does is give the model the real number and make its answer
   checkable against a logged tool call. For the facts a customer acts on
   (price, stock), the stronger move is to show them on the page straight
   from the database, so they're right no matter what the chat says. *CoS
   translation:* don't make an AI the only source for a number someone will
   rely on. Put it in a deterministic system of record, let the AI explain
   it, and keep a log that proves which source it used.

2. **Grounding reduces errors; an audit trail is what lets you trust it.**
   "It looks things up in the database" sounds like a guarantee, but it's
   really a lower error rate. Trust comes from being able to check
   afterward: was the tool called, what did it return, does the answer
   match. *CoS translation:* when a vendor says their AI is "grounded in
   your data," ask how you'd verify a specific answer after the fact.

3. **Prose is not an interface.** For chat search to update the page, the
   agent has to return product IDs in a fixed structure, not a paragraph
   describing the products. Code can't reliably act on prose. The split
   that works: the backend decides *which* products, the frontend decides
   *how* they look. *CoS translation:* when one team's output feeds another
   team's work, agree on a structured handoff format. A well-written memo
   is not a spec. (Same lesson as HW1's revenue/expense label that survived
   only in a sentence.)

4. **Keep the LLM out of deterministic, security-sensitive paths.** Login is
   a strict yes/no hash comparison. Routing it through an LLM would add
   cost and latency, send credentials to a third-party API, and open a door
   to someone talking the model into "logging them in." *CoS translation:*
   decide on purpose which steps need judgment (use AI) and which need
   exactness or control (use plain code). "We could use AI for that too"
   isn't a reason.

5. **Check a reused pattern against the actual data before copying it.**
   Lecture 08's login code used bcrypt, but HW4's database stores PBKDF2
   hashes. Copying the earlier code as-is would have locked every existing
   user out, with no error until someone tried to log in. *CoS translation:*
   reusing institutional knowledge is high-leverage (see Lecture 07), but
   only after confirming the new situation actually matches the old one.

6. **Plan backward from the delivery spec, and scope a visibility decision
   to its container.** The submission problem (a public repo, a required
   folder name, a list of files that must never be committed) was read
   first, so every earlier step builds toward the right place. It also
   caught a trap: the instinct to "just make my repo public" would have
   published the whole private workspace, including other coursework and a
   database with signup emails. The fix is a separate public repo holding
   only the deliverable. *CoS translation:* read the delivery requirements
   before the work starts, and when something is made public, check
   everything that comes with it, not just the part you meant to share.

**Soundbite:** "Let the model explain; let code state the facts — and make
sure you can prove which one said what."

### HW4 build lessons (P3–P8), 2026-10-06

7. **A silent cap looks exactly like a complete answer.** Search returned
   "at most 10" results. For "show me hoodies," the page would have said
   "Hoodies · 10 items" with no error. It looks finished, and it's wrong,
   because there are 27. It was caught only by counting against the
   database *before* building. *CoS translation:* when a report says "here
   are the results," ask "is this all of them, or the first N?" Limits
   don't announce themselves.

8. **The change on disk isn't necessarily the change that's running.** The
   agent kept refusing to tell a customer their own email, even after the
   rule was fixed, because the server only reloads on code changes and was
   still running the old prompt. Several "fixes" were tested against a
   system that hadn't received them. *CoS translation:* before judging
   whether a fix worked, confirm the fix is actually live. Same lesson as
   Lecture 08's stale production bundle.

9. **Defaults are decisions someone else made for you.** The web
   framework's standard error message echoed the whole form back,
   password included. Nobody chose that; it was the default. *CoS
   translation:* when adopting a tool, ask what it does by default with
   sensitive data, not just what it can be configured to do.

10. **Treat a vendor's safety control as a layer to handle, not an
    obstacle.** The AI provider's content filter blocked a jailbreak test
    and crashed the chat. The fix was to handle the block gracefully (a
    polite in-character reply), not to reword the test to slip past it.
    Our own rules caught the milder version that the filter let through.
    *CoS translation:* layered controls are a feature. Design for each
    layer to fail gracefully instead of trying to get around the one in
    your way.
