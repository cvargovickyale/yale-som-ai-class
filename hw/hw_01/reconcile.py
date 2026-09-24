"""Reconcile receipt, bank, credit-card, and supporting-document evidence."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


RECONCILIATION_SCHEMA = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "amounts_seen": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                    },
                    "included_in_income_statement": {"type": "string"},
                    "amount_used_in_income_statement": {"type": "number"},
                    "resolution": {"type": "string"},
                },
                "required": [
                    "id", "sources", "amounts_seen",
                    "included_in_income_statement",
                    "amount_used_in_income_statement", "resolution",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["rows"],
    "additionalProperties": False,
}


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_json(path: Path) -> object:
    if not path.exists():
        raise SystemExit(f"Required input is missing: {path}")
    return json.loads(path.read_text())


def supporting_documents(docs_dir: Path) -> str:
    parts = []
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        filename = path.name
        logical_name = filename.split("\\")[-1]
        if logical_name.startswith("email_") and path.suffix.lower() == ".txt":
            parts.append(f"--- {filename} ---\n{path.read_text()}")
        elif logical_name.startswith(("iou_", "quote_", "ebay_")) and path.suffix.lower() == ".pdf":
            parts.append(f"--- {filename} ---\n{read_pdf(path)}")
    return "\n\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a reconciliation decision log.")
    parser.add_argument("--docs-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    load_dotenv(Path(__file__).parents[2] / ".env")
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise SystemExit("PORTKEY_API_KEY is missing from .env")

    input_dir = args.out_dir
    prompt_template = (Path(__file__).parent / "prompts" / "reconcile.md").read_text()
    prompt = prompt_template.format(
        receipts_json=json.dumps(load_json(input_dir / "receipts.json"), indent=2),
        bank_json=json.dumps(load_json(input_dir / "bank_transactions.json"), indent=2),
        card_json=json.dumps(load_json(input_dir / "credit_card_transactions.json"), indent=2),
        supporting_text=supporting_documents(args.docs_dir),
    )
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        default_headers={"x-portkey-api-key": api_key},
    )
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    response = client.chat.completions.create(
        model=model,
        # The required amounts_seen mapping has dynamic document-filename keys,
        # which the endpoint's strict schema mode does not permit.
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You reconcile business records accurately and avoid double counting."},
            {"role": "user", "content": prompt},
        ],
    )
    rows = json.loads(response.choices[0].message.content)["rows"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.out_dir / "reconciliation_log.json"
    output_path.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Wrote {len(rows)} reconciliation rows to {output_path}")


if __name__ == "__main__":
    main()
