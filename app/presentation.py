"""Map recorded backend outputs to the Milestone 4 presentation contracts (normalize.js).

Pure functions over the JSON that the pipeline wrote. They rename and group fields;
they never upgrade a standing, invent a quotation, or change a gate decision.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

RELATIONSHIP = {"supports": "Supporting", "partially_supports": "Partially supporting",
                "does_not_support": "Unsupported", "contradicts": "Contradictory"}
APPROVAL_STATUS = {"pending": "Pending", "approved": "Approved", "rejected": "Rejected",
                   "executing": "Executing", "executed": "Executed", "failed_execution": "Failed"}


def run_summary(run: dict[str, Any]) -> dict[str, Any]:
    phase = "Discover" if run["status"] != "completed" else f"Discover · {run['decision']} ({run['rule']})"
    finished = run.get("finished")
    return {"id": run["id"], "title": run["title"], "status": run["status"].capitalize(), "phase": phase,
            "recordedAt": finished if run["status"] in ("completed", "failed", "blocked") else None,
            "stage": run["stage"], "error": run.get("error"), "created": run["created"]}


def _host(url: str | None) -> str:
    if not url:
        return "No source URL"
    host = urlparse(url).netloc
    return "Hacker News comment" if host.endswith("ycombinator.com") else (host or "Unknown source")


def findings(outputs: dict[str, Any]) -> list[dict[str, Any]]:
    inv = outputs.get("investigation")
    if not inv:
        return []
    related: dict[str, list[str]] = {}
    for a in (outputs.get("challenge") or {}).get("assumptions", []):
        for fid in a.get("related_findings", []):
            related.setdefault(fid, []).append(f"{a['id']}: {a['text']}")
    out = []
    for f in inv["findings"]:
        verified = [q for q in f["quotes"] if q["status"] == "verified"]
        url = verified[0]["url"] if verified else None
        assessment = [f["reason"] or "Not assessed by the model."]
        if f.get("second_check") is not None:
            assessment.append(f"Second check: {'agreed' if f['second_check'] else 'disagreed'}. "
                              f"{f.get('second_check_note') or ''}".strip())
        assessment.append(f"Relevance to the brief: {f['relevance'].replace('_', '-')}"
                          + (f" (shared: {', '.join(f['shared_terms'])})" if f.get("shared_terms") else ""))
        limitations = [f["limitations"]] if f.get("limitations") else []
        limitations += [f"Needs review: {r}" for r in f.get("review", [])]
        limitations += f.get("notes", [])
        if not verified:
            limitations.append("No verified quotation: this claim is an ASSUMPTION, not evidence.")
        kind = "founder statement check" if f["origin"] == "hypothesis_check" else f["type"].replace("_", " ")
        out.append({
            "id": f["id"], "claim": f["claim"], "type": kind,
            "standing": f["standing"].upper(),
            "relationship": RELATIONSHIP.get(f["verdict"]) if f.get("verdict") else None,
            "sourceName": _host(url), "url": url or "",
            "quote": "\n\n".join(q["text"] for q in verified),
            "assessment": " ".join(a for a in assessment if a),
            "limitations": " ".join(limitations) or "None recorded.",
            "assumption": "; ".join(related.get(f["id"], [])) or "Not linked to a founder assumption.",
            "sources": [q["url"] for q in verified],
        })
    return out


def challenges(outputs: dict[str, Any]) -> list[dict[str, Any]]:
    chal = outputs.get("challenge")
    if not chal:
        return []
    experiments = {e["assumption"]: e for e in chal.get("experiments", [])}
    out = []
    if chal.get("status") != "ok":
        out.append({"id": "CHALLENGER", "basis": "FAILED — no model analysis", "claim": "The Challenger did not complete.",
                    "risk": chal.get("error") or "Unknown error", "severity": None, "findings": [], "missing": [],
                    "experiment": "Not provided"})
    for r in chal.get("reviews", []):
        e = experiments.get(r["assumption"])
        out.append({
            "id": r["assumption"],
            "basis": f"{r['basis']} · stance {r['stance']}"
                     + (f" (model said {r['model_stance']}; reasons are advisory)" if r.get("model_stance") else ""),
            "claim": f"{'Stated' if r['stated'] else 'Implied'} founder assumption: {r['assumption_text']}",
            "risk": r["reason"], "severity": None,
            "findings": r.get("evidence", []),
            "missing": [f"{link['finding']}: {link['relationship']} — {link['why']}" for link in r.get("links", [])
                        if link["relationship"] != "direct"],
            "experiment": f"{e['name']}: {e['method']} Supports if: {e['support_if']} Weakens if: {e['weaken_if']}"
                          if e else "Not provided",
        })
    for i, h in enumerate(chal.get("new_hypotheses", []), 1):
        out.append({"id": f"NH{i}", "basis": f"CHALLENGER HYPOTHESIS · {h['basis']} (not the founder's claim)",
                    "claim": h["text"], "risk": "A new hypothesis raised by the Challenger; untested.", "severity": None,
                    "findings": h.get("evidence", []), "missing": [], "experiment": "Not provided"})
    for i, r in enumerate(chal.get("risks", []), 1):
        out.append({"id": f"R{i}", "basis": f"{r['kind'].upper()} RISK to {r['assumption']} · {r['basis']}",
                    "claim": r["text"], "risk": f"Tied to founder assumption {r['assumption']}.", "severity": None,
                    "findings": r.get("evidence", []), "missing": [], "experiment": "Not provided"})
    return out


def decision(outputs: dict[str, Any], builder_note: str) -> dict[str, Any] | None:
    gate = outputs.get("gate")
    if not gate:
        return None
    e, cf = gate["evidence"], gate["counterfactual"]
    meaning = {"GO": "Permission to run further validation with customers. Not proof of demand or of success.",
               "REPEAT": "Evidence or validation is insufficient. Gather more and test again.",
               "PIVOT": "Test the supported alternative instead.",
               "STOP": "Do not proceed under current conditions."}[gate["decision"]]
    return {
        "outcome": gate["decision"], "rule": gate["rule"],
        "explanation": f"{gate['rule_meaning']} {meaning}",
        "findings": e["supporting"] + e.get("corroborating_checks", []) + e["contradicting_checks"]
                    + [a["finding"] for a in e["alternatives"]],
        "missing": cf["missing_evidence"],
        "risks": gate.get("feasibility_notes", []),
        "next": f"Reconsidered by: {cf['reconsidered_by']}.",
        "action": builder_note,
    }


def counterfactual(outputs: dict[str, Any]) -> dict[str, Any] | None:
    gate = outputs.get("gate")
    if not gate:
        return None
    cf = gate["counterfactual"]
    ex = cf["experiments"]
    numbered = lambda key: " ".join(f"({i}) {x[key]}" for i, x in enumerate(ex, 1)) or "Not provided"
    limitation = cf["no_guarantee"]
    if cf.get("alternative_hypothesis"):
        limitation = f"Alternative hypothesis: {cf['alternative_hypothesis']['hypothesis']}. " + limitation
    return {"requirement": " ".join(cf["missing_evidence"]) or "Not provided", "limitation": limitation,
            "experiment": " ".join(f"({i}) {x['name']}: {x['method']}" for i, x in enumerate(ex, 1))
                          or "No experiment can change this decision.",
            "strengthen": numbered("support_if"), "weaken": numbered("weaken_if"), "gate": cf["reconsidered_by"]}


def agents(run: dict[str, Any], outputs: dict[str, Any], approvals: list[dict[str, Any]],
           builder_blocked: str | None) -> list[dict[str, Any]]:
    status, stage = run["status"], run["stage"]
    actions = [p["agent"] for p in run["progress"]]
    order = ["Investigator", "Challenger", "Judge (deterministic rules)", "Judge (counterfactual)"]

    def state(agent: str, label: str) -> str:
        if status in ("blocked",):
            return "Blocked"
        if status == "queued":
            return "Waiting"
        if status == "failed" and stage.startswith(label):
            return "Failed"
        if agent in actions and (status == "completed" or not stage.startswith(label)):
            return "Completed"
        if status == "running" and stage.startswith(label):
            return "Running"
        return "Not started" if status != "failed" else "Not started"

    skipped = any(p["action"] == "skip_research" for p in run["progress"])
    inv_task = "Retrieving public sources, extracting and verifying quotations (local model)."
    chal_task = "Reviewing the founder's assumptions against the findings (local model)."
    if skipped:
        inv_task = chal_task = "Not run: a STOP rule applied before research."
    if status == "blocked":
        inv_task = run.get("error") or "Blocked."
    elif status == "running" and stage.startswith("Waiting for the local model"):
        inv_task = stage + ". Research starts automatically when it is ready."
    calls = (outputs.get("investigation") or {}).get("model_calls")
    if calls is not None:
        inv_task += f" {calls} model calls."
    builder_status, builder_task = "Not started", "Prepares a validation kit only when you request it; writes files only after your approval."
    if builder_blocked:
        builder_status, builder_task = "Blocked", builder_blocked
    elif approvals:
        latest = approvals[-1]["status"]
        builder_status = {"Pending": "Waiting", "Approved": "Waiting", "Executed": "Completed",
                          "Failed": "Failed", "Executing": "Running"}.get(latest, "Not started")
        builder_task = f"Latest request {approvals[-1]['id']}: {latest}."
    gate = outputs.get("gate")
    judge_task = (f"Deterministic rule {gate['rule']} decided {gate['decision']} (Python rules, no model)."
                  if gate else "Applies fixed Python rules after the Challenger; no model is involved.")
    return [
        {"agent": "Investigator", "status": "Not started" if skipped else state("investigator", "Investigator"), "task": inv_task},
        {"agent": "Challenger", "status": "Not started" if skipped else state("challenger", "Challenger"), "task": chal_task},
        {"agent": "Judge", "status": "Completed" if gate else ("Blocked" if status == "blocked" else
                                                                ("Failed" if status == "failed" else "Waiting")),
         "task": judge_task},
        {"agent": "Builder", "status": builder_status, "task": builder_task},
    ]


def approval(request, expires_at, expired: bool) -> dict[str, Any]:
    status = APPROVAL_STATUS[request.status.value]
    if expired and status in ("Pending", "Approved"):
        status = "Expired"
    return {"id": request.action_id, "runId": request.run_id, "artifactId": request.action_id,
            "fingerprint": request.artifact_sha256, "action": request.action_type,
            "description": request.description, "status": status,
            "expiresAt": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ") if expires_at else None}
