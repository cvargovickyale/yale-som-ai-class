import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


SCHEMA = {
    "type": "object",
    "properties": {
        "leases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "property_name": {"type": "string"},
                    "address": {"type": "string"},
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "tenant": {"type": "string"},
                    "latitude": {"type": ["number", "null"]},
                    "longitude": {"type": ["number", "null"]},
                    "lease_start": {"type": ["string", "null"]},
                    "lease_end": {"type": ["string", "null"]},
                    "annual_base_rent": {"type": ["number", "null"]},
                    "cash_flows": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "year": {"type": "integer"},
                                "amount": {"type": "number"},
                            },
                            "required": ["year", "amount"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "property_name", "address", "city", "state", "tenant",
                    "latitude", "longitude", "lease_start", "lease_end",
                    "annual_base_rent", "cash_flows",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["leases"],
    "additionalProperties": False,
}


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_with_model(pdf_text: str, filename: str, client: OpenAI, model: str) -> dict:
    prompt = f"""Extract the commercial lease in {filename} into the supplied JSON schema.
Use null for unknown scalar values and an empty list when no cash-flow schedule is present.
cash_flows must contain one entry per calendar year with the total scheduled base-rent amount.
Keep the address in the lease document. For New Haven-area properties, provide best-effort
latitude and longitude; otherwise use null. Do not invent rent or dates.

LEASE TEXT:
{pdf_text}
"""
    response = client.chat.completions.create(
        model=model,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "lease_data", "strict": True, "schema": SCHEMA},
        },
        messages=[
            {"role": "system", "content": "You extract accurate structured lease data."},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract lease PDFs into leases.json via Portkey.")
    parser.add_argument("--input", type=Path, default=Path(__file__).parents[1] / "data")
    parser.add_argument("--output", type=Path, default=Path(__file__).parents[1] / "leases.json")
    args = parser.parse_args()

    load_dotenv(Path(__file__).parents[3] / ".env")
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise SystemExit("PORTKEY_API_KEY is missing from .env")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
        default_headers={"x-portkey-api-key": api_key},
    )
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    leases = []
    for pdf_path in sorted(args.input.glob("*.pdf")):
        print(f"Extracting {pdf_path.name}...")
        extracted = extract_with_model(read_pdf(pdf_path), pdf_path.name, client, model)
        for lease in extracted["leases"]:
            lease["source_file"] = pdf_path.name
            leases.append(lease)

    args.output.write_text(json.dumps({"leases": leases}, indent=2) + "\n")
    print(f"Wrote {len(leases)} leases to {args.output}")


if __name__ == "__main__":
    main()
