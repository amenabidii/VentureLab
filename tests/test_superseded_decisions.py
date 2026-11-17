"""A gate decision made by superseded rules can never reach the Builder.

Runs use the STUBBED model and STUBBED sources from conftest. "Superseding" a run means
removing the rule-set version from its recorded gate decision, which is exactly what
runs recorded before RULESET_VERSION 2 look like (for example the accessible-PDF GO).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from builder_adapter import BuilderBlocked, adapt, run_outputs
from gates import RULESET_VERSION
from tests.test_integration_api import decide, make, start


def supersede(svc, run_id: str) -> None:
    path = svc.runs_root / run_id / "phase1_gate_decision.json"
    gate = json.loads(path.read_text(encoding="utf-8"))
    assert gate["ruleset_version"] == RULESET_VERSION and gate["decision"] == "GO"
    del gate["ruleset_version"]
    path.write_text(json.dumps(gate), encoding="utf-8")


@pytest.fixture
def go_request(tmp_path):
    api, svc, _ = make(tmp_path)
    run_id, run = start(api, svc)
    assert run["decision"] == "GO"
    approval = api.post(f"/api/runs/{run_id}/builder").json()["approval"]
    return tmp_path, api, svc, run_id, approval, svc.approvals.founder_path.read_text()


def execute(api, approval, run_id, key):
    return api.post(f"/api/approvals/{approval['id']}/execute", json={"run_id": run_id, "founder_key": key})


def test_current_runs_record_the_rule_set_version(go_request):
    _, api, svc, run_id, _, _ = go_request
    gate = json.loads((svc.runs_root / run_id / "phase1_gate_decision.json").read_text(encoding="utf-8"))
    assert gate["ruleset_version"] == RULESET_VERSION


def test_a_pending_request_from_a_superseded_go_cannot_be_approved_even_after_a_restart(go_request):
    tmp_path, api, svc, run_id, approval, key = go_request
    supersede(svc, run_id)
    r = decide(api, approval, run_id, key)
    assert r.status_code == 409 and "superseded" in r.json()["detail"]
    assert api.get(f"/api/runs/{run_id}/approvals").json()[0]["status"] == "Pending"
    # The refused attempt is recorded (the approval store keeps only a sanitized failure type).
    assert any(e.get("action") == "approval_decision" and e.get("outcome") == "failed: ApprovalError"
               and e.get("action_id") == approval["id"] for e in svc.approvals.audit_events())
    # A restart rebuilds every service from the same state: the refusal is recomputed, not remembered.
    api2, svc2, _ = make(tmp_path)
    assert decide(api2, approval, run_id, key).status_code == 409
    assert execute(api2, approval, run_id, key).status_code == 409
    assert not (svc2.builder_root / run_id).exists()
    # The founder can still reject it.
    assert decide(api2, approval, run_id, key, "reject").json()["status"] == "Rejected"


def test_an_approved_request_from_a_superseded_go_cannot_be_executed(go_request):
    _, api, svc, run_id, approval, key = go_request
    assert decide(api, approval, run_id, key).json()["status"] == "Approved"
    supersede(svc, run_id)
    r = execute(api, approval, run_id, key)
    assert r.status_code == 409 and "superseded" in r.json()["detail"]
    assert not (svc.builder_root / run_id).exists()


def test_a_superseded_run_cannot_prepare_a_new_request(go_request):
    _, api, svc, run_id, approval, key = go_request
    decide(api, approval, run_id, key, "reject")
    supersede(svc, run_id)
    r = api.post(f"/api/runs/{run_id}/builder")
    assert r.status_code == 409 and "superseded" in r.json()["detail"]
    shown = api.get(f"/api/runs/{run_id}/decision").json()
    assert "superseded" in shown["action"]  # the workspace says why the Builder is unavailable
    assert shown["outcome"] == "GO"  # the recorded decision is shown as it was: history is not rewritten


def test_files_written_after_a_valid_approval_stay_intact(go_request):
    _, api, svc, run_id, approval, key = go_request
    decide(api, approval, run_id, key)
    assert execute(api, approval, run_id, key).status_code == 200
    written = {p: p.read_bytes() for p in (svc.builder_root / run_id).rglob("*") if p.is_file()}
    supersede(svc, run_id)
    items = api.get(f"/api/runs/{run_id}/artifacts").json()
    assert items and all(a["status"] == "Generated — written after your approval" for a in items)
    assert {p: p.read_bytes() for p in (svc.builder_root / run_id).rglob("*") if p.is_file()} == written


def test_the_recorded_accessible_pdf_go_is_blocked_from_the_builder():
    """The real run committed under outputs/runs/ was decided by the superseded rule."""
    outputs = run_outputs(Path("outputs/runs/run-4209f27582724d6f"))
    assert outputs["gate"]["decision"] == "GO" and "ruleset_version" not in outputs["gate"]
    with pytest.raises(BuilderBlocked, match="superseded"):
        adapt("run-4209f27582724d6f", outputs)
