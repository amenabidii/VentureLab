"""Append-only audit log: one entry per agent action, written to decision_log.json.

Every entry has the five required keys (`action`, `sources`, `model`, `cost`,
`approved_by`) plus `timestamp`, `agent` and `run_id`. Extra keys such as
`outcome` or `rule` may be added. `approved_by` is "founder" only for actions
the founder explicitly approved; nothing in the Discover phase needs approval,
because nothing is published, sent, spent or signed.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_KEYS = ("timestamp", "agent", "action", "sources", "model", "cost", "approved_by")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_entry(entry: dict[str, Any]) -> None:
    """Raise ValueError if an entry does not follow the log schema."""
    missing = [k for k in REQUIRED_KEYS if k not in entry]
    if missing:
        raise ValueError(f"log entry missing keys: {missing}")
    if not isinstance(entry["action"], str) or not entry["action"]:
        raise ValueError("action must be a non-empty string")
    if not isinstance(entry["sources"], list) or not all(isinstance(s, str) for s in entry["sources"]):
        raise ValueError("sources must be a list of URL strings")
    if entry["model"] is not None and not isinstance(entry["model"], str):
        raise ValueError("model must be a string or null")
    if not isinstance(entry["cost"], (int, float)) or isinstance(entry["cost"], bool) or entry["cost"] < 0:
        raise ValueError("cost must be a non-negative number (USD)")
    if entry["approved_by"] not in (None, "founder"):
        raise ValueError('approved_by must be "founder" or null')


class AuditLog:
    def __init__(self, path: str | Path, run_id: str) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self._lock = threading.Lock()

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists() or not self.path.read_text(encoding="utf-8").strip():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{self.path} must hold a JSON list")
        return data

    def record(
        self,
        agent: str,
        action: str,
        *,
        sources: list[str] | None = None,
        model: str | None = None,
        cost: float = 0,
        approved_by: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": utc_now(),
            "agent": agent,
            "action": action,
            "sources": list(dict.fromkeys(sources or [])),
            "model": model,
            "cost": cost,
            "approved_by": approved_by,
            "run_id": self.run_id,
            **extra,
        }
        check_entry(entry)
        with self._lock:
            entries = self.entries()
            entries.append(entry)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return entry
