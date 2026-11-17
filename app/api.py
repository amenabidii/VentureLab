"""Web API connecting the founder workspace to the real Milestone 2 and 3 backends.

Nothing here re-implements research, gates or approvals:
- runs are executed by `orchestrator.run_discover` in the background (jobs.py);
- findings, challenges, decisions and counterfactuals are read from that run's
  recorded outputs and only reshaped for display (app/presentation.py);
- Builder preparation goes through builder_adapter -> builder_service.prepare ->
  ApprovalStore.create; decisions and execution go through ApprovalStore only.

Trust model (local prototype, single founder):
- Approving or executing requires the founder capability: the 64-character key that
  the approval store keeps in `<state>/approvals.sqlite3.founder` on the founder's
  machine. The API never returns it; a request without it is refused and recorded.
  This is a local capability check, not multi-user authentication.
- There are no cookies or sessions, so there is no ambient authority for a forged
  cross-site request to use; every protected call carries the key explicitly.
"""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app import presentation as view
from approval import ApprovalError, ApprovalStore
from audit import append_entries, read_entries
from brief import FounderBrief
from builder_adapter import BuilderBlocked, adapt, run_outputs
from builder_models import ApprovalDecision
from builder_service import prepare
from config import Settings, get_settings
from jobs import JobManager, QueueFull, RunStore
from llm import LLMError, OllamaClient
from sources import SourceFetcher

router = APIRouter(prefix="/api")
MAX_ARTIFACT_BYTES = 500_000
FILE_TITLES = {
    "phase2_step1_validation-kit.md": ("Validation experiment kit and interview guide", "Experiment kit", "text"),
    "phase2_step1_validation-kit.json": ("Validation experiment kit (structured)", "Experiment kit data", "text"),
    "phase3_step1_landing-spec.json": ("Landing-page specification", "Landing-page data", "text"),
    "phase3_step1_landing-page.html": ("Local landing-page prototype", "Landing page", "html"),
}


@dataclass
class Services:
    settings: Settings
    runs: RunStore
    jobs: JobManager
    approvals: ApprovalStore
    runs_root: Path
    builder_root: Path
    log_path: Path
    client_factory: Any
    builder_lock: threading.Lock


def build_services(settings: Settings | None = None, *, client_factory=None, fetcher_factory=None,
                   root: Path | None = None) -> Services:
    settings = settings or get_settings()
    root = Path(root or Path.cwd()).absolute()
    # normpath removes ".." without resolving symlinks, so the approval store's own
    # symlink/junction refusal still applies to the real locations.
    state = Path(os.path.normpath(root / settings.state_dir))
    outputs = Path(os.path.normpath(root / settings.output_dir))
    log_path = Path(os.path.normpath(root / settings.decision_log))
    client_factory = client_factory or (lambda: OllamaClient(settings))
    fetcher_factory = fetcher_factory or SourceFetcher
    runs = RunStore(state / "runs.sqlite3")
    jobs = JobManager(runs, settings.model, outputs / "runs", log_path, client_factory, fetcher_factory,
                      max_queued=settings.max_queued_runs, model_wait_s=settings.model_wait_s)
    approvals = ApprovalStore(state / "approvals.sqlite3", outputs / "builder", ttl_seconds=settings.approval_ttl_s)
    return Services(settings, runs, jobs, approvals, outputs / "runs", outputs / "builder", log_path,
                    client_factory, threading.Lock())


_default: Services | None = None
_default_lock = threading.Lock()


def services(request: Request) -> Services:
    global _default
    found = getattr(request.app.state, "services", None)
    if found is not None:
        return found
    with _default_lock:
        if _default is None:
            _default = build_services()
        request.app.state.services = _default
        return _default


# --- founder brief ---------------------------------------------------------------------------

class BriefIn(BaseModel):
    """The workspace form, mapped onto Milestone 2's authoritative FounderBrief."""
    model_config = ConfigDict(extra="forbid")
    idea: str
    market: str
    customer: str
    problem: str
    skills: str
    hours: float
    budget: float
    currency: Literal["EUR", "USD", "EGP"]
    values: str
    constraints: str
    sources: list[str] = Field(default_factory=list, max_length=10)
    effort: Literal["full", "quick"] = "full"


