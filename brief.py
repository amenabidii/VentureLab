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


# Practices this project must never help with, whatever the product (see the key rules:
# no fake reviews, sign-ups or urgency, no impersonation, no promised income). A match in
# a sentence about detecting or preventing the practice ("a tool that flags fake reviews")
# is not counted, so anti-fraud products stay possible.
DECEPTIVE: dict[str, re.Pattern[str]] = {
    "fake_reviews_or_social_proof": re.compile(
        r"\b(?:fake|bogus|paid|purchased|invented|fabricated|made[- ]up|astroturf\w*)\s+"
        r"(?:\w+\s+){0,2}?(?:reviews?|ratings?|testimonials?|sign-?ups?|followers|likes|upvotes|endorsements?)\b"
        r"|\b(?:write|writes|writing|generate[sd]?|generating|create[sd]?|creating|post(?:s|ing)?|buy(?:s|ing)?|"
        r"sell(?:s|ing)?|produce[sd]?|mass[- ]produce)\s+(?:\w+\s+){0,3}?"
        r"(?:\d+\s+)?(?:five|5)[- ]star\s+(?:reviews?|ratings?)\b"
        r"|\b(?:inflate[sd]?|inflating|pad(?:s|ding)?)\s+(?:\w+\s+){0,2}?(?:sign-?up|waitlist|review|follower|user)"
        r"\s*(?:counts?|numbers?|totals?)\b",
        re.IGNORECASE,
    ),
    "fake_urgency_or_scarcity": re.compile(
        r"\b(?:fake|false|artificial|manufactured|invented)\s+(?:\w+\s+){0,1}?(?:urgency|scarcity|countdowns?|"
        r"deadlines?|stock (?:levels?|counts?))\b"
        r"|\b(?:always|perpetual|evergreen|resetting|fake)\s+(?:\w+\s+){0,2}?(?:countdown|timer|scarcity)\w*"
        r"|\bonly \d+ (?:left|remaining)\b",
        re.IGNORECASE,
    ),
    "impersonation": re.compile(
        r"\bimpersonat\w*"
        r"|\b(?:pose[sd]?|posing|pretend(?:s|ed|ing)?|masquerad\w*)\s+(?:to be\s+|as\s+)"
        r"(?:\w+\s+){0,2}?(?:customers?|users?|buyers?|people|humans?|founders?|celebrit\w+|brands?|employees?)\b"
        r"|\bposts?\s+as\s+(?:\w+\s+){0,2}?(?:customers?|users?|buyers?|people)\b"
        r"|\bsock ?puppet\w*"
        r"|\bunder\s+(?:different|other|fake|false|made[- ]up|invented|several|many)\s+"
        r"(?:customer|people'?s?|user|buyer|reviewer)?\s*names\b",
        re.IGNORECASE,
    ),
    "income_promise": re.compile(
        r"\bguarantee[sd]?\s+(?:\w+\s+){0,4}?(?:income|earnings|profits?|revenue|returns?|sales|\$|€|£)"
        r"|\bguaranteed\s+(?:\w+\s+){0,2}?(?:income|earnings|profits?|returns?|sales|money)\b",
        re.IGNORECASE,
    ),
}
# Only a counter-measure verb right before the match (at most three words earlier) exempts it,
# so "write fake reviews" is not excused by "detect" elsewhere in the brief.
_COUNTER_MEASURE = re.compile(
    r"\b(?:detect\w*|spot\w*|flag\w*|identif\w*|remov\w*|report\w*|filter\w*|moderat\w*|prevent\w*|"
    r"block\w*|fight\w*|combat\w*|audit\w*|verif\w*|tell apart|distinguish\w*|recogni[sz]\w*|catch\w*|"
    r"tell)\s+(?:\w+\s+){0,3}$", re.IGNORECASE)


def _deceptive_matches(fields: list[str]) -> dict[str, list[str]]:
    found: dict[str, set[str]] = {}
    for field in fields:  # each field separately: words in one field never excuse another
        for category, pattern in DECEPTIVE.items():
            for m in pattern.finditer(field):
                if _COUNTER_MEASURE.search(field[max(0, m.start() - 60):m.start()]):
                    continue
                found.setdefault(category, set()).add(" ".join(m.group(0).lower().split()))
    return {k: sorted(v) for k, v in found.items()}


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
    matches |= _deceptive_matches([brief.idea, brief.problem_statement, brief.target_customer, brief.market,
                                   *brief.values_and_constraints])
    return CategoryScreen(allowed=not matches, matches=matches)
