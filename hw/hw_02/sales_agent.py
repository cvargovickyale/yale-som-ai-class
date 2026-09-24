"""Run the single Homework 2 research agent in profile or discovery mode."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urldefrag, urljoin, urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright


PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR.parent.parent
load_dotenv(WORKSPACE_DIR / ".env")

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PROMPT_PATH = PROJECT_DIR / "prompts" / "sales_agent.md"
OUTPUT_PATH = PROJECT_DIR / "assets" / "company_profile.json"
AUDIT_PATH = PROJECT_DIR / "output" / "audit_log.json"
DEFAULT_MAX_PAGES = 8
DEFAULT_PAGE_TIMEOUT_MS = 8_000
DEFAULT_RUN_TIMEOUT_SECONDS = 90
MAX_TARGETS_TO_EVALUATE = 20
MAX_SEARCH_RESULTS_PER_CALL = 10
MAX_DISCOVERY_SEARCH_CALLS = 4
MAX_DISCOVERY_CRAWL_CALLS = 8
MAX_DISCOVERY_PAGES_PER_CANDIDATE = 4


class ProfileMetadata(BaseModel):
    available_field_count: int = 0
    requested_field_count: int = 0
    coverage_percentage: float = 0.0
    insufficient_profile_coverage: bool = True
    coverage_notes: list[str] = Field(default_factory=list)


class CompanyProfile(BaseModel):
    """Permissive structured envelope; the prompt supplies field semantics."""

    model_config = ConfigDict(extra="allow")

    company_name: Any = None
    website_url: Any = None
    company_type: Any = None
    ownership_structure: Any = None
    year_founded: Any = None
    evidence_sources: list[Any] = Field(default_factory=list)
    headquarters_location: Any = None
    project_locations: list[Any] = Field(default_factory=list)
    distance_to_nearest_sanhaw_location: Any = None
    service_area_fit: Any = None
    delivery_or_pickup_feasibility: Any = None
    local_market: Any = None
    employee_count: Any = None
    revenue_or_size_band: Any = None
    annual_project_volume: Any = None
    residential_vs_commercial_mix: Any = None
    contractor_specialty: Any = None
    project_types: list[Any] = Field(default_factory=list)
    estimated_material_intensity: Any = None
    growth_or_hiring_signal: Any = None
    independent_or_network_affiliation: Any = None
    likely_products_needed: list[Any] = Field(default_factory=list)
    fit_with_sanhaw_products: Any = None
    fit_with_sanhaw_services: Any = None
    repeat_purchase_potential: Any = None
    commercial_account_potential: Any = None
    delivery_need: Any = None
    millwork_or_field_service_need: Any = None
    differentiation_or_pain_point: Any = None
    decision_maker_name: Any = None
    decision_maker_title: Any = None
    business_email: Any = None
    phone: Any = None
    contact_source_url: Any = None
    preferred_contact_channel: Any = None
    recent_trigger: Any = None
    personalization_evidence: Any = None
    contact_confidence: Any = None
    target_score: Any = None
    fit_reasons: list[Any] = Field(default_factory=list)
    risks_or_disqualifiers: list[Any] = Field(default_factory=list)
    unknowns: list[Any] = Field(default_factory=list)
    research_date: Any = None
    source_quality: Any = None
    recommended_next_step: Any = None
    email_status: Any = "not drafted"
    profile_metadata: ProfileMetadata = Field(default_factory=ProfileMetadata)


class TargetCompany(BaseModel):
    model_config = ConfigDict(extra="allow")

    company_name: Any = None
    website_url: Any = None
    company_type: Any = None
    ownership_structure: Any = None
    year_founded: Any = None
    evidence_sources: list[Any] = Field(default_factory=list)
    headquarters_location: Any = None
    project_locations: list[Any] = Field(default_factory=list)
    distance_to_nearest_sanhaw_location: Any = None
    service_area_fit: Any = None
    delivery_or_pickup_feasibility: Any = None
    local_market: Any = None
    employee_count: Any = None
    revenue_or_size_band: Any = None
    annual_project_volume: Any = None
    residential_vs_commercial_mix: Any = None
    contractor_specialty: Any = None
    project_types: list[Any] = Field(default_factory=list)
    estimated_material_intensity: Any = None
    growth_or_hiring_signal: Any = None
    independent_or_network_affiliation: Any = None
    likely_products_needed: list[Any] = Field(default_factory=list)
    fit_with_sanhaw_products: Any = None
    fit_with_sanhaw_services: Any = None
    repeat_purchase_potential: Any = None
    commercial_account_potential: Any = None
    delivery_need: Any = None
    millwork_or_field_service_need: Any = None
    differentiation_or_pain_point: Any = None
    decision_maker_name: Any = None
    decision_maker_title: Any = None
    business_email: Any = None
    phone: Any = None
    contact_source_url: Any = None
    preferred_contact_channel: Any = None
    recent_trigger: Any = None
    personalization_evidence: Any = None
    contact_confidence: Any = None
    target_score: Any = None
    fit_reasons: list[Any] = Field(default_factory=list)
    risks_or_disqualifiers: list[Any] = Field(default_factory=list)
    unknowns: list[Any] = Field(default_factory=list)
    research_date: Any = None
    source_quality: Any = None
    recommended_next_step: Any = None
    email_status: Any = "draft ready"


class DraftEmail(BaseModel):
    model_config = ConfigDict(extra="allow")

    target_company_name: str
    target_website_url: str
    recipient_name: Any = None
    recipient_title: Any = None
    recipient_email: Any = None
    subject: str
    body: str
    personalization_sources: list[Any] = Field(default_factory=list)
    factuality_notes: list[Any] = Field(default_factory=list)
    status: str = "draft — not sent"


class TargetResearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    targets: list[TargetCompany] = Field(default_factory=list)
    emails: list[DraftEmail] = Field(default_factory=list)
    search_summary: Any = None
    rejected_candidates: list[Any] = Field(default_factory=list)
    research_metadata: dict[str, Any] = Field(default_factory=dict)


class Candidate(BaseModel):
    company_name: str | None = None
    website_url: str
    company_type: str | None = None
    geography: str | None = None
    discovery_reason: str | None = None
    source_urls: list[str] = Field(default_factory=list)


class CandidateList(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)
    rejected_or_duplicate_notes: list[str] = Field(default_factory=list)
    search_summary: str | None = None


class AgentDeps:
    def __init__(
        self, max_pages: int, page_timeout_ms: int, deadline: float,
        discovery_mode: bool = False,
        discovery_only: bool = False,
    ) -> None:
        self.max_pages = max_pages
        self.page_timeout_ms = page_timeout_ms
        self.deadline = deadline
        self.discovery_mode = discovery_mode
        self.discovery_only = discovery_only
        self.search_calls = 0
        self.crawl_calls = 0
        self.tool_calls: list[dict[str, Any]] = []
        self.crawled_urls: list[str] = []

    def record_tool(self, name: str, arguments: dict[str, Any], summary: str) -> None:
        self.tool_calls.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "name": name,
            "arguments": arguments,
            "result_summary": summary,
        })


def _clean_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("The URL must begin with http:// or https://")
    return urldefrag(url)[0].rstrip("/")


async def crawl_site(
    url: str, *, max_pages: int, page_timeout_ms: int, deadline: float,
) -> tuple[str, list[str], list[str]]:
    """Collect readable same-domain pages without downloading arbitrary assets."""

    start_url = _clean_url(url)
    parsed_start = urlparse(start_url)
    allowed_host = parsed_start.netloc.lower().removeprefix("www.")
    queue = [start_url]
    seen: set[str] = set()
    pages: list[str] = []
    errors: list[str] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Homework2ResearchAgent/1.0 (respectful public-page research)",
        )
        page = await context.new_page()
        try:
            while queue and len(pages) < max_pages and time.monotonic() < deadline:
                current = queue.pop(0)
                if current in seen:
                    continue
                seen.add(current)
                try:
                    await page.goto(current, wait_until="domcontentloaded", timeout=page_timeout_ms)
                    title = await page.title()
                    body = await page.locator("body").inner_text(timeout=page_timeout_ms)
                    body = " ".join(body.split())
                    if body:
                        pages.append(f"URL: {current}\nTITLE: {title}\nTEXT: {body[:12000]}")
                    links = await page.locator("a[href]").evaluate_all(
                        "els => els.map(a => a.href)"
                    )
                    for href in links:
                        candidate = urldefrag(urljoin(current, href))[0].rstrip("/")
                        parsed = urlparse(candidate)
                        host = parsed.netloc.lower().removeprefix("www.")
                        if (parsed.scheme in {"http", "https"}
                                and host == allowed_host
                                and candidate not in seen
                                and candidate not in queue
                                and not parsed.path.lower().endswith(
                                    (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip")
                                )):
                            queue.append(candidate)
                except PlaywrightTimeoutError:
                    errors.append(f"Timed out: {current}")
                except Exception as exc:  # Continue so one bad page does not end the run.
                    errors.append(f"Could not read {current}: {type(exc).__name__}")
        finally:
            await context.close()
            await browser.close()
    return "\n\n--- PAGE ---\n\n".join(pages), list(seen), errors


async def search_site(query: str, *, max_results: int, page_timeout_ms: int) -> tuple[str, list[str]]:
    """Use a bounded Bing HTML search for public candidate discovery."""

    search_url = "https://www.bing.com/search?q=" + quote_plus(query)
    results: list[str] = []
    snippets: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Homework2ResearchAgent/1.0 (respectful public research)",
        )
        page = await context.new_page()
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=page_timeout_ms)
            cards = page.locator("li.b_algo")
            count = min(await cards.count(), max_results)
            for index in range(count):
                card = cards.nth(index)
                link = card.locator("h2 a")
                if await link.count() == 0:
                    continue
                href = await link.get_attribute("href")
                title = (await link.inner_text()).strip()
                snippet_locator = card.locator(".b_caption p")
                snippet = (await snippet_locator.inner_text()).strip() if await snippet_locator.count() else ""
                if href and href.startswith(("http://", "https://")):
                    results.append(href)
                    snippets.append(f"TITLE: {title}\nURL: {href}\nSNIPPET: {snippet}")
        finally:
            await context.close()
            await browser.close()
    return "\n\n--- SEARCH RESULT ---\n\n".join(snippets), results


def build_agent(output_type: Any) -> Agent[Any, Any]:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the workspace .env")
    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key)
    model = OpenAIResponsesModel(MODEL_NAME, provider=provider)
    return Agent(
        model,
        deps_type=AgentDeps,
        output_type=output_type,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        retries=1,
    )


def register_tools(agent: Agent[Any, Any]) -> None:
    """Register tools on the exact agent instance used for each run."""

    @agent.tool
    async def crawl_company_website(
        ctx: RunContext[AgentDeps], url: str,
    ) -> str:
        """Crawl a bounded set of readable same-domain public pages for the profile."""

        if time.monotonic() >= ctx.deps.deadline:
            raise TimeoutError("The bounded research window has expired.")
        if ctx.deps.discovery_only:
            ctx.deps.record_tool(
                "crawl_company_website",
                {"url": url, "max_pages": 0},
                "Discovery-only mode; no candidate crawl performed",
            )
            return "Discovery-only mode does not crawl candidate websites. Return candidate URLs only."
        if ctx.deps.discovery_mode and ctx.deps.crawl_calls >= MAX_DISCOVERY_CRAWL_CALLS:
            ctx.deps.record_tool(
                "crawl_company_website",
                {"url": url, "max_pages": 0},
                "Candidate crawl budget exhausted; no crawl performed",
            )
            return "Candidate crawl budget exhausted. Evaluate only candidates already researched."
        ctx.deps.crawl_calls += 1
        crawl_page_limit = min(
            ctx.deps.max_pages,
            MAX_DISCOVERY_PAGES_PER_CANDIDATE if ctx.deps.discovery_mode else ctx.deps.max_pages,
        )
        text, crawled_urls, errors = await crawl_site(
            url,
            max_pages=crawl_page_limit,
            page_timeout_ms=ctx.deps.page_timeout_ms,
            deadline=ctx.deps.deadline,
        )
        ctx.deps.crawled_urls.extend(crawled_urls)
        summary = f"Read {len(crawled_urls)} pages; collected {len(text)} characters"
        if errors:
            summary += f"; {len(errors)} page issues"
        ctx.deps.record_tool(
            "crawl_company_website",
            {"url": url, "max_pages": crawl_page_limit},
            summary,
        )
        return text or "No readable page text was collected. Treat all unsupported fields as unknown."

    @agent.tool
    async def search_for_prospective_companies(
        ctx: RunContext[AgentDeps], query: str, max_results: int = 10,
    ) -> str:
        """Search public web results for possible business targets; never contact them."""

        bounded_results = max(1, min(max_results, MAX_SEARCH_RESULTS_PER_CALL))
        if time.monotonic() >= ctx.deps.deadline:
            raise TimeoutError("The bounded research window has expired.")
        if ctx.deps.search_calls >= MAX_DISCOVERY_SEARCH_CALLS:
            ctx.deps.record_tool(
                "search_for_prospective_companies",
                {"query": query, "max_results": bounded_results},
                "Search budget exhausted; no search performed",
            )
            return "Search budget exhausted. Evaluate only candidates from earlier results."
        ctx.deps.search_calls += 1
        try:
            text, urls = await search_site(
                query, max_results=bounded_results, page_timeout_ms=ctx.deps.page_timeout_ms,
            )
            summary = f"Returned {len(urls)} public search results"
            ctx.deps.record_tool(
                "search_for_prospective_companies",
                {"query": query, "max_results": bounded_results},
                summary,
            )
            return text or "No usable search results. Do not invent candidates."
        except Exception as exc:
            ctx.deps.record_tool(
                "search_for_prospective_companies",
                {"query": query, "max_results": bounded_results},
                f"Search failed: {type(exc).__name__}",
            )
            return "Search was unavailable. Do not invent candidates; report the limitation."


def load_audit() -> dict[str, Any]:
    if not AUDIT_PATH.exists():
        return {"runs": [], "unique_input_urls": [], "unique_urls_seen": []}
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("audit log is not an object")
        data.setdefault("runs", [])
        data.setdefault("unique_input_urls", [])
        data.setdefault("unique_urls_seen", [])
        return data
    except (OSError, json.JSONDecodeError, ValueError):
        return {"runs": [], "unique_input_urls": [], "unique_urls_seen": []}


def append_audit(run: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = load_audit()
    input_url = run.get("input_url")
    if input_url and input_url not in data["unique_input_urls"]:
        data["unique_input_urls"].append(input_url)
    urls_seen = list(run.get("crawled_urls", []))
    for tool_call in run.get("tool_calls", []):
        tool_url = tool_call.get("arguments", {}).get("url")
        if tool_url:
            urls_seen.append(tool_url)
    for seen_url in urls_seen:
        if seen_url not in data["unique_urls_seen"]:
            data["unique_urls_seen"].append(seen_url)
    data["runs"].append(run)
    AUDIT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


async def run(
    query: str,
    url: str | None,
    *,
    profile_path: Path | None,
    candidates_path: Path | None,
    discovery_only: bool,
    max_pages: int,
    timeout_seconds: int,
) -> Any:
    started = datetime.now(timezone.utc)
    start_clock = time.monotonic()
    deps = AgentDeps(
        max_pages=max_pages,
        page_timeout_ms=DEFAULT_PAGE_TIMEOUT_MS,
        deadline=start_clock + timeout_seconds,
        discovery_mode=profile_path is not None,
        discovery_only=discovery_only,
    )
    run_record: dict[str, Any] = {
        "run_started_at": started.isoformat(),
        "query": query,
        "input_url": url,
        "input_profile": str(profile_path) if profile_path else None,
        "model": MODEL_NAME,
        "max_pages": max_pages,
        "timeout_seconds": timeout_seconds,
        "iterations": [],
    }
    try:
        if profile_path:
            profile_json = json.loads(profile_path.read_text(encoding="utf-8"))
            candidate_json = ""
            if candidates_path:
                candidate_json = (
                    "\n\nCandidate list to qualify (use these URLs rather than broad new discovery):\n"
                    + json.dumps(json.loads(candidates_path.read_text(encoding="utf-8")), indent=2)
                )
            user_input = (
                f"Human request: {query}\n\n"
                f"Seller profile JSON to use as the seller context:\n"
                f"{json.dumps(profile_json, indent=2)}{candidate_json}"
            )
            output_type = CandidateList if discovery_only else TargetResearchResult
        elif not discovery_only:
            if not url:
                raise ValueError("A company URL is required when --profile is not used.")
            user_input = f"Human request: {query}\n\nCompany URL to research: {url}"
            output_type = CompanyProfile
        agent = build_agent(output_type)
        register_tools(agent)
        run_record["iterations"].append({
            "iteration": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "agent_run_started",
            "decision_summary": "Agent received the human query and URL; it may crawl the site before producing the structured profile.",
        })
        result = await asyncio.wait_for(
            agent.run(
                user_input,
                deps=deps,
            ),
            timeout=timeout_seconds,
        )
        profile = result.output
        if isinstance(profile, CompanyProfile):
            profile.research_date = started.date().isoformat()
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_PATH.write_text(
                json.dumps(profile.model_dump(mode="json"), indent=2) + "\n",
                encoding="utf-8",
            )
        elif isinstance(profile, CandidateList):
            candidate_path = PROJECT_DIR / "output" / "candidate_list.json"
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_path.write_text(
                json.dumps(profile.model_dump(mode="json"), indent=2) + "\n",
                encoding="utf-8",
            )
            run_record["output_paths"] = [str(candidate_path.relative_to(PROJECT_DIR))]
        else:
            for target in profile.targets:
                target.research_date = started.date().isoformat()
                target.email_status = "draft ready" if any(
                    email.target_company_name == target.company_name
                    for email in profile.emails
                ) else "needs review"
            targets_path = PROJECT_DIR / "output" / "targets.json"
            emails_path = PROJECT_DIR / "output" / "emails.json"
            targets_path.parent.mkdir(parents=True, exist_ok=True)
            if profile.targets:
                targets_path.write_text(
                    json.dumps([target.model_dump(mode="json") for target in profile.targets], indent=2) + "\n",
                    encoding="utf-8",
                )
                emails_path.write_text(
                    json.dumps([email.model_dump(mode="json") for email in profile.emails], indent=2) + "\n",
                    encoding="utf-8",
                )
            else:
                run_record["preserved_previous_outputs"] = (
                    targets_path.exists() and emails_path.exists()
                )
            run_record["output_paths"] = [
                str(targets_path.relative_to(PROJECT_DIR)),
                str(emails_path.relative_to(PROJECT_DIR)),
            ]
        run_record["iterations"].append({
            "iteration": 2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "agent_run_completed",
            "decision_summary": "Structured profile returned and written to assets/company_profile.json.",
        })
        run_record["status"] = "completed"
        if isinstance(profile, CompanyProfile):
            run_record["output_path"] = str(OUTPUT_PATH.relative_to(PROJECT_DIR))
        run_record["crawled_urls"] = list(dict.fromkeys(deps.crawled_urls))
        run_record["tool_calls"] = deps.tool_calls
        return profile
    except asyncio.TimeoutError:
        run_record["status"] = "stopped_timeout"
        run_record["stop_reason"] = f"Run exceeded {timeout_seconds} seconds. No further model or crawl work was attempted."
        run_record["tool_calls"] = deps.tool_calls
        raise RuntimeError(run_record["stop_reason"])
    except Exception as exc:
        run_record["status"] = "failed"
        run_record["stop_reason"] = f"{type(exc).__name__}: {exc}"
        run_record["tool_calls"] = deps.tool_calls
        raise
    finally:
        run_record["run_finished_at"] = datetime.now(timezone.utc).isoformat()
        run_record["elapsed_seconds"] = round(time.monotonic() - start_clock, 3)
        append_audit(run_record)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a company profile with the Homework 2 sales agent.")
    parser.add_argument("query", help="The human instruction to the agent.")
    parser.add_argument("--url", help="The public company website URL to research.")
    parser.add_argument("--profile", type=Path, help="Seller profile JSON for target discovery.")
    parser.add_argument("--candidates", type=Path, help="Candidate list JSON to qualify.")
    parser.add_argument("--discover", action="store_true", help="Create a broad candidate list without crawling candidates.")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_RUN_TIMEOUT_SECONDS)
    args = parser.parse_args()
    if args.max_pages < 1 or args.max_pages > 20:
        parser.error("--max-pages must be between 1 and 20")
    if args.timeout_seconds < 10 or args.timeout_seconds > 90:
        parser.error("--timeout-seconds must be between 10 and 90")
    if args.discover and (args.url or not args.profile):
        parser.error("--discover requires --profile and cannot use --url")
    if not args.discover and bool(args.url) == bool(args.profile):
        parser.error("provide exactly one of --url or --profile")
    if args.candidates and (args.url or args.discover or not args.profile):
        parser.error("--candidates requires --profile and a qualification run")
    url = _clean_url(args.url) if args.url else None
    if args.profile:
        profile_candidate = args.profile
        if not profile_candidate.is_absolute() and not profile_candidate.exists():
            profile_candidate = PROJECT_DIR / profile_candidate
        profile_path = profile_candidate.resolve()
    else:
        profile_path = None
    if profile_path and not profile_path.exists():
        parser.error(f"profile file does not exist: {profile_path}")
    if args.candidates:
        candidates_candidate = args.candidates
        if not candidates_candidate.is_absolute() and not candidates_candidate.exists():
            candidates_candidate = PROJECT_DIR / candidates_candidate
        candidates_path = candidates_candidate.resolve()
    else:
        candidates_path = None
    if candidates_path and not candidates_path.exists():
        parser.error(f"candidate file does not exist: {candidates_path}")
    try:
        profile = asyncio.run(run(
            args.query,
            url,
            profile_path=profile_path,
            candidates_path=candidates_path,
            discovery_only=args.discover,
            max_pages=args.max_pages,
            timeout_seconds=args.timeout_seconds,
        ))
    except Exception as exc:
        raise SystemExit(f"Agent stopped: {exc}") from exc
    if isinstance(profile, CompanyProfile):
        metadata = profile.profile_metadata
        print(f"Wrote {OUTPUT_PATH}")
        print(
            f"Coverage: {metadata.available_field_count}/{metadata.requested_field_count} "
            f"({metadata.coverage_percentage:.1f}%); "
            f"insufficient={metadata.insufficient_profile_coverage}"
        )
    elif isinstance(profile, CandidateList):
        print(f"Wrote {PROJECT_DIR / 'output' / 'candidate_list.json'}")
        print(f"Candidates: {len(profile.candidates)}")
    else:
        print(f"Wrote {PROJECT_DIR / 'output' / 'targets.json'}")
        print(f"Wrote {PROJECT_DIR / 'output' / 'emails.json'}")
    print(f"Audit log: {AUDIT_PATH}")


if __name__ == "__main__":
    main()
