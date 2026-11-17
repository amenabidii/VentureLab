"""Background execution of Discover runs for the web application.

- Run records live in a small SQLite file (`<state>/runs.sqlite3`), so the run list,
  statuses and outputs survive a restart. The work queue itself is in memory: a run
  that was queued or running when the process stopped is marked `failed` with the
  reason "interrupted", never silently resumed or reported as finished.
- One worker thread runs one analysis at a time (local CPU inference); at most
  `max_queued` runs may wait. Further submissions are refused, not dropped.
- An identical brief that is already queued or running returns that run instead of
  starting a duplicate.
- States: queued -> running -> completed | failed | blocked. `blocked` means the run
  could not start (the model or Ollama is unavailable); nothing was inferred.
- Progress is read from the audit entries the pipeline writes (the same records that
  go to decision_log.json), so the stage shown is what actually happened.
"""

from __future__ import annotations

import hashlib
import json
import queue
import sqlite3
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agents.investigator import FULL, QUICK
from brief import FounderBrief, screen_brief
from gates import pre_research_stop
from llm import LLMError, OllamaClient
from sources import SourceFetcher

STATES = ("queued", "running", "completed", "failed", "blocked")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class QueueFull(RuntimeError):
    pass


class RunStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS runs(
                id TEXT PRIMARY KEY, created TEXT NOT NULL, updated TEXT NOT NULL, status TEXT NOT NULL,
                stage TEXT NOT NULL, title TEXT NOT NULL, brief TEXT NOT NULL, brief_hash TEXT NOT NULL,
                effort TEXT NOT NULL, error TEXT, decision TEXT, rule TEXT, progress TEXT NOT NULL,
                finished TEXT)""")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, run_id: str, brief: FounderBrief, brief_hash: str, effort: str) -> dict[str, Any]:
        t = now()
        with self._lock, self._db() as db:
            db.execute("INSERT INTO runs(id,created,updated,status,stage,title,brief,brief_hash,effort,progress)"
                       " VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (run_id, t, t, "queued", "Waiting for the worker", brief.idea[:120],
                        brief.model_dump_json(), brief_hash, effort, "[]"))
        return self.get(run_id)

    def update(self, run_id: str, **fields: Any) -> None:
        fields["updated"] = now()
        keys = ", ".join(f"{k}=?" for k in fields)
        with self._lock, self._db() as db:
            db.execute(f"UPDATE runs SET {keys} WHERE id=?", (*fields.values(), run_id))

    def add_progress(self, run_id: str, step: dict[str, Any], stage: str) -> None:
        with self._lock, self._db() as db:
            row = db.execute("SELECT progress FROM runs WHERE id=?", (run_id,)).fetchone()
            steps = json.loads(row["progress"]) if row else []
            steps.append(step)
            db.execute("UPDATE runs SET progress=?, stage=?, updated=? WHERE id=?",
                       (json.dumps(steps[-200:]), stage, now(), run_id))

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return None if row is None else {**dict(row), "progress": json.loads(row["progress"])}

    def list(self) -> list[dict[str, Any]]:
        with self._db() as db:
            rows = db.execute("SELECT * FROM runs ORDER BY created DESC, id DESC").fetchall()
        return [{**dict(r), "progress": json.loads(r["progress"])} for r in rows]

    def active_with_hash(self, brief_hash: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute("SELECT id FROM runs WHERE brief_hash=? AND status IN ('queued','running')",
                             (brief_hash,)).fetchone()
        return None if row is None else self.get(row["id"])

    def count_active(self) -> int:
        with self._db() as db:
            return db.execute("SELECT COUNT(*) FROM runs WHERE status IN ('queued','running')").fetchone()[0]

    def mark_interrupted(self) -> int:
        """Runs left queued/running by a previous process did not finish; say so."""
        with self._lock, self._db() as db:
            cur = db.execute("UPDATE runs SET status='failed', stage='Interrupted', finished=?, updated=?,"
                             " error='Interrupted: the application stopped before this run finished. It was not "
                             "resumed and has no completed result.' WHERE status IN ('queued','running')",
                             (now(), now()))
            return cur.rowcount


def brief_hash(brief: FounderBrief, effort: str) -> str:
    return hashlib.sha256((brief.model_dump_json() + effort).encode()).hexdigest()


AGENT_STAGES = {"orchestrator": "Starting", "investigator": "Investigator", "challenger": "Challenger",
                "gate": "Judge (deterministic rules)", "counterfactual": "Judge (counterfactual)"}


@dataclass
class JobManager:
    store: RunStore
    model: str
    out_root: Path
    log_path: Path
    client_factory: Callable[[], OllamaClient]
    fetcher_factory: Callable[[], SourceFetcher]
    max_queued: int = 3
    # On a fresh machine the model is still downloading when the app starts. A run waits
    # for it (and says so) for up to this many seconds before it is blocked.
    model_wait_s: float = 900
    model_poll_s: float = 15

    def __post_init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._submit_lock = threading.Lock()
        self.interrupted = self.store.mark_interrupted()
        self._thread = threading.Thread(target=self._worker, name="venturelab-runs", daemon=True)
        self._thread.start()

    def out_dir(self, run_id: str) -> Path:
        return self.out_root / run_id

    def submit(self, brief: FounderBrief, effort: str = "full") -> tuple[dict[str, Any], bool]:
        """Returns (run, created). An identical active brief returns the existing run."""
        h = brief_hash(brief, effort)
        with self._submit_lock:
            existing = self.store.active_with_hash(h)
            if existing:
                return existing, False
            if self.store.count_active() >= self.max_queued:
                raise QueueFull(f"{self.max_queued} runs are already queued or running; try again when one finishes")
            run_id = "run-" + uuid.uuid4().hex[:16]
            run = self.store.create(run_id, brief, h, effort)
            self._queue.put(run_id)
            return run, True

    def _worker(self) -> None:
        while True:
            run_id = self._queue.get()
            try:
                self.execute(run_id)
            except Exception:  # never let the worker die; the run records the failure
                self.store.update(run_id, status="failed", stage="Failed", finished=now(),
                                  error="Unexpected error: " + traceback.format_exc(limit=2)[-500:])
            finally:
                self._queue.task_done()

    def execute(self, run_id: str) -> None:
        import orchestrator  # late import keeps module loading light for the web process

        run = self.store.get(run_id)
        brief = FounderBrief.model_validate_json(run["brief"])
        self.store.update(run_id, status="running", stage="Starting")
        client, fetcher = self.client_factory(), self.fetcher_factory()
        try:
            if not pre_research_stop(brief, screen_brief(brief)):
                deadline = time.monotonic() + self.model_wait_s
                while True:
                    try:
                        available, problem = client.has_model(self.model), None
                    except LLMError as exc:
                        available, problem = False, f"Ollama is not reachable: {exc}"
                    if available:
                        break
                    if time.monotonic() >= deadline:
                        reason = problem or f"Model {self.model} is not downloaded yet"
                        self.store.update(run_id, status="blocked", stage="Blocked", finished=now(),
                                          error=f"{reason}, so no research was started. On a first start the "
                                                f"one-time model download can take several minutes; submit the "
                                                f"brief again once /health/model reports ready."[:500])
                        return
                    self.store.update(run_id, stage=f"Waiting for the local model {self.model} "
                                                    "(first start: the one-time download is still running)")
                    time.sleep(self.model_poll_s)

            def listener(entry: dict[str, Any]) -> None:
                stage = AGENT_STAGES.get(entry["agent"], entry["agent"])
                self.store.add_progress(run_id, {"timestamp": entry["timestamp"], "agent": entry["agent"],
                                                 "action": entry["action"], "outcome": entry.get("outcome")}, stage)

            result = orchestrator.run_discover(
                brief, client=client, model=self.model, fetcher=fetcher, log_path=self.log_path,
                out_dir=self.out_dir(run_id), effort=QUICK if run["effort"] == "quick" else FULL,
                warm=True, run_id=run_id, listener=listener)
            self.store.update(run_id, status="completed", stage="Completed", finished=now(),
                              decision=result.gate.decision.value, rule=result.gate.rule.id)
        except Exception as exc:
            self.store.update(run_id, status="failed", stage="Failed", finished=now(),
                              error=f"{type(exc).__name__}: {exc}"[:500])
        finally:
            client.close()
            fetcher.close()
