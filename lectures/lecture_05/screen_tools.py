"""Screen capture helpers for the immersive browser agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO

import mss
from PIL import Image


@dataclass(frozen=True)
class Screenshot:
    """A PNG screenshot plus the metadata shown by the Dash UI."""

    png: bytes
    captured_at: str
    region: str
    width: int
    height: int


def capture_screen(region: str = "window") -> Screenshot:
    """Capture the primary display with mss and encode it as a PNG with Pillow.

    The native Qt window can span two displays and is not exposed consistently
    by cross-platform window APIs. The primary display therefore provides the
    dependable capture surface; ``window`` remains the agent-facing label.
    """

    with mss.mss() as grabber:
        # mss exposes index 1 as the primary display when a desktop is
        # available; headless sessions may expose only the virtual all-screen
        # monitor at index 0.
        monitor = grabber.monitors[1] if len(grabber.monitors) > 1 else grabber.monitors[0]
        raw = grabber.grab(monitor)
        image = Image.frombytes("RGB", raw.size, raw.rgb)

    # Keep multimodal turns responsive while retaining enough detail to read
    # normal browser text. Older full-resolution screenshots can otherwise
    # make each subsequent conversation turn unnecessarily large.
    image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return Screenshot(
        png=output.getvalue(),
        captured_at=datetime.now(timezone.utc).isoformat(),
        region=region,
        width=image.width,
        height=image.height,
    )
