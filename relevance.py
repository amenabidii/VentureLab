"""Deterministic relevance: does a passage or quote talk about the founder's claim?

Relevance is measured by shared key words (lower-cased, plural-stripped,
without stop words and without words that appear in almost any discussion).
It is deliberately simple and explainable: the shared words are recorded with
every decision, so a reader can see why something was kept or set aside.
"""

from __future__ import annotations

import evidence as ev

# Words too general to show that two texts are about the same thing.
GENERIC = frozenset(
    "spend spent spending time too much lot many more most very really work working people person thing "
    "things use used using make makes made get gets got need needs want wants like just also small big "
    "good bad new way ways day days week weeks year years every all some any one two know think".split()
)
MIN_SHARED = 2  # key words a text must share with a claim to count as about it


def key_terms(text: str) -> set[str]:
    return {t for t in ev._terms(text) if t not in GENERIC}


def shared(claim_terms: set[str], text: str) -> set[str]:
    return claim_terms & key_terms(text)


def is_about(claim_terms: set[str], text: str) -> bool:
    return len(shared(claim_terms, text)) >= MIN_SHARED


class BriefTerms:
    """Key words of a founder brief, split so that customer words alone never make
    a text relevant. "Indie game developers" in a comment about playing indie games
    is about the customer, not about their problem; a relevant text must also share
    two words specific to the problem (for the topic: two words specific to the
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
