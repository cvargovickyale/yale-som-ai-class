"""Extract structured charges from the January credit-card statement."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


TRANSACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": ["string", "null"]},
                    "merchant": {"type": ["string", "null"]},
                    "amount_usd": {"type": ["number", "null"]},
                    "classification": {"type": ["string", "null"]},
                    "expense_category": {"type": ["string", "null"]},
                    "source_file": {"type": "string"},
                    "fields_not_found": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "date", "merchant", "amount_usd", "classification",
                    "expense_category", "source_file", "fields_not_found",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["transactions"],
    "additionalProperties": False,
}


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_charges(
    statement_text: str, source_file: str, prompt_template: str,
    client: OpenAI, model: str,
) -> list[dict]:
    prompt = prompt_template.format(
        source_file=source_file,
        statement_text=statement_text,
    )
    response = client.chat.completions.create(
        model=model,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "credit_card_transactions",
                "strict": True,
                "schema": TRANSACTION_SCHEMA,
            },
        },
        messages=[
            {"role": "system", "content": "You extract accurate charge data from credit-card statements."},
            {"role": "user", "content": prompt},
        ],
    )
    rows = json.loads(response.choices[0].message.content)["transactions"]
    for row in rows:
        row["source_file"] = source_file
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract credit-card charges into a JSON array.")
    parser.add_argument("--docs-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    load_dotenv(Path(__file__).parent / ".env")
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise SystemExit("PORTKEY_API_KEY is missing from .env")

    prompt_path = Path(__file__).parent / "prompts" / "card_extract.md"
    prompt_template = prompt_path.read_text()
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        default_headers={"x-portkey-api-key": api_key},
    )
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    statement_paths = sorted(
        path for path in args.docs_dir.rglob("*.pdf")
        if "credit_card" in path.name.lower().split("\\")[-1]
    )
    if not statement_paths:
        raise SystemExit(f"No credit-card statement PDF found in {args.docs_dir}")
    if len(statement_paths) > 1:
        raise SystemExit(f"Expected one credit-card statement PDF, found {len(statement_paths)}")

    statement_path = statement_paths[0]
    print(f"Extracting {statement_path.name}...")
    rows = extract_charges(
        read_pdf(statement_path), statement_path.name, prompt_template, client, model,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.out_dir / "credit_card_transactions.json"
    output_path.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Wrote {len(rows)} charges to {output_path}")


if __name__ == "__main__":
    main()
