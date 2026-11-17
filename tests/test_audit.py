"""The audit log schema (decision_log.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from audit import REQUIRED_KEYS, AuditLog, check_entry

ROOT = Path(__file__).resolve().parent.parent


def test_record_appends_entries_with_all_required_keys(tmp_path):
    log = AuditLog(tmp_path / "decision_log.json", "run-1")
    log.record("investigator", "retrieve_source", sources=["https://example.test/a", "https://example.test/a"])
    log.record("gate", "evidence_gate", outcome="repeat", rule="REPEAT_INSUFFICIENT_EVIDENCE")
    data = json.loads((tmp_path / "decision_log.json").read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 2
    for entry in data:
        assert set(REQUIRED_KEYS) <= set(entry)
        check_entry(entry)
    assert data[0]["sources"] == ["https://example.test/a"]  # de-duplicated
    assert data[1]["model"] is None and data[1]["cost"] == 0 and data[1]["approved_by"] is None
    assert data[1]["timestamp"].endswith("Z")


@pytest.mark.parametrize(
    "bad",
    [
        {"action": ""},
        {"sources": "https://example.test"},
        {"sources": [1]},
        {"model": 3},
        {"cost": -1},
        {"cost": True},
        {"approved_by": "agent"},
    ],
)
def test_bad_entries_are_refused(tmp_path, bad):
    good = {"timestamp": "2026-01-01T00:00:00Z", "agent": "a", "action": "x", "sources": [], "model": None,
            "cost": 0, "approved_by": None}
    with pytest.raises(ValueError):
        check_entry(good | bad)
    missing = dict(good)
    del missing["approved_by"]
    with pytest.raises(ValueError, match="missing"):
        check_entry(missing)


def test_committed_decision_log_follows_the_schema():
    path = ROOT / "decision_log.json"
    if not path.exists():
        pytest.skip("no decision_log.json yet")
    entries = json.loads(path.read_text(encoding="utf-8"))
    assert entries
    for entry in entries:
        check_entry(entry)
