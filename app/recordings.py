"""Read-only replay of explicitly indexed, genuine repository executions.

The index pins bytes, not truth: it detects edits but cannot independently prove
that a recorded source or model judgment is correct. No run database is restored,
no approval becomes active, and no operation can be executed through this router.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import APIRouter, HTTPException
from app import presentation as view
from gates import RULESET_VERSION

router = APIRouter(prefix="/api/recordings", tags=["read-only recorded executions"])
ROOT = Path(__file__).resolve().parents[1]
INDEX = Path(__file__).with_name("recorded_runs.json")



def _index() -> dict[str, Any]:
    try:
        runs = json.loads(INDEX.read_text(encoding="utf-8"))["runs"]
        if not isinstance(runs, dict):
            raise ValueError("Invalid recording index")
        return runs
    except (ValueError, KeyError, OSError, TypeError) as exc:
        raise HTTPException(409, "Recording index unavailable; no replacement data was generated.") from exc


def _bytes(relative: str, digest: str) -> bytes:
    parts = PurePosixPath(relative).parts
    if not parts or parts[0] != "outputs" or any(p in ("..", ".") for p in parts) or "\\" in relative:
        raise ValueError("Invalid recording path")
    path = ROOT.joinpath(*parts)
    if path.resolve() != path.absolute() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Linked recording path refused")
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError("Missing or oversized recording")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Recorded file changed; its indexed checksum no longer matches")
    return data


def _record(run_id: str) -> dict[str, Any]:
    index = _index()
    if not re.fullmatch(r"record-[0-9a-f]{16}", run_id) or run_id not in index:
        raise HTTPException(404, "Unknown recorded execution")
    entry = index[run_id]
    try:
        files = {name: _bytes(name, digest) for name, digest in entry["files"].items()}
        outputs = {key: json.loads(files[name]) for key, name in entry["outputs"].items()}
        execution_id=entry["execution_id"]
        gate, brief = outputs["gate"], outputs["brief"]
        if gate["run_id"] != execution_id or brief["run_id"] != execution_id:
            raise ValueError("Recording identity mismatch")
        events = entry["audit"]
        version = gate.get("ruleset_version", 1)
        superseded = version != RULESET_VERSION
        note = (f"Historical gate rules v{version}; current rules v{RULESET_VERSION}. This decision is superseded. "
                if superseded else "Recorded decision under the current rule version. ")
        note += "Read-only prior execution. No research is running and no historical approval authorizes a new action."
        summary = {"id": run_id, "title": brief["brief"]["idea"], "status": "Recorded · superseded" if superseded else "Recorded",
                   "phase": f"Discover · {gate['decision']}", "recordedAt": entry["recorded_at"],
                   "readOnly": True, "rulesetVersion": version, "currentRulesetVersion": RULESET_VERSION,
                   "provenance": note, "executionId": execution_id}
        agents = []
        for role, name in [("investigator", "Investigator"), ("challenger", "Challenger"), ("gate", "Judge")]:
            occurred = any(e["agent"] == role for e in events)
            agents.append({"agent": name, "status": "Completed" if occurred else "Not started",
                           "task": "Historical action recorded; inspect Decision history." if occurred else "No action recorded in this execution."})
        agents.append({"agent": "Builder", "status": "Blocked", "task": "Read-only archive. Historical files do not restore approval authority."})
        artifacts = []
        for name, data in files.items():
            if not name.startswith(f"outputs/builder/{execution_id}/") or not name.endswith((".md", ".html")):
                continue
            artifacts.append({"id": name.removeprefix("outputs/"), "title": PurePosixPath(name).name,
                              "type": "Recorded local artifact", "status": "Historical file · read-only",
                              "description": "Committed output from a prior execution. Not newly generated or approved.",
                              "format": "html" if name.endswith(".html") else "text", "content": data.decode("utf-8"),
                              "fingerprint": entry["files"][name], "approval": "Historical record only; no active permission"})
        return {"run": summary, "brief": view.founder_brief(brief["brief"]), "agents": agents,
                "findings": view.findings(outputs),
                "challenges": view.challenges(outputs), "decision": view.decision(outputs, note, builder_allowed=False),
                "counterfactual": view.counterfactual(outputs), "audit": events,
                "artifacts": artifacts, "approvals": [], "files": entry["files"],
                "integrity": "SHA-256 matches indexed files; this is not an independent audit of the claims."}
    except (ValueError, KeyError, OSError, TypeError) as exc:
        raise HTTPException(409, "Recording unavailable: integrity or format validation failed. No replacement data was generated.") from exc


@router.get("")
def recordings():
    rows = []
    for run_id in _index():
        try:
            rows.append(_record(run_id)["run"])
        except HTTPException:
            rows.append({"id": run_id, "title": "Recording unavailable — integrity check failed", "status": "Unavailable",
                         "phase": "Historical execution", "recordedAt": None, "readOnly": True})
    return sorted(rows, key=lambda row: row["recordedAt"] or "", reverse=True)


@router.get("/{run_id}")
def recording(run_id: str):
    return _record(run_id)
