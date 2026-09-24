# Homework 2 Agent Harness

## Human summary

This project uses one research agent to help Sanford & Hawley find potential
business customers. A human gives the agent an instruction and either a
company URL or a prepared list of candidate URLs. The agent can search for
leads, visit public company websites, compare each company with Sanford &
Hawley’s products and service area, and write structured profiles and draft
emails.

The agent is deliberately kept on a short leash. It can read public webpages,
but it cannot send email, submit forms, or invent missing information. It stops
when it has enough well-supported results, reaches its page/tool/time budget,
or encounters a problem it cannot resolve honestly. Every run records what it
was asked to do, which tools it used, which URLs it visited, how long it took,
and whether it succeeded or stopped early.

The simplest way to think about the workflow is:

```text
human request + seller profile
              ↓
       discover candidate leads
              ↓
     verify promising websites
              ↓
   select good-fit businesses
              ↓
      draft emails for review
```

The files are the handoff points: `candidate_list.json` contains leads,
`targets.json` contains qualified companies, `emails.json` contains drafts,
and `audit_log.json` explains what happened during the run.

## What the harness is

The harness is the surrounding system that makes the single PydanticAI agent
useful, bounded, and auditable. `sales_agent.py` receives a human query and
either a company URL or a seller profile. It loads `prompts/sales_agent.md` as
the system prompt, gives the agent only the registered research tools, and
writes structured files rather than relying on conversational prose.

The agent has three related operating modes:

```zsh
# Profile one company
python sales_agent.py "Build a profile of this company." --url https://sanhaw.com/

# Discover broad candidate leads without crawling them
python sales_agent.py "Find up to 20 plausible customer candidates." \
  --profile assets/company_profile.json --discover

# Qualify the cached leads and draft unsent outreach
python sales_agent.py "Find 3 good customer targets and draft outreach emails." \
  --profile assets/company_profile.json --candidates output/candidate_list.json
```

The input query is the human’s instruction. `--url`, `--profile`, and
`--candidates` are explicit data inputs. The seller brief informs the prompt
and schema design; the runtime agent uses the supplied profile/list and does
not depend on chat history.

## Tools, reasons, inputs, and outputs

### PydanticAI agent

- **Why:** interprets the human request, chooses research steps, evaluates
  evidence, and returns structured output.
- **Input:** the query plus either a company URL or seller/profile context.
- **Output:** a `CompanyProfile`, `CandidateList`, or `TargetResearchResult`
  validated through Pydantic models.

### `search_for_prospective_companies`

- **Why:** discovers possible business customers when a seed list is not yet
  available.
- **Input:** a focused search query and a bounded result count.
- **Output:** public search titles, snippets, and URLs. These are leads only;
  they are not treated as verified company facts.
- **Limits:** at most four search calls per discovery run, with at most ten
  results per call.

### `crawl_company_website`

- **Why:** verifies a candidate’s public business context, geography,
  services, and public business contact details.
- **Input:** one HTTP(S) company URL.
- **Output:** readable text from same-hostname HTML pages, plus crawled URLs
  and timeout/error summaries in the audit log.
- **Limits:** at most eight candidate crawls in discovery/qualification mode,
  four pages per candidate, and eight seconds per page. Discovery-only mode
  does not crawl candidates.

### Portkey/OpenAI model client

- **Why:** supplies the model reasoning and structured response generation.
- **Input:** the system prompt, human query, tool results, and profile/list
  context.
- **Output:** the Pydantic-validated result; it does not directly send email
  or perform business actions.
- **Configuration:** `PORTKEY_API_KEY`, `PORTKEY_BASE_URL`, and
  `OPENAI_MODEL` come from the root `.env`; the secret is never printed or
  copied into the submission.

### Playwright Chromium and dotenv

Playwright supplies the browser implementation used by the two research tools.
`python-dotenv` loads local configuration. Neither is an agent decision tool
or an external-action tool.

## Outputs and data flow

