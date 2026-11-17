"""End-to-end Discover workflow on STUBBED sources and a STUBBED model."""

from __future__ import annotations

import json

import httpx

import orchestrator
from agents.investigator import QUICK
from audit import check_entry
from brief import FounderBrief
from tests.conftest import RoutedOllama, stub_sources
from tests.test_agents import BRIEF, COMMENTS, CONFIRMED, FAITHFUL, QUERIES, SUPPORTS, extraction

CHALLENGE = json.dumps({
    "reviews": {"A1": {"stance": "supported", "reason": "Two people describe it.", "evidence": ["F1", "F2"]}},
    "new_hypotheses": [], "risks": [], "experiments": [],
})
CONTRADICTS = json.dumps({"reason": "They say it is quick.", "limitations": "", "verdict": "contradicts"})


def run(tmp_path, *, brief=BRIEF, replies=None, routes=None, effort=orchestrator.FULL):
    model = RoutedOllama({"queries": QUERIES, "extract": FAITHFUL, "assess": SUPPORTS, "confirm": CONFIRMED,
                          "challenge": CHALLENGE} | (replies or {}))
    result = orchestrator.run_discover(
        brief, client=model.client(), model="qwen3:4b",
        fetcher=stub_sources(routes or {"hn.algolia.com": COMMENTS}),
        log_path=tmp_path / "decision_log.json", out_dir=tmp_path / "outputs", effort=effort, warm=True)
    entries = json.loads((tmp_path / "decision_log.json").read_text(encoding="utf-8"))
    return result, model, entries


def statement_contradicted(user: str) -> str:
    return CONTRADICTS if "CLAIM: Small software teams" in user else SUPPORTS


def test_full_pipeline_writes_named_outputs_and_a_valid_log(tmp_path):
    result, model, entries = run(tmp_path)
    assert sorted(p.name for p in result.files) == sorted([
        "phase1_step1_founder_brief.json", "phase1_step2_investigation.json", "phase1_step2_investigation.md",
        "phase1_step3_challenge.json", "phase1_step3_challenge.md", "phase1_gate_decision.json",
        "phase1_gate_decision.md"])
    for path in result.files:
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
    # Two faithful, relevant, confirmed claims from two different comments: GO to further validation.
    assert result.gate.decision.value == "GO" and result.gate.rule.id == "GO_TO_FURTHER_VALIDATION"
    gate = json.loads((tmp_path / "outputs" / "phase1_gate_decision.json").read_text(encoding="utf-8"))
    assert gate["rule"] == "GO_TO_FURTHER_VALIDATION" and gate["model_calls"] == result.model_calls
    assert "not proof of demand" in gate["rule_meaning"]
    assert any("Demand" in m for m in gate["counterfactual"]["missing_evidence"])
    for e in entries:
        check_entry(e)
        assert e["run_id"] == result.run_id
    actions = [e["action"] for e in entries]
    for expected in ("validate_brief", "load_model", "plan_searches", "retrieve_source",
                     "select_relevant_comments", "extract_claims", "assess_claim", "check_founder_statement",
                     "challenge_assumptions", "evidence_gate", "explain_decision"):
        assert expected in actions, expected
    assert all(e["approved_by"] is None for e in entries)  # nothing in this phase needs approval
    challenge = json.loads((tmp_path / "outputs" / "phase1_step3_challenge.json").read_text(encoding="utf-8"))
    assert challenge["grounded_reviews"] >= 1
    md = (tmp_path / "outputs" / "phase1_step2_investigation.md").read_text(encoding="utf-8")
    assert "news.ycombinator.com/item?id=201" in md and "set aside as off-topic" in md


def test_wrongly_attributed_claims_cannot_produce_go(tmp_path):
    wrong = extraction(
        ("customer_problem", "Product managers say the release notes take an hour every Friday.",
         ["takes me an hour"]),
        ("customer_problem", "One designer says I spend two hours writing release notes for each release.",
         ["two hours writing"]),
    )
    result, _, _ = run(tmp_path, replies={"extract": wrong})
    assert result.gate.decision.value == "REPEAT"
    assert len(result.gate.evidence.needs_review) >= 2 and result.gate.evidence.supporting == []


