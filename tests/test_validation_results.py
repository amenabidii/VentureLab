"""Founder-reported validation results against the threshold approved before testing.

Unit tests use SYNTHETIC counts. API tests use the STUBBED model and sources from conftest;
every count below is a test input, never a real experiment result.
"""

from __future__ import annotations

import json

import pytest

import validation
from tests.test_integration_api import decide, make, start
from tests.test_superseded_decisions import supersede


# --- the deterministic rule -------------------------------------------------------------------------

def test_the_problem_statement_example_fails_the_gate():
    """A target of 100 sign-ups that gets 12 must fail, not be spun."""
    out = validation.evaluate(validation.Plan("waitlist sign-ups in 14 days", 100, 100), 100, 12)
    assert out.decision == "STOP" and out.rule == "STOP_FAILED_VALIDATION_CONDITION"
    assert "Do not lower the threshold" in out.next_step and "pivot back to Discover" in out.next_step


@pytest.mark.parametrize(("participants", "successes", "decision"), [
    (5, 3, "GO"), (3, 3, "GO"),          # threshold reached, even before the sample is complete
    (5, 2, "STOP"), (4, 0, "STOP"),      # cannot reach 3 of 5 any more
    (2, 1, "REPEAT"), (3, 1, "REPEAT"),  # still open
])
def test_three_of_five(participants, successes, decision):
    assert validation.evaluate(validation.Plan("m", 3, 5), participants, successes).decision == decision


def test_go_is_never_called_proof_of_demand():
    assert "not proof of demand" in validation.evaluate(validation.Plan("m", 3, 5), 5, 5).meaning


@pytest.mark.parametrize(("previous", "participants", "successes", "reason"), [
    ([], 6, 3, "larger sample"),
    ([], 2, 3, "between 0"),
    ([], 0, 0, "at least one"),
    ([{"participants": 3, "successes": 1, "outcome": {"decision": "REPEAT", "rule": "r"}}], 2, 1, "cannot go down"),
    ([{"participants": 3, "successes": 1, "outcome": {"decision": "REPEAT", "rule": "r"}}], 4, 3, "cannot exceed"),
    ([{"participants": 5, "successes": 1, "outcome": {"decision": "STOP", "rule": "r"}}], 5, 5, "final"),
    ([{"participants": 3, "successes": 3, "outcome": {"decision": "GO", "rule": "r"}}], 4, 3, "final"),
])
def test_observations_that_would_spin_the_result_are_refused(previous, participants, successes, reason):
    with pytest.raises(validation.ResultRefused, match=reason):
        validation.check_observation(validation.Plan("m", 3, 5), previous, participants, successes)


# --- through the API ------------------------------------------------------------------------------

@pytest.fixture
def written_kit(tmp_path):
    api, svc, _ = make(tmp_path)
    run_id, _ = start(api, svc)
    approval = api.post(f"/api/runs/{run_id}/builder").json()["approval"]
    key = svc.approvals.founder_path.read_text()
    assert decide(api, approval, run_id, key).status_code == 200
    assert api.post(f"/api/approvals/{approval['id']}/execute",
                    json={"run_id": run_id, "founder_key": key}).status_code == 200
    return tmp_path, api, svc, run_id, approval["id"], key


def record(api, action_id, run_id, key, participants, successes, notes=""):
    return api.post(f"/api/approvals/{action_id}/results", json={
        "run_id": run_id, "founder_key": key, "participants": participants, "successes": successes, "notes": notes})


