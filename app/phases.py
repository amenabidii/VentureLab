"""Read-only view of the six phases: each phase's gate decision and its output files.

Serves only files directly in the outputs folder whose names follow the CLAUDE.md
convention (phase<N>_step<M>_* / phase<N>_gate_* / payment_test_log.md). No writes, no
approvals: running and approving phases stays in `workflow.py` behind founder approval.
HTML outputs are served with a sandboxing Content-Security-Policy (no scripts, no network).
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from config import get_settings

router = APIRouter()
NAME = re.compile(r"^(?:phase[1-6]_(?:step\d+|gate)_[A-Za-z0-9][A-Za-z0-9._-]*|payment_test_log)\.(md|json|html)$")
PHASES = {1: "Discover", 2: "Validate", 3: "Build", 4: "Commercial setup", 5: "Launch", 6: "Operate & learn"}
HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
           "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; "
                                      "base-uri 'none'; form-action 'none'"}


def _outputs() -> Path:
    return (Path.cwd() / get_settings().output_dir).absolute()


def _files() -> list[Path]:
    root = _outputs()
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_file() and not p.is_symlink() and NAME.match(p.name))


def _decision(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unreadable"
    return str(data.get("decision", "—"))


@router.get("/phases", response_class=HTMLResponse, include_in_schema=False)
def phases_page() -> HTMLResponse:
    files = _files()
    sections = []
    for n, title in PHASES.items():
        mine = [p for p in files if p.name.startswith(f"phase{n}_")]
        gates = [p for p in mine if p.name.startswith(f"phase{n}_gate_") and p.suffix == ".json"]
        gate_rows = "".join(f"<li><b>{escape(_decision(g))}</b> · <a href='/phases/view/{escape(g.name)}'>"
                            f"{escape(g.name)}</a></li>" for g in gates) or "<li>No gate file yet.</li>"
        file_rows = "".join(f"<li><a href='/phases/view/{escape(p.name)}'>{escape(p.name)}</a></li>"
                            for p in mine if p not in gates) or "<li>No outputs yet.</li>"
        sections.append(f"<section><h2>{n}. {escape(title)}</h2><h3>Gate decisions</h3><ul>{gate_rows}</ul>"
                        f"<h3>Outputs</h3><ul>{file_rows}</ul></section>")
    runs_dir = _outputs() / "runs"
    run_rows = []
    if runs_dir.is_dir():
        for gate in sorted(runs_dir.glob("run-*/phase1_gate_decision.json"), reverse=True):
            rid = gate.parent.name
            if re.fullmatch(r"run-[0-9a-f]{16}", rid):
                data = json.loads(gate.read_text(encoding="utf-8"))
                from gates import RULESET_VERSION
                state = (escape(str(data.get("decision"))) if data.get("ruleset_version") == RULESET_VERSION
                         else f"{escape(str(data.get('decision')))} (superseded rules: re-run Discover)")
                run_rows.append(f"<li><a href='/phases/run/{escape(rid)}'>{escape(rid)}</a> · Discover <b>{state}</b></li>")
    runs_html = ("<section><h2>Run phases 2–6 for a workspace run</h2><ul>" + "".join(run_rows) + "</ul></section>"
                 if run_rows else "<p>Submit a brief in the workspace; finished runs appear here.</p>")
    log = [p for p in files if p.name == "payment_test_log.md"]
    extra = (f"<p>Sale-to-cash test log (MOCKED): <a href='/phases/view/payment_test_log.md'>payment_test_log.md</a></p>"
             if log else "")
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Phases 1–6 · VentureLab</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 16px;color:#17251f;background:#fff}}
section{{border:1px solid #d4ddd4;border-radius:10px;padding:4px 18px 10px;margin:14px 0}}
.note{{background:#f3f6f0;padding:10px 14px;border-radius:8px}}a{{color:#195b48}}</style></head><body>
<p><a href="/">← Workspace</a></p><h1>Phases 1–6: gates and outputs</h1>
<p class="note">Files come from real runs (the workspace or <code>orchestrator.py</code> for Discover,
<code>workflow.py</code> for later phases). After a REPEAT, phases 2–6 run only as a founder-approved REHEARSAL,
and every sale-to-cash event is MOCKED. Run phases 2–6 from a run's own page below or with
<code>workflow.py</code>; every step needs the founder's approval with the founder key.</p>{runs_html}<h2>Committed demo rehearsal (run-a9f21cd634924cca, current gate rules)</h2>{extra}{''.join(sections)}</body></html>"""
    return HTMLResponse(body, headers=HEADERS)


@router.get("/phases/view/{name}", include_in_schema=False)
def phase_file(name: str) -> Response:
    if not NAME.match(name):
        raise HTTPException(404, "Not a phase output")
    path = _outputs() / name
    if path.is_symlink() or not path.is_file() or path.parent != _outputs():
        raise HTTPException(404, "Not a phase output")
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".html":
        # Generated pages are shown inert: sandboxed, no scripts, no network.
        return HTMLResponse(text, headers={**HEADERS, "Content-Security-Policy": "sandbox; " + HEADERS["Content-Security-Policy"]})
    return PlainTextResponse(text, headers=HEADERS)
