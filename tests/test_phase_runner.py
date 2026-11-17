"""Phases 2-6 from the browser: same gates as workflow.py, founder key required, same-origin only.

SYNTHETIC run files in a temporary root; founder decisions here are SIMULATED test decisions.
"""
import json
import re

import pytest

from gates import RULESET_VERSION
from fastapi.testclient import TestClient

from app.api import build_services
from app.main import app
from tests.conftest import TEST_SETTINGS
from tests.test_later_phases import BRIEF

RUN = "run-0123456789abcdef"
ORIGIN = {"origin": "http://testserver"}


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("VENTURELAB_ADVISOR_MODEL", "0")
    svc = build_services(TEST_SETTINGS, root=tmp_path)
    run = svc.runs_root / RUN
    run.mkdir(parents=True)
    (run / "phase1_gate_decision.json").write_text(json.dumps({
        "run_id": RUN, "decision": "REPEAT", "rule": "REPEAT_INSUFFICIENT_EVIDENCE", "ruleset_version": RULESET_VERSION,
        "counterfactual": {"experiments": [{"name": "Problem interviews", "method": "Talk to 10 people",
                                            "support_if": "x", "weaken_if": "y"}]}}))
    (run / "phase1_step1_founder_brief.json").write_text(json.dumps({"brief": BRIEF}))
    app.state.services = svc
    yield TestClient(app), svc
    app.state.services = None


def approve_all(client, svc, key):
    """Approve whatever the page lists as pending, the way a founder would click through."""
    page = client.get(f"/phases/run/{RUN}").text
    for action, sha in re.findall(r"name='action' value='([^']+)'>\s*<input type='hidden' name='sha256' value='([0-9a-f]{64})'", page):
        data = {"action": action, "sha256": sha, "decision": "approve", "founder_key": key, "reason": "SIMULATED"}
        if action == "set_price":
            data["option"] = "pro-8"
        assert "Recorded: approve" in client.post(f"/phases/run/{RUN}/approve", data=data, headers=ORIGIN).text


def test_full_web_flow_with_founder_key(web):
    client, svc = web
    key = svc.approvals.founder_path.read_text()
    assert "Gate blocked" in client.post(f"/phases/run/{RUN}/step/plan", headers=ORIGIN).text  # rehearsal first
    approve_all(client, svc, key)
    assert "plan finished" in client.post(f"/phases/run/{RUN}/step/plan", headers=ORIGIN).text
    approve_all(client, svc, key)
    assert "prepare-launch finished" in client.post(f"/phases/run/{RUN}/step/prepare-launch", headers=ORIGIN).text
    approve_all(client, svc, key)
    done = client.post(f"/phases/run/{RUN}/step/launch", headers=ORIGIN).text
    assert "Sale-to-cash checks passed: True" in done
    out = svc.runs_root.parent / "phases" / RUN
    assert (out / "payment_test_log.md").exists() and (out / "phase6_step3_persevere-or-pivot-memo.md").exists()
    assert "Nothing is waiting for approval" in client.get(f"/phases/run/{RUN}").text


def test_wrong_key_and_cross_site_requests_are_refused(web):
    client, svc = web
    page = client.get(f"/phases/run/{RUN}").text
    sha = re.search(r"name='sha256' value='([0-9a-f]{64})'", page).group(1)
    data = {"action": "rehearse_after_repeat", "sha256": sha, "decision": "approve", "founder_key": "wrong"}
    assert "Refused" in client.post(f"/phases/run/{RUN}/approve", data=data, headers=ORIGIN).text
    key = svc.approvals.founder_path.read_text()
    evil = {"origin": "https://evil.example"}
    assert client.post(f"/phases/run/{RUN}/approve", data=dict(data, founder_key=key), headers=evil).status_code == 403
    assert client.post(f"/phases/run/{RUN}/step/plan", headers=evil).status_code == 403
    assert client.post(f"/phases/run/{RUN}/approve", data=dict(data, founder_key=key)).status_code == 403  # no origin
    assert "Gate blocked" in client.post(f"/phases/run/{RUN}/step/plan", headers=ORIGIN).text


def test_approval_for_a_changed_file_is_refused(web):
    client, svc = web
    key = svc.approvals.founder_path.read_text()
    approve_all(client, svc, key)
    client.post(f"/phases/run/{RUN}/step/plan", headers=ORIGIN)
    page = client.get(f"/phases/run/{RUN}").text
    old = re.search(r"value='set_price'>\s*<input type='hidden' name='sha256' value='([0-9a-f]{64})'", page).group(1)
    pricing = svc.runs_root.parent / "phases" / RUN / "phase4_step1_pricing.json"
    pricing.write_text(pricing.read_text().replace("Paid tier", "Paid tier (edited)"))
    data = {"action": "set_price", "sha256": old, "decision": "approve", "founder_key": key, "option": "pro-8"}
    assert "not pending or its file changed" in client.post(f"/phases/run/{RUN}/approve", data=data, headers=ORIGIN).text


def test_unknown_runs_and_paths_are_404(web):
    client, _ = web
    for url in ("/phases/run/run-xyz", "/phases/run/../../etc", f"/phases/run/{RUN}/view/secret.txt",
                f"/phases/run/{RUN}/view/..%2F..%2Fdecision_log.json"):
        assert client.get(url).status_code == 404, url


def test_stop_run_disables_steps(web):
    client, svc = web
    gate = svc.runs_root / RUN / "phase1_gate_decision.json"
    gate.write_text(json.dumps(dict(json.loads(gate.read_text()), decision="STOP", rule="STOP_PROHIBITED_CATEGORY")))
    page = client.get(f"/phases/run/{RUN}").text
    assert "phases 2–6 are blocked" in page and "<button disabled>" in page
    assert "Gate blocked" in client.post(f"/phases/run/{RUN}/step/plan", headers=ORIGIN).text


def test_form_pages_send_their_origin_and_null_origin_is_refused(web):
    client, _ = web
    assert client.get(f"/phases/run/{RUN}").headers["referrer-policy"] == "same-origin"
    assert client.post(f"/phases/run/{RUN}/step/plan", headers={"origin": "null"}).status_code == 403
