"""Run phases 2–6 for a workspace run from the browser, with the same gates as `workflow.py`.

- Steps call `workflow.plan`, `workflow.prepare_launch` and `workflow.launch` unchanged, so
  STOP blocks, REPEAT/PIVOT need a rehearsal approval, and every file is fingerprinted.
- Founder approvals require the same founder key as the Builder's approvals
  (`.venturelab/approvals.sqlite3.founder`), are bound to the fingerprint shown on the page,
  and are only accepted for requests that are actually pending (a changed file is refused).
- POSTs are accepted only from this origin. Outputs of web runs go to
  `outputs/phases/<run>/`, so they never overwrite the committed demo rehearsal.
Nothing is published, sent or paid: those steps are MOCKED.
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from starlette.concurrency import run_in_threadpool

import workflow
from app.api import Services, services, mirror_builder_events
from app.phases import HEADERS, NAME

router = APIRouter()
RUN_ID = re.compile(r"^run-[0-9a-f]{16}$")
FORM_HEADERS = {**HEADERS, "Referrer-Policy": "same-origin", "Content-Security-Policy": HEADERS["Content-Security-Policy"].replace(
    "form-action 'none'", "form-action 'self'")}
STEPS = (("plan", "1. Plan: scorecard, Lean Canvas, advisor proposals, MVP scope, pricing, policies"),
         ("prepare-launch", "2. Prepare launch: store page, posts, product file, acceptance checks"),
         ("launch", "3. Launch: MOCKED sale to cash, support, metrics, persevere-or-pivot memo"))


def _same_origin(request: Request) -> None:
    host = request.headers.get("host", "")
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if not origin or origin.split("://", 1)[-1].split("/", 1)[0] != host:
        raise HTTPException(403, "Founder actions are accepted only from this VentureLab page")


def _ctx(svc: Services, run_id: str) -> workflow.Context:
    if not RUN_ID.match(run_id):
        raise HTTPException(404, "Unknown run")
    run_dir = svc.runs_root / run_id
    if not (run_dir / "phase1_gate_decision.json").is_file():
        raise HTTPException(404, "This run has no Discover gate decision yet")
    out = svc.runs_root.parent / "phases" / run_id
    # The state folder is wherever the app keeps its approval store (same founder key, same root).
    return workflow.Context(run_dir, out, svc.log_path, Path(svc.approvals.database).parent, store=svc.approvals)


def pending(ctx: workflow.Context) -> list[dict[str, Any]]:
    """What still needs the founder, computed from files and signed approvals."""
    items, appr = [], ctx.approvals
    if ctx.rehearsal and ctx.decision != "STOP":
        action = ctx.rehearsal_action
        if not appr.approved(action, ctx.gate_sha):
            why = (f"although Discover decided {ctx.decision}" if ctx.decision != "GO"
                   else "although the Phase 2 validation gate has not passed")
            items.append({"action": action, "sha": ctx.gate_sha, "choices": None, "file": None,
                          "what": f"Run phases 2–6 as a labelled REHEARSAL {why}"})
    pricing = ctx.out / "phase4_step1_pricing.json"
    if pricing.exists():
        sha = workflow.sha256(pricing.read_bytes())
        if not appr.chosen("set_price:", sha):
            opts = json.loads(pricing.read_text(encoding="utf-8"))["options"]
            items.append({"action": "set_price", "sha": sha, "file": "phase4_step1_pricing.md",
                          "what": "Choose the test price (ASSUMPTION; nothing is charged)",
                          "choices": [(o["id"], f"{o['id']} (€{o['price_eur_per_month']}/month)") for o in opts]})
    for action, name, what in (
            ("publish_store_page", "phase5_step1_store-page.html", "MOCKED local publish of this exact store page"),
            ("enable_mock_delivery", "phase5_step2_mock-product.md",
             "MOCKED automatic delivery of this exact product file to simulated test orders")):
        path = ctx.out / name
        if path.exists():
            sha = workflow.sha256(path.read_bytes())
            if not appr.approved(action, sha):
                items.append({"action": action, "sha": sha, "what": what, "choices": None, "file": name})
    return items


def _page(ctx: workflow.Context, message: str = "") -> HTMLResponse:
    rid = escape(ctx.run_id)
    files = sorted(p.name for p in ctx.out.iterdir() if NAME.match(p.name)) if ctx.out.exists() else []
    file_list = "".join(f"<li><a href='/phases/run/{rid}/view/{escape(n)}'>{escape(n)}</a></li>" for n in files) \
        or "<li>Nothing generated yet.</li>"
    forms = []
    for item in pending(ctx):
        choice = ""
        if item["choices"]:
            choice = "<label>Option <select name='option'>" + "".join(
                f"<option value='{escape(v)}'>{escape(t)}</option>" for v, t in item["choices"]) + "</select></label>"
        view = f" · <a href='/phases/run/{rid}/view/{escape(item['file'])}'>review the file</a>" if item["file"] else ""
        forms.append(
            f"<form method='post' action='/phases/run/{rid}/approve' class='card'>"
            f"<p><b>{escape(item['what'])}</b>{view}<br><small>Action <code>{escape(item['action'])}</code> · "
            f"fingerprint <code>{escape(item['sha'])}</code></small></p>"
            f"<input type='hidden' name='action' value='{escape(item['action'])}'>"
            f"<input type='hidden' name='sha256' value='{escape(item['sha'])}'>{choice}"
            f"<label>Founder key <input type='password' name='founder_key' required autocomplete='off'></label>"
            f"<label>Reason <input name='reason' maxlength='300' placeholder='optional'></label>"
            f"<button name='decision' value='approve'>Approve</button> "
            f"<button name='decision' value='reject'>Reject</button></form>")
    blocked = ("Discover decided STOP: phases 2–6 are blocked." if ctx.decision == "STOP" else
               "This decision was made by superseded gate rules: re-run Discover to continue." if ctx.superseded else "")
    steps = "".join(f"<form method='post' action='/phases/run/{rid}/step/{s}'><label>Founder key <input type='password' name='founder_key' required autocomplete='off'></label><button {'disabled' if blocked else ''}>"
                    f"{escape(label)}</button></form>" for s, label in STEPS)
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Phases 2–6 · {rid}</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 16px;color:#17251f;background:#fff}}
.card{{border:1px solid #d4ddd4;border-radius:10px;padding:10px 16px;margin:12px 0}}
.msg{{background:#fff4e5;padding:10px 14px;border-radius:8px}}button{{font:inherit;padding:6px 12px;margin:4px 0}}
input,select{{font:inherit;margin:2px 6px}}</style></head><body>
<p><a href="/phases">← Phases 1–6</a> · <a href="/">Workspace</a></p>
<h1>Phases 2–6 for <code>{rid}</code></h1>
<p>Discover gate: <b>{escape(str(ctx.decision))}</b> ({escape(str(ctx.gate.get('rule')))}). {escape(blocked)}
Each step stops at a gate until the founder approves. Publishing and the sale to cash are MOCKED: nothing is
published, sent or paid. Approvals need the founder key in <code>.venturelab/approvals.sqlite3.founder</code>.</p>
{f"<p class='msg' role='status'>{escape(message)}</p>" if message else ""}
<h2>Steps</h2>{steps}<p><small>Plan calls the local model once (about 2 minutes on a CPU laptop).</small></p>
<h2>Waiting for the founder</h2>{''.join(forms) or '<p>Nothing is waiting for approval.</p>'}
<h2>Outputs</h2><ul>{file_list}</ul></body></html>"""
    return HTMLResponse(body, headers=FORM_HEADERS)