- Profile mode writes `assets/company_profile.json`.
- Discovery mode writes `output/candidate_list.json`.
- Qualification mode writes `output/targets.json` and `output/emails.json`.
- Every mode appends to `output/audit_log.json`.
- `assets/seller_brief.md` is the durable seller context and field-design
  reference, not a generated target profile.

## Stopping rules

The agent must stop when any of these occurs:

- It has returned the requested number of defensible targets and corresponding
  draft emails.
- It has exhausted the allowed search/crawl budget.
- It reaches the 90-second individual agent-run timeout.
- A required input is missing, invalid, inaccessible, or ambiguous.
- The requested result would require inventing a fact, contact, company, or
  source.

Success can cause an early stop: if three well-supported targets with usable
  evidence and draftable outreach are complete, the agent should stop rather
  than keep searching for a theoretically better fourth target. Likewise, a
  profile run should stop once the requested fields are reasonably covered and
  remaining fields are documented as unknown.

The timeout applies to one invocation of `sales_agent.py`, not to the overall
human/agent development session. The process does not continue in the
background after a timeout.

## What counts as failure

A failure is not merely an incomplete profile. The harness distinguishes:

- **Input failure:** invalid URL, missing profile/list, or unreadable input.
- **Tool failure:** browser timeout, blocked page, search failure, or model
  call failure. The agent may continue past one bad page, but it must record
  the issue and treat the affected facts as unknown.
- **Budget failure:** the run reaches its wall-clock or tool budget before a
  valid result is returned. No incomplete result replaces a prior non-empty
  output.
- **Validation failure:** the model returns data that cannot satisfy the
  required structured output contract.
- **Factuality failure:** a result depends on an unsupported claim, invented
  contact, fabricated source, or unmarked inference. The correct response is
  to omit/reject it, not to make the output look complete.

Failures are recorded in the audit log with status and stop reason. A failed
run must not silently be presented as a successful qualification.

## Guardrails

These are the explicit no-nose rules for this assignment:

- Never send email, submit a contact form, make a purchase, or take another
  external business action.
- Use public business information only; do not infer or expose private contact
  information.
- Never invent company facts, customer relationships, ratings, metrics,
  emails, people, dates, quotes, or source URLs.
- Mark assessments and unknowns clearly; do not turn marketing language into
  verified operating facts.
- Treat search snippets and review-site comments as leads/anecdotal signals,
  not representative truth.
- Reject poor-fit prospects rather than forcing the requested count.
- Keep the seller profile, target profiles, candidate leads, and email drafts
  distinguishable.
- Stay within `hw/hw_02/.venv` and use the configured Portkey endpoint/model.
- Keep research same-hostname for company crawling, respect timeouts/rate
  limits, and never run indefinitely.
- Keep `.env`, API keys, `.venv/`, and other secrets out of submission files.

## Where the guardrails are enforced

They are intentionally layered rather than placed in one fragile location:

- **Prompt layer:** factuality, tone, public-source rules, rejection criteria,
  no sending, and output requirements live in `prompts/sales_agent.md`.
- **Code layer:** URL validation, same-host crawling, page/search/crawl/run
  budgets, CLI input validation, no send tool, and output routing live in
  `sales_agent.py`.
- **Schema/output layer:** Pydantic models require structured profiles,
  targets, candidate lists, and draft emails; the script preserves prior
  non-empty target outputs when a later discovery run returns nothing.
- **Audit layer:** timestamps, queries, tool names/arguments, result summaries,
  URLs, statuses, and stop/failure reasons are appended to
  `output/audit_log.json`.
- **Packaging layer:** `.gitignore`, `.env.example`, and the final zip checklist
  keep secrets and the virtual environment out of the submission.

The audit records observable decision summaries and tool activity, not hidden
chain-of-thought. That gives reproducibility without pretending private model
reasoning is a reliable or appropriate audit artifact.

## Memory

Durable memory is the prompt, seller brief, profile/list inputs, generated
outputs, and audit log. Full chat history is not required at runtime; relevant
context is passed explicitly through files and the terminal arguments.
