"""CLI integration with synthetic fixture and simulated founder decisions."""
import json
from pathlib import Path

from builder_cli import main


def test_cli_round_trip(tmp_path, capsys):
    options = ["--state", str(tmp_path / "state.sqlite3"), "--outputs", str(tmp_path / "outputs")]
    fixture = Path(__file__).parent / "fixtures/builder_input.json"
    assert main(options + ["prepare", str(fixture)]) == 0
    request = json.loads(capsys.readouterr().out)
    action = request["action_id"]
    assert main(options + ["execute", action]) == 1
    capsys.readouterr()
    assert main(options + ["inspect", action]) == 0
    inspection = json.loads(capsys.readouterr().out)
    assert "phase3_step1_landing-page.html" in inspection["files"]
    assert main(options + ["decide", action, "approve", "--sha256", request["artifact_sha256"], "--reason", "SIMULATED test approval"]) == 0
    capsys.readouterr()
    assert main(options + ["execute", action]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["files"]) == 4
    assert main(options + ["audit"]) == 0
    assert json.loads(capsys.readouterr().out)[-1]["outcome"] == "executed"
    assert main(options + ["receipt", action]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["request"]["status"] == "executed"
    assert receipt["artifact_sha256_matches_current_renderer"] is True
