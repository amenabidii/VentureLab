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
        r"trading (?:signals?|bots?|tips)|day[- ]trading|forex|stock[- ](?:picks?|picking|pickers?|tips|signals?)|"
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
        r"\s*(?:counts?|numbers?|totals?)\b"
        # Reviews or testimonials written by the seller, not by customers.
        r"|\b(?:writ(?:e|es|ing)|generat(?:e|es|ed|ing)|creat(?:e|es|ed|ing)|produc(?:e|es|ed|ing)|draft(?:s|ed|ing)?|"
        r"post(?:s|ed|ing)?|invent(?:s|ed|ing)?|ghostwrit\w*)\s+(?:\w+\s+){0,3}?"
        r"(?:testimonials?|(?:customer |user |buyer |product |positive |glowing )?reviews?\s+(?:for|of|about|on)\s+"
        r"(?:my|our|the|his|her|their)\b)"
        r"|\b(?:fake|false|fabricated|manufactured)\s+social proof\b"
        r"|\b(?:look|looks|seem|seems|appear|appears)\s+(?:like|as if)\s+(?:[\d,]+|many|lots of|hundreds of|"
        r"thousands of|millions of)\s+(?:people|users|customers|buyers)\b",
        re.IGNORECASE,
    ),
    "fake_urgency_or_scarcity": re.compile(
        r"\b(?:fake|false|artificial|manufactured|invented)\s+(?:\w+\s+){0,1}?(?:urgency|scarcity|countdowns?|"
        r"deadlines?|stock (?:levels?|counts?))\b"
        r"|\b(?:always|perpetual|evergreen|resetting|fake)\s+(?:\w+\s+){0,2}?(?:countdown|timer|scarcity)\w*"
        r"|\bonly \d+ (?:left|remaining)\b"
        # A sales countdown that restarts per visitor or page load is a fake deadline.
        r"|\b(?:countdowns?|timers?)\s+(?:\w+\s+){0,2}?(?:that|which)\s+(?:\w+\s+)?resets?\s+(?:for|on|when|with|at|"
        r"after)\s+(?:\w+\s+){0,2}?(?:visit\w*|page|load|reload|refresh\w*|customers?|buyers?|users?|sessions?)\b",
        re.IGNORECASE,
    ),
    "impersonation": re.compile(
        r"\bimpersonat\w*"
        r"|\b(?:pose[sd]?|posing|pretend(?:s|ed|ing)?|masquerad\w*)\s+(?:to be\s+|as\s+)"
        r"(?:\w+\s+){0,2}?(?:customers?|users?|buyers?|people|humans?|founders?|celebrit\w+|brands?|employees?)\b"
        r"|\bposts?\s+as\s+(?:\w+\s+){0,2}?(?:customers?|users?|buyers?|people)\b"
        r"|\bsock ?puppet\w*"
        r"|\bunder\s+(?:different|other|fake|false|made[- ]up|invented|several|many)\s+"
        r"(?:customer|people'?s?|user|buyer|reviewer)?\s*names\b"
        r"|\b(?:sign(?:s|ed|ing)?|writ(?:e|es|ing)|post(?:s|ed|ing)?|repl(?:y|ies|ied|ying)|email(?:s|ed|ing)?|"
        r"messag(?:e|es|ed|ing)|tweet(?:s|ed|ing)?|send(?:s|ing)?)\s+(?:\w+\s+){0,3}?as\s+(?:the\s+|a\s+)?"
        r"(?:founder|ceo|owner|official|spokes\w+|support team|staff)\s+(?:of|at|from|for)\b",
        re.IGNORECASE,
    ),
    "income_promise": re.compile(
        r"\bguarantee[sd]?\s+(?:\w+\s+){0,4}?(?:income|earnings|profits?|revenue|returns?|sales|\$|€|£)"
        r"|\bguaranteed\s+(?:\w+\s+){0,2}?(?:income|earnings|profits?|returns?|sales|money)\b"
        r"|\bpromis(?:e|es|ed|ing)\s+(?:\w+\s+){0,5}?(?:(?:passive |extra |monthly |steady )?income|earnings|"
        r"profits?|returns|to make money|make money|get rich|financial freedom|\$|€|£)",
        re.IGNORECASE,
    ),
}
# Speaking as a named brand ("reply to tweets as Nike"): case-sensitive, a capitalised name after "as",
# excluding words that commonly follow "as" in an honest brief (formats, languages, roles).
_AS_BRAND = re.compile(
    r"\b(?:[Ss]ign(?:s|ed|ing)?|[Ww]rit(?:e|es|ing)|[Pp]ost(?:s|ed|ing)?|[Rr]epl(?:y|ies|ied|ying)|"
    r"[Ee]mail(?:s|ed|ing)?|[Tt]weet(?:s|ed|ing)?|[Cc]omment(?:s|ed|ing)?|[Ss]peak(?:s|ing)?|[Rr]espond(?:s|ed|ing)?)"
    r"\s+(?:\w+\s+){0,3}?as\s+(?!(?:PDF|PDFs|HTML|CSV|JSON|Markdown|English|Arabic|French|Spanish|German|I|We|"
    r"You|Monday|Friday|Slack|Python|Gmail)\b)[A-Z][\w&.'-]+")
