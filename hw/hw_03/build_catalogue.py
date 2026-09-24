"""One-time build of output/catalogue.json from data/products/*.jpg.

Not part of the four-file agent (prompts/prompt.md, agent.py, tools.py,
models.py) — this is a preprocessing script run once (rerun only if the
product photo set changes) to turn the raw product photos into the
structured catalogue the later identify agent matches against.

Speed strategy (see output/harness.md for the full rationale):
  1. Concurrent requests (thread pool) instead of one-image-at-a-time.
  2. Per-image preprocessing that autocrops the uniform white/black margin
     around the garment (when one exists) before downscaling, so shrinking
     the image loses background, not the branding detail.

Manual-review fallback: a small number of photos get rejected by the vision
backend's own content-safety filter (seen in practice on heraldic crest
photos — a false positive on real merch, not a code or key problem; see
output/harness.md). No automated retry can fix a moderation decision, so
instead of silently dropping those photos, this script flags them and, when
run in a real interactive terminal, asks Christopher to look at the photo
himself and enter the same fields a human would read off the image.
"""

from __future__ import annotations

import argparse
import base64
import io
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageChops

from models import BrandingStyle, CatalogueEntry, MerchType, ProductCatalogue

PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR.parent.parent
PRODUCTS_DIR = PROJECT_DIR / "data" / "products"
OUTPUT_PATH = PROJECT_DIR / "output" / "catalogue.json"

DEFAULT_MAX_WORKERS = 8
MAX_IMAGE_SIDE = 640
JPEG_QUALITY = 75
BACKGROUND_TOLERANCE = 12
CROP_PADDING = 12

SYSTEM_PROMPT = """\
You catalogue Campus Customs Yale merchandise photos for a product database.
Look only at the garment shown and answer with the requested structured
fields. Be specific about which Yale entity the branding names (the
university generically, a specific residential college, a school like Yale
School of Music or Yale Law School, a varsity sport, or a family/affinity
line like "Yale Dad"), and be precise about whether that identity appears as
text (wordmark), an icon/mascot (logo), a shield (crest), a combination, or
no identifiable branding at all. The filename field in your response must
exactly match the filename given to you.
"""


def _corner_background(im: Image.Image) -> tuple[int, int, int] | None:
    """Return the background color if all four corners agree it's near-white
    or near-black, otherwise None (garment fills the frame; do not crop)."""
    corners = [
        im.getpixel((0, 0)),
        im.getpixel((im.width - 1, 0)),
        im.getpixel((0, im.height - 1)),
        im.getpixel((im.width - 1, im.height - 1)),
    ]
    channels = list(zip(*corners))
    if any(max(c) - min(c) > BACKGROUND_TOLERANCE for c in channels):
        return None
    avg = tuple(sum(c) // len(c) for c in channels)
    if all(v >= 235 for v in avg) or all(v <= 20 for v in avg):
        return avg
    return None


def _autocrop(im: Image.Image) -> Image.Image:
    bg_color = _corner_background(im)
    if bg_color is None:
        return im
    bg = Image.new("RGB", im.size, bg_color)
    bbox = ImageChops.difference(im, bg).getbbox()
    if bbox is None:
        return im
    left, upper, right, lower = bbox
    left = max(0, left - CROP_PADDING)
    upper = max(0, upper - CROP_PADDING)
    right = min(im.width, right + CROP_PADDING)
    lower = min(im.height, lower + CROP_PADDING)
    return im.crop((left, upper, right, lower))


def _resize_max_side(im: Image.Image, max_side: int = MAX_IMAGE_SIDE) -> Image.Image:
    if max(im.size) <= max_side:
        return im
    ratio = max_side / max(im.size)
    new_size = (round(im.width * ratio), round(im.height * ratio))
    return im.resize(new_size, Image.LANCZOS)


def preprocess_image(path: Path) -> tuple[str, dict]:
    im = Image.open(path).convert("RGB")
    original_size = im.size
    cropped = _autocrop(im)
    resized = _resize_max_side(cropped)
    buf = io.BytesIO()
    resized.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    stats = {
        "original_size": original_size,
        "final_size": resized.size,
        "cropped": cropped.size != original_size,
    }
    return encoded, stats


def catalogue_one(client: OpenAI, model: str, path: Path) -> tuple[CatalogueEntry, dict]:
    encoded, stats = preprocess_image(path)
    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Filename: {path.name}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                    },
                ],
            },
        ],
        response_format=CatalogueEntry,
    )
    entry = completion.choices[0].message.parsed
    if entry.filename != path.name:
        entry = entry.model_copy(update={"filename": path.name})
    return entry, stats


def _prompt_choice(label: str, options: list) -> object:
    while True:
        for i, opt in enumerate(options, 1):
            print(f"    {i}. {opt.value}")
        raw = input(f"  {label} [1-{len(options)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Not a valid choice, try again.")


