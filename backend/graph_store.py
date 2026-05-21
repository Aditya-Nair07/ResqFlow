"""Persist graph analysis snapshots for audit replay."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACE_DIR = ROOT / "data" / "traces"


def save_trace_analysis(trace_id: str, payload: dict) -> str:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in trace_id)
    path = TRACE_DIR / f"{safe_id}.json"
    record = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return str(path.relative_to(ROOT))


def list_saved_traces(limit: int = 20) -> list[dict[str, str]]:
    if not TRACE_DIR.exists():
        return []
    files = sorted(TRACE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = []
    for path in files[:limit]:
        if path.name == ".gitkeep":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                {
                    "trace_id": data.get("trace_id", path.stem),
                    "saved_at": data.get("saved_at", ""),
                    "incident_id": str(data.get("incident_id", "")),
                    "resource_id": str(data.get("resource_id", "")),
                    "file": path.name,
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return items


def load_saved_trace(trace_id: str) -> dict | None:
    safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in trace_id)
    path = TRACE_DIR / f"{safe_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