PHASE_NAMES = {2: "Validate", 3: "Build", 4: "Commercial setup", 5: "Launch", 6: "Operate & learn"}


@router.get("/api/runs/{run_id}/journey")
def run_journey(run_id: str, svc: Services = Depends(services)) -> dict[str, Any]:
    """Phases 2-6 as recorded on disk, for the workspace. Read-only: nothing is generated or approved."""
    if not RUN_ID.match(run_id):
        raise HTTPException(404, "Unknown run")
    if not (svc.runs_root / run_id / "phase1_gate_decision.json").is_file():
        return {"available": False, "reason": "The Discover analysis has not produced a decision yet.",
                "phases": [], "pending": [], "runner": None}
    ctx = _ctx(svc, run_id)
    blocked = ("Discover decided STOP: phases 2–6 are blocked." if ctx.decision == "STOP" else
               "This decision was made by superseded gate rules: run a new analysis to continue."
               if ctx.superseded else None)
    files = sorted(p.name for p in ctx.out.iterdir() if NAME.match(p.name)) if ctx.out.exists() else []
    phases = []
    for n, title in PHASE_NAMES.items():
        mine = [f for f in files if f.startswith(f"phase{n}_")]
        gates = []
        for name in mine:
            if name.startswith(f"phase{n}_gate_") and name.endswith(".json"):
                g = json.loads((ctx.out / name).read_text(encoding="utf-8"))
                gates.append({"name": name, "outcome": g.get("outcome"), "decision": g.get("decision"),
                              "launch": g.get("launch_recommendation"), "rehearsal": bool(g.get("rehearsal"))})
        phases.append({"phase": n, "title": title,
                       "files": [{"name": f, "url": f"/phases/run/{run_id}/view/{f}"} for f in mine],
                       "gates": gates})
    return {"available": True, "discover": ctx.decision, "superseded": ctx.superseded, "blocked": blocked,
            "rehearsal": ctx.rehearsal, "validated": ctx.validated, "phases": phases,
            "pending": [{"action": p["action"], "what": p["what"], "file": p["file"],
                         "fingerprint": p["sha"]} for p in pending(ctx)],
            "runner": f"/phases/run/{run_id}"}


