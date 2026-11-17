"""Deterministic relevance: does a passage or quote talk about the founder's claim?

Method (no model, no external service):
1. Words are lower-cased and lightly normalised ("writing", "writes", "write"
   -> "writ"; "notes" -> "not"), and stop words plus words that appear in almost
   any discussion ("time", "people", "work" ...) are dropped.
2. A small, fixed concept list maps synonyms and multi-word phrases to one
   concept: "changelog", "change log", "release notes", "patch notes" all become
   `release_notes`; "bug", "defect", "glitch" become `bug`. The list is
   hand-written, short and printed in full below, so every match can be checked.
3. Relevance is decided by shared concepts, never by customer words alone:
   a text is about the founder's problem statement only if it shares at least
   two key concepts with it, at least two of them specific to the problem
   (not to the customer description); one concept is enough only when the
   problem itself has only one.

Limitations (by design, documented rather than hidden):
- Synonyms outside the concept list are not recognised ("ship notes" is not
  `release_notes`), so relevant material can be missed. Missing material lowers
  recall; it cannot make an irrelevant text count, which is the safe direction.
- Sharing concepts is not sharing meaning: a text can mention the same concepts
  and still be about something else ("release notes became a communication
  channel" shares `release_notes` with "teams spend too long on release notes").
  Relevance only decides what is looked at and counted; whether a quote SUPPORTS
  a claim is decided by the evidence assessment and the rules in evidence.py and
  agents/challenger.py.
- Negation and sarcasm are not understood here.
"""

from __future__ import annotations

import re

import evidence as ev

# Words too general to show that two texts are about the same thing.
GENERIC = frozenset(
    "spend spent spending time too much lot many more most very really work working people person thing "
    "things use used using make makes made get gets got need needs want wants like just also small big "
    "good bad new way ways day days week weeks year years every all some any one two know think".split()
)
MIN_SHARED = 2  # key concepts a text must share with a claim to count as about it

_TOKEN = re.compile(r"[a-z0-9]+")


def normalise(word: str) -> str:
    """Light, predictable suffix stripping; not a full stemmer."""
    for suffix in ("ings", "ing", "ed", "es", "s", "e"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _n(text: str) -> tuple[str, ...]:
    return tuple(normalise(t) for t in text.split())


# Phrases (two words) are matched before single words. Keep this list short and general.
PHRASES: dict[tuple[str, ...], str] = {
    _n("release notes"): "release_notes",
    _n("release note"): "release_notes",
    _n("patch notes"): "release_notes",
    _n("change log"): "release_notes",
    _n("pull request"): "pull_request",
    _n("pull requests"): "pull_request",
    _n("merge request"): "pull_request",
    _n("bug report"): "bug_report",
    _n("bug reports"): "bug_report",
    _n("issue report"): "bug_report",
    _n("crash report"): "bug_report",
    _n("customer support"): "support",
    _n("help desk"): "support",
}
WORDS: dict[str, str] = {normalise(k): v for k, v in {
    "changelog": "release_notes", "changelogs": "release_notes",
    "bug": "bug", "bugs": "bug", "defect": "bug", "defects": "bug", "glitch": "bug", "glitches": "bug",
    "invoice": "invoice", "invoices": "invoice", "invoicing": "invoice", "bill": "invoice", "bills": "invoice",
    "pay": "pay", "paid": "pay", "paying": "pay", "payment": "pay", "payments": "pay",
    "client": "customer", "clients": "customer", "customer": "customer", "customers": "customer",
    "docs": "documentation", "documentation": "documentation",
    "developer": "developer", "developers": "developer", "programmer": "developer", "programmers": "developer",
    "dev": "developer", "devs": "developer",
}.items()}


def concepts(text: str) -> list[str]:
    """Normalised tokens of a text with phrases and synonyms mapped to concepts."""
    tokens = [normalise(t) for t in _TOKEN.findall(text.lower())]
    out: list[str] = []
    i = 0
    while i < len(tokens):
        pair = tuple(tokens[i:i + 2])
        if len(pair) == 2 and pair in PHRASES:
            out.append(PHRASES[pair])
            i += 2
            continue
        out.append(WORDS.get(tokens[i], tokens[i]))
        i += 1
    return out


_DROP = {normalise(w) for w in ev._STOP} | {normalise(w) for w in GENERIC}


def key_terms(text: str) -> set[str]:
    return {c for c in concepts(text) if c not in _DROP and len(c) > 2}


def shared(claim_terms: set[str], text: str) -> set[str]:
    return claim_terms & key_terms(text)


def is_about(claim_terms: set[str], text: str) -> bool:
    return len(shared(claim_terms, text)) >= MIN_SHARED


class BriefTerms:
    """Key concepts of a founder brief, split so that customer words alone never make
    a text relevant. "Indie game developers" in a comment about playing indie games
    is about the customer, not about their problem; a relevant text must also share
    two concepts specific to the problem (for the topic: two concepts specific to the
    problem or the idea). An on-topic finding can be offered as an alternative
    hypothesis, so it must be about the same kind of problem, not just the same people."""

    def __init__(self, problem_statement: str, idea: str, target_customer: str) -> None:
        customer = key_terms(target_customer)
        self.statement = key_terms(problem_statement)
        self.topic = self.statement | key_terms(idea) | customer
        self.problem = (self.statement - customer) or self.statement
        self.core = ((self.statement | key_terms(idea)) - customer) or self.topic

    def statement_match(self, text: str) -> set[str] | None:
        shared_terms = shared(self.statement, text)
        if len(shared_terms) >= MIN_SHARED and len(shared_terms & self.problem) >= min(MIN_SHARED, len(self.problem)):
            return shared_terms
        return None

    def topic_match(self, text: str) -> set[str] | None:
        shared_terms = shared(self.topic, text)
        if len(shared_terms) >= MIN_SHARED and len(shared_terms & self.core) >= min(MIN_SHARED, len(self.core)):
            return shared_terms
        return None
