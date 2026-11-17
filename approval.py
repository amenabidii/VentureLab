"""Authenticated local approvals; the OS account and authority files are trusted.

HMAC detects database-only tampering, not arbitrary code execution or an attacker
who can read the founder/signing keys or roll back all trusted filesystem state.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

from builder_models import ApprovalDecision, ApprovalRequest, ApprovalStatus, AuditEvent, BuilderResult
from builder_service import ArtifactBundle


class ApprovalError(RuntimeError):
    pass


def _secret(path: Path, create: bool) -> bytes:
    if path.is_symlink():
        raise ApprovalError("Authority files must not be symlinks")
    if create and not path.exists():
        try:
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stream:
                stream.write(secrets.token_hex(32).encode("ascii"))
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            pass
    try:
        value = path.read_bytes()
        if len(value) != 64 or any(c not in b"0123456789abcdef" for c in value):
            raise ValueError
        return value
    except (OSError, ValueError) as exc:
        raise ApprovalError("Authority file missing or invalid; never regenerate keys for existing state") from exc


DEFAULT_TTL_SECONDS = 2 * 60 * 60  # a request must be decided and executed within this window


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ApprovalStore:
    # Workflow authority is event-sourced in the SAME authenticated audit chain as
    # Builder authority. No mutable latest-record projection can revive a rejection.
    def _workflow_events(self, db):
        self._verify_audit(db)
        events = [json.loads(r[0]) for r in db.execute("SELECT event FROM audit ORDER BY sequence")]
        return [e for e in events if e["action"].startswith("workflow_")]

    def _workflow_event(self, db, action, payload, request=None, founder=False):
        self._event(db, "workflow_" + action, json.dumps(payload, sort_keys=True),
                    SimpleNamespace(**request) if request else None, founder=founder)

    def require_founder(self, token):
        if not self.verify_founder(token):
            error = ApprovalError("Founder capability required")
            self.record_failure("workflow_authentication", error)
            raise error

    @staticmethod
    def workflow_file(path):
        path = Path(path).absolute()
        if path.resolve() != path or not path.is_file():
            raise ApprovalError("Artifact missing or unsafe")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def workflow_requests(self):
        with self._connection() as db:
            db.execute("BEGIN")
            return [json.loads(e["outcome"])["request"] for e in self._workflow_events(db)
                    if e["action"] == "workflow_request"]

    @staticmethod
    def _check_workflow_action(action):
        if not isinstance(action, str):
            raise ApprovalError("Unsupported workflow action")
        if not re.fullmatch(r"(?:set_price:[a-zA-Z0-9_-]+|rehearse_after_repeat|rehearse_after_pivot|rehearse_without_validation|publish_store_page|enable_mock_delivery)", action):
            raise ApprovalError("Unsupported workflow action")

    def request_workflow(self, run_id, action, path, digest, *, expires=None):
        self._check_workflow_action(action)
        if self.workflow_file(path) != digest:
            raise ApprovalError("Artifact changed")
        request = dict(action_id=uuid4().hex, action_type=action, run_id=run_id,
                       artifact_identity=Path(path).name, artifact_sha256=digest,
                       destination=str(Path(path).absolute()))
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            self._workflow_event(db, "request", {"request": request, "status": "pending",
                "expires": expires if expires is not None else datetime.now(timezone.utc).timestamp() + self.ttl_seconds}, request)
        return request

    def decide_workflow(self, request, decision, reason, token):
        try:
            return self._decide_workflow(request, decision, reason, token)
        except (ApprovalError, OSError, ValueError) as exc:
            self.record_failure("workflow_decision_refused", exc)
            raise

    def _decide_workflow(self, request, decision, reason, token):
        self.require_founder(token)
        if decision not in ("approve", "reject"):
            raise ApprovalError("Invalid decision")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            events = self._workflow_events(db)
            created = next((json.loads(e["outcome"]) for e in events
                            if e["action"] == "workflow_request" and e["action_id"] == request["action_id"]), None)
            if not created or created["request"] != request:
                raise ApprovalError("Missing or mismatched request")
            if any(e["action"] == "workflow_decision" and e["action_id"] == request["action_id"] for e in events):
                raise ApprovalError("Request already decided; create a new request")
            if created["expires"] < datetime.now(timezone.utc).timestamp():
                raise ApprovalError("Request expired")
            if self.workflow_file(request["destination"]) != request["artifact_sha256"]:
                raise ApprovalError("Artifact changed")
            # Never include caller-supplied secrets or raw errors in the journal.
            self._workflow_event(db, "decision", {"decision": decision}, request, founder=True)

    def _workflow_authorized(self, events, request, *, replay=False):
        group = lambda action: "set_price" if action.startswith("set_price:") else action
        matching = [e for e in events if e["action"] == "workflow_request"
                    and e["run_id"] == request["run_id"] and group(e["action_type"]) == group(request["action_type"])
                    and e["destination"] == request["destination"]]
        if not matching or matching[-1]["action_id"] != request["action_id"]:
            return False
        created = json.loads(matching[-1]["outcome"])
        if created["request"] != request:
            return False
        decisions = [e for e in events if e["action"] == "workflow_decision" and e["action_id"] == request["action_id"]]
        persistent = request["action_type"].startswith(("set_price:", "rehearse_"))
        return bool(decisions and json.loads(decisions[-1]["outcome"])["decision"] == "approve"
                    and (persistent or replay or created["expires"] >= datetime.now(timezone.utc).timestamp())
                    and self.workflow_file(request["destination"]) == request["artifact_sha256"])

    def workflow_approved(self, request):
        with self._connection() as db:
            db.execute("BEGIN")
            events = self._workflow_events(db)
            failed = any(e["action"] == "workflow_failed" and request["action_id"] in
                         json.loads(e["outcome"])["approvals"] for e in events)
            if failed:
                return False
            completed = any(e["action"] == "workflow_completed" and request["action_id"] in
                            json.loads(e["outcome"])["approvals"] for e in events)
            return self._workflow_authorized(events, request, replay=completed)

    def execute_workflow(self, requests, token, callback):
        try:
            return self._execute_workflow(requests, token, callback)
        except (ApprovalError, OSError, ValueError) as exc:
            self.record_failure("workflow_execution_refused", exc)
            raise

    def _execute_workflow(self, requests, token, callback):
        """Atomically claim both launch approvals. Crash/failure consumes; success replays only the result."""
        self.require_founder(token)
        if sorted(r["action_type"] for r in requests) != ["enable_mock_delivery", "publish_store_page"] or len({r["run_id"] for r in requests}) != 1:
            raise ApprovalError("Launch requires both approvals for the same run")
        ids = sorted(r["action_id"] for r in requests)
        identity = hashlib.sha256(json.dumps(ids).encode()).hexdigest()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            events = self._workflow_events(db)
            done = next((json.loads(e["outcome"]) for e in events if e["action"] == "workflow_completed"
                         and json.loads(e["outcome"])["execution"] == identity), None)
            if not all(self._workflow_authorized(events, r, replay=bool(done)) for r in requests):
                raise ApprovalError("Missing, rejected, stale or expired workflow approval")
            if done:
                self._workflow_event(db, "replay", {"execution": identity}, founder=True)
                return done["result"]
            if any(e["action"] == "workflow_claimed" and set(ids).intersection(json.loads(e["outcome"])["approvals"]) for e in events):
                raise ApprovalError("Launch already claimed; in progress, interrupted or failed (consumed)")
            self._workflow_event(db, "claimed", {"execution": identity, "approvals": ids}, founder=True)
        try:
            result = callback()
        except BaseException:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                self._verify_audit(db)
                self._workflow_event(db, "failed", {"execution": identity, "approvals": ids})
            raise
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            self._workflow_event(db, "completed", {"execution": identity, "approvals": ids, "result": result}, founder=True)
        return result

    def import_workflow_legacy(self, state, run_id, resolve, token, *, apply=False):
        """Explicit per-run migration. Dry run by default; never used by normal execution.

        Legacy per-record MACs cannot prove a list was never truncated. The human
        must review that limitation before explicitly importing their local state.
        """
        self.require_founder(token)
        source = Path(state) / "workflow_approvals.json"
        key_path = Path(state) / "workflow.founder"
        if source.is_symlink() or key_path.is_symlink():
            raise ApprovalError("Unsafe legacy state")
        key = _secret(key_path, False)
        records = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
            raise ApprovalError("Invalid legacy records")
        # Validate the entire list before grouping: otherwise tampering with a
        # rejection's action/run could move it out of the history being imported.
        invalid_history = False
        for rec in records:
            body = json.dumps({k: rec.get(k) for k in ("run_id", "action", "sha256", "decision", "reason", "at")}, sort_keys=True)
            mac = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
            signature = rec.get("mac")
            if not isinstance(signature, str) or not hmac.compare_digest(signature, mac):
                invalid_history = True
        report, accepted, groups = [], [], {}
        for rec in records:
            if rec.get("run_id") == run_id:
                action = rec.get("action", "")
                if not isinstance(action, str):
                    report.append({"action": None, "status": "refused: malformed action"})
                    continue
                group = "set_price" if action.startswith("set_price:") else action
                groups.setdefault(group, []).append(rec)
        for group, rows in groups.items():
            last = rows[-1]
            status = "eligible"
            try:
                if invalid_history:
                    raise ApprovalError("invalid MAC in legacy history; entire import refused")
                if last.get("decision") != "approve":
                    raise ApprovalError("latest decision is not approval")
                self._check_workflow_action(last["action"])
                path = resolve(last["action"])
                if self.workflow_file(path) != last["sha256"]:
                    raise ApprovalError("stale SHA-256")
                expires = None
                if not last["action"].startswith(("set_price:", "rehearse_")):
                    expires = _parse_time(last["at"]).timestamp() + self.ttl_seconds
                    if expires < datetime.now(timezone.utc).timestamp():
                        raise ApprovalError("legacy execution approval expired; request fresh approval")
                accepted.append((last, path, expires))
            except (ApprovalError, ValueError, KeyError, OSError, RuntimeError) as exc:
                status = "refused: " + (str(exc) if isinstance(exc, ApprovalError) else type(exc).__name__)
            report.append({"action": last.get("action"), "sha256": last.get("sha256"), "status": status})
        marker = hashlib.sha256((str(source.absolute()) + run_id).encode()).hexdigest()
        if apply:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                events = self._workflow_events(db)
                if any(e["action"] == "workflow_import_started" and json.loads(e["outcome"])["import_id"] == marker for e in events):
                    raise ApprovalError("Legacy import already attempted for this run")
                if any(e["action"] == "workflow_request" and e["run_id"] == run_id for e in events):
                    raise ApprovalError("New approval history already exists for this run; legacy import refused")
                self._workflow_event(db, "import_started", {"import_id": marker}, founder=True)
            for rec, path, expires in accepted:
                req = self.request_workflow(run_id, rec["action"], path, rec["sha256"], expires=expires)
                self.decide_workflow(req, "approve", "Legacy signed founder decision", token)
            for row in report:
                if row["status"] == "eligible":
                    row["status"] = "imported"
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            self._workflow_event(db, "import_report", {"apply": apply, "run_id": run_id, "records": report}, founder=True)
        return report

    def __init__(self, database: Path, output_root: Path, ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self.database = Path(database).absolute()
        self.output_root = Path(output_root).absolute()
        if self.database.resolve() != self.database or self.output_root.resolve() != self.output_root:
            raise ApprovalError("Database and output paths must not contain symlinks or junctions")
        self.key_path = self.database.with_suffix(self.database.suffix + ".key")
        self.founder_path = self.database.with_suffix(self.database.suffix + ".founder")
        self.spent_root = self.database.with_suffix(self.database.suffix + ".spent")
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables and "metadata" not in tables:
                raise ApprovalError("Legacy unsigned database: preserve it and prepare new requests in a new state file")
            new = not tables
            self._key = _secret(self.key_path, new)
            if new:
                authority = _secret(self.founder_path, True)
                for statement in (
                    "CREATE TABLE approvals(action_id TEXT PRIMARY KEY, request TEXT NOT NULL, bundle TEXT NOT NULL, status TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0, mac TEXT NOT NULL)",
                    "CREATE TABLE audit(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,mac TEXT NOT NULL)",
                    "CREATE TABLE metadata(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL,mac TEXT NOT NULL)",
                ):
                    db.execute(statement)
                data = json.dumps({"version": 2, "store_id": uuid4().hex, "output_root": str(self.output_root),
                                   "founder_hash": hashlib.sha256(authority).hexdigest(), "audit_sequence": 0, "audit_mac": ""}, sort_keys=True)
                db.execute("INSERT INTO metadata VALUES(1,?,?)", (data, self._mac("metadata", data)))
            metadata = self._metadata(db)
            if metadata["version"] != 2 or metadata["output_root"] != str(self.output_root):
                raise ApprovalError("State version or destination differs from this store")
            self._verify_audit(db)

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.database, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _mac(self, domain: str, *values) -> str:
        data = json.dumps([domain, *values], ensure_ascii=True, separators=(",", ":")).encode()
        return hmac.new(self._key, data, hashlib.sha256).hexdigest()

    def _metadata(self, db) -> dict:
        row = db.execute("SELECT data,mac FROM metadata WHERE id=1").fetchone()
        if row is None or not hmac.compare_digest(row["mac"], self._mac("metadata", row["data"])):
            raise ApprovalError("Approval metadata integrity check failed")
        return json.loads(row["data"])

    def _save_metadata(self, db, metadata):
        data = json.dumps(metadata, sort_keys=True)
        db.execute("UPDATE metadata SET data=?,mac=? WHERE id=1", (data, self._mac("metadata", data)))

    def _verify_audit(self, db):
        metadata = self._metadata(db)
        if metadata["output_root"] != str(self.output_root):
            raise ApprovalError("Output destination differs from authenticated configuration")
        previous, sequence = "", 0
        for row in db.execute("SELECT * FROM audit ORDER BY sequence"):
            if row["sequence"] != sequence + 1 or not hmac.compare_digest(row["mac"], self._mac("audit", previous, row["event"])):
                raise ApprovalError("Audit integrity check failed")
            previous, sequence = row["mac"], row["sequence"]
        if (sequence, previous) != (metadata["audit_sequence"], metadata["audit_mac"]):
            raise ApprovalError("Audit history is missing or truncated")

    def _row(self, db, action_id):
        row = db.execute("SELECT * FROM approvals WHERE action_id=?", (action_id,)).fetchone()
        if row is not None:
            values = [row[key] for key in ("action_id", "request", "bundle", "status", "consumed")]
            if not hmac.compare_digest(row["mac"], self._mac("approval", *values)):
                raise ApprovalError("Approval record integrity check failed")
            if ApprovalRequest.model_validate_json(row["request"]).action_id != action_id:
                raise ApprovalError("Approval action identity mismatch")
        return row

    def _transition(self, db, row, status, consumed):
        values = [row["action_id"], row["request"], row["bundle"], status.value, consumed]
        db.execute("UPDATE approvals SET status=?,consumed=?,mac=? WHERE action_id=?",
                   (status.value, consumed, self._mac("approval", *values), row["action_id"]))

    def _event(self, db, action, outcome, request=None, bundle=None, *, action_id=None, founder=False):
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            agent="builder" if action in {"prepare_artifacts", "execute_artifacts"} else "approval",
            action=action, outcome=outcome, sources=[str(e.source_url) for e in bundle.brief.supporting_evidence] if bundle else [],
            model=bundle.model if bundle and action == "prepare_artifacts" else None,
            approved_by="founder" if founder else None, action_id=request.action_id if request else action_id,
            run_id=request.run_id if request else None, artifact_sha256=request.artifact_sha256 if request else None,
            artifact_identity=request.artifact_identity if request else None,
            action_type=request.action_type if request else None, destination=request.destination if request else None,
        ).model_dump_json()
        metadata = self._metadata(db)
        mac = self._mac("audit", metadata["audit_mac"], event)
        cursor = db.execute("INSERT INTO audit(event,mac) VALUES (?,?)", (event, mac))
        metadata.update(audit_sequence=cursor.lastrowid, audit_mac=mac)
        self._save_metadata(db, metadata)

    def record_failure(self, action: str, exception: Exception, action_id: str | None = None):
        """Persist a sanitized ingress failure, never the raw rejected input."""
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            self._event(db, action, f"failed: {type(exception).__name__}", action_id=action_id)

    def create(self, bundle: ArtifactBundle) -> ApprovalRequest:
        bundle = ArtifactBundle.model_validate_json(bundle.model_dump_json())
        action_id = uuid4().hex
        request = ApprovalRequest(action_id=action_id, action_type="generate_local_artifacts", run_id=bundle.run_id,
            artifact_identity=bundle.artifact_identity, artifact_sha256=bundle.fingerprint(),
            destination=str(self.output_root / bundle.run_id / action_id),
            description=("Write this exact experiment kit and landing-page concept locally. " if bundle.landing_page is not None
                         else "Write this exact experiment kit and interview guide locally (no landing page: the gate decision was not GO). ")
            + "Approval accepts proposed numerical experiment settings, not evidence of validation. No export, publishing or sending is authorized.")
        values = [action_id, request.model_dump_json(), bundle.model_dump_json(), request.status.value, 0]
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            db.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?)", (*values, self._mac("approval", *values)))
            self._event(db, "prepare_artifacts", "prepared_for_review", request, bundle)
            self._event(db, "request_approval", "pending", request)
        return request

    # --- integration helpers: expiry, founder check and listing ---------------------------

    def _created_at(self, db, action_id: str) -> datetime | None:
        for row in db.execute("SELECT event FROM audit ORDER BY sequence"):
            event = json.loads(row[0])
            if event.get("action") == "request_approval" and event.get("action_id") == action_id:
                return _parse_time(event["timestamp"])
        return None

    def expires_at(self, action_id: str) -> datetime | None:
        with self._connection() as db:
            db.execute("BEGIN")
            self._verify_audit(db)
            created = self._created_at(db, action_id)
        return None if created is None else datetime.fromtimestamp(created.timestamp() + self.ttl_seconds, timezone.utc)

    def _check_not_expired(self, db, action_id: str):
        created = self._created_at(db, action_id)
        if created is None or datetime.now(timezone.utc).timestamp() > created.timestamp() + self.ttl_seconds:
            raise ApprovalError("Approval request expired; prepare a new request")

    def verify_founder(self, founder_token: bytes | None) -> bool:
        with self._connection() as db:
            db.execute("BEGIN")
            return isinstance(founder_token, bytes) and hmac.compare_digest(
                hashlib.sha256(founder_token).hexdigest(), self._metadata(db)["founder_hash"])

    def list_requests(self, run_id: str | None = None) -> list[ApprovalRequest]:
        with self._connection() as db:
            db.execute("BEGIN")
            self._verify_audit(db)
            ids = [row[0] for row in db.execute("SELECT action_id FROM approvals ORDER BY rowid")]
            out = []
            for action_id in ids:
                row = self._row(db, action_id)
                request = ApprovalRequest.model_validate_json(row["request"]).model_copy(
                    update={"status": ApprovalStatus(row["status"])})
                if run_id is None or request.run_id == run_id:
                    out.append(request)
        return out

    def inspect(self, action_id: str) -> tuple[ApprovalRequest, ArtifactBundle]:
        with self._connection() as db:
            db.execute("BEGIN")
            self._verify_audit(db)
            row = self._row(db, action_id)
        if row is None:
            raise ApprovalError("Approval does not exist")
        request = ApprovalRequest.model_validate_json(row["request"]).model_copy(update={"status": ApprovalStatus(row["status"])})
        return request, ArtifactBundle.model_validate_json(row["bundle"])

    def decide(self, decision: ApprovalDecision, *, founder_token: bytes | None = None) -> ApprovalRequest:
        decision = ApprovalDecision.model_validate_json(decision.model_dump_json())
        error, request, authenticated = None, None, False
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            try:
                authenticated = isinstance(founder_token, bytes) and hmac.compare_digest(
                    hashlib.sha256(founder_token).hexdigest(), self._metadata(db)["founder_hash"])
                row = self._row(db, decision.action_id)
                request = ApprovalRequest.model_validate_json(row["request"]) if row else None
                if not authenticated:
                    raise ApprovalError("Founder capability required; actor text is not authorization")
                if row is None:
                    raise ApprovalError("Approval does not exist")
                if row["status"] != ApprovalStatus.PENDING.value or row["consumed"]:
                    raise ApprovalError("Only pending approvals can be decided")
                if decision.artifact_sha256 != request.artifact_sha256:
                    raise ApprovalError("Decision fingerprint differs from the requested artifact")
                self._check_not_expired(db, decision.action_id)
                if ArtifactBundle.model_validate_json(row["bundle"]).fingerprint() != request.artifact_sha256:
                    raise ApprovalError("Draft or renderer changed; prepare a new request")
                status = ApprovalStatus.APPROVED if decision.decision == "approve" else ApprovalStatus.REJECTED
                self._transition(db, row, status, 0)
                self._event(db, "approval_decision", f"{status.value}: {decision.reason}" if decision.reason else f"{status.value}: [No reason provided]", request, founder=True)
            except (ApprovalError, ValueError) as exc:
                error = str(exc) if isinstance(exc, ApprovalError) else "Invalid stored artifact"
                self._event(db, "approval_decision", error, request, action_id=decision.action_id, founder=authenticated)
        if error:
            raise ApprovalError(error)
        return self.inspect(decision.action_id)[0]

    def _publish(self, request: ApprovalRequest, files: dict[str, bytes]):
        # Defense in depth for direct calls: this helper is not an ungated writer.
        with self._connection() as db:
            db.execute("BEGIN")
            self._verify_audit(db)
            row = self._row(db, request.action_id)
            if row is None or row["status"] != ApprovalStatus.EXECUTING.value or row["consumed"] != 1:
                raise ApprovalError("Execution must first claim an approved action")
            recorded = ApprovalRequest.model_validate_json(row["request"])
            expected_files, digest = ArtifactBundle.model_validate_json(row["bundle"]).snapshot()
            if request != recorded or files != expected_files or digest != recorded.artifact_sha256:
                raise ApprovalError("Publication payload differs from the approved snapshot")
        # This ledger lives outside SQLite so replaying an old signed approved row fails.
        if self.spent_root.resolve() != self.spent_root:
            raise ApprovalError("Unsafe consumption ledger")
        self.spent_root.mkdir(mode=0o700, exist_ok=True)
        with (self.spent_root / request.action_id).open("xb") as stream:
            stream.write(request.artifact_sha256.encode("ascii"))
            stream.flush()
            os.fsync(stream.fileno())
        directory = Path(request.destination)
        if directory.resolve() != directory or not directory.is_relative_to(self.output_root):
            raise ApprovalError("Unsafe output destination")
        directory.parent.mkdir(parents=True, exist_ok=True)
        if directory.parent.resolve() != directory.parent or directory.exists():
            raise ApprovalError("Unsafe or existing output destination")
        stage = directory.parent / (".pending-" + uuid4().hex)
        stage.mkdir(mode=0o700)
        for name, data in files.items():
            if Path(name).name != name or not name.startswith("phase"):
                raise ApprovalError("Unsafe artifact filename")
            with (stage / name).open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        if directory.parent.resolve() != directory.parent or directory.exists():
            raise ApprovalError("Output destination changed during generation")
        stage.rename(directory)

    def execute(self, action_id: str, *, bundle: ArtifactBundle | None = None) -> BuilderResult:
        error, request, files = None, None, None
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            try:
                row = self._row(db, action_id)
                if row is None:
                    raise ApprovalError("Missing approval")
                request = ApprovalRequest.model_validate_json(row["request"])
                if row["status"] != ApprovalStatus.APPROVED.value or row["consumed"]:
                    raise ApprovalError("Approval is not approved or was already consumed")
                self._check_not_expired(db, action_id)
                try:
                    candidate = bundle if bundle is not None else ArtifactBundle.model_validate_json(row["bundle"])
                    candidate = ArtifactBundle.model_validate_json(candidate.model_dump_json())
                    files, digest = candidate.snapshot()
                    if (digest != request.artifact_sha256 or candidate.run_id != request.run_id
                            or candidate.artifact_identity != request.artifact_identity
                            or str(self.output_root / request.run_id / action_id) != request.destination):
                        raise ApprovalError("Artifact or destination changed after approval")
                except Exception:
                    self._transition(db, row, ApprovalStatus.FAILED, 1)
                    raise
                self._transition(db, row, ApprovalStatus.EXECUTING, 1)
                self._event(db, "execute_artifacts", "execution_started", request, founder=True)
            except Exception as exc:
                error = str(exc) if isinstance(exc, ApprovalError) else f"Invalid artifact: {type(exc).__name__}"
                self._event(db, "execute_artifacts", error, request, action_id=action_id)
        if error:
            raise ApprovalError(error)
        try:
            self._publish(request, files)
            result = BuilderResult(action_id=action_id, run_id=request.run_id, artifact_sha256=request.artifact_sha256,
                                   output_directory=request.destination, files=tuple(files))
        except Exception as exc:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                self._verify_audit(db)
                self._transition(db, self._row(db, action_id), ApprovalStatus.FAILED, 1)
                self._event(db, "execute_artifacts", f"failed_execution: {type(exc).__name__}", request, founder=True)
            raise ApprovalError("Local generation failed; approval consumed. Any .pending directory is incomplete, not a successful artifact.") from exc
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._verify_audit(db)
            self._transition(db, self._row(db, action_id), ApprovalStatus.EXECUTED, 1)
            self._event(db, "execute_artifacts", "executed", request, founder=True)
        return result

    def audit_events(self) -> list[dict]:
        with self._connection() as db:
            db.execute("BEGIN")
            self._verify_audit(db)
            return [json.loads(row[0]) for row in db.execute("SELECT event FROM audit ORDER BY sequence")]
