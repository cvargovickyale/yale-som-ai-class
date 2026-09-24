"""Small optional JSONL audit log for local agent development."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_event(event: dict[str, Any], path: Path | None = None) -> None:
    """Append one non-secret event to ``output/audit_log.json``."""

    target = path or Path(__file__).parent / "output" / "audit_log.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []
    existing.append(event)
    target.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
