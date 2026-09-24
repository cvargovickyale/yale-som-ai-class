"""Campus Customs agent entry point.

Two abilities, one agent:

    python agent.py --image "data/test_images/example.jpg"
    python agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_student.json"

The first decides whether a Campus Customs product is visible in a photo,
and which one if possible (output/identify_product.json). The second judges
how effective an ad video would be at convincing one customer profile to
shop with Campus Customs (output/ad_effectiveness.json). Both output files
accumulate one result per thing ever checked (a JSON list); rerunning on the
same input replaces just that entry.

Every run of either ability -- success or failure -- also appends one
AuditEntry to output/audit_trail.json (never overwritten, never skipped).
See output/harness.md for the full design and the safety rules this agent
follows around real photos/video of people.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import (
    AdEffectivenessResult,
    AuditEntry,
    AuditStep,
    CustomerProfile,
    IdentifyResult,
    ProductCatalogue,
)
from tools import (
    AgentDeps,
    get_catalogue_summary,
    get_customer_profile_summary,
    load_image_bytes,
    load_product_images,
    watch_ad_video,
)

PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR.parent.parent
PRODUCTS_DIR = PROJECT_DIR / "data" / "products"
CATALOGUE_PATH = PROJECT_DIR / "output" / "catalogue.json"
PROMPT_PATH = PROJECT_DIR / "prompts" / "prompt.md"
IDENTIFY_OUTPUT_PATH = PROJECT_DIR / "output" / "identify_product.json"
AD_OUTPUT_PATH = PROJECT_DIR / "output" / "ad_effectiveness.json"
AUDIT_PATH = PROJECT_DIR / "output" / "audit_trail.json"
RESULT_SUMMARY_MAX_CHARS = 200

ModelT = TypeVar("ModelT", bound=BaseModel)


def _build_model() -> OpenAIChatModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the workspace .env")
    base_url = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
    model_name = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIChatModel(model_name, provider=provider)


def build_identify_agent() -> Agent[AgentDeps, IdentifyResult]:
    agent = Agent(
        _build_model(),
        deps_type=AgentDeps,
        output_type=IdentifyResult,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        retries=2,
    )
    # Wiring: tools.py holds the plain functions; registering them here with
    # agent.tool(...) is what turns them into things this specific agent
    # instance can call. Nothing in tools.py can run on its own.
    agent.tool(get_catalogue_summary)
    agent.tool(load_product_images)
    return agent


def build_ad_agent() -> Agent[AgentDeps, AdEffectivenessResult]:
    agent = Agent(
        _build_model(),
        deps_type=AgentDeps,
        output_type=AdEffectivenessResult,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        retries=2,
    )
    agent.tool(get_customer_profile_summary)
    agent.tool(watch_ad_video)
    return agent


def identify(image_path: Path) -> tuple[IdentifyResult, object]:
    load_dotenv(WORKSPACE_DIR / ".env")
    if not CATALOGUE_PATH.exists():
        raise RuntimeError(f"{CATALOGUE_PATH} not found; run build_catalogue.py first.")
    catalogue = ProductCatalogue.model_validate_json(CATALOGUE_PATH.read_text())
    deps = AgentDeps(catalogue=catalogue, products_dir=PRODUCTS_DIR)

    agent = build_identify_agent()
    query_bytes = load_image_bytes(image_path)
    user_prompt = [
        f"Query photo: {image_path.name}",
        BinaryContent(data=query_bytes, media_type="image/jpeg"),
    ]
    result = agent.run_sync(user_prompt, deps=deps)

    # Trust our own bookkeeping over the model's self-report for what was
    # actually loaded, same reasoning as overriding `filename` in
    # build_catalogue.py: code knows this for certain, the model is guessing.
    output = result.output.model_copy(
        update={
            "query_image": str(image_path),
            "candidates_considered": list(deps.candidates_loaded),
        }
    )
    return output, result


def judge_ad_effectiveness(video_path: Path, profile_path: Path) -> tuple[AdEffectivenessResult, object]:
    load_dotenv(WORKSPACE_DIR / ".env")
    profile = CustomerProfile.model_validate_json(profile_path.read_text())
    deps = AgentDeps(profile=profile, video_path=video_path)

    agent = build_ad_agent()
    user_prompt = (
        f"Judge how effective the ad video at {video_path} would be at convincing "
        f"the customer '{profile.name}' to shop with Campus Customs."
    )
    result = agent.run_sync(user_prompt, deps=deps)

    output = result.output.model_copy(
        update={"video_path": str(video_path), "customer_name": profile.name}
    )
    return output, result


def _extract_audit_steps(result) -> list[AuditStep]:
    """Walk the agent's actual message history into one AuditStep per turn.
    `thought` only ever holds text the model visibly produced in that turn
    (often none, for a pure tool-calling turn) -- never a guess at hidden
    reasoning."""
    steps: list[AuditStep] = []
    pending: dict[str, AuditStep] = {}
    for message in result.all_messages():
        if isinstance(message, ModelResponse):
            thought = " ".join(
                p.content.strip() for p in message.parts if isinstance(p, TextPart) and p.content.strip()
            )
            tool_calls = [p for p in message.parts if isinstance(p, ToolCallPart)]
            timestamp = message.timestamp.isoformat()
            if not tool_calls:
                if thought:
                    steps.append(AuditStep(timestamp=timestamp, thought=thought))
                continue
            for call in tool_calls:
                args = call.args
                if isinstance(args, str):
                    try:
                        args = json.loads(args) if args else {}
                    except json.JSONDecodeError:
                        args = {"raw": args}
                step = AuditStep(
                    timestamp=timestamp, thought=thought, tool_name=call.tool_name, tool_args=args
                )
                pending[call.tool_call_id] = step
                steps.append(step)
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart) and part.tool_call_id in pending:
                    text = part.content if isinstance(part.content, str) else str(part.content)
                    if len(text) > RESULT_SUMMARY_MAX_CHARS:
                        text = text[:RESULT_SUMMARY_MAX_CHARS] + "..."
                    pending[part.tool_call_id].result_summary = text
    return steps


def _append_audit_entry(entry: AuditEntry) -> None:
    """output/audit_trail.json is append-only: every run adds one entry,
    nothing already there is ever rewritten or dropped, including for a
    failed/aborted run."""
    existing: list[dict] = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
    existing.append(entry.model_dump(mode="json"))
    AUDIT_PATH.write_text(json.dumps(existing, indent=2) + "\n")


def _load_json_list(path: Path, model: type[ModelT]) -> list[ModelT]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, dict):  # migrate an older single-result file
        data = [data]
    return [model.model_validate(item) for item in data]


def _save_json_list(path: Path, results: list[ModelT], sort_key) -> None:
    results = sorted(results, key=sort_key)
    payload = [r.model_dump(mode="json") for r in results]
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _handle_content_safety_error(
    exc: ModelHTTPError, what: str, mode: str, inputs: dict[str, str]
) -> None:
    if exc.status_code == 400 and "content safety" in str(exc.body).lower():
        _append_audit_entry(
            AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode=mode,
                inputs=inputs,
                steps=[],  # the run_sync call raised before any message history existed
                stop_reason=f"Aborted: vision model content-safety rejection on {what}.",
            )
        )
        print(
            f"Could not check {what}: the vision model's own content-safety "
            "filter rejected this input (a false positive, not a bug here — "
            "see output/harness.md). Nothing was written; this is not a "
            "'nothing found' result, it's 'could not be checked.'",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    raise exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Path to a photo to check for a Campus Customs product.")
    parser.add_argument("--video", help="Path to an ad video to judge.")
    parser.add_argument("--profile", help="Path to a customer profile JSON (required with --video).")
    args = parser.parse_args()

    if args.image and (args.video or args.profile):
        parser.error("--image cannot be combined with --video/--profile.")
    if bool(args.video) != bool(args.profile):
        parser.error("--video and --profile must be given together.")
    if not args.image and not args.video:
        parser.error("Provide either --image, or --video together with --profile.")

    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        try:
            output, result = identify(image_path)
        except ModelHTTPError as exc:
            _handle_content_safety_error(
                exc, str(image_path), mode="identify", inputs={"image": str(image_path)}
            )
            return

        if output.product_present and output.match:
            outcome_summary = f"product_present=True, match={output.match.filename} ({output.match.confidence})"
        elif output.product_present:
            outcome_summary = "product_present=True, no confident match"
        else:
            outcome_summary = "product_present=False"
        _append_audit_entry(
            AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode="identify",
                inputs={"image": str(image_path)},
                steps=_extract_audit_steps(result),
                stop_reason="Completed normally: produced a final IdentifyResult.",
                outcome_summary=outcome_summary,
            )
        )

        results = _load_json_list(IDENTIFY_OUTPUT_PATH, IdentifyResult)
        results = [r for r in results if r.query_image != str(image_path)]
        results.append(output)
        _save_json_list(IDENTIFY_OUTPUT_PATH, results, sort_key=lambda r: r.query_image)

        if output.product_present and output.match:
            print(f"Product present: {output.match.filename} ({output.match.confidence} confidence)")
        elif output.product_present:
            print("Product present, but not confidently matched to one catalogue item.")
        else:
            print("No Campus Customs product identified in this photo.")
        print(
            f"Considered {len(output.candidates_considered)} candidate photo(s) "
            f"-> {IDENTIFY_OUTPUT_PATH}"
        )
        return

    video_path = Path(args.video)
    profile_path = Path(args.profile)
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    if not profile_path.exists():
        raise FileNotFoundError(profile_path)

    try:
        output, result = judge_ad_effectiveness(video_path, profile_path)
    except ModelHTTPError as exc:
        _handle_content_safety_error(
            exc,
            f"{video_path} / {profile_path}",
            mode="ad_effectiveness",
            inputs={"video": str(video_path), "profile": str(profile_path)},
        )
        return

    _append_audit_entry(
        AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode="ad_effectiveness",
            inputs={"video": str(video_path), "profile": str(profile_path)},
            steps=_extract_audit_steps(result),
            stop_reason="Completed normally: produced a final AdEffectivenessResult.",
            outcome_summary=f"{output.customer_name}: effectiveness={output.effectiveness}",
        )
    )

    results = _load_json_list(AD_OUTPUT_PATH, AdEffectivenessResult)
    results = [
        r
        for r in results
        if not (r.video_path == str(video_path) and r.customer_name == output.customer_name)
    ]
    results.append(output)
    _save_json_list(AD_OUTPUT_PATH, results, sort_key=lambda r: (r.video_path, r.customer_name))

    print(f"Effectiveness for {output.customer_name}: {output.effectiveness}")
    print(f"Ad themes: {[c.value for c in output.ad_themes]}")
    print(f"Matched to customer interests: {[c.value for c in output.matched_categories]}")
    print(f"-> {AD_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
