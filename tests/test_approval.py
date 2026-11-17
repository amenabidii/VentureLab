"""Actual local persistence and I/O; founder decisions are simulated in tests only."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3

import pytest

from approval import ApprovalError, ApprovalStore
from builder_models import ApprovalDecision, ApprovalStatus, AuditEvent, BuilderInput, LandingPageSpec
from builder_service import prepare


@pytest.fixture
def bundle():
    data = json.loads((Path(__file__).parent / "fixtures/builder_input.json").read_text())
    return prepare(BuilderInput.model_validate(data["brief"]), LandingPageSpec.model_validate(data["landing_page"]))


@pytest.fixture
def store(tmp_path):
    return ApprovalStore(tmp_path / "state.sqlite3", tmp_path / "outputs")


def decide(store, request, decision="approve", digest=None):
    return store.decide(ApprovalDecision(action_id=request.action_id, artifact_sha256=digest or request.artifact_sha256,
                                        decision=decision, actor="founder", reason="SIMULATED founder decision in unit test"))


def test_approval_creation(store, bundle):
    request = store.create(bundle)
    assert request.status == ApprovalStatus.PENDING
    assert request.artifact_sha256 == bundle.fingerprint()
    assert request.run_id == bundle.run_id
    assert request.artifact_identity == bundle.artifact_identity
    assert not store.output_root.exists()


@pytest.mark.parametrize("decision", [None, "reject"])
def test_pending_or_rejected_blocks(store, bundle, decision):
    request = store.create(bundle)
    if decision:
        decide(store, request, decision)
    with pytest.raises(ApprovalError):
        store.execute(request.action_id)
    assert not store.output_root.exists()
    assert store.audit_events()[-1]["action"] == "execute_artifacts"


def test_missing_approval_audited(store):
    with pytest.raises(ApprovalError, match="Missing"):
        store.execute("missing")
    assert store.audit_events()[-1]["action_id"] == "missing"


def test_wrong_decision_hash(store, bundle):
    request = store.create(bundle)
    with pytest.raises(ApprovalError, match="fingerprint"):
        decide(store, request, digest="0" * 64)
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.PENDING


def test_change_after_approval_invalidates_authority(store, bundle):
    request = store.create(bundle)
    decide(store, request)
    altered = bundle.model_copy(update={"landing_page": bundle.landing_page.model_copy(update={"headline": "Changed proposal"})})
    with pytest.raises(ApprovalError, match="changed"):
        store.execute(request.action_id, bundle=altered)
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.FAILED
    with pytest.raises(ApprovalError):
        store.execute(request.action_id, bundle=bundle)
    assert not store.output_root.exists()


def test_different_action_not_authorized(store, bundle):
    first, second = store.create(bundle), store.create(bundle)
    decide(store, first)
    with pytest.raises(ApprovalError):
        store.execute(second.action_id)


def test_different_destination_not_authorized(store, bundle, tmp_path):
    request = store.create(bundle)
    decide(store, request)
    other = ApprovalStore(store.database, tmp_path / "elsewhere")
    with pytest.raises(ApprovalError, match="destination"):
        other.execute(request.action_id)


def test_generate_once_persisted_and_audit_compatible(store, bundle):
    request = store.create(bundle)
    decide(store, request)
    reopened = ApprovalStore(store.database, store.output_root)
    result = reopened.execute(request.action_id)
    for name, content in bundle.files().items():
        assert (Path(result.output_directory) / name).read_bytes() == content
    with pytest.raises(ApprovalError):
        reopened.execute(request.action_id)
    for event in store.audit_events():
        AuditEvent.model_validate(event)
        assert {"timestamp", "agent", "action", "sources", "model", "cost", "approved_by"} <= event.keys()
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.EXECUTED


def test_concurrent_execution_one_winner(store, bundle):
    request = store.create(bundle)
    decide(store, request)
    def run(_):
        try:
            store.execute(request.action_id)
            return True
        except ApprovalError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [False, True]


def test_failed_write_consumes_approval(store, bundle):
    request = store.create(bundle)
    decide(store, request)
    Path(request.destination).mkdir(parents=True)
    with pytest.raises(ApprovalError, match="generation failed"):
        store.execute(request.action_id)
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.FAILED
    assert "failed_execution" in store.audit_events()[-1]["outcome"]


def test_decision_cannot_be_changed(store, bundle):
    request = store.create(bundle)
    decide(store, request, "reject")
    with pytest.raises(ApprovalError):
        decide(store, request)


def test_renderer_change_invalidates_approval(store, bundle, monkeypatch):
    request = store.create(bundle)
    decide(store, request)
    import builder_service
    original = builder_service.render_landing_page
    monkeypatch.setattr(builder_service, "render_landing_page", lambda spec: original(spec) + "\n")
    with pytest.raises(ApprovalError, match="changed"):
        store.execute(request.action_id)


def test_interrupted_execution_remains_consumed(store, bundle):
    request = store.create(bundle)
    decide(store, request)
    with sqlite3.connect(store.database) as db:
        db.execute("UPDATE approvals SET status='executing',consumed=1 WHERE action_id=?", (request.action_id,))
    with pytest.raises(ApprovalError):
        store.execute(request.action_id)


def test_unknown_action_type_rejected(bundle):
    from builder_models import ApprovalRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ApprovalRequest(action_id="x", run_id=bundle.run_id, artifact_identity="x", artifact_sha256=bundle.fingerprint(),
                        description="Publish", destination="elsewhere", action_type="publish")


def test_missing_decision_is_audited(store):
    with pytest.raises(ApprovalError):
        store.decide(ApprovalDecision(action_id="missing", artifact_sha256="0" * 64,
                                     decision="reject", actor="founder", reason="SIMULATED test decision"))
    assert store.audit_events()[-1]["action_id"] == "missing"


def test_stored_draft_change_before_decision_blocked(store, bundle):
    request = store.create(bundle)
    altered = bundle.model_copy(update={"artifact_identity": "different"})
    with sqlite3.connect(store.database) as db:
        db.execute("UPDATE approvals SET bundle=? WHERE action_id=?", (altered.model_dump_json(), request.action_id))
    with pytest.raises(ApprovalError, match="changed"):
        decide(store, request)
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.PENDING
