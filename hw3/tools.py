"""Tool functions for the Campus Customs agent (product-identify and
ad-effectiveness abilities).

These are plain functions, not decorated here — agent.py imports them and
wires each one onto its own Agent instance with `agent.tool(...)`. Keeping
the logic here and the registration in agent.py is what "wiring a tool"
means in PydanticAI: a function only becomes something the model can invoke
once it's registered on a specific agent, with a JSON schema generated from
its signature.

Deliberately self-contained rather than importing build_catalogue.py's image
helpers: the agent (this file, agent.py, models.py, prompts/prompt.md) is
meant to run on its own, independent of the one-time catalogue-building
script.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import cv2
from PIL import Image, ImageChops
from pydantic_ai import BinaryContent, ModelRetry, RunContext, ToolReturn

from models import CustomerProfile, ProductCatalogue

MAX_CANDIDATE_IMAGES = 10
MAX_IMAGE_SIDE = 640
JPEG_QUALITY = 75
BACKGROUND_TOLERANCE = 12
CROP_PADDING = 12
AD_FRAME_SAMPLE_COUNT = 8


@dataclass
class AgentDeps:
    """Shared state for one agent run. Product-identify mode uses `catalogue`
    /`products_dir`/`candidates_loaded`; ad-effectiveness mode uses `profile`
    /`video_path`. Each mode's Agent only registers its own tools, so the
    other mode's fields simply go unused rather than needing a second
    dataclass."""

    catalogue: ProductCatalogue | None = None
    products_dir: Path | None = None
    candidates_loaded: list[str] = field(default_factory=list)
    profile: CustomerProfile | None = None
    video_path: Path | None = None


def _corner_background(im: Image.Image) -> tuple[int, int, int] | None:
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


def load_image_bytes(path: Path) -> bytes:
    """Crop/downscale one photo (same trick as build_catalogue.py) and return
    encoded JPEG bytes ready for BinaryContent. Safe no-op crop when a photo
    doesn't have a plain background to trim (e.g. a real lifestyle photo)."""
    im = Image.open(path).convert("RGB")
    cropped = _autocrop(im)
    if max(cropped.size) > MAX_IMAGE_SIDE:
        ratio = MAX_IMAGE_SIDE / max(cropped.size)
        cropped = cropped.resize(
            (round(cropped.width * ratio), round(cropped.height * ratio)), Image.LANCZOS
        )
    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def get_catalogue_summary(ctx: RunContext[AgentDeps]) -> str:
    """List every Campus Customs product as plain text: filename, merch type,
    school/program, and branding style. No product photos are loaded by this
    call. Use it first to judge which catalogue entries are even worth
    looking at before loading any images."""
    lines = [
        f"{e.filename} | {e.merch_type.value} | {e.school_or_program} | {e.branding_style.value}"
        for e in ctx.deps.catalogue.entries
    ]
    return "\n".join(lines)


def load_product_images(ctx: RunContext[AgentDeps], filenames: list[str]) -> ToolReturn:
    """Load up to 10 specific catalogue product photos, by filename, so you
    can visually compare them against the query photo. Call this only after
    narrowing down with get_catalogue_summary; never pass more than 10
    filenames in one call."""
    if len(filenames) > MAX_CANDIDATE_IMAGES:
        raise ModelRetry(
            f"At most {MAX_CANDIDATE_IMAGES} filenames per call; you gave {len(filenames)}. "
            "Narrow your shortlist to your best guesses and try again."
        )
    known = {e.filename for e in ctx.deps.catalogue.entries}
    content: list[str | BinaryContent] = []
    loaded: list[str] = []
    unknown: list[str] = []
    for name in filenames:
        if name not in known:
            unknown.append(name)
            continue
        image_bytes = load_image_bytes(ctx.deps.products_dir / name)
        content.append(f"Product photo: {name}")
        content.append(BinaryContent(data=image_bytes, media_type="image/jpeg"))
        loaded.append(name)
    ctx.deps.candidates_loaded.extend(loaded)
    summary = f"Loaded {len(loaded)} product photo(s): {', '.join(loaded) or 'none'}"
    if unknown:
        summary += f". Ignored unknown filename(s) not in the catalogue: {', '.join(unknown)}"
    return ToolReturn(return_value=summary, content=content)


def get_customer_profile_summary(ctx: RunContext[AgentDeps]) -> str:
    """Return the customer profile being judged against: role, program,
    age range, the appeal categories they respond to, where they'd actually
    wear the merch, style preferences, and budget sensitivity. Plain text, no
    video frames loaded by this call."""
    profile = ctx.deps.profile
    interests = ", ".join(i.value for i in profile.interests)
    occasions = ", ".join(profile.wear_occasions) or "none given"
    return (
        f"name: {profile.name}\n"
        f"role: {profile.role}\n"
        f"relationship_to_yale: {profile.relationship_to_yale}\n"
        f"program: {profile.program}\n"
        f"age_range: {profile.age_range}\n"
        f"interests (appeal categories this customer responds to): {interests}\n"
        f"wear_occasions (where/when they'd actually wear the merch): {occasions}\n"
        f"style_preferences: {profile.style_preferences}\n"
        f"budget_sensitivity: {profile.budget_sensitivity}\n"
        f"notes: {profile.notes}"
    )


def _sample_video_frames(path: Path, count: int = AD_FRAME_SAMPLE_COUNT) -> list[bytes]:
    """Pull `count` evenly-spaced frames from the video and return them as
    encoded JPEG bytes. No system ffmpeg required -- opencv reads the file
    directly."""
    cap = cv2.VideoCapture(str(path))
    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            raise RuntimeError(f"Could not read any frames from {path}")
        frames = []
        for i in range(count):
            frame_idx = int(frame_count * (i + 0.5) / count)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            if not ok:
                continue
            # OpenCV reads BGR; PIL/JPEG expect RGB.
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(rgb)
            if max(im.size) > MAX_IMAGE_SIDE:
                ratio = MAX_IMAGE_SIDE / max(im.size)
                im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            frames.append(buf.getvalue())
        return frames
    finally:
        cap.release()


def watch_ad_video(ctx: RunContext[AgentDeps]) -> ToolReturn:
    """Load a handful of evenly-spaced frames from the ad video so you can see
    what it actually shows -- setting, people, clothing, tone, energy. Call
    this once before judging ad_themes; there's only one video per run, so
    there's no filename to pick."""
    frames = _sample_video_frames(ctx.deps.video_path)
    content: list[str | BinaryContent] = [
        f"{len(frames)} sampled frames from {ctx.deps.video_path.name}, in chronological order:"
    ]
    for i, frame_bytes in enumerate(frames, 1):
        content.append(f"Frame {i}/{len(frames)}:")
        content.append(BinaryContent(data=frame_bytes, media_type="image/jpeg"))
    return ToolReturn(
        return_value=f"Loaded {len(frames)} frames from {ctx.deps.video_path.name}.",
        content=content,
    )