def test_support_plus_contradiction_is_mixed_evidence(tmp_path):
    result, _, _ = run(tmp_path, replies={"assess": statement_contradicted})
    assert result.gate.rule.id == "REPEAT_MIXED_EVIDENCE"


def test_contradiction_with_an_established_alternative_pivots(tmp_path):
    alternative = extraction(
        ("customer_problem", "One commenter says we moved our web app to a new pull request workflow.",
         ["new pull request workflow"]))
    result, _, _ = run(tmp_path, replies={"extract": alternative, "assess": statement_contradicted})
    assert result.gate.decision.value == "PIVOT" and result.gate.rule.id == "PIVOT_ALTERNATIVE_SUPPORTED"
    assert "pull request workflow" in result.counterfactual["alternative_hypothesis"]["hypothesis"]


def test_quick_mode_runs_every_step(tmp_path):
    result, model, entries = run(tmp_path, effort=QUICK)
    assert result.investigation.effort == "quick" and len(result.investigation.queries) == 1
    assert {"queries", "extract", "assess", "challenge"} <= set(model.calls)
    assert result.gate.decision.value in ("GO", "REPEAT")


def test_prohibited_brief_stops_without_research_or_model_calls(tmp_path):
    brief = FounderBrief.model_validate(BRIEF.model_dump(mode="json")
                                        | {"idea": "A newsletter with daily crypto trading signals."})
    result, model, entries = run(tmp_path, brief=brief)
    assert result.gate.decision.value == "STOP" and result.gate.rule.id == "STOP_PROHIBITED_CATEGORY"
    assert model.calls == [] and result.investigation is None and result.model_calls == 0
    assert [p.name for p in result.files] == ["phase1_step1_founder_brief.json", "phase1_gate_decision.json",
                                              "phase1_gate_decision.md"]
    assert [e["action"] for e in entries] == ["validate_brief", "skip_research", "evidence_gate",
                                              "explain_decision"]


def test_low_availability_does_not_stop_the_run(tmp_path):
    brief = FounderBrief.model_validate(BRIEF.model_dump(mode="json") | {"hours_per_week": 1})
    result, _, _ = run(tmp_path, brief=brief)
    assert result.gate.decision.value == "GO"
    assert any("Limited availability" in n for n in result.gate.feasibility_notes)


def test_all_sources_unavailable_is_repeat_not_stop(tmp_path):
    result, _, entries = run(tmp_path, routes={"hn.algolia.com": httpx.ConnectError("offline")})
    assert result.gate.decision.value == "REPEAT" and result.gate.rule.id == "REPEAT_NO_READABLE_SOURCES"
    assert result.investigation.findings == []
    assert any(e["action"] == "retrieve_source" and e["outcome"] == "unavailable" for e in entries)


def test_cli_rejects_an_invalid_brief(tmp_path, capsys):
    bad = tmp_path / "brief.json"
    bad.write_text(json.dumps({"idea": "too short"}), encoding="utf-8")
    assert orchestrator.main(["--brief", str(bad), "--out", str(tmp_path), "--log", str(tmp_path / "l.json")]) == 2
    assert "Invalid founder brief" in capsys.readouterr().err
    assert not (tmp_path / "l.json").exists()


def test_suffix_names_outputs_for_a_failed_condition(tmp_path):
    brief = FounderBrief.model_validate(BRIEF.model_dump(mode="json") | {
        "validation_conditions": [{"id": "interviews", "description": "people confirming the problem",
                                   "metric": "confirmed", "minimum": 5}],
        "experiment_results": {"confirmed": 1}})
    result = orchestrator.run_discover(
        brief, client=RoutedOllama({}).client(), model="qwen3:4b", fetcher=stub_sources({}),
        log_path=tmp_path / "l.json", out_dir=tmp_path, suffix="_example")
    assert result.gate.rule.id == "STOP_FAILED_VALIDATION_CONDITION"
    assert {p.name for p in result.files} == {"phase1_step1_founder_brief_example.json",
                                              "phase1_gate_decision_example.json", "phase1_gate_decision_example.md"}
