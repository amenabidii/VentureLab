"""Submission compliance checks against the repository conventions in CLAUDE.md.

These read the repository as committed; they do not run the pipeline and they do not
check hard-coded demo answers. They are written to stay valid after the Builder and
UI branches merge (nested output directories and extra log fields are allowed).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

README_HEADINGS = [
    "Quickstart",
    "What works and what is mocked",
    "Architecture",
    "Models and free resources",
    "Cost per run",
    "Demo video",
    "What our system will NOT do",
    "How the project stays alive after the hackathon",
]
ARCHITECTURE_HEADINGS = ["Overview", "Phases", "Gates", "Sale to cash", "Data flow", "Built vs. stubbed", "Roadmap"]
LOG_KEYS = {"timestamp", "agent", "action", "sources", "model", "cost", "approved_by"}
OUTPUT_NAME = re.compile(r"^phase\d+_(?:step\d+|gate)_[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:md|json|csv|txt|html)$")
TEXT_SUFFIXES = {".md", ".json", ".csv", ".txt", ".html"}


def h2(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    return [m.group(1).strip() for m in re.finditer(r"^## (.+)$", text, re.M)]


def section(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, heading
    return match.group(1)


def tracked_files() -> list[str]:
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("git metadata not available (for example inside the Docker image)")
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8").split("\0") if p]


@pytest.mark.parametrize("name", ["README.md", "ARCHITECTURE.md", "LICENSE", "decision_log.json",
                                  ".env.example", "CLAUDE.md"])
def test_required_root_files_exist(name):
    assert (ROOT / name).is_file()


@pytest.mark.parametrize("name", ["outputs", "tests", "prompts"])
def test_required_directories_exist_and_are_not_empty(name):
    assert any((ROOT / name).iterdir())


def test_compose_file_exists():
    assert (ROOT / "docker-compose.yml").is_file() or (ROOT / "compose.yaml").is_file()


def test_readme_has_exactly_the_required_headings_in_order():
    assert h2(ROOT / "README.md") == README_HEADINGS


def test_quickstart_has_a_bash_block_with_docker_compose_up():
    blocks = re.findall(r"```bash\n(.*?)```", section(ROOT / "README.md", "Quickstart"), re.S)
    assert any(line.strip() == "docker compose up" for block in blocks for line in block.splitlines())


def test_cost_per_run_states_a_dollar_figure():
    assert re.search(r"\$\d+(?:\.\d+)?", section(ROOT / "README.md", "Cost per run"))


def test_status_table_uses_honest_labels():
    table = section(ROOT / "README.md", "What works and what is mocked")
    rows = [line for line in table.splitlines() if line.startswith("|") and not set(line) <= set("|- ")]
    assert len(rows) > 3
    for row in rows[1:]:
        assert re.search(r"Working|MOCKED|STUBBED", row), row
    assert "STUBBED" in table and "MOCKED" in table


def test_demo_video_section_is_a_link_or_says_not_recorded():
    body = section(ROOT / "README.md", "Demo video")
    assert re.search(r"https://(?:www\.)?(?:youtube\.com|youtu\.be|vimeo\.com|loom\.com|drive\.google\.com)/", body) \
        or "not yet recorded" in body.lower()


def test_architecture_has_required_sections_and_a_text_diagram():
    headings = h2(ROOT / "ARCHITECTURE.md")
    positions = [headings.index(h) for h in ARCHITECTURE_HEADINGS]
    assert positions == sorted(positions)
    text = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "```mermaid" in text or "```text" in text
    for phase in ["Discover", "Validate", "Build", "Commercial Setup", "Launch", "Operate & Learn"]:
        assert re.search(rf"^### \d\. {re.escape(phase)}", text, re.M), phase
    for outcome in ["GO", "REPEAT", "PIVOT", "STOP"]:
        assert outcome in section(ROOT / "ARCHITECTURE.md", "Gates")


def test_unbuilt_phases_and_payments_are_labelled_stubbed():
    text = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    for phase in ["Commercial Setup", "Launch", "Operate & Learn"]:
        assert re.search(rf"^### \d\. {re.escape(phase)} \(STUBBED\)", text, re.M), phase
    assert "STUBBED" in section(ROOT / "ARCHITECTURE.md", "Sale to cash")


def test_license_is_complete_mit_text():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License")
    for phrase in ["Permission is hereby granted, free of charge",
                   "The above copyright notice and this permission notice shall be included",
                   'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND']:
        assert phrase in text
    assert re.search(r"Copyright \(c\) \d{4} \S", text)


def test_decision_log_entries_have_the_required_keys_and_types():
    log = json.loads((ROOT / "decision_log.json").read_text(encoding="utf-8"))
    assert isinstance(log, list) and log
    for entry in log:
        assert LOG_KEYS <= entry.keys(), entry
        assert isinstance(entry["action"], str) and entry["action"]
        assert isinstance(entry["sources"], list) and all(isinstance(s, str) for s in entry["sources"])
        assert entry["model"] is None or isinstance(entry["model"], str)
        assert isinstance(entry["cost"], (int, float)) and entry["cost"] >= 0
        assert entry["approved_by"] in (None, "founder")
        assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", entry["timestamp"])


def test_founder_approvals_in_the_log_name_the_founder_only_on_approval_actions():
    log = json.loads((ROOT / "decision_log.json").read_text(encoding="utf-8"))
    for entry in log:
        if entry["approved_by"] == "founder":
            assert entry.get("agent") in {"approval", "builder"} or "approv" in entry["action"], entry


def output_files() -> list[Path]:
    return [p for p in (ROOT / "outputs").rglob("*") if p.is_file() and p.name != ".gitkeep"]


def test_output_files_follow_phase_step_naming_and_are_small_text():
    files = output_files()
    assert files
    for path in files:
        assert OUTPUT_NAME.match(path.name), path.name
        assert path.suffix in TEXT_SUFFIXES, path.name
        assert path.stat().st_size < 1_000_000, path.name


def test_at_least_one_gate_decision_and_one_stop_are_recorded():
    gates = [p for p in output_files() if re.match(r"^phase\d+_gate_", p.name) and p.suffix == ".json"]
    assert gates
    decisions = {json.loads(p.read_text(encoding="utf-8")).get("decision") for p in gates}
    assert "STOP" in decisions


def test_committed_artifacts_contain_no_personal_absolute_paths_or_keys():
    pattern = re.compile(r"[A-Za-z]:\\\\?Users\\\\?|/Users/[^/\s]+/|/home/[^/\s]+/|sk-[A-Za-z0-9]{20,}|"
                         r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
    for path in [ROOT / "decision_log.json", *output_files()]:
        assert not pattern.search(path.read_text(encoding="utf-8", errors="replace")), path


def test_every_prompt_file_is_used_by_code_and_every_referenced_prompt_exists():
    code = "\n".join(p.read_text(encoding="utf-8") for p in ROOT.rglob("*.py")
                     if ".venv" not in p.parts and "tests" not in p.parts)
    prompts = {p.name for p in (ROOT / "prompts").glob("*.md")}
    assert prompts
    for name in prompts:
        assert name in code or name.removesuffix(".md") in code, f"unused prompt {name}"
    for name in set(re.findall(r"prompts/([\w-]+\.md)", code)):
        assert name in prompts, f"missing prompt {name}"


def test_no_paid_ai_service_is_configured_or_required():
    paid = re.compile(r"OPENAI|ANTHROPIC|GEMINI|GROQ|COHERE|MISTRAL_API|TOGETHER_API|REPLICATE|api\.openai\.com",
                      re.I)
    for name in ["requirements.txt", ".env.example", "docker-compose.yml", "config.py"]:
        path = ROOT / name
        if path.exists():
            assert not paid.search(path.read_text(encoding="utf-8")), name
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "ollama" in compose


def test_env_example_holds_placeholders_only():
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if re.search(r"KEY|TOKEN|SECRET|PASSWORD", key, re.I):
                assert value.strip() in {"", "changeme", "placeholder"} or value.startswith("<"), key


def test_no_secrets_or_local_state_are_tracked():
    forbidden = re.compile(r"(?:^|/)\.env$|\.sqlite3?$|\.db$|\.key$|\.founder$|\.spent/|(?:^|/)\.venturelab/|"
                           r"\.pem$|id_rsa|(?:^|/)\.venv/|__pycache__/|\.pyc$")
    offenders = [p for p in tracked_files() if forbidden.search(p)]
    assert not offenders, offenders


def test_gitignore_covers_env_files():
    assert re.search(r"^\.env$", (ROOT / ".gitignore").read_text(encoding="utf-8"), re.M)


def test_no_text_in_the_repository_addresses_reviewers():
    pattern = re.compile(r"\b(?:dear (?:judges?|reviewers?)|to the (?:judges?|reviewers?)|"
                         r"(?:judges?|reviewers?),? please)\b", re.I)
    for path in [ROOT / "README.md", ROOT / "ARCHITECTURE.md", *(ROOT / "docs").rglob("*.md")]:
        assert not pattern.search(path.read_text(encoding="utf-8")), path
