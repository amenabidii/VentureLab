"""Integrated web API: founder journey, evidence, Builder, approvals, jobs.

Everything here uses the STUBBED Ollama (RoutedOllama) and STUBBED public sources
from conftest: these are mocked integration tests of the real code paths, not
evidence about any market and not a live model run.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import build_services
from app.main import app
from audit import check_entry
from jobs import RunStore
from tests.conftest import TEST_SETTINGS, RoutedOllama, stub_sources
from tests.test_agents import (
    ALICE, BOB, COMMENTS, CONFIRMED, FAITHFUL, QUERIES, SUPPORTS, extraction,
)

CHALLENGE = json.dumps({"reviews": {}, "new_hypotheses": [], "risks": [], "experiments": []})
BRIEF = {
    "idea": "A web app that drafts release notes from merged pull requests.",
    "market": "online", "customer": "developers at small SaaS companies",
    "problem": "Small software teams spend too much time writing release notes.",
    "skills": "Python, technical writing", "hours": 10, "budget": 0, "currency": "EGP",
    "values": "Honest marketing", "constraints": "None", "sources": [],
}
PROHIBITED = BRIEF | {"idea": "A paid newsletter with daily crypto trading signals for beginners."}


class Model(RoutedOllama):
    """STUBBED Ollama that also reports the configured model as installed."""

    def __init__(self, replies, installed=True):
        super().__init__(replies)
        self.installed = installed

    def handler(self, request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}] if self.installed else []})
        return super().handler(request)


def make(tmp_path, replies=None, routes=None, installed=True, ttl=7200, max_queued=3, gate=None, model_wait=0):
    model = Model({"queries": QUERIES, "extract": FAITHFUL, "assess": SUPPORTS, "confirm": CONFIRMED,
                   "challenge": CHALLENGE} | (replies or {}), installed=installed)

    def client():
        if gate is not None:
            gate.wait(10)
        return model.client()

    settings = replace(TEST_SETTINGS, approval_ttl_s=ttl, max_queued_runs=max_queued, model_wait_s=model_wait)
    svc = build_services(settings, client_factory=client,
                         fetcher_factory=lambda: stub_sources(routes or {"hn.algolia.com": COMMENTS}), root=tmp_path)
    app.state.services = svc
    return TestClient(app), svc, model


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.state.services = None


def wait(svc, run_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        run = svc.runs.get(run_id)
        if run["status"] not in ("queued", "running"):
            return run
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def start(api, svc, brief=BRIEF):
    r = api.post("/api/runs", json=brief)
    assert r.status_code == 202, r.text
    run = wait(svc, r.json()["run"]["id"])
    return run["id"], run


# --- founder journey ----------------------------------------------------------------------------

def test_full_journey_research_decision_builder_approval_execution(tmp_path):
    api, svc, model = make(tmp_path)
    run_id, run = start(api, svc)
    assert run["status"] == "completed" and run["decision"] == "GO"
    assert {"queries", "extract", "assess", "confirm", "challenge"} <= set(model.calls)

    findings = api.get(f"/api/runs/{run_id}/findings").json()
    f1 = next(f for f in findings if f["quote"] == ALICE)
    assert f1["standing"] == "ESTABLISHED" and f1["url"].startswith("https://news.ycombinator.com/item?id=")
    decision = api.get(f"/api/runs/{run_id}/decision").json()
    assert decision["outcome"] == "GO" and decision["rule"] == "GO_TO_FURTHER_VALIDATION"
    assert "not proof of demand" in decision["explanation"]
    cf = api.get(f"/api/runs/{run_id}/counterfactual").json()
    assert "does not guarantee" in cf["limitation"] and cf["gate"]
    agents = {a["agent"]: a["status"] for a in api.get(f"/api/runs/{run_id}/agents").json()}
    assert agents == {"Investigator": "Completed", "Challenger": "Completed", "Judge": "Completed",
                      "Builder": "Not started"}

    prep = api.post(f"/api/runs/{run_id}/builder").json()
    approval = prep["approval"]
    assert approval["status"] == "Pending" and approval["runId"] == run_id
    names = [a["id"].split(":")[-1] for a in api.get(f"/api/runs/{run_id}/artifacts").json()]
    assert "phase3_step1_landing-page.html" in names  # GO: landing page included
    assert not (svc.builder_root / run_id).exists()  # nothing written before approval

    key = svc.approvals.founder_path.read_text()
    ok = api.post(f"/api/approvals/{approval['id']}/decision", json={
        "run_id": run_id, "fingerprint": approval["fingerprint"], "decision": "approve",
        "reason": "Reviewed the kit", "founder_key": key})
    assert ok.status_code == 200 and ok.json()["status"] == "Approved"
    done = api.post(f"/api/approvals/{approval['id']}/execute", json={"run_id": run_id, "founder_key": key})
    assert done.status_code == 200 and done.json()["status"] == "executed"
    arts = api.get(f"/api/runs/{run_id}/artifacts").json()
    assert all(a["status"].startswith("Generated") for a in arts)
    html = next(a for a in arts if a["format"] == "html")
    assert html["content"].startswith("<!doctype html>") and "<script" not in html["content"]

    audit = api.get(f"/api/runs/{run_id}/audit").json()
    for entry in audit:
        check_entry(entry)
    actions = [(e["agent"], e["action"], e["approved_by"]) for e in audit]
    for expected in [("investigator", "extract_claims", None), ("challenger", "challenge_assumptions", None),
                     ("gate", "evidence_gate", None), ("builder", "prepare_artifacts", None),
                     ("approval", "approval_decision", "founder"), ("builder", "execute_artifacts", "founder")]:
        assert expected in actions, expected
    assert next(e for e in audit if e["action"] == "evidence_gate")["model"] is None  # deterministic


def test_repeat_run_gets_kit_without_landing_page(tmp_path):
    wrong = extraction(("customer_problem", "Most managers say the notes take an hour.", ["takes me an hour"]))

    def assess(user):
        if "this problem: Small software teams" in user:
            return json.dumps({"reason": "Not about time.", "limitations": "", "verdict": "does_not_support"})
        return SUPPORTS
    api, svc, _ = make(tmp_path, replies={"extract": wrong, "assess": assess})
    run_id, run = start(api, svc)
    assert run["decision"] == "REPEAT"
    approval = api.post(f"/api/runs/{run_id}/builder").json()["approval"]
    assert "no landing page" in approval["description"]
    names = [a["id"].split(":")[-1] for a in api.get(f"/api/runs/{run_id}/artifacts").json()]
    assert "phase2_step1_validation-kit.md" in names and "phase3_step1_landing-page.html" not in names


def test_invalid_brief_maps_errors_to_form_fields(tmp_path):
    api, svc, _ = make(tmp_path)
    r = api.post("/api/runs", json=BRIEF | {"idea": "short", "sources": ["javascript:alert(1)"], "hours": 500})
    assert r.status_code == 422
    assert {"idea", "sources", "hours"} <= set(r.json()["fields"])
    assert api.post("/api/runs", json=BRIEF | {"surprise": 1}).status_code == 422
    assert svc.runs.list() == []


def test_prohibited_brief_stops_without_model_and_blocks_builder(tmp_path):
    api, svc, model = make(tmp_path)
    run_id, run = start(api, svc, PROHIBITED)
    assert run["decision"] == "STOP" and run["rule"] == "STOP_PROHIBITED_CATEGORY" and model.calls == []
    r = api.post(f"/api/runs/{run_id}/builder")
    assert r.status_code == 409 and "STOP" in r.json()["detail"]
    agents = {a["agent"]: a["status"] for a in api.get(f"/api/runs/{run_id}/agents").json()}
    assert agents["Builder"] == "Blocked" and agents["Investigator"] == "Not started"


# --- evidence ------------------------------------------------------------------------------------

def test_wrong_attribution_contradiction_and_missing_quotes_keep_their_standing(tmp_path):
    def assess(user):
        if "this problem: Small software teams" in user:
            return json.dumps({"reason": "They say it is quick.", "limitations": "", "verdict": "contradicts"})
        return SUPPORTS
    reply = lambda user: json.dumps({"claims": [
        {"type": "customer_problem", "claim": "One developer says the notes take an hour every Friday.",
         "passages": [int(next(p for p in user.split("[P")[1:] if "takes me an hour" in p).split("]")[0])]},
        {"type": "customer_problem", "claim": "One user says so.", "passages": [999]}]})
    api, svc, _ = make(tmp_path, replies={"extract": reply, "assess": assess})
    run_id, _ = start(api, svc)
    by_id = {f["id"]: f for f in api.get(f"/api/runs/{run_id}/findings").json()}
    assert by_id["F1"]["standing"] == "NEEDS_REVIEW"  # wrong speaker: never ESTABLISHED
    assert by_id["F2"]["standing"] == "ASSUMPTION" and by_id["F2"]["quote"] == ""
    assert "No verified quotation" in by_id["F2"]["limitations"]
    assert by_id["H1"]["standing"] == "CONTRADICTED" and by_id["H1"]["relationship"] == "Contradictory"


def test_unavailable_sources_give_an_honest_empty_result(tmp_path):
    api, svc, _ = make(tmp_path, routes={"hn.algolia.com": httpx.ConnectError("offline")})
    run_id, run = start(api, svc)
    assert run["status"] == "completed" and run["rule"] == "REPEAT_NO_READABLE_SOURCES"
    assert api.get(f"/api/runs/{run_id}/findings").json() == []


# --- approval security -------------------------------------------------------------------------------

@pytest.fixture
def pending(tmp_path):
    api, svc, _ = make(tmp_path)
    run_id, _ = start(api, svc)
    approval = api.post(f"/api/runs/{run_id}/builder").json()["approval"]
    return api, svc, run_id, approval, svc.approvals.founder_path.read_text()


def decide(api, approval, run_id, key, choice="approve", fingerprint=None):
    return api.post(f"/api/approvals/{approval['id']}/decision", json={
        "run_id": run_id, "fingerprint": fingerprint or approval["fingerprint"], "decision": choice,
        "reason": "Reviewed", "founder_key": key})


def test_execution_without_approval_is_refused(pending):
    api, svc, run_id, approval, key = pending
    r = api.post(f"/api/approvals/{approval['id']}/execute", json={"run_id": run_id, "founder_key": key})
    assert r.status_code == 409 and not (svc.builder_root / run_id).exists()


@pytest.mark.parametrize("key", ["", "0" * 64, "not-a-key"])
def test_decision_without_the_founder_key_is_refused_and_recorded(pending, key):
    api, svc, run_id, approval, _ = pending
    assert decide(api, approval, run_id, key).status_code == 403
    assert api.get(f"/api/runs/{run_id}/approvals").json()[0]["status"] == "Pending"
    assert any(e["action"] == "approval_decision" and "capability" in e["outcome"]
               for e in api.get(f"/api/runs/{run_id}/audit").json())


def test_wrong_run_wrong_fingerprint_and_unknown_ids_are_refused(pending):
    api, svc, run_id, approval, key = pending
    assert decide(api, approval, "run-0000000000000000", key).status_code == 409
    assert decide(api, approval, run_id, key, fingerprint="0" * 64).status_code == 409
    assert api.post("/api/approvals/../../etc/execute", json={"run_id": run_id, "founder_key": key}).status_code == 404
    assert api.post(f"/api/approvals/{'f' * 32}/execute", json={"run_id": run_id, "founder_key": key}).status_code == 404
    assert api.get("/api/runs/..%2F..%2Fapprovals.sqlite3/findings").status_code == 404


def test_rejected_request_cannot_execute(pending):
    api, svc, run_id, approval, key = pending
    assert decide(api, approval, run_id, key, "reject").json()["status"] == "Rejected"
    r = api.post(f"/api/approvals/{approval['id']}/execute", json={"run_id": run_id, "founder_key": key})
    assert r.status_code == 409


def test_execution_needs_the_founder_key_and_cannot_be_replayed(pending):
    api, svc, run_id, approval, key = pending
    decide(api, approval, run_id, key)
    body = {"run_id": run_id, "founder_key": key}
    assert api.post(f"/api/approvals/{approval['id']}/execute", json=body | {"founder_key": "x"}).status_code == 403
    assert api.post(f"/api/approvals/{approval['id']}/execute", json=body).status_code == 200
    replay = api.post(f"/api/approvals/{approval['id']}/execute", json=body)
    assert replay.status_code == 409 and "consumed" in replay.json()["detail"]
    assert decide(api, approval, run_id, key).status_code == 409  # a used approval cannot be re-decided


def test_expired_requests_cannot_be_approved_or_executed(tmp_path):
    api, svc, _ = make(tmp_path, ttl=0.5)
    run_id, _ = start(api, svc)
    approval = api.post(f"/api/runs/{run_id}/builder").json()["approval"]
    time.sleep(0.7)
    assert api.get(f"/api/runs/{run_id}/approvals").json()[0]["status"] == "Expired"
    r = decide(api, approval, run_id, svc.approvals.founder_path.read_text())
    assert r.status_code == 409 and "expired" in r.json()["detail"]


def test_files_changed_on_disk_after_execution_are_flagged(pending):
    api, svc, run_id, approval, key = pending
    decide(api, approval, run_id, key)
    api.post(f"/api/approvals/{approval['id']}/execute", json={"run_id": run_id, "founder_key": key})
    page = next(Path(p) for p in (svc.builder_root / run_id).rglob("phase2_step1_validation-kit.md"))
    page.write_text("<script>alert(1)</script>", encoding="utf-8")
    arts = api.get(f"/api/runs/{run_id}/artifacts").json()
    assert all("differ from the approved snapshot" in a["status"] for a in arts)
    assert all("<script>alert(1)" not in a["content"] for a in arts)  # the approved snapshot is shown


def test_malicious_brief_text_is_escaped_in_the_landing_page(tmp_path):
    api, svc, _ = make(tmp_path)
    evil = BRIEF | {"idea": 'A web app <img src=x onerror="alert(1)"> that drafts release notes from pull requests.'}
    run_id, run = start(api, svc, evil)
    if run["decision"] != "GO":
        pytest.skip("landing page only exists after GO")
    api.post(f"/api/runs/{run_id}/builder")
    html = next(a for a in api.get(f"/api/runs/{run_id}/artifacts").json() if a["format"] == "html")
    assert "<img" not in html["content"] and "&lt;img" in html["content"]


# --- jobs ------------------------------------------------------------------------------------------

def test_duplicate_submission_returns_the_active_run_and_queue_is_bounded(tmp_path):
    gate = threading.Event()
    api, svc, _ = make(tmp_path, gate=gate, max_queued=2)
    first = api.post("/api/runs", json=BRIEF).json()
    again = api.post("/api/runs", json=BRIEF).json()
    assert again["created"] is False and again["run"]["id"] == first["run"]["id"]
    second = api.post("/api/runs", json=BRIEF | {"market": "Egypt"})
    assert second.status_code == 202
    third = api.post("/api/runs", json=BRIEF | {"market": "Europe"})
    assert third.status_code == 429
    statuses = {r["status"] for r in api.get("/api/runs").json()}
    assert statuses <= {"Queued", "Running"}
    gate.set()
    wait(svc, first["run"]["id"])


def test_missing_model_blocks_the_run_without_research(tmp_path):
    api, svc, model = make(tmp_path, installed=False)
    run_id, run = start(api, svc)
    assert run["status"] == "blocked" and "not downloaded" in run["error"] and model.calls == []
    assert {a["status"] for a in api.get(f"/api/runs/{run_id}/agents").json()} >= {"Blocked"}


def test_unreachable_ollama_blocks_the_run(tmp_path):
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)
    from llm import OllamaClient
    api, svc, _ = make(tmp_path)
    svc.jobs.client_factory = lambda: OllamaClient(TEST_SETTINGS, transport=httpx.MockTransport(refuse))
    run_id, run = start(api, svc)
    assert run["status"] == "blocked" and "not reachable" in run["error"]


def test_restart_marks_interrupted_runs(tmp_path):
    from app.api import BriefIn, to_founder_brief
    store = RunStore(tmp_path / ".venturelab" / "runs.sqlite3")
    brief = to_founder_brief(BriefIn.model_validate(BRIEF))
    store.create("run-aaaaaaaaaaaaaaaa", brief, "h", "full")
    store.update("run-aaaaaaaaaaaaaaaa", status="running")
    api, svc, _ = make(tmp_path)  # a new process: the job manager starts over the same store
    run = svc.runs.get("run-aaaaaaaaaaaaaaaa")
    assert run["status"] == "failed" and "Interrupted" in run["error"]
    assert api.get("/api/runs").json()[0]["status"] == "Failed"


def test_unknown_run_is_404(tmp_path):
    api, _, _ = make(tmp_path)
    for path in ("findings", "decision", "artifacts", "audit", "agents"):
        assert api.get(f"/api/runs/run-0123456789abcdef/{path}").status_code == 404


def test_a_run_waits_for_the_first_model_download_and_says_so(tmp_path):
    api, svc, model = make(tmp_path, installed=False, model_wait=5)
    svc.jobs.model_poll_s = 0.05
    run_id = api.post("/api/runs", json=BRIEF).json()["run"]["id"]
    deadline = time.time() + 5
    while "Waiting for the local model" not in svc.runs.get(run_id)["stage"]:
        assert time.time() < deadline
        time.sleep(0.02)
    assert svc.runs.get(run_id)["status"] == "running" and model.calls == []  # waiting, no research
    model.installed = True  # the download finishes
    run = wait(svc, run_id)
    assert run["status"] == "completed" and "queries" in model.calls


def test_a_run_is_blocked_with_an_explanation_if_the_model_never_arrives(tmp_path):
    api, svc, model = make(tmp_path, installed=False, model_wait=0.2)
    svc.jobs.model_poll_s = 0.05
    run_id, run = start(api, svc)
    assert run["status"] == "blocked" and "one-time model download" in run["error"] and model.calls == []
