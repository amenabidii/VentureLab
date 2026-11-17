"""Lean Canvas: every box states its basis, and nothing is filled in without input.

Uses the SYNTHETIC Builder fixture (tests/fixtures/builder_input.json); no model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from builder_models import BuilderInput
from builder_service import ArtifactBundle, prepare
from lean_canvas import BOXES, build_canvas, canvas_markdown


def brief(**update) -> BuilderInput:
    data = json.loads((Path(__file__).parent / "fixtures/builder_input.json").read_text())
    gate = {"gate_context": {"decision_id": "synthetic", "outcome": "REPEAT"}}  # SYNTHETIC
    return BuilderInput.model_validate(data["brief"] | gate | update)


def boxes(bundle):
    return {b.name: b for b in bundle.lean_canvas.boxes}


def test_every_box_is_present_and_labelled():
    bundle = prepare(brief(), None)
    assert tuple(b.name for b in bundle.lean_canvas.boxes) == BOXES
    assert all(b.basis in ("EVIDENCE", "FOUNDER-STATED", "PROPOSED", "ASSUMPTION") for b in bundle.lean_canvas.boxes)
    assert "not validated facts" in bundle.lean_canvas.label


def test_unknowns_stay_unknown():
    b = boxes(prepare(brief(), None))
    assert b["Revenue streams"].basis == "ASSUMPTION" and "no pricing" in b["Revenue streams"].content
    assert "never a real or sandbox payment" in b["Revenue streams"].next_test
    assert b["Unfair advantage"].content == "None established."
    assert b["Unique value proposition"].basis == "ASSUMPTION"


def test_the_problem_is_evidence_only_with_an_established_finding():
    weak = brief(supporting_evidence=[{"statement": "F1 [NEEDS_REVIEW] someone said something",
                                       "source_url": "https://news.ycombinator.com/item?id=1"}])
    assert boxes(prepare(weak, None))["Problem"].basis == "FOUNDER-STATED"
    strong = brief(supporting_evidence=[
        {"statement": "F2 [ESTABLISHED] I spend hours on this", "source_url": "https://news.ycombinator.com/item?id=2"},
        {"statement": "F3 [NEEDS_REVIEW] maybe", "source_url": "https://news.ycombinator.com/item?id=3"}])
    problem = boxes(prepare(strong, None))["Problem"]
    assert problem.basis == "EVIDENCE" and [str(u) for u in problem.sources] == ["https://news.ycombinator.com/item?id=2"]


def test_key_metric_is_the_kit_pass_mark():
    bundle = prepare(brief(), None)
    c = bundle.kit.success_criteria
    km = boxes(bundle)["Key metrics"]
    assert km.basis == "PROPOSED" and km.content.startswith(f"{c.threshold} of {c.sample_size}")


def test_the_canvas_is_written_with_the_kit_and_covered_by_the_fingerprint():
    bundle = prepare(brief(), None)
    files = bundle.files()
    assert {"phase2_step1_lean-canvas.json", "phase2_step1_lean-canvas.md"} <= set(files)
    assert "| Revenue streams |" in files["phase2_step1_lean-canvas.md"].decode()
    altered = json.loads(bundle.model_dump_json())
    altered["lean_canvas"]["boxes"][5]["content"] = "Customers will pay 50 EUR a month."
    with pytest.raises(ValidationError, match="Lean Canvas is inconsistent"):
        ArtifactBundle.model_validate(altered)


def test_bundles_approved_before_the_canvas_keep_their_fingerprint():
    bundle = prepare(brief(), None).model_copy(update={"lean_canvas": None})
    old_payload = {"bundle": {k: v for k, v in bundle.model_dump(mode="json").items() if k != "lean_canvas"},
                   "files": {n: d.decode() for n, d in bundle.files().items()}}
    old_digest = hashlib.sha256(json.dumps(old_payload, sort_keys=True, ensure_ascii=False,
                                           separators=(",", ":")).encode()).hexdigest()
    assert bundle.fingerprint() == old_digest
    assert "phase2_step1_lean-canvas.md" not in bundle.files()


def test_markdown_escapes_table_breaking_text():
    b = brief(target_customer="teams | with pipes")
    assert "teams \\| with pipes" in canvas_markdown(build_canvas(b, prepare(b, None).kit))

