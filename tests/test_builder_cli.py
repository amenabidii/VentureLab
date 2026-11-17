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
    assert len(result["files"]) == 6  # kit, Lean Canvas and landing page, each as data and readable file
    assert any(f.endswith("phase2_step1_lean-canvas.md") for f in result["files"])
    assert main(options + ["audit"]) == 0
    assert json.loads(capsys.readouterr().out)[-1]["outcome"] == "executed"
    assert main(options + ["receipt", action]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["request"]["status"] == "executed"
    assert receipt["artifact_sha256_matches_current_renderer"] is True


def test_exported_paths_are_relative_to_the_working_directory(tmp_path, monkeypatch, capsys):
    import json as _json
    from pathlib import Path as _Path
    monkeypatch.chdir(tmp_path)
    source = _Path(__file__).parent / "fixtures/builder_input.json"
    assert main(["--state", "state/db.sqlite3", "--outputs", "out", "prepare", str(source)]) == 0
    request = _json.loads(capsys.readouterr().out)
    assert request["destination"].startswith("out/synthetic-unit-test/")
    assert str(tmp_path) not in request["destination"]
