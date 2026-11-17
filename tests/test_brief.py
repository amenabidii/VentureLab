"""Founder brief validation and the prohibited-category screen."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from brief import FounderBrief, load_brief, screen_brief

ROOT = Path(__file__).resolve().parent.parent

VALID = {
    "idea": "A web app that drafts release notes from merged pull requests.",
    "problem_statement": "Small software teams spend too much time writing release notes.",
    "target_customer": "developers at small SaaS companies",
    "market": "online",
    "founder_skills": ["Python"],
    "hours_per_week": 10,
    "budget_eur": 0,
}


def test_valid_brief_is_accepted_and_screened_clean():
    brief = FounderBrief.model_validate(VALID)
    assert brief.values_and_constraints == [] and brief.source_urls == []
    assert screen_brief(brief).allowed


@pytest.mark.parametrize("path", sorted((ROOT / "briefs").glob("*.json")))
def test_example_briefs_are_valid(path):
    load_brief(path)


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"idea": "short"}, "idea"),
        ({"hours_per_week": -1}, "hours_per_week"),
        ({"hours_per_week": 200}, "hours_per_week"),
        ({"budget_eur": -5}, "budget_eur"),
        ({"founder_skills": []}, "founder_skills"),
        ({"founder_skills": ["  "]}, "founder_skills"),
        ({"source_urls": ["not a url"]}, "source_urls"),
        ({"surprise": "extra field"}, "surprise"),
        ({"validation_conditions": [{"id": "x", "description": "too", "metric": "m", "minimum": 1}]},
         "validation_conditions"),
    ],
)
def test_invalid_brief_is_rejected(change, field):
    with pytest.raises(ValidationError) as exc:
        FounderBrief.model_validate(VALID | change)
    assert field in str(exc.value)


def test_missing_required_field_is_rejected():
    data = dict(VALID)
    del data["target_customer"]
    with pytest.raises(ValidationError, match="target_customer"):
        FounderBrief.model_validate(data)


@pytest.mark.parametrize(
    ("idea", "category"),
    [
        ("A newsletter with daily crypto trading signals for beginners.", "financial_investment_or_crypto"),
        ("An online shop selling handmade candles and printed t-shirts.", "physical_goods"),
        ("An app that gives medical advice and diagnoses rashes from photos.", "health_advice"),
        ("A chatbot that gives legal advice to tenants in disputes.", "legal_advice"),
        ("A robo-advisor that picks stocks for retirement savings.", "financial_investment_or_crypto"),
    ],
)
def test_prohibited_categories_are_caught(idea, category):
    brief = FounderBrief.model_validate(VALID | {"idea": idea})
    screen = screen_brief(brief)
    assert not screen.allowed
    assert category in screen.matches
    assert category in screen.summary()


def test_constraints_are_screened_too():
    brief = FounderBrief.model_validate(VALID | {"values_and_constraints": ["we will also ship hardware"]})
    assert "physical_goods" in screen_brief(brief).matches
