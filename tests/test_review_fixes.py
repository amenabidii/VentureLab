"""Regression tests for defects found in review of the later-phase code.

All inputs are SYNTHETIC; no model is called.
"""

from __future__ import annotations

import pytest

from agents.advisor import Advice, sanitize
from agents.launcher import launch_posts
from agents.operator import persevere_or_pivot
from agents.strategist import score_opportunities
from mvp.thread_digest import supported

BRIEF = {"idea": "A bot that summarises long Discord bug threads for moderators",
         "problem_statement": "Moderators lose bug reports in long chat threads.",
         "target_customer": "Discord community moderators", "market": "online"}


def advice(**fields) -> Advice:
    base = dict(value_proposition="Bug threads summarised for moderators", current_alternatives=["pinned messages"],
                channels=[], key_metric="interviewees who lost a report last month", price_anchor="none known",
                price_points_eur_per_month=[5], pricing_rationale="to be tested", interview_questions=[],
                launch_angle="Lost bug reports", riskiest_assumption="moderators care", kill_criterion="stop if 0 of 5")
    return Advice(**(base | fields))


@pytest.mark.parametrize(("field", "text"), [
    ("value_proposition", "The #1 proven way moderators never lose a bug report again"),
    ("value_proposition", "Trusted across Discord by moderators"),
    ("pricing_rationale", "Half the cost of alternatives; pays for itself in a week"),
    ("launch_angle", "Join before spots run out"),
    ("launch_angle", "Limited time offer for early moderators"),
])
def test_unsourced_superiority_and_urgency_claims_are_dropped(field, text):
    out = sanitize(advice(**{field: text}), set(), "qwen3:4b")
    assert out[field] is None and any(field in d for d in out["dropped"])


def test_plain_model_text_still_passes():
    out = sanitize(advice(), set(), "qwen3:4b")
    assert out["value_proposition"] == "Bug threads summarised for moderators"


def test_the_founder_voice_announcement_never_uses_model_text():
    adv = sanitize(advice(value_proposition="Bug threads summarised automatically"), set(), "qwen3:4b")
    posts = launch_posts("Concept", BRIEF, {"price_eur_per_month": 5}, adv)
    announcement = posts.split("## Short announcement")[1].split("##")[0]
    assert "summarised automatically" not in announcement
    assert "Early concept: a bot that summarises" in announcement
    assert f"Suggested value proposition ({adv['label']})" in posts  # still offered, labelled
    assert f"Angle to lead with ({adv['label']})" in posts


def test_model_alternatives_do_not_inherit_evidence_by_substring():
    gate = {"decision": "REPEAT", "run_id": "r", "evidence": {}}
    inv = {"findings": [{"id": "F1", "type": "customer_problem", "standing": "established",
                         "claim": "Moderators say bug reports get lost in chat",
                         "quotes": [{"url": "https://news.ycombinator.com/item?id=1", "status": "verified"}]}]}
    adv = {"source": "model", "label": "ASSUMPTION", "current_alternatives": ["bug"]}
    data = score_opportunities(BRIEF, gate, inv, None, adv)
    row = next(r for r in data["options"] if r["option"] == "Current alternative: bug")
    assert row["problem_evidence"] == 0 and row["sources"] == []


@pytest.mark.parametrize(("discover", "validation", "expected"), [
    ("GO", "GO", "PERSEVERE"),
    ("REPEAT", "GO", "REPEAT"),   # validation alone cannot outrank the Discover gate
    ("PIVOT", "GO", "REPEAT"),
    ("STOP", "GO", "STOP"),
])
def test_persevere_needs_both_gates(discover, validation, expected):
    memo = persevere_or_pivot({"decision": discover}, {}, None,
                              {"decision": validation, "rule": "VALIDATION_THRESHOLD_MET",
                               "successes": 3, "participants": 5})
    assert memo["recommendation"] == expected
    if expected != "PERSEVERE":
        assert memo["launch_recommendation"].startswith("DO NOT LAUNCH")


def test_results_typed_into_the_brief_cannot_justify_launching():
    brief = {"validation_conditions": [{"id": "c1", "metric": "signups", "minimum": 10}],
             "experiment_results": {"signups": 50}}
    memo = persevere_or_pivot({"decision": "GO"}, brief, None, None)
    assert memo["recommendation"] == "REPEAT" and memo["launch_recommendation"].startswith("DO NOT LAUNCH")


@pytest.mark.parametrize("idea", [
    "A mobile game where players catch up on missed story chapters told through chat messages",
    "A voice assistant that gives podcast recaps and lets listeners comment",
    "A video course platform whose forum shows a digest of new courses",
])
def test_other_products_are_not_called_a_working_thread_digest(idea):
    assert not supported(idea)


def test_diagnostics_label_mocked_metrics():
    from app.main import app
    from fastapi.testclient import TestClient
    page = TestClient(app).get("/diagnostics")
    assert page.status_code == 200 and "metrics MOCKED" in page.text