@router.get("/phases/run/{run_id}", response_class=HTMLResponse, include_in_schema=False)
def run_page(run_id: str, svc: Services = Depends(services)) -> HTMLResponse:
    return _page(_ctx(svc, run_id))


@router.post("/phases/run/{run_id}/step/{step}", response_class=HTMLResponse, include_in_schema=False)
async def run_step(run_id: str, step: str, request: Request, svc: Services = Depends(services)) -> HTMLResponse:
    _same_origin(request)
    form = await _form(request)
    token = form.get("founder_key", "").strip().encode("ascii", "replace")
    if not svc.approvals.verify_founder(token):
        from approval import ApprovalError
        svc.approvals.record_failure("workflow_authentication", ApprovalError("Unauthorized"))
        mirror_builder_events(svc, None)
        raise HTTPException(403, "Founder key missing or wrong")
    ctx = _ctx(svc, run_id)
    ctx.approvals.token = token
    fn = {"plan": workflow.plan, "prepare-launch": workflow.prepare_launch, "launch": workflow.launch}.get(step)
    if fn is None:
        raise HTTPException(404, "Unknown step")
    try:
        result = await run_in_threadpool(fn, ctx)
        extra = f" Sale-to-cash checks passed: {result['payment_tests_passed']}; memo: {result['memo']}." \
            if isinstance(result, dict) else ""
        message = f"{step} finished.{extra}"
    except workflow.GateBlocked as exc:
        message = f"Gate blocked: {exc}"
    except ValueError as exc:  # content rules refused a draft: explain, never a 500
        ctx.rec(3, "content_rule_block", str(exc))
        message = f"Blocked by the content rules: {exc}. Nothing more was written for this step."
    ctx.approvals.mirror()
    return _page(ctx, message)


async def _form(request: Request) -> dict[str, str]:
    """URL-encoded form body, parsed with the standard library (no extra dependency)."""
    if not request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        raise HTTPException(415, "Expected a form submission")
    raw = await request.body()
    if len(raw) > 4096:
        raise HTTPException(413, "Form too large")
    fields = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True, max_num_fields=10)
    return {k: v[0] for k, v in fields.items()}


@router.post("/phases/run/{run_id}/approve", response_class=HTMLResponse, include_in_schema=False)
async def run_approve(run_id: str, request: Request, svc: Services = Depends(services)) -> HTMLResponse:
    form = await _form(request)
    action, sha256 = form.get("action", "")[:60], form.get("sha256", "")[:64]
    decision, founder_key = form.get("decision", ""), form.get("founder_key", "")[:200]
    reason, option = form.get("reason", "")[:300], form.get("option", "")[:40]
    _same_origin(request)
    ctx = _ctx(svc, run_id)
    if decision not in ("approve", "reject") or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise HTTPException(422, "Invalid decision")
    if not svc.approvals.verify_founder(founder_key.strip().encode("ascii", "replace")):
        from approval import ApprovalError
        svc.approvals.record_failure("workflow_authentication", ApprovalError("Unauthorized"))
        mirror_builder_events(svc, None)
        ctx.log.record("approval", "founder_decision_refused", model=None, cost=0, approved_by=None,
                       outcome="refused: founder key missing or wrong", action_requested=action)
        return _page(ctx, "Refused: the founder key is missing or wrong. Nothing was approved.")
    allowed = {i["action"]: i for i in pending(ctx)}
    if action not in allowed or allowed[action]["sha"] != sha256:
        return _page(ctx, "Refused: this request is not pending or its file changed. Review the current version.")
    full = action
    if action == "set_price":
        if option not in {v for v, _ in allowed[action]["choices"]}:
            return _page(ctx, "Refused: choose one of the listed price options.")
        full = f"set_price:{option}"
    ctx.approvals.token = founder_key.strip().encode("ascii", "replace")
    ctx.approvals.record(full, sha256, decision, reason.strip() or "[No reason provided]")
    ctx.log.record("approval", f"founder_{decision}", model=None, cost=0,
                   approved_by="founder" if decision == "approve" else None, outcome=f"{decision}: {full}",
                   sha256=sha256, via="web workspace")
    return _page(ctx, f"Recorded: {decision} {full}.")


@router.get("/phases/run/{run_id}/view/{name}", include_in_schema=False)
def run_file(run_id: str, name: str, svc: Services = Depends(services)) -> Response:
    ctx = _ctx(svc, run_id)
    path = ctx.out / name
    if not NAME.match(name) or path.is_symlink() or not path.is_file():
        raise HTTPException(404, "Not a phase output")
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        return HTMLResponse(text, headers={**HEADERS, "Content-Security-Policy": "sandbox; " + HEADERS["Content-Security-Policy"]})
    return PlainTextResponse(text, headers=HEADERS)
