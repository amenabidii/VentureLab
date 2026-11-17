"""Adversarial regression probes; all claims/identities here are SYNTHETIC TEST DATA."""
import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from approval import ApprovalError, ApprovalStore
from builder_cli import main
from builder_models import BuilderInput, LandingPageSpec
from builder_service import prepare


def sample_bundle():
    data = json.loads((Path(__file__).parent / "fixtures/builder_input.json").read_text())
    return prepare(BuilderInput.model_validate(data["brief"]), LandingPageSpec.model_validate(data["landing_page"]))


def test_database_status_forgery_is_blocked(tmp_path):
    store = ApprovalStore(tmp_path / "state.db", tmp_path / "outputs")
    request = store.create(sample_bundle())
    with sqlite3.connect(store.database) as db:
        db.execute("UPDATE approvals SET status='approved' WHERE action_id=?", (request.action_id,))
    with pytest.raises(ApprovalError):
        store.execute(request.action_id)
    assert not Path(request.destination).exists()


def test_audit_identifies_artifact_version(tmp_path):
    store = ApprovalStore(tmp_path / "state.db", tmp_path / "outputs")
    request = store.create(sample_bundle())
    assert all(event.get("artifact_sha256") == request.artifact_sha256 for event in store.audit_events())


def test_hypothesis_is_problem_aligned_and_operational():
    bundle = sample_bundle()
    assert bundle.brief.core_problem in bundle.kit.hypothesis
    assert bundle.brief.target_customer in bundle.kit.hypothesis
    assert str(bundle.kit.success_criteria.threshold) in bundle.kit.hypothesis


def test_markdown_cannot_embed_remote_images():
    bundle = sample_bundle()
    brief = bundle.brief.model_copy(update={"main_assumptions": ("![tracking](https://example.org/pixel)",)})
    page = prepare(brief, bundle.landing_page).files()["phase2_step1_validation-kit.md"].decode()
    assert "![tracking](https://example.org/pixel)" not in page


@pytest.mark.parametrize("value", [None, 42, True])
def test_cli_invalid_root_is_a_controlled_failure(tmp_path, capsys, value):
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(value))
    assert main(["--state", str(tmp_path / "state.db"), "--outputs", str(tmp_path / "outputs"), "prepare", str(source)]) == 1
    assert "failed" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("claim", ["10,000 happy customers", "Ｇｕａｒａｎｔｅｅｄ success", "Our interviews revealed strong demand"])
def test_obfuscated_fabricated_claims_rejected(claim):
    data = sample_bundle().landing_page.model_dump()
    data["headline"] = claim
    with pytest.raises(ValidationError):
        LandingPageSpec.model_validate(data)


def test_code_review_product_is_permitted():
    data = sample_bundle().landing_page.model_dump()
    data["headline"] = "Organize code reviews for your development team"
    assert LandingPageSpec.model_validate(data)