_SOLICIT = re.compile(r"\b(?:ask\w*|invit\w*|request\w*|remind\w*|encourag\w*|help\w*|let\w*|allow\w*|collect\w*)"
                      r"\s+(?:\w+\s+){0,3}$", re.IGNORECASE)
# Only a counter-measure verb right before the match (at most three words earlier) exempts it,
# so "write fake reviews" is not excused by "detect" elsewhere in the brief.
_COUNTER_MEASURE = re.compile(
    r"\b(?:detect\w*|spot\w*|flag\w*|identif\w*|remov\w*|report\w*|filter\w*|moderat\w*|prevent\w*|"
    r"block\w*|fight\w*|combat\w*|audit\w*|verif\w*|tell apart|distinguish\w*|recogni[sz]\w*|catch\w*|"
    r"tell)\s+(?:\w+\s+){0,3}$", re.IGNORECASE)


# --- broader wording: paraphrases, other languages, leetspeak (added after red-teaming) ---------
_R = r"(?:reviews?|reveiws?|reviws?|revews?)"
_EXTRA_PROHIBITED: dict[str, re.Pattern[str]] = {
    "physical_goods": re.compile(
        r"\b(?:sells? and ships?|ships? (?:\w+\s+){0,2}?(?:orders|products|goods|items|worldwide)|"
        r"deliver(?:ed|s|y)? to (?:your|their|the) (?:door|home)|handmade soaps?|printed mugs?|sneakers|"
        r"print[- ]on[- ]demand)\b", re.IGNORECASE),
    "financial_investment_or_crypto": re.compile(
        r"\b(?:web3|presales?|meme ?coins?|(?:community|new) coins?|minted|mint(?:ing)? nfts?|solana|blockchain|"
        r"shares to buy|stocks to buy|options trading|trading alerts?|sports betting|betting tips|bets|gambling|"
        r"casinos?|sportsbook|lottery)\b", re.IGNORECASE),
    "health_advice": re.compile(
        r"\b(?:(?:online |ai |virtual )therap(?:y|ists?)|therap(?:y|ist) (?:chatbots?|bots?|apps?|advice|sessions?)|"
        r"telehealth|nutritionists?|symptoms?|vitamins?|herbal remed\w*|"
        r"(?:for|treat\w*|cure\w*)\s+(?:people with\s+)?(?:depression|anxiety|insomnia|adhd|diabet\w*)|"
        r"meal plans? for diabet\w*|likely condition)\b", re.IGNORECASE),
    "legal_advice": re.compile(
        r"\b(?:lawyers|attorneys|tax returns?|deductions? to claim|divorce|wills? and (?:testaments?|divorce)|"
        r"ndas?|employment contracts?|which clauses)\b", re.IGNORECASE),
}
_EXTRA_DECEPTIVE: dict[str, re.Pattern[str]] = {
    "fake_reviews_or_social_proof": re.compile(
        r"\b(?:\d+|fifty|twenty|hundred|a hundred|dozens of)\s+(?:\w+\s+){0,1}?(?:five|5)[- ]?(?:stars?|\*)\s*"
        r"(?:\w+\s+){0,1}?(?:" + _R[3:-1] + r"|ratings?)"
        r"|\b(?:write|writes|writing|make|makes|compose|draft|type out|leave|leaves|leaving|seed|seeding|"
        r"generate|generates|create|creates|produce|post|posts)\s+"
        r"(?:(?!(?:to|on|of|about|replies|responses|answers|summar\w*|reports?|weekly|monthly|code|peer|performance|"
        r"book|film|movie|game|paper|academic|literature)\b)\w+\s+){0,4}?(?:reviews|reveiws|reviws|revews)\b"
        r"|\b(?:fake|bogus|paid|invented|fabricated|made[- ]up)\s+(?:\w+\s+){0,2}?" + _R
        + r"|\bastroturf\w*|\bsock ?puppets?\b|\bai[- ](?:written|generated)\s+(?:\w+\s+){0,2}?(?:"
        + _R[3:-1] + r"|testimonials?)"
        r"|\b(?:negative|bad|1[- ]star|one[- ]star)\s+(?:" + _R[3:-1] + r"|ratings?)\s+(?:\w+\s+){0,3}?competitors?"
        r"|\b(?:buy|buys|buying|purchase|purchasing|sell|selling)\s+(?:\w+\s+){0,3}?"
        r"(?:followers|likes|upvotes|views|subscribers)\b"
        r"|\b(?:bot|fake|multiple|several|many|different)\s+accounts?\s+(?:that|to|which)?\s*(?:\w+\s+){0,2}?"
        r"(?:upvote|like|comment|review|vote|praise)"
        r"|\b(?:testimonials?|" + _R[3:-1] + r")\s+(?:from|by|written by)\s+(?:\w+\s+){0,1}?"
        r"(?:ai|fictional|made[- ]up|synthetic|bots?)\b"
        r"|\bpersonas?\s+(?:who|that|to)\s+(?:\w+\s+){0,1}?(?:leave|write|post|give)\s+(?:\w+\s+){0,1}?"
        r"(?:testimonials?|" + _R[3:-1] + r")"
        r"|\bin the voice of\s+(?:\w+\s+){0,2}?(?:buyers|customers|users|clients|reviewers)\b"
        r"|\bfake\s+sign\s+ups?\b|\bmade[- ]up\s+(?:e-?mails?|names|users|accounts|sign[- ]?ups?)\b"
        r"|\bfill\w*\s+(?:\w+\s+){0,2}?(?:waitlist|wait list)\s+with\b"
        r"|\bas if\s+(?:it|they)\s+(?:were|was|are)\s+(?:real\s+)?(?:users|customers|people|buyers)\b"
        r"|faux (?:avis|témoignages|commentaires)|avis (?:\w+\s+){0,2}?(?:bidons?|inventés)"
        r"|(?:تقييم\w*|مراجع\w*|شهاد\w*)[^.]{0,40}(?:مزيف\w*|وهمي\w*|مزور\w*)"
        r"|(?:مزيف\w*|وهمي\w*|مزور\w*)[^.]{0,40}(?:تقييم\w*|مراجع\w*|شهاد\w*)", re.IGNORECASE),
    "fake_urgency_or_scarcity": re.compile(
        r"\bonly (?:\d+|a few|few|a handful of)\s+(?:spots?|seats?|copies|places|units|items|licen[cs]es|pieces|"
        r"slots|left|remaining)\b|\b(?:limited stock|almost sold out|selling out fast|low stock)\b"
        r"|\bends? in \d+ (?:minutes|hours|seconds)\s+(?:\w+\s+){0,2}?(?:every|each)\s+(?:new\s+)?"
        r"(?:visitor|user|customer|buyer)", re.IGNORECASE),
    "income_promise": re.compile(
        r"(?:income|earnings|profits?|revenue|returns?|money|\$[\d,.]+k?)\s+(?:\w+\s+){0,4}?guaranteed\b"
        r"|\bmake (?:you |them )?rich\b|\bget[- ]rich\b|\b(?:results|income|earnings|profits?) "
        r"(?:assured|guaranteed)\b|\bcertain to (?:double|triple|increase|grow)\b", re.IGNORECASE),
    "phishing_credentials_or_private_data": re.compile(
        r"\bphish\w*|\b(?:collect|harvest|steal|capture)\w*\s+(?:\w+\s+){0,3}?(?:passwords?|credentials|logins?|"
        r"card numbers?)\b|\blogin page that looks like\b|\blooks? like (?:\w+\s+){0,3}?(?:login|sign[- ]in) page"
        r"|\bstor(?:e|es|ing)\s+(?:\w+\s+){0,2}?(?:card numbers?|credit cards?|cvvs?)\b"
        r"|\bscrap(?:e|es|ing)\s+(?:\w+\s+){0,4}?(?:private|personal)\b", re.IGNORECASE),
}
_LEET = str.maketrans({"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t", "@": "a", "$": "s"})
# A founder's own value ("No fake reviews", "never promise income") states the rule; it does not ask
# to break it. Only honoured in the values-and-constraints field.
_NEGATION = re.compile(r"\b(?:no|never|not|avoid\w*|without|refus\w*|ban\w*|forbid\w*|zero|don'?t|won'?t|"
                       r"against)\s+(?:\w+\s+){0,2}$", re.IGNORECASE)