FIELD_MAP = {"idea": "idea", "problem_statement": "problem", "target_customer": "customer", "market": "market",
             "founder_skills": "skills", "hours_per_week": "hours", "budget_eur": "budget",
             "budget_currency": "currency", "values_and_constraints": "constraints", "source_urls": "sources"}


def _items(text: str, label: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[\n;]+", text) if p.strip()]
    return [f"{label}: {p}" for p in parts]


def to_founder_brief(b: BriefIn) -> FounderBrief:
    return FounderBrief.model_validate({
        "idea": b.idea, "problem_statement": b.problem, "target_customer": b.customer, "market": b.market,
        "founder_skills": [s.strip() for s in re.split(r"[,\n]+", b.skills) if s.strip()],
        "hours_per_week": b.hours, "budget_eur": b.budget, "budget_currency": b.currency,
        "values_and_constraints": _items(b.values, "Value") + _items(b.constraints, "Constraint"),
        "source_urls": b.sources,
    })


def _field_errors(exc: ValidationError) -> dict[str, str]:
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = err.get("loc") or ("idea",)
        key = FIELD_MAP.get(str(loc[0]), str(loc[0]))
        fields.setdefault(key if key in BriefIn.model_fields else "idea", err.get("msg", "Invalid value")[:300])
    return fields


@router.post("/runs", status_code=202)
def create_run(payload: dict[str, Any], svc: Services = Depends(services)):
    try:
        b = BriefIn.model_validate(payload)
        brief = to_founder_brief(b)
    except ValidationError as exc:
        return JSONResponse({"error": "invalid_brief", "fields": _field_errors(exc)}, status_code=422)
    try:
        run, created = svc.jobs.submit(brief, b.effort)
    except QueueFull as exc:
        raise HTTPException(429, str(exc)) from exc
    return {"run": view.run_summary(run), "created": created}


def _run(svc: Services, run_id: str) -> dict[str, Any]:
    run = svc.runs.get(run_id) if re.fullmatch(r"run-[0-9a-f]{16}", run_id) else None
    if run is None:
        raise HTTPException(404, "Unknown run")
    return run


def _outputs(svc: Services, run_id: str) -> dict[str, Any]:
    return run_outputs(svc.runs_root / run_id)


@router.get("/runs")
def list_runs(svc: Services = Depends(services)):
    return [view.run_summary(r) for r in svc.runs.list()]


@router.get("/runs/{run_id}")
def get_run(run_id: str, svc: Services = Depends(services)):
    run = _run(svc, run_id)
    return view.run_summary(run) | {"progress": run["progress"], "effort": run["effort"]}


def _builder_blocked(svc: Services, run: dict[str, Any], outputs: dict[str, Any]) -> str | None:
    if run["status"] != "completed":
        return None
    try:
        adapt(run["id"], outputs)
        return None
    except BuilderBlocked as exc:
        return str(exc)


@router.get("/runs/{run_id}/agents")
def run_agents(run_id: str, svc: Services = Depends(services)):
    run = _run(svc, run_id)
    outputs = _outputs(svc, run_id)
    return view.agents(run, outputs, _approvals(svc, run_id), _builder_blocked(svc, run, outputs))


@router.get("/runs/{run_id}/findings")
def run_findings(run_id: str, svc: Services = Depends(services)):
    _run(svc, run_id)
    return view.findings(_outputs(svc, run_id))


@router.get("/runs/{run_id}/challenges")
def run_challenges(run_id: str, svc: Services = Depends(services)):
    _run(svc, run_id)
    return view.challenges(_outputs(svc, run_id))


@router.get("/runs/{run_id}/decision")
def run_decision(run_id: str, svc: Services = Depends(services)):
    run = _run(svc, run_id)
    outputs = _outputs(svc, run_id)
    blocked = _builder_blocked(svc, run, outputs)
    note = blocked or ("You may ask the Builder to prepare a validation kit for review. Nothing is written "
                       "until you approve the exact request, and nothing is ever published or sent.")
    return view.decision(outputs, note, builder_allowed=blocked is None and run["status"] == "completed")


@router.get("/runs/{run_id}/counterfactual")
def run_counterfactual(run_id: str, svc: Services = Depends(services)):
    _run(svc, run_id)
    return view.counterfactual(_outputs(svc, run_id))


@router.get("/runs/{run_id}/audit")
def run_audit(run_id: str, svc: Services = Depends(services)):
    _run(svc, run_id)
    rows = [e for e in read_entries(svc.log_path) if e.get("run_id") == run_id]
    return sorted(rows, key=lambda e: e["timestamp"])


# --- Builder and founder approval ----------------------------------------------------------------

def _expired(svc: Services, action_id: str) -> tuple[datetime | None, bool]:
    expires = svc.approvals.expires_at(action_id)
    return expires, expires is None or datetime.now(timezone.utc) > expires


def _approvals(svc: Services, run_id: str) -> list[dict[str, Any]]:
    out = []
    for request in svc.approvals.list_requests(run_id):
        expires, expired = _expired(svc, request.action_id)
        out.append(view.approval(request, expires, expired))
    return out


def mirror_builder_events(svc: Services, run_id: str | None) -> None:
    """Copy approval-store events into decision_log.json (the store remains authoritative)."""
    events = [e for e in svc.approvals.audit_events() if run_id is None or e.get("run_id") == run_id]
    present = {(e.get("timestamp"), e.get("action"), e.get("action_id"), e.get("outcome"))
               for e in read_entries(svc.log_path) if e.get("agent") in ("builder", "approval")}
    new = [e | {"recorded_in": "approval_store"} for e in events
           if (e.get("timestamp"), e.get("action"), e.get("action_id"), e.get("outcome")) not in present]
    if new:
        append_entries(svc.log_path, new)


@router.get("/runs/{run_id}/approvals")
def run_approvals(run_id: str, svc: Services = Depends(services)):
    _run(svc, run_id)
    return _approvals(svc, run_id)


@router.post("/runs/{run_id}/builder", status_code=201)
def prepare_builder(run_id: str, svc: Services = Depends(services)):
    run = _run(svc, run_id)
    if run["status"] != "completed":
        raise HTTPException(409, "The run has not completed; there is no gate decision to build on")
    with svc.builder_lock:
        for existing in _approvals(svc, run_id):
            if existing["status"] in ("Pending", "Approved"):
                return {"approval": existing, "created": False, "notes": ["A request is already open for this run."]}
        try:
            adapted = adapt(run_id, _outputs(svc, run_id))
        except BuilderBlocked as exc:
            raise HTTPException(409, str(exc)) from exc
        client = svc.client_factory()
        try:
            try:
                bundle = prepare(adapted.builder_input, adapted.landing_page, client)
            except LLMError:
                # The model only chooses which supplied assumption to test; without it the
                # deterministic template is used and provenance says so.
                bundle = prepare(adapted.builder_input, adapted.landing_page, None)
                adapted.notes.append("The model was unavailable; the experiment kit used the deterministic template.")
        except ValueError as exc:
            raise HTTPException(409, f"The Builder refused this input: {exc}") from exc
        finally:
            client.close()
        request = svc.approvals.create(bundle)
    mirror_builder_events(svc, run_id)
    expires, expired = _expired(svc, request.action_id)
    return {"approval": view.approval(request, expires, expired), "created": True, "notes": adapted.notes}


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    fingerprint: str
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=3, max_length=500)
    founder_key: str = Field(max_length=200)


class ExecuteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    founder_key: str = Field(max_length=200)


def _request_for(svc: Services, action_id: str, run_id: str):
    if not re.fullmatch(r"[0-9a-f]{32}", action_id):
        raise HTTPException(404, "Unknown approval request")
    try:
        request, bundle = svc.approvals.inspect(action_id)
    except ApprovalError as exc:
        raise HTTPException(404, "Unknown approval request") from exc
    if request.run_id != run_id:
        svc.approvals.record_failure("approval_decision", ApprovalError("run mismatch"), action_id)
        mirror_builder_events(svc, None)
        raise HTTPException(409, "This approval request belongs to a different run")
    return request, bundle


def _refuse_if_run_superseded(svc: Services, run_id: str, action_id: str, action: str) -> None:
    """Re-check the run's gate decision under the current rules before approving or executing.

    Nothing about this is stored: it is computed from the recorded run every time, so a
    restart cannot restore a permission the current rules deny.
    """
    try:
        adapt(run_id, _outputs(svc, run_id))
    except BuilderBlocked as exc:
        svc.approvals.record_failure(action, ApprovalError("gate decision superseded or blocked"), action_id)
        mirror_builder_events(svc, run_id)
        raise HTTPException(409, f"{exc}. This request cannot be approved or executed; it can still be "
                                 "rejected.") from exc


