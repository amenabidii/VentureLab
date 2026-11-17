"""Integrity of the labelled evidence benchmarks and their scoring."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from bench.ollama_bench import CASES_FILE, HELDOUT_FILE, V1_PROMPT_FILE, score

# Labels and the archived prompt were frozen before the runs that use them.
# Changing a case, a label or the prompt changes the hash and fails this test,
# so edits cannot slip in unnoticed after results are known.
FROZEN = {
    CASES_FILE: "3581781aab4007d58f202a87cb9a9eaddb7051b8f935227ab62bdfc9b2a259dc",
    HELDOUT_FILE: "04a515ebc2c37fa10924aa521e9b0f9e085b3c0c3684e036745f3b0327697bf4",
    V1_PROMPT_FILE: "768a3a68afe5a0cf4a5d045e51ab9aa4aecb0f167ceed1d5b91e3e62498c89f7",
}
LABELS = {"supports", "partially_supports", "does_not_support", "contradicts"}


@pytest.mark.parametrize("path", list(FROZEN))
def test_fixtures_are_frozen(path):
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == FROZEN[path]


@pytest.mark.parametrize(("path", "minimum"), [(CASES_FILE, 30), (HELDOUT_FILE, 16)])
def test_benchmark_size_and_balance(path, minimum):
    cases = json.loads(Path(path).read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= minimum
    assert len({c["id"] for c in cases}) == len(cases)
    per_category = Counter(c["category"] for c in cases)
    assert len(per_category) == 8
    assert len(set(per_category.values())) == 1


@pytest.mark.parametrize("path", [CASES_FILE, HELDOUT_FILE])
def test_cases_are_well_formed_and_labelled_synthetic(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert "SYNTHETIC" in data["notice"]
    for c in data["cases"]:
        assert c["expected"] in LABELS, c["id"]
        assert c["quote"] in c["context"], c["id"]
        assert c["rationale"], c["id"]


def test_dev_and_heldout_do_not_overlap():
    dev = json.loads(Path(CASES_FILE).read_text(encoding="utf-8"))["cases"]
    held = json.loads(Path(HELDOUT_FILE).read_text(encoding="utf-8"))["cases"]
    assert not {c["claim"] for c in dev} & {c["claim"] for c in held}
    assert not {c["id"] for c in dev} & {c["id"] for c in held}


CASES = [
    {"id": "a", "category": "x", "expected": "supports", "claim": "One user asked for CSV export.",
     "context": "I asked for CSV export twice."},
    {"id": "b", "category": "x", "expected": "partially_supports", "claim": "Most shops struggle."},
    {"id": "c", "category": "y", "expected": "contradicts", "claim": "The app has a free plan.",
     "context": "The app has no free plan."},
    {"id": "d", "category": "y", "expected": "does_not_support", "claim": "Hosts want AI editing."},
    {"id": "e", "category": "y", "expected": "partially_supports", "claim": "Freelancers are willing to pay."},
]


def test_score_demand_rule_blocks_confirmed_demand_claim():
    preds = [{"id": "e", "predicted": "supports", "confirmed": True, "reason": ""}]
    s = score(CASES, preds, "v2")
    assert [e["id"] for e in s["false_before_demand_rule"]] == ["e"]
    assert s["false_established"] == []


def test_score_wording_rule_blocks_claim_that_goes_beyond_the_text():
    cases = [{"id": "w", "category": "x", "expected": "partially_supports",
              "claim": "Two posters asked for CSV export.", "context": "I asked for CSV export."}]
    preds = [{"id": "w", "predicted": "supports", "confirmed": True, "reason": ""}]
    s = score(cases, preds, "v2")
    assert [e["id"] for e in s["false_before_demand_rule"]] == ["w"]
    assert s["false_established"] == []


def test_score_v2_only_confirmed_supports_count_as_established():
    preds = [
        {"id": "a", "predicted": "supports", "confirmed": True, "reason": ""},
        {"id": "b", "predicted": "supports", "confirmed": False, "reason": ""},  # wrong label, caught by check
        {"id": "c", "predicted": "supports", "confirmed": True, "reason": ""},  # wrong label, check missed it
        {"id": "d", "predicted": None, "confirmed": None, "reason": "no answer"},
    ]
    s = score(CASES, preds, "v2")
    assert s["correct"] == 1
    assert [e["id"] for e in s["verdict_critical"]] == ["b", "c"]
    assert [e["id"] for e in s["false_established"]] == ["c"]
    assert s["missed_established"] == []
    assert s["per_category"] == {"x": "1/2", "y": "0/2"}


def test_score_v1_supports_alone_establishes():
    preds = [
        {"id": "a", "predicted": "partially_supports", "confirmed": None, "reason": ""},
        {"id": "b", "predicted": "supports", "confirmed": None, "reason": ""},
        {"id": "c", "predicted": "contradicts", "confirmed": None, "reason": ""},
        {"id": "d", "predicted": "does_not_support", "confirmed": None, "reason": ""},
    ]
    s = score(CASES, preds, "v1")
    assert [e["id"] for e in s["false_established"]] == ["b"]
    assert [e["id"] for e in s["missed_established"]] == ["a"]
