"""Five varied permitted briefs; all are synthetic test fixtures, not evidence."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agents.builder import generate_kit
from builder_models import BuilderInput, LandingPageSpec
from builder_service import ArtifactBundle, prepare

CASES = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((Path(__file__).parent / "fixtures").glob("audit_*.json"))]


@pytest.mark.parametrize("case", CASES, ids=[case["brief"]["run_id"] for case in CASES])
def test_varied_briefs_produce_consistent_specific_artifacts(case):
    brief, spec = BuilderInput.model_validate(case["brief"]), LandingPageSpec.model_validate(case["landing_page"])
    bundle = prepare(brief, spec)
    assert bundle.fingerprint() == prepare(brief, spec).fingerprint()
    files = bundle.files()
    kit = json.loads(files["phase2_step1_validation-kit.json"])
    assert kit["target_audience"] == brief.target_customer
    assert brief.core_problem in kit["hypothesis"]
    assert kit["success_criteria"]["sample_size"] == brief.experiment_design.sample_size
    assert kit["success_criteria"]["threshold"] == brief.experiment_design.success_minimum
    assert str(brief.experiment_design.success_minimum) in kit["failure_criteria"]
    assert kit["assumption_under_test"] == brief.main_assumptions[0]
    assert kit["untested_assumptions"] == [brief.main_assumptions[1]]
    assert kit["results_status"].startswith("NOT RUN")
    assert all("if any" in q or "if anything" in q or "?" in q for q in kit["interview_questions"])
    assert brief.core_problem.encode() in files["phase2_step1_validation-kit.md"]
    assert json.loads(files["phase3_step1_landing-spec.json"]) == spec.model_dump(mode="json")
    for feature in spec.features:
        assert feature.encode() in files["phase3_step1_landing-page.html"]


def test_maximum_valid_brief_lengths_do_not_overflow_generated_schema():
    case = CASES[0]
    brief = dict(case["brief"], business_idea="a" * 2000, core_problem="b" * 2000,
                 target_customer="c" * 2000, main_assumptions=["d" * 2000])
    spec = dict(case["landing_page"], target_audience=brief["target_customer"])
    assert prepare(BuilderInput.model_validate(brief), LandingPageSpec.model_validate(spec))


@pytest.mark.parametrize("outcome", ["STOP", "PIVOT", "REPEAT"])
def test_supplied_non_go_gate_blocks_landing_bundle(outcome):
    brief = dict(CASES[0]["brief"], gate_context={"decision_id": "upstream-test-gate", "outcome": outcome})
    with pytest.raises(ValidationError, match="gate"):
        prepare(BuilderInput.model_validate(brief), LandingPageSpec.model_validate(CASES[0]["landing_page"]))


def test_audience_mismatch_is_rejected():
    spec = dict(CASES[0]["landing_page"], target_audience="A different customer segment")
    with pytest.raises(ValidationError, match="audience"):
        prepare(BuilderInput.model_validate(CASES[0]["brief"]), LandingPageSpec.model_validate(spec))


def test_direct_forged_kit_cannot_enter_approval_bundle():
    bundle = prepare(BuilderInput.model_validate(CASES[0]["brief"]), LandingPageSpec.model_validate(CASES[0]["landing_page"]))
    data = bundle.model_dump()
    data["kit"]["hypothesis"] = "Unrelated claim"
    with pytest.raises(ValidationError, match="inconsistent"):
        ArtifactBundle.model_validate(data)


@pytest.mark.parametrize("index", [2, 11])
def test_mocked_model_cannot_select_nonexistent_assumption(fake_ollama, index):
    client = fake_ollama(chat_replies=[json.dumps({"assumption_index": index})]).client()
    try:
        with pytest.raises(ValueError, match="outside"):
            generate_kit(BuilderInput.model_validate(CASES[0]["brief"]), client)
    finally:
        client.close()


@pytest.mark.parametrize("value", [True, "3", 3.0])
def test_numeric_settings_are_strict_integers(value):
    brief = dict(CASES[0]["brief"], experiment_design={"sample_size": 5, "success_minimum": value})
    with pytest.raises(ValidationError):
        BuilderInput.model_validate(brief)