@router.post("/approvals/{action_id}/decision")
def decide(action_id: str, body: DecisionIn, svc: Services = Depends(services)):
    request, _ = _request_for(svc, action_id, body.run_id)
    if body.decision == "approve":
        _refuse_if_run_superseded(svc, request.run_id, action_id, "approval_decision")
    try:
        decision = ApprovalDecision(action_id=action_id, artifact_sha256=body.fingerprint, decision=body.decision,
                                    actor="founder", reason=body.reason)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid decision (fingerprint or reason)") from exc
    try:
        result = svc.approvals.decide(decision, founder_token=body.founder_key.strip().encode("ascii", "replace"))
    except ApprovalError as exc:
        mirror_builder_events(svc, request.run_id)
        raise HTTPException(403 if "capability" in str(exc) else 409, str(exc)) from exc
    mirror_builder_events(svc, request.run_id)
    expires, expired = _expired(svc, action_id)
    return view.approval(result, expires, expired)


@router.post("/approvals/{action_id}/execute")
def execute(action_id: str, body: ExecuteIn, svc: Services = Depends(services)):
    request, _ = _request_for(svc, action_id, body.run_id)
    if not svc.approvals.verify_founder(body.founder_key.strip().encode("ascii", "replace")):
        svc.approvals.record_failure("execute_artifacts", ApprovalError("founder capability required"), action_id)
        mirror_builder_events(svc, request.run_id)
        raise HTTPException(403, "Founder capability required; execution was not attempted")
    _refuse_if_run_superseded(svc, request.run_id, action_id, "execute_artifacts")
    try:
        result = svc.approvals.execute(action_id)
    except ApprovalError as exc:
        mirror_builder_events(svc, request.run_id)
        raise HTTPException(409, str(exc)) from exc
    mirror_builder_events(svc, request.run_id)
    return {"action_id": result.action_id, "run_id": result.run_id, "fingerprint": result.artifact_sha256,
            "files": list(result.files), "status": result.status}


@router.get("/runs/{run_id}/artifacts")
def run_artifacts(run_id: str, svc: Services = Depends(services)):
    _run(svc, run_id)
    out = []
    root = svc.builder_root.resolve()
    for request in svc.approvals.list_requests(run_id):
        _, bundle = svc.approvals.inspect(request.action_id)
        expires, expired = _expired(svc, request.action_id)
        status = view.approval(request, expires, expired)["status"]
        proposed = bundle.files()
        written: dict[str, bytes] = {}
        if status == "Executed":
            directory = Path(request.destination)
            if directory.resolve().is_relative_to(root):
                for name in proposed:
                    path = (directory / name).resolve()
                    if path.parent == directory.resolve() and path.is_file() and path.stat().st_size <= MAX_ARTIFACT_BYTES:
                        written[name] = path.read_bytes()
        intact = status == "Executed" and written == proposed
        label = {"Executed": "Generated — written after your approval" if intact
                 else "Executed, but the files on disk differ from the approved snapshot",
                 "Pending": "Proposed — not written; awaiting your decision",
                 "Approved": "Approved — not written yet; execute to write it locally",
                 "Rejected": "Rejected — not written", "Expired": "Expired — not written",
                 "Failed": "Failed — not a successful artifact", "Executing": "Executing"}[status]
        kind = "kit and landing page" if bundle.landing_page is not None else "kit only (gate was not GO)"
        source = written if intact else proposed
        out.append({"id": request.action_id, "title": "Validation artifact bundle", "type": f"Builder bundle · {kind}",
                    "status": label, "description": request.description,
                    "format": "text", "content": source["phase2_step1_validation-kit.md"].decode()[:MAX_ARTIFACT_BYTES],
                    "fingerprint": request.artifact_sha256, "approval": status,
                    "generator": bundle.generator, "model": bundle.model})
        for name, data in source.items():
            title, kind_label, fmt = FILE_TITLES[name]
            out.append({"id": f"{request.action_id}:{name}", "title": title, "type": kind_label, "status": label,
                        "description": f"{name} · {'written to the local outputs folder' if intact else 'not written'}",
                        "format": fmt, "content": data.decode()[:MAX_ARTIFACT_BYTES],
                        "fingerprint": request.artifact_sha256, "approval": status})
    return out
