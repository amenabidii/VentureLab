"""Index existing tracked executions without generating or changing their outputs.

Run from the repository root after reviewing the provenance of the recordings.
The index is a reproducibility aid, never a claim that checksums establish truth.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z", "outputs"], cwd=ROOT).decode().split("\0")
    events = json.loads((ROOT / "decision_log.json").read_text(encoding="utf-8"))
    result = {}
    keys = {"timestamp", "agent", "action", "sources", "model", "cost", "approved_by", "run_id", "outcome"}
    for name in sorted(tracked):
        path = Path(name)
        if not path.name.startswith("phase1_gate_decision") or path.suffix != ".json":
            continue
        gate = json.loads((ROOT / path).read_text(encoding="utf-8"))
        run_id = gate.get("run_id")
        audit = [{k: v for k, v in e.items() if k in keys} for e in events if e.get("run_id") == run_id]
        gate_events = [e for e in audit if e["agent"] == "gate" and e["action"] == "evidence_gate"]
        if not gate_events:
            continue  # Older milestone outputs have separate logs; do not invent provenance.
        suffix = path.name.removeprefix("phase1_gate_decision").removesuffix(".json")
        logical = {"gate": name}
        for key, stem in {"brief":"phase1_step1_founder_brief", "investigation":"phase1_step2_investigation", "challenge":"phase1_step3_challenge"}.items():
            candidate=(path.parent / (stem+suffix+".json")).as_posix()
            if candidate in tracked:
                logical[key]=candidate
        if "brief" not in logical:
            continue
        related = set(logical.values()) | {p for p in tracked if p.startswith(f"outputs/builder/{run_id}/")}
        files = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(related)}
        if gate_events[-1]["outcome"].upper() != gate["decision"]:
            raise ValueError(f"Gate and log disagree for {run_id}")
        record_id="record-"+hashlib.sha256(run_id.encode()).hexdigest()[:16]
        result[record_id] = {"execution_id":run_id,"recorded_at":gate_events[-1]["timestamp"],"outputs":logical,"files":files,"audit":audit}
    (ROOT / "app/recorded_runs.json").write_text(json.dumps({"schema": 1, "runs": result}, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(result)} existing executions; no outputs or decisions changed.")


if __name__ == "__main__":
    main()
