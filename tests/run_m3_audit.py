"""Reproducible real CLI audit. All inputs and founder decisions are SIMULATED tests.

Run: python -m tests.run_m3_audit --work .venturelab/audit-run --report PATH
Never write this test run's artifacts into final demo outputs or decision_log.json.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


def run(work: Path) -> dict:
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "classification": "SYNTHETIC FIXTURES / SIMULATED founder decisions; actual program execution, not market evidence",
              "generator": "deterministic-template", "cases": []}
    for source in sorted((Path(__file__).parent / "fixtures").glob("audit_*.json")):
        case = json.loads(source.read_text(encoding="utf-8"))
        base = work / case["brief"]["run_id"]
        options = [sys.executable, "-m", "builder_cli", "--state", str(base / "state.sqlite3"), "--outputs", str(base / "artifacts")]
        def command(*args, expected=0):
            result = subprocess.run(options + list(args), capture_output=True, text=True, encoding="utf-8")
            assert result.returncode == expected, result.stderr
            return json.loads(result.stdout) if expected == 0 else result.stderr.strip()
        pending = command("prepare", str(source))
        inspected = command("inspect", pending["action_id"])
        assert inspected["request"]["artifact_sha256"] == pending["artifact_sha256"]
        missing = command("execute", "missing", expected=1)
        blocked = command("execute", pending["action_id"], expected=1)
        command("decide", pending["action_id"], "approve", "--sha256", pending["artifact_sha256"],
                "--reason", "SIMULATED founder decision for synthetic engineering audit; not real validation")
        result = command("execute", pending["action_id"])
        hashes = {}
        for name in result["files"]:
            content = (Path(result["output_directory"]) / name).read_bytes()
            assert content == inspected["files"][name].encode()
            hashes[name] = hashlib.sha256(content).hexdigest()
        repeated = command("execute", pending["action_id"], expected=1)
        rejected = command("prepare", str(source))
        command("decide", rejected["action_id"], "reject", "--sha256", rejected["artifact_sha256"], "--reason", "SIMULATED audit rejection")
        rejection = command("execute", rejected["action_id"], expected=1)
        changed = command("prepare", str(source))
        command("decide", changed["action_id"], "approve", "--sha256", changed["artifact_sha256"], "--reason", "SIMULATED modification probe")
        # Actual backend call with a changed, otherwise-valid content version.
        from approval import ApprovalError, ApprovalStore
        store = ApprovalStore(base / "state.sqlite3", base / "artifacts")
        _, bundle = store.inspect(changed["action_id"])
        altered = bundle.model_copy(update={"landing_page": bundle.landing_page.model_copy(update={"headline": "A revised concept"})})
        try:
            store.execute(changed["action_id"], bundle=altered)
        except ApprovalError as exc:
            modified = str(exc)
        else:
            raise AssertionError("Changed artifact executed")
        report["cases"].append({"input": source.as_posix(), "run_id": case["brief"]["run_id"],
            "action_id": pending["action_id"], "artifact_sha256": pending["artifact_sha256"],
            "files_sha256": hashes, "output_directory": str(Path(result["output_directory"]).relative_to(work)),
            "blocked_attempts": {"missing": missing, "pending": blocked, "repeated": repeated, "rejected": rejection, "changed": modified},
            "events": command("audit")})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.work)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {len(result['cases']) * 4} actual fixture-based artifacts; all bypass attempts blocked")
