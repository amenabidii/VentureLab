"""SYNTHETIC artifacts and SIMULATED founder decisions; never touches real state."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import sqlite3
from threading import Event

import pytest

from approval import ApprovalError, ApprovalStore
from builder_models import AuditEvent


@pytest.fixture
def env(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.sqlite3", tmp_path / "out")
    path = tmp_path / "page.html"
    path.write_text("SYNTHETIC local artifact")
    return store, path, store.founder_path.read_bytes()


def request(env, action="publish_store_page", run="run-test", decide="approve"):
    store, path, key = env
    req = store.request_workflow(run, action, path, store.workflow_file(path))
    if decide:
        store.decide_workflow(req, decide, "SIMULATED", key)
    return req


def pair(env):
    return [request(env), request(env, "enable_mock_delivery")]


def test_pending_rejection_and_restart(env):
    store, path, key = env
    first = request(env)
    assert store.workflow_approved(first)
    pending = request(env, decide=None)
    assert not store.workflow_approved(first)
    assert not store.workflow_approved(pending)
    store.decide_workflow(pending, "reject", "SIMULATED", key)
    reopened = ApprovalStore(store.database, store.output_root)
    assert not reopened.workflow_approved(first)
    assert not reopened.workflow_approved(pending)
    for event in reopened.audit_events():
        AuditEvent.model_validate(event)


@pytest.mark.parametrize("sql", [
    "DELETE FROM audit WHERE sequence=(SELECT MAX(sequence) FROM audit)",
    "UPDATE audit SET event='{}' WHERE sequence=(SELECT MAX(sequence) FROM audit)",
])
def test_rejection_deletion_or_edit_fails_closed(env, sql):
    store, _, _ = env
    approved = request(env)
    request(env, decide="reject")
    with sqlite3.connect(store.database) as db:
        db.execute(sql)
    with pytest.raises(ApprovalError):
        store.workflow_approved(approved)
    with pytest.raises(ApprovalError):
        ApprovalStore(store.database, store.output_root)


@pytest.mark.parametrize("field,value", [("run_id", "another-run"), ("action_type", "enable_mock_delivery"),
                                          ("action_id", "unknown"), ("artifact_identity", "other")])
def test_binding_cannot_be_reused(env, field, value):
    store, _, _ = env
    approved = request(env)
    assert not store.workflow_approved(dict(approved, **{field: value}))


def test_changed_file_blocks_execution(env):
    store, path, key = env
    requests = pair(env)
    path.write_text("CHANGED SYNTHETIC artifact")
    with pytest.raises(ApprovalError):
        store.execute_workflow(requests, key, lambda: pytest.fail("must not execute"))


@pytest.mark.parametrize("token", [None, b"wrong"])
def test_missing_or_wrong_key(env, token):
    store, _, _ = env
    req = request(env, decide=None)
    with pytest.raises(ApprovalError):
        store.decide_workflow(req, "approve", "SIMULATED", token)
    with pytest.raises(ApprovalError):
        store.execute_workflow([req], token, lambda: pytest.fail("must not execute"))


def test_expiry_and_persistent_choices(env, monkeypatch):
    import approval
    store, _, key = env
    requests = pair(env)
    choice = request(env, "set_price:pro-8")
    pending = request(env, "rehearse_after_repeat", decide=None)
    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) + timedelta(hours=3)
    monkeypatch.setattr(approval, "datetime", Later)
    assert store.workflow_approved(choice)  # choice persists while exact file is unchanged
    with pytest.raises(ApprovalError, match="expired"):
        store.execute_workflow(requests, key, lambda: None)
    with pytest.raises(ApprovalError, match="expired"):
        store.decide_workflow(pending, "approve", "SIMULATED", key)


def test_concurrent_claim_and_idempotent_restart(env):
    store, _, key = env
    requests = pair(env)
    entered, release = Event(), Event()
    calls = []
    def execute():
        calls.append(True)
        entered.set()
        assert release.wait(10)
        return {"mocked": True}
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(store.execute_workflow, requests, key, execute)
        assert entered.wait(10)
        try:
            with pytest.raises(ApprovalError, match="claimed"):
                store.execute_workflow(requests, key, execute)
        finally:
            release.set()
        assert first.result() == {"mocked": True}
    reopened = ApprovalStore(store.database, store.output_root)
    assert reopened.execute_workflow(requests, key, execute) == {"mocked": True}
    assert len(calls) == 1


def test_failed_execution_stays_consumed(env):
    store, _, key = env
    requests = pair(env)
    def fail():
        raise OSError("SIMULATED write failure")
    with pytest.raises(OSError):
        store.execute_workflow(requests, key, fail)
    assert not store.workflow_approved(requests[0])
    with pytest.raises(ApprovalError, match="consumed"):
        store.execute_workflow(requests, key, lambda: None)
    assert store.audit_events()[-1]["action"] == "workflow_execution_refused"


def test_price_choice_supersedes_other_option_even_when_rejected(env):
    store, _, _ = env
    original = request(env, "set_price:pro-8")
    replacement = request(env, "set_price:pro-4", decide="reject")
    assert not store.workflow_approved(original)
    assert not store.workflow_approved(replacement)


def test_missing_approval_and_mixed_runs_block(env):
    store, _, key = env
    with pytest.raises(ApprovalError):
        store.execute_workflow([], key, lambda: pytest.fail("must not execute"))
    requests = [request(env), request(env, "enable_mock_delivery", run="other-run")]
    with pytest.raises(ApprovalError, match="same run"):
        store.execute_workflow(requests, key, lambda: pytest.fail("must not execute"))


@pytest.mark.parametrize("fault", [None, "mac", "stale", "rejected"])
def test_explicit_legacy_import(env, fault):
    store, path, token = env
    state = store.database.parent
    key = b"a" * 64
    (state / "workflow.founder").write_bytes(key)
    rec = dict(run_id="run-test", action="set_price:pro-8", sha256=store.workflow_file(path),
               decision="reject" if fault == "rejected" else "approve", reason="SIMULATED", at="2026-11-17T00:00:00Z")
    rec["mac"] = hmac.new(key, json.dumps(rec, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    if fault == "mac":
        rec["mac"] = "0" * 64
    if fault == "stale":
        path.write_text("CHANGED")
    (state / "workflow_approvals.json").write_text(json.dumps([rec]))
    preview = store.import_workflow_legacy(state, "run-test", lambda _: path, token)
    assert store.workflow_requests() == []
    result = store.import_workflow_legacy(state, "run-test", lambda _: path, token, apply=True)
    if fault is None:
        assert preview[0]["status"] == "eligible"
        assert result[0]["status"] == "imported"
        assert store.workflow_approved(store.workflow_requests()[0])
    else:
        assert result[0]["status"].startswith("refused")
        assert not store.workflow_requests()
    with pytest.raises(ApprovalError, match="already attempted"):
        store.import_workflow_legacy(state, "run-test", lambda _: path, token, apply=True)


@pytest.mark.parametrize("expired", [False, True])
def test_legacy_execution_import_preserves_expiry(env, expired):
    store, path, token = env
    state = store.database.parent
    key = b"b" * 64
    (state / "workflow.founder").write_bytes(key)
    at = datetime.now(timezone.utc) - timedelta(hours=3 if expired else 1)
    rec = dict(run_id="run-test", action="publish_store_page", sha256=store.workflow_file(path),
               decision="approve", reason="SIMULATED", at=at.isoformat())
    rec["mac"] = hmac.new(key, json.dumps(rec, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    (state / "workflow_approvals.json").write_text(json.dumps([rec]))
    report = store.import_workflow_legacy(state, "run-test", lambda _: path, token, apply=True)
    if expired:
        assert "expired" in report[0]["status"] and not store.workflow_requests()
    else:
        assert report[0]["status"] == "imported"
        created = next(json.loads(e["outcome"]) for e in store.audit_events() if e["action"] == "workflow_request")
        assert created["expires"] == at.timestamp() + store.ttl_seconds


def test_legacy_rejection_cannot_be_moved_to_another_action(env):
    store, path, token = env
    state = store.database.parent
    key = b"c" * 64
    (state / "workflow.founder").write_bytes(key)
    records = []
    for decision in ("approve", "reject"):
        rec = dict(run_id="run-test", action="set_price:pro-8", sha256=store.workflow_file(path),
                   decision=decision, reason="SIMULATED", at="2026-11-17T00:00:00Z")
        rec["mac"] = hmac.new(key, json.dumps(rec, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        records.append(rec)
    records[-1]["action"] = "enable_mock_delivery"
    (state / "workflow_approvals.json").write_text(json.dumps(records))
    report = store.import_workflow_legacy(state, "run-test", lambda _: path, token, apply=True)
    assert all("invalid MAC" in r["status"] for r in report)
    assert not store.workflow_requests()
