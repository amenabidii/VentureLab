"""Persistent, one-use founder approvals for local artifact generation only.

Trust boundary: the local OS user is the founder. No public HTTP approval endpoint
is exposed. Agents may prepare requests; only the founder-facing CLI calls decide.
Do not expose this service remotely without authentication and authorization.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from builder_models import ApprovalDecision, ApprovalRequest, ApprovalStatus, AuditEvent, BuilderResult
from builder_service import ArtifactBundle


class ApprovalError(RuntimeError):
    pass


class ApprovalStore:
    def __init__(self, database: Path, output_root: Path):
        self.database = Path(database).resolve()
        self.output_root = Path(output_root).resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS approvals (
                    action_id TEXT PRIMARY KEY, request TEXT NOT NULL, bundle TEXT NOT NULL,
                    status TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL
                );
            ''')

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.database, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _event(db, action: str, outcome: str, request: ApprovalRequest | None = None,
               bundle: ArtifactBundle | None = None, *, action_id: str | None = None,
               founder: bool = False):
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            agent="builder" if action in {"prepare_artifacts", "execute_artifacts"} else "approval",
            action=action, outcome=outcome, sources=[str(e.source_url) for e in bundle.brief.supporting_evidence] if bundle else [],
            model=bundle.model if bundle and action == "prepare_artifacts" else None,
            approved_by="founder" if founder else None,
            action_id=request.action_id if request else action_id,
            run_id=request.run_id if request else None,
        )
        db.execute("INSERT INTO audit(event) VALUES (?)", (event.model_dump_json(),))

    def create(self, bundle: ArtifactBundle) -> ApprovalRequest:
        bundle = ArtifactBundle.model_validate_json(bundle.model_dump_json())
        if bundle.run_id != bundle.brief.run_id:
            raise ValueError("Bundle and input run IDs differ")
        action_id = uuid4().hex
        request = ApprovalRequest(
            action_id=action_id, action_type="generate_local_artifacts", run_id=bundle.run_id,
            artifact_identity=bundle.artifact_identity, artifact_sha256=bundle.fingerprint(),
            destination=str(self.output_root / bundle.run_id / action_id),
            description="Write this exact experiment kit and landing-page concept locally. Approval accepts the proposed experiment thresholds, not evidence of validation. No export, publishing or sending is authorized.",
        )
        with self._connection() as db:
            db.execute("INSERT INTO approvals(action_id,request,bundle,status) VALUES (?,?,?,?)",
                       (action_id, request.model_dump_json(), bundle.model_dump_json(), request.status.value))
            self._event(db, "prepare_artifacts", "prepared_for_review", request, bundle)
            self._event(db, "request_approval", "pending", request)
        return request

    def inspect(self, action_id: str) -> tuple[ApprovalRequest, ArtifactBundle]:
        with self._connection() as db:
            row = db.execute("SELECT * FROM approvals WHERE action_id=?", (action_id,)).fetchone()
        if row is None:
            raise ApprovalError("Approval does not exist")
        request = ApprovalRequest.model_validate_json(row["request"]).model_copy(update={"status": ApprovalStatus(row["status"])})
        return request, ArtifactBundle.model_validate_json(row["bundle"])

    def decide(self, decision: ApprovalDecision) -> ApprovalRequest:
        decision = ApprovalDecision.model_validate_json(decision.model_dump_json())
        error = None
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM approvals WHERE action_id=?", (decision.action_id,)).fetchone()
            request = ApprovalRequest.model_validate_json(row["request"]) if row else None
            if row is None:
                error = "Approval does not exist"
            elif row["status"] != ApprovalStatus.PENDING.value:
                error = "Only pending approvals can be decided"
            elif decision.artifact_sha256 != request.artifact_sha256:
                error = "Decision fingerprint differs from the requested artifact"
            elif ArtifactBundle.model_validate_json(row["bundle"]).fingerprint() != request.artifact_sha256:
                error = "Draft or renderer changed; prepare a new approval request"
            if error:
                self._event(db, "approval_decision", error, request, action_id=decision.action_id, founder=True)
            else:
                status = ApprovalStatus.APPROVED if decision.decision == "approve" else ApprovalStatus.REJECTED
                db.execute("UPDATE approvals SET status=? WHERE action_id=?", (status.value, decision.action_id))
                self._event(db, "approval_decision", f"{status.value}: {decision.reason}", request, founder=True)
        if error:
            raise ApprovalError(error)
        return self.inspect(decision.action_id)[0]

    def execute(self, action_id: str, *, bundle: ArtifactBundle | None = None) -> BuilderResult:
        """Atomically consume authority before I/O. A crash cannot authorize a retry.

        An interrupted action remains executing/consumed. A new reviewed request is
        required. Files may remain after a write failure; they never imply success.
        """
        error = None
        request = None
        files = None
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM approvals WHERE action_id=?", (action_id,)).fetchone()
            if row is None:
                error = "Missing approval"
            else:
                request = ApprovalRequest.model_validate_json(row["request"])
                if row["status"] != ApprovalStatus.APPROVED.value or row["consumed"]:
                    error = "Approval is not approved or was already consumed"
                else:
                    try:
                        candidate = bundle if bundle is not None else ArtifactBundle.model_validate_json(row["bundle"])
                        candidate = ArtifactBundle.model_validate_json(candidate.model_dump_json())
                        expected = self.output_root / request.run_id / action_id
                        if (candidate.fingerprint() != request.artifact_sha256
                                or candidate.run_id != request.run_id
                                or candidate.artifact_identity != request.artifact_identity
                                or str(expected) != request.destination):
                            raise ApprovalError("Artifact or destination changed after approval")
                        files = candidate.files()
                    except (ValueError, ApprovalError) as exc:
                        error = str(exc)
                        db.execute("UPDATE approvals SET status=?,consumed=1 WHERE action_id=?", (ApprovalStatus.FAILED.value, action_id))
            if error:
                self._event(db, "execute_artifacts", error, request, action_id=action_id)
            else:
                db.execute("UPDATE approvals SET status=?,consumed=1 WHERE action_id=?", (ApprovalStatus.EXECUTING.value, action_id))
                self._event(db, "execute_artifacts", "execution_started", request, founder=True)
        if error:
            raise ApprovalError(error)
        try:
            directory = Path(request.destination)
            # Never follow symlinks/junctions beneath the configured output root.
            if directory.resolve() != directory or not directory.is_relative_to(self.output_root):
                raise ApprovalError("Unsafe output destination")
            directory.mkdir(parents=True, exist_ok=False)
            for name, data in files.items():
                with (directory / name).open("xb") as stream:
                    stream.write(data)
            result = BuilderResult(action_id=action_id, run_id=request.run_id,
                                   artifact_sha256=request.artifact_sha256,
                                   output_directory=str(directory), files=tuple(files))
        except Exception as exc:
            with self._connection() as db:
                db.execute("UPDATE approvals SET status=? WHERE action_id=?", (ApprovalStatus.FAILED.value, action_id))
                self._event(db, "execute_artifacts", f"failed_execution: {type(exc).__name__}", request, founder=True)
            raise ApprovalError("Local generation failed; approval consumed. Inspect local files and create a new request.") from exc
        with self._connection() as db:
            db.execute("UPDATE approvals SET status=? WHERE action_id=?", (ApprovalStatus.EXECUTED.value, action_id))
            self._event(db, "execute_artifacts", "executed", request, founder=True)
        return result

    def audit_events(self) -> list[dict]:
        with self._connection() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT event FROM audit ORDER BY sequence")]
