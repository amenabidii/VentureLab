"""Security regression tests. Founder authorization is explicitly SIMULATED."""
import json
from pathlib import Path
import sqlite3
import subprocess
import os

import pytest

from approval import ApprovalError, ApprovalStore
from builder_models import ApprovalDecision, ApprovalStatus
from tests.test_m3_audit import sample_bundle


@pytest.fixture
def context(tmp_path):
    store = ApprovalStore(tmp_path / "state.db", tmp_path / "outputs")
    request = store.create(sample_bundle())
    return store, request


def approve(store, request):
    return store.decide(ApprovalDecision(action_id=request.action_id, artifact_sha256=request.artifact_sha256,
        decision="approve", actor="founder", reason="SIMULATED security-test founder"),
        founder_token=store.founder_path.read_bytes())


@pytest.mark.parametrize("token", [None, b"forged capability"])
def test_direct_decision_requires_founder_capability(context, token):
    store, request = context
    with pytest.raises(ApprovalError, match="capability"):
        store.decide(ApprovalDecision(action_id=request.action_id, artifact_sha256=request.artifact_sha256,
            decision="approve", actor="founder", reason="SIMULATED unauthorized caller"), founder_token=token)
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.PENDING
    event = store.audit_events()[-1]
    assert event["approved_by"] is None and event["artifact_sha256"] == request.artifact_sha256


def test_direct_writer_call_does_not_bypass_approval(context):
    store, request = context
    with pytest.raises(ApprovalError):
        store._publish(request, sample_bundle().files())
    assert not Path(request.destination).exists()


@pytest.mark.parametrize("column,value", [("status", "approved"), ("consumed", 0), ("bundle", "{}"), ("request", "{}"), ("mac", "0" * 64)])
def test_signed_record_fields_cannot_be_modified(context, column, value):
    store, request = context
    # For consumed, first reach a different signed value.
    if column == "consumed":
        approve(store, request)
        store.execute(request.action_id)
    with sqlite3.connect(store.database) as db:
        db.execute(f"UPDATE approvals SET {column}=? WHERE action_id=?", (value, request.action_id))
    with pytest.raises(ApprovalError, match="integrity"):
        store.execute(request.action_id)


def test_row_copy_cannot_authorize_different_action(context):
    store, request = context
    approve(store, request)
    with sqlite3.connect(store.database) as db:
        db.execute("INSERT INTO approvals SELECT 'other',request,bundle,status,consumed,mac FROM approvals WHERE action_id=?", (request.action_id,))
    with pytest.raises(ApprovalError, match="integrity"):
        store.execute("other")


def test_replay_old_signed_approved_row_blocked_by_consumption_ledger(context, tmp_path):
    store, request = context
    approve(store, request)
    with sqlite3.connect(store.database) as db:
        old = db.execute("SELECT status,consumed,mac FROM approvals WHERE action_id=?", (request.action_id,)).fetchone()
    store.execute(request.action_id)
    destination = Path(request.destination)
    archive = tmp_path / "already-generated"
    assert destination.is_relative_to(tmp_path) and archive.is_relative_to(tmp_path)
    destination.rename(archive)
    with sqlite3.connect(store.database) as db:
        db.execute("UPDATE approvals SET status=?,consumed=?,mac=? WHERE action_id=?", (*old, request.action_id))
    with pytest.raises(ApprovalError, match="consumed"):
        store.execute(request.action_id)
    assert not destination.exists() and archive.is_dir()


@pytest.mark.parametrize("operation", ["UPDATE audit SET event='{}' WHERE sequence=1", "DELETE FROM audit WHERE sequence=1", "DELETE FROM audit WHERE sequence=(SELECT MAX(sequence) FROM audit)"])
def test_audit_tamper_or_truncation_fails_closed(context, operation):
    store, request = context
    approve(store, request)
    with sqlite3.connect(store.database) as db:
        db.execute(operation)
    with pytest.raises(ApprovalError, match="Audit"):
        store.execute(request.action_id)
    assert not Path(request.destination).exists()


def test_metadata_tamper_fails_closed(context):
    store, request = context
    with sqlite3.connect(store.database) as db:
        db.execute("UPDATE metadata SET data='{}'")
    with pytest.raises(ApprovalError, match="metadata"):
        store.execute(request.action_id)


def test_signed_rejection_cannot_be_executed(context):
    store, request = context
    store.decide(ApprovalDecision(action_id=request.action_id, artifact_sha256=request.artifact_sha256,
        decision="reject", actor="founder", reason="SIMULATED rejection"), founder_token=store.founder_path.read_bytes())
    with pytest.raises(ApprovalError):
        store.execute(request.action_id)
    assert store.audit_events()[-1]["artifact_sha256"] == request.artifact_sha256


def test_error_mid_write_leaves_no_final_artifact_and_cannot_retry(context, monkeypatch):
    store, request = context
    approve(store, request)
    original = Path.open
    def fail_second_file(path, *args, **kwargs):
        if path.name == "phase2_step1_validation-kit.md" and args and args[0] == "xb":
            raise OSError("SIMULATED disk failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_second_file)
    with pytest.raises(ApprovalError, match="generation failed"):
        store.execute(request.action_id)
    assert not Path(request.destination).exists()
    assert list(Path(request.destination).parent.glob(".pending-*"))
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.FAILED
    with pytest.raises(ApprovalError):
        store.execute(request.action_id)


def test_renderer_unexpected_error_consumes_authority(context, monkeypatch):
    store, request = context
    approve(store, request)
    import builder_service
    def broken(_):
        raise RuntimeError("SIMULATED renderer failure")
    monkeypatch.setattr(builder_service, "render_landing_page", broken)
    with pytest.raises(ApprovalError):
        store.execute(request.action_id)
    assert store.inspect(request.action_id)[0].status == ApprovalStatus.FAILED


def test_legacy_unsigned_database_not_silently_upgraded(tmp_path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE approvals(action_id TEXT)")
    with pytest.raises(ApprovalError, match="Legacy"):
        ApprovalStore(database, tmp_path / "outputs")
    assert not database.with_suffix(".db.key").exists()


def test_output_parent_symlink_or_junction_is_blocked(context, tmp_path):
    store, request = context
    approve(store, request)
    outside = tmp_path / "outside-output-root"
    outside.mkdir()
    store.output_root.mkdir()
    link = store.output_root / request.run_id
    if os.name == "nt":
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"New-Item -ItemType Junction -Path {quote(link)} -Target {quote(outside)} | Out-Null"], check=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ApprovalError):
        store.execute(request.action_id)
    assert not list(outside.iterdir())


def test_runtime_output_root_change_blocked(context, tmp_path):
    store, request = context
    approve(store, request)
    store.output_root = tmp_path / "different"
    with pytest.raises(ApprovalError, match="destination"):
        store.execute(request.action_id)