def prompt_manual_entry(path: Path, reason: str) -> CatalogueEntry | None:
    """Ask a human to look at one photo and fill in the catalogue fields by
    hand. Used only for photos the automated vision call could not process
    (most often a content-safety false positive on crest artwork)."""

    print(f"\n--- Needs manual review: {path.name} ---")
    print(f"  Automated identification failed: {reason[:160]}")
    print(f"  Open it yourself: {path}")
    response = input("  Enter catalogue fields for this photo now? [y/N]: ").strip().lower()
    if response not in ("y", "yes"):
        return None
    merch_type = _prompt_choice("Merch type", list(MerchType))
    description = input("  Description (1-2 sentences): ").strip()
    school_or_program = input("  School/program (e.g. 'Yale Baseball'): ").strip()
    branding_style = _prompt_choice("Branding style", list(BrandingStyle))
    colors_raw = input("  Primary colors, comma-separated (optional): ").strip()
    primary_colors = [c.strip() for c in colors_raw.split(",") if c.strip()]
    return CatalogueEntry(
        filename=path.name,
        source="manual",
        merch_type=merch_type,
        description=description,
        school_or_program=school_or_program,
        branding_style=branding_style,
        primary_colors=primary_colors,
    )


def run_manual_review(products_dir: Path, failures: list[dict]) -> tuple[list[CatalogueEntry], list[dict]]:
    """Offer manual entry for each failed photo. Returns (manual_entries,
    still_failed) so callers can tell what got resolved vs. what stayed
    skipped."""

    if not failures:
        return [], []
    if not sys.stdin.isatty():
        print(
            f"\n{len(failures)} photo(s) need manual review, but this isn't an "
            "interactive terminal (no one to prompt). Run `python build_catalogue.py` "
            "yourself in a real terminal to be asked for these by hand, or use "
            "--no-manual-review to silence this note."
        )
        return [], failures
    print(f"\n{len(failures)} photo(s) could not be catalogued automatically.")
    manual_entries: list[CatalogueEntry] = []
    still_failed: list[dict] = []
    for failure in failures:
        entry = prompt_manual_entry(products_dir / failure["filename"], failure["error"])
        if entry is not None:
            manual_entries.append(entry)
        else:
            still_failed.append(failure)
    return manual_entries, still_failed


def build_catalogue(
    client: OpenAI, model: str, paths: list[Path], max_workers: int
) -> tuple[list[CatalogueEntry], list[dict], int]:
    entries: list[CatalogueEntry] = []
    failures: list[dict] = []
    cropped_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(catalogue_one, client, model, p): p for p in paths}
        for future in as_completed(futures):
            path = futures[future]
            try:
                entry, stats = future.result()
            except Exception as exc:  # noqa: BLE001 - one bad image must not sink the batch
                failures.append({"filename": path.name, "error": str(exc)})
                continue
            entries.append(entry)
            if stats["cropped"]:
                cropped_count += 1
    entries.sort(key=lambda e: e.filename)
    return entries, failures, cropped_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument(
        "--limit", type=int, default=None, help="Only catalogue the first N products (testing)."
    )
    parser.add_argument(
        "--no-manual-review",
        action="store_true",
        help="Don't prompt for photos the vision call couldn't process; leave them skipped.",
    )
    args = parser.parse_args()

    load_dotenv(WORKSPACE_DIR / ".env")
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the workspace .env")
    base_url = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    client = OpenAI(api_key=api_key, base_url=base_url)

    paths = sorted(PRODUCTS_DIR.glob("*.jpg"))
    if args.limit:
        paths = paths[: args.limit]

    started = time.monotonic()
    entries, failures, cropped_count = build_catalogue(client, model, paths, args.workers)
    elapsed = time.monotonic() - started

    still_failed = failures
    if failures and not args.no_manual_review:
        manual_entries, still_failed = run_manual_review(PRODUCTS_DIR, failures)
        entries.extend(manual_entries)

    entries.sort(key=lambda e: e.filename)
    catalogue = ProductCatalogue(
        model=model,
        generated_at=datetime.now(timezone.utc).isoformat(),
        entries=entries,
        skipped=[f["filename"] for f in still_failed],
    )
    OUTPUT_PATH.write_text(catalogue.model_dump_json(indent=2) + "\n")

    print(
        f"\nCatalogued {len(entries)}/{len(paths)} products in {elapsed:.1f}s "
        f"with {args.workers} workers ({cropped_count} autocropped) -> {OUTPUT_PATH}"
    )
    if still_failed:
        print(f"{len(still_failed)} still skipped: {[f['filename'] for f in still_failed]}")


if __name__ == "__main__":
    main()
