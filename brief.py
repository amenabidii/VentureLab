"""The founder brief: structured, validated input, and the prohibited-category screen.

Validation (types, lengths, ranges) rejects malformed input with an error.
The category screen is separate: a well-formed brief for a prohibited product
is accepted as input, and the decision gate then records a STOP with the rule
and the matched words, so the founder can see exactly why.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ValidationCondition(BaseModel):
    """A pass/fail condition the founder sets BEFORE an experiment is run."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    description: str = Field(min_length=5, max_length=300)
    metric: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    minimum: float = Field(ge=0)


class FounderBrief(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    idea: str = Field(min_length=10, max_length=500, description="The business idea, in a sentence or two.")
    problem_statement: str = Field(
        min_length=10, max_length=300, description="The customer problem the idea assumes, as one sentence."
    )
    target_customer: str = Field(min_length=3, max_length=200)
    market: str = Field(min_length=2, max_length=200, description="Market or location.")
    founder_skills: list[str] = Field(min_length=1, max_length=10)
    hours_per_week: float = Field(ge=0, le=100)
    budget_eur: float = Field(ge=0, le=1_000_000)
    # The amount above is in this currency (the field name predates multi-currency input).
    # No exchange rate is applied anywhere: converting would invent a number.
    budget_currency: Literal["EUR", "USD", "EGP"] = "EUR"
    values_and_constraints: list[str] = Field(default_factory=list, max_length=10)
    # Optional public pages the founder wants checked (competitor pages, forum threads).
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=5)
    # Conditions set before testing, and results entered by the founder after testing.
    validation_conditions: list[ValidationCondition] = Field(default_factory=list, max_length=10)
    experiment_results: dict[str, float] = Field(default_factory=dict)

    @field_validator("founder_skills", "values_and_constraints")
    @classmethod
    def _non_empty_items(cls, items: list[str]) -> list[str]:
        cleaned = [i.strip() for i in items]
        if any(not i or len(i) > 200 for i in cleaned):
            raise ValueError("each item must be 1 to 200 characters")
        return cleaned

    def text(self) -> str:
        """Every free-text field, for the category screen."""
        return " ".join([self.idea, self.problem_statement, self.target_customer, self.market,
                         *self.values_and_constraints])


def load_brief(path: str | Path) -> FounderBrief:
    return FounderBrief.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


# --- prohibited categories -----------------------------------------------------------
# Products this project must never help build (see CLAUDE.md). Matching is by
# keyword, so it can over-match; the matched words are always shown.

PROHIBITED: dict[str, re.Pattern[str]] = {
    "physical_goods": re.compile(
        r"\b(?:physical (?:product|goods|item)s?|hardware|merch(?:andise)?|t-?shirts?|clothing|apparel|"
        r"jewel(?:le)?ry|furniture|cosmetics?|skincare|candles?|food (?:product|delivery|truck)s?|"
        r"snacks?|beverages?|ship(?:ping)? (?:boxes|products|goods)|dropshipping|subscription box(?:es)?|"
        r"3d[- ]printed|handmade (?:goods|products|items))\b",
        re.IGNORECASE,
    ),
    "financial_investment_or_crypto": re.compile(
        r"\b(?:crypto(?:currenc(?:y|ies))?|bitcoin|ethereum|blockchain tokens?|nfts?|defi|tokens? sale|"
        r"trading (?:signals?|bots?|tips)|day[- ]trading|forex|stock (?:picks?|tips|signals?)|"
        r"investment (?:advice|tips|signals?|recommendations?)|financial advice|"
        r"(?:payday |personal )?loans?|lending|insurance (?:policies|products)|robo[- ]advis[oe]r)\b",
        re.IGNORECASE,
    ),
    "health_advice": re.compile(
        r"\b(?:medical (?:advice|diagnos[ie]s)|diagnos(?:e|es|is|ing)|symptom checker|treatment plans?|"
        r"health advice|therap(?:y|ist) (?:advice|sessions?)|mental health advice|supplements?|"
        r"diet plans?|weight[- ]loss (?:plans?|programs?)|prescri(?:be|ption)s?|medication)\b",
        re.IGNORECASE,
    ),
    "legal_advice": re.compile(
        r"\b(?:legal advice|lawyer|attorney|legal opinions?|contract review|draft(?:ing)? (?:legal )?contracts|"
        r"immigration advice|tax advice)\b",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class CategoryScreen:
    allowed: bool
    matches: dict[str, list[str]]  # category -> matched words

    def summary(self) -> str:
        if self.allowed:
            return "no prohibited category matched"
        return "; ".join(f"{cat}: {', '.join(words)}" for cat, words in self.matches.items())


def screen_brief(brief: FounderBrief) -> CategoryScreen:
    text = brief.text()
    matches = {}
    for category, pattern in PROHIBITED.items():
        found = sorted({m.group(0).lower() for m in pattern.finditer(text)})
        if found:
            matches[category] = found
    return CategoryScreen(allowed=not matches, matches=matches)
