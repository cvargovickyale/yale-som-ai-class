"""Extract structured purchase data from receipt PDFs."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


RECEIPT_NAMES = (
    "receipt_",
)

SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "amount_usd": {"type": ["number", "null"]},
        "category": {"type": ["string", "null"]},
        "source_file": {"type": "string"},
        "fields_not_found": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "vendor", "date", "description", "amount_usd", "category",
        "source_file", "fields_not_found",
    ],
    "additionalProperties": False,
}


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_receipt(
    receipt_text: str, source_file: str, prompt_template: str,
    client: OpenAI, model: str,
) -> dict:
    prompt = prompt_template.format(
        source_file=source_file,
        receipt_text=receipt_text,
    )
    response = client.chat.completions.create(
        model=model,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "receipt", "strict": True, "schema": SCHEMA},
        },
        messages=[
            {"role": "system", "content": "You extract accurate structured data from business receipts."},
            {"role": "user", "content": prompt},
        ],
    )
    result = json.loads(response.choices[0].message.content)
    result["source_file"] = source_file
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract receipt PDFs into a JSON array.")
    parser.add_argument("--docs-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    load_dotenv(Path(__file__).parent / ".env")
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise SystemExit("PORTKEY_API_KEY is missing from .env")

    prompt_path = Path(__file__).parent / "prompts" / "receipts_extract.md"
    prompt_template = prompt_path.read_text()
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        default_headers={"x-portkey-api-key": api_key},
    )
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    receipt_paths = sorted(
        path for path in args.docs_dir.rglob("*.pdf")
        if path.name.lower().split("\\")[-1].startswith(RECEIPT_NAMES)
    )
    if not receipt_paths:
        raise SystemExit(f"No receipt PDFs found in {args.docs_dir}")

    rows = []
    for pdf_path in receipt_paths:
        print(f"Extracting {pdf_path.name}...")
        rows.append(extract_receipt(
            read_pdf(pdf_path), pdf_path.name, prompt_template, client, model,
        ))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.out_dir / "receipts.json"
    output_path.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Wrote {len(rows)} receipts to {output_path}")


if __name__ == "__main__":
    main()