# "for real buyers to leave reviews": the reviews are written by the buyers themselves.
_BY_BUYERS = re.compile(r"\b(?:buyers|customers|users|clients|guests|patients|readers|students)\s+(?:to\s+)?$",
                        re.IGNORECASE)


def _deleet(text: str) -> str:
    """'f4ke r3views' -> 'fake reviews'; digits next to spaces or symbols (50, 5-star, $5) are kept."""
    return re.sub(r"(?<=[a-z])[0134579@$]+|[0134579@$]+(?=[a-z])", lambda m: m.group(0).translate(_LEET),
                  text, flags=re.IGNORECASE)


def _deceptive_matches(fields: list[str], values: frozenset[str] = frozenset()) -> dict[str, list[str]]:
    found: dict[str, set[str]] = {}
    patterns = [(c, p) for c, p in DECEPTIVE.items()] + [(c, p) for c, p in _EXTRA_DECEPTIVE.items()]
    for raw in fields:  # each field separately: words in one field never excuse another
      for field in dict.fromkeys((raw, _deleet(raw))):
        for category, pattern in patterns:
            for m in pattern.finditer(field):
                before = field[max(0, m.start() - 60):m.start()]
                if _COUNTER_MEASURE.search(before):
                    continue
                if raw in values and _NEGATION.search(before):
                    continue
                # "ask real customers to write reviews for our shop" is the honest way to get reviews.
                if category == "fake_reviews_or_social_proof" and (_SOLICIT.search(before) or _BY_BUYERS.search(before)):
                    continue
                found.setdefault(category, set()).add(" ".join(m.group(0).lower().split()))
        for m in _AS_BRAND.finditer(field):
            if not _COUNTER_MEASURE.search(field[max(0, m.start() - 60):m.start()]):
                found.setdefault("impersonation", set()).add(" ".join(m.group(0).lower().split()))
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
        found = {m.group(0).lower() for t in dict.fromkeys((text, _deleet(text))) for m in pattern.finditer(t)}
        extra = _EXTRA_PROHIBITED.get(category)
        if extra:
            found |= {m.group(0).lower() for t in dict.fromkeys((text, _deleet(text))) for m in extra.finditer(t)}
        if found:
            matches[category] = sorted(found)
    matches |= _deceptive_matches([brief.idea, brief.problem_statement, brief.target_customer, brief.market,
                                   *brief.founder_skills, *brief.values_and_constraints], frozenset(brief.values_and_constraints))
    return CategoryScreen(allowed=not matches, matches=matches)