def test_recorded_results_reach_a_stop_and_the_result_is_final(written_kit):
    tmp_path, api, svc, run_id, action_id, key = written_kit
    first = record(api, action_id, run_id, key, 2, 0, "two interviews so far")
    assert first.status_code == 201 and first.json()["outcome"]["decision"] == "REPEAT"
    assert first.json()["plan"] == {"metric": first.json()["plan"]["metric"], "threshold": 3, "sample_size": 5,
                                    "approved_before_results": True}
    second = record(api, action_id, run_id, key, 4, 0)
    assert second.json()["outcome"]["rule"] == "STOP_FAILED_VALIDATION_CONDITION"
    assert record(api, action_id, run_id, key, 5, 5).status_code == 409  # cannot be rescued afterwards

    [kit] = api.get(f"/api/runs/{run_id}/validation").json()
    assert kit["id"] == action_id and kit["final"] and kit["latest"]["decision"] == "STOP"
    assert [o["outcome"]["decision"] for o in kit["observations"]] == ["REPEAT", "STOP"]
    assert all(o["result_source"].startswith("FOUNDER-REPORTED") for o in kit["observations"])
    gate = json.loads((svc.runs_root / run_id / "phase2_gate_validation.json").read_text(encoding="utf-8"))
    assert gate["decision"] == "STOP" and gate["result_source"].startswith("FOUNDER-REPORTED")
    # The phase 1 decision is not rewritten by later results.
    assert api.get(f"/api/runs/{run_id}/decision").json()["outcome"] == "GO"

    log = [e for e in json.loads(svc.log_path.read_text(encoding="utf-8")) if e.get("run_id") == run_id]
    founder = [e for e in log if e["action"] == "record_validation_result"]
    gates = [e for e in log if e["action"] == "validation_gate"]
    assert len(founder) == 2 and all(e["approved_by"] == "founder" and e["model"] is None for e in founder)
    assert [e["outcome"] for e in gates] == ["repeat", "stop"]

    # A restart keeps the record and the finality.
    api2, _, _ = make(tmp_path)
    assert len(api2.get(f"/api/runs/{run_id}/validation").json()[0]["observations"]) == 2
    assert record(api2, action_id, run_id, key, 5, 5).status_code == 409


def test_threshold_met_gives_go_to_the_next_phase(written_kit):
    _, api, _, run_id, action_id, key = written_kit
    [kit] = api.get(f"/api/runs/{run_id}/validation").json()  # the plan is visible before any result
    assert kit["plan"]["threshold"] == 3 and kit["plan"]["sampleSize"] == 5 and kit["observations"] == []
    r = record(api, action_id, run_id, key, 3, 3)
    assert r.json()["outcome"]["decision"] == "GO" and "not proof of demand" in r.json()["outcome"]["meaning"]


@pytest.mark.parametrize(("participants", "successes"), [(6, 3), (2, 3)])
def test_bending_the_plan_is_refused_and_nothing_is_recorded(written_kit, participants, successes):
    _, api, svc, run_id, action_id, key = written_kit
    assert record(api, action_id, run_id, key, participants, successes).status_code == 409
    assert api.get(f"/api/runs/{run_id}/validation").json()[0]["observations"] == []


@pytest.mark.parametrize("key", ["", "0" * 64, "not-a-key"])
def test_results_need_the_founder_key(written_kit, key):
    _, api, svc, run_id, action_id, _ = written_kit
    assert record(api, action_id, run_id, key, 3, 3).status_code == 403
    assert api.get(f"/api/runs/{run_id}/validation").json()[0]["observations"] == []
    assert not any(e["action"] == "record_validation_result" for e in json.loads(svc.log_path.read_text("utf-8")))


def test_results_need_a_kit_that_was_approved_and_written(tmp_path):
    api, svc, _ = make(tmp_path)
    run_id, _ = start(api, svc)
    approval = api.post(f"/api/runs/{run_id}/builder").json()["approval"]
    key = svc.approvals.founder_path.read_text()
    assert record(api, approval["id"], run_id, key, 3, 3).status_code == 409  # pending
    decide(api, approval, run_id, key)
    assert record(api, approval["id"], run_id, key, 3, 3).status_code == 409  # approved, not written


def test_a_changed_kit_on_disk_cannot_take_results(written_kit):
    _, api, svc, run_id, action_id, key = written_kit
    kit = next((svc.builder_root / run_id / action_id).glob("phase2_step1_validation-kit.json"))
    kit.write_text(kit.read_text(encoding="utf-8").replace('"threshold": 3', '"threshold": 1'), encoding="utf-8")
    r = record(api, action_id, run_id, key, 1, 1)
    assert r.status_code == 409 and "differs" in r.json()["detail"]


def test_a_superseded_run_cannot_take_results(written_kit):
    _, api, svc, run_id, action_id, key = written_kit
    supersede(svc, run_id)
    r = record(api, action_id, run_id, key, 3, 3)
    assert r.status_code == 409 and "superseded" in r.json()["detail"]


def test_results_for_another_run_or_unknown_request_are_refused(written_kit):
    _, api, _, run_id, action_id, key = written_kit
    assert record(api, action_id, "run-0000000000000000", key, 3, 3).status_code == 409
    assert record(api, "f" * 32, run_id, key, 3, 3).status_code == 404
