# Homework 2 AI Prompts

This file records the prompts used with AI for each homework problem. It will
be updated as the work progresses. The assignment builds a sales agent for
Sanford & Hawley that identifies prospective business customers and drafts
outreach emails; it does not send emails.

## Assignment setup prompt

**Prompt:** Use the HW1 prompt-log convention for Homework 2. Work
systematically through Problems 2–8 to create an agent that helps Sanford &
Hawley (sanhaw.com) find other business customers and draft, but not send,
outreach emails. Use the configured Portkey API key for AI model calls and use
a stronger model for the agent if appropriate. Record the first prompt for
each problem and one follow-up prompt only if one is needed.

**Follow-up prompt used:** Not yet needed; record one here only if the initial
problem prompt requires a correction, clarification, or rerun.

## General execution plan

1. Establish the seller brief: what Sanford & Hawley sells, whom it serves,
   what makes a target valuable, and what outreach constraints apply.
2. Convert that brief into the agent’s system prompt and operating rules.
3. Build the agent, add the company profile, and run a first profile-grounded
   test.
4. Expand the prompt with customer-discovery requirements and identify
   candidate business customers.
5. Document the agent harness and its reproducible inputs, outputs, and checks.
6. Rank the targets, draft personalized emails, and preserve the drafts as
   reviewable output only.
7. Build the dashboard webpage that presents the targets, rankings, and email
   drafts with clear provenance and status.

## Problem 2 — Seller brief

**Prompt:** Create `assets/seller_brief.md` for Sanford & Hawley
(`https://sanhaw.com/`). Capture verified seller background, the owner’s
reason for choosing the local family-owned lumber business, products and
services, known customer audiences, and open questions about contractor types,
contractor size, independent versus network ownership, and the unknown share
of sales from DIY/homeowner customers. Define the additional fields that will
matter when finding and qualifying sales targets, especially location and
serviceability. The brief should prepare those fields for later use in the
agent, but the agent will receive the website URL from the terminal and does
not need to read the brief at runtime. Do not invent unsupported facts.

**Follow-up prompt used:** None needed.

**Completed artifact:** `assets/seller_brief.md`

## Problem 3 — Agent system prompt

**Prompt:** Build one PydanticAI agent total. Its system prompt is
`prompts/sales_agent.md`. When the human asks for a company profile or gives a
company URL, crawl the company website provided through the terminal and work
toward `assets/company_profile.json`. Use the seller-brief field framework for
the profile, record only verified information, preserve unknowns, and flag the
profile if fewer than half of the requested fields are available. Keep the
agent friendly and approachable while remaining factual. The prompt should
support later extensions for finding customers and drafting unsent outreach
emails.

**Follow-up prompt used:** None needed.

**Completed artifact:** `prompts/sales_agent.md`.

## Problem 4 — Build agent + profile run

**Prompt:** Build the single PydanticAI agent in `sales_agent.py`. Load
`prompts/sales_agent.md` as its system prompt. Give it a bounded Playwright
web-crawler tool and the dependencies it needs. The script must accept the
human’s query text plus a terminal `--url`, pass both to the agent, and write
the separate researched company profile to `assets/company_profile.json`.
Keep runs safe and cost-efficient: stay in `hw_02/.venv`, stop within about a
minute, record tool activity and unique input URLs in `output/audit_log.json`,
and never send email. Document the harness, memory, stopping rules,
guardrails, and audit design in `HARNESS.md`, then run it on `https://sanhaw.com/`.

**Follow-up prompt used:** The first run exposed that the crawler tool was
registered on a different agent instance and therefore the model saw zero
tools. Register the tool on the exact per-run agent instance and rerun the
profile.

**Completed artifacts:** `sales_agent.py`, `requirements.txt`,
`.env.example`, `HARNESS.md`, `README.md`, `assets/company_profile.json`, and
`output/audit_log.json`.

## Problem 5 — Expand prompt + find customers

**Prompt:** Extend the same single agent so it can find prospective Sanford &
Hawley customers when given the seller profile. Search the web for candidate
companies, evaluate their fit, reject poor candidates, inspect promising
candidate websites for business context and public contact email, and draft
one targeted but unsent outreach email per selected target. Write company and
contact information to `output/targets.json`, drafts to `output/emails.json`,
and continue appending to `output/audit_log.json`. Evaluate no more than twenty
candidates, do not invent facts, and keep the run bounded and cost-safe.

**Follow-up prompt used:** Find 3 good customer targets for this company and
draft outreach emails. Return only targets with verified public website
evidence and public business contact information; if fewer than 3 qualify,
return fewer.

**Completed artifacts:** expanded `prompts/sales_agent.md`,
`output/targets.json`, `output/emails.json`, and the appended
`output/audit_log.json`.

The workflow now also supports a discovery-only pass that creates
`output/candidate_list.json` before qualification, using a 90-second maximum
per individual agent run with separate search and crawl budgets.

## Problem 6 — Agent harness summary

**Prompt:** Prepare an Agent harness summary in the project-root `HARNESS.md`.
Explain how the single agent is harnessed, the tools it can use and why,
inputs and outputs, normal and early-success stopping rules, failure types,
guardrails, and where the audit trail is recorded. Explain which guardrails
are enforced in the prompt, code, schemas, audit layer, and packaging.

**Follow-up prompt used:** None needed.

**Completed artifact:** `HARNESS.md`.

## Problem 7 — Rank targets and emails

**Prompt:** To be recorded when Problem 7 begins.

**Follow-up prompt used:** None yet.

**Planned artifacts:** ranked targets and draft outreach emails. Emails will
not be sent.

## Problem 8 — Sales dashboard webpage

**Prompt:** Build a small self-contained `dashboard.html` showing Sanford &
Hawley’s company profile, the three selected target customers, their scores,
fit highlights, contact information, and drafted emails. Include the number of
seeded/checked companies where available. Use tabs for readable company-by-
company review. Embed all profile, target, and email data directly in the HTML
so graders need no JSON files or setup. Give it a simple early-2000s Windows
desktop aesthetic with restrained retro lumber-themed pixel art and a
nighttime forest mood. Keep all emails clearly unsent.

**Follow-up prompt used:** None yet.

**Completed artifact:** `dashboard.html`.

## Final packaging checklist

- [ ] Package the submission as `hw2.zip` with a top-level `hw2/` folder.
- [ ] Include `AI_prompts.md`, `HARNESS.md`, `requirements.txt`, and
  `.env.example` with placeholder values only.
- [ ] Include the agent, dashboard, assets, prompts, and output artifacts.
- [ ] Exclude `.env`, `.venv/`, API keys, and any other real secrets.