# --- second extension (probe set) ---
_PROBE_DECEPTIVE = {
 "fake_reviews_or_social_proof": (
   r"\b(?:five|5)[- ]star\s+(?:reviews?|ratings?)\b"
   r"|\b(?:buy|buys|buying|purchase[sd]?|purchasing)\s+(?:\w+\s+){0,2}?(?:followers|likes|upvotes|reviews?|ratings?|sign-?ups?)\b"
   r"|\bbot accounts?\b|\bsock[- ]?puppet\w*|\bastroturf\w*"
   r"|\b(?:reviews?|ratings?|testimonials?)\b(?:\W+\w+){0,6}?\W+(?:personas?|on behalf of|never existed|non-?existent|imaginary|fictional)\b"
   r"|\b(?:customers?|users?|clients?|people|buyers?)\s+(?:who|that)\s+never\s+existed\b"
   r"|\bfake\s+users?\b"
   r"|\b\d+\s+people\s+are\s+(?:viewing|watching|looking at|buying)\b"),
 "fake_urgency_or_scarcity": (
   r"\bcountdowns?\b(?:\W+\w+){0,8}?\W+reset\w*"
   r"|\bonly\s+\d+\s+(?:\w+\s+){0,2}?(?:left|remaining)\b"
   r"|\b(?:never|doesn'?t|does not|won'?t|will not)\s+(?:actually\s+|really\s+)?expires?\b"
   r"|\beven though (?:it|they|that) (?:won'?t|will not|isn'?t|is not|doesn'?t)\b"
   r"|\bregardless of (?:the )?(?:real|actual) (?:stock|inventory|demand|availability)\b"),
 "impersonation": (
   r"\b(?:pretend\w*|pose[sd]?|posing)\s+(?:to be|as)\s+[A-Z][\w&.'-]+"
   r"|\bas (?:if|though) (?:it|they|the \w+) (?:came|come|comes|were|was) (?:from|written by|sent by)\b"
   r"|\b(?:tells?|claims?)\s+(?:\w+\s+){0,2}?(?:it|she|he)\s+is\s+(?:a\s+)?(?:human|real person)\b"),
 "income_promise": (
   r"\bguarantee\w*\b(?:\W+\w+){0,8}?\W+(?:income|earn\w*|make|profits?|revenue|returns?|money|\$|€|£)"
   r"|(?:\$|€|£)\s?[\d,.]+k?\b(?:\W+\w+){0,5}?\W+guarantee\w*"
   r"|\bget[- ]rich\b"
   r"|\b(?:certain|sure|ensur\w*|promis\w*)\s+(?:\w+\s+){0,3}?(?:to\s+)?(?:earn|make)\s+(?:\w+\s+){0,2}?(?:income|money|\$|€|£|\d)"),
}
_PROBE_PROHIBITED = {
 "financial_investment_or_crypto": r"\b(?:\w+coins?|web3|airdrops?|ICOs?|staking|yield farming|tokens? to buy|which (?:stocks?|tokens?|coins?) to buy|(?:sports )?betting|gambl\w*|casinos?)\b",
 "health_advice": r"\b(?:anxiety|depression|diabet\w*|meal plans?|nutrition (?:plans?|advice)|mental health)\b",
 "legal_advice": r"\b(?:legal (?:questions?|help|rights)|evictions?|tenants?'? rights|power of attorney)\b",
}
for k, extra in _PROBE_DECEPTIVE.items():
    DECEPTIVE[k] = re.compile(DECEPTIVE[k].pattern + "|" + extra, re.IGNORECASE)
for k, extra in _PROBE_PROHIBITED.items():
    PROHIBITED[k] = re.compile(PROHIBITED[k].pattern + "|" + extra, re.IGNORECASE)
# impersonation brand rule must be case-sensitive for [A-Z]; compile separately
DECEPTIVE["impersonation"] = re.compile(DECEPTIVE["impersonation"].pattern, re.IGNORECASE)
