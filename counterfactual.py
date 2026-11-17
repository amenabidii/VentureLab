"""Counterfactual Challenge: what could change a gate decision, and how to test it.

Deterministic, built from the gate's recorded inputs and the Challenger's
experiments. It names missing evidence, experiments, what would support or
weaken the hypothesis and which gate reconsiders the result. It never says
that more evidence will lead to GO: new evidence can move a decision either way.
"""

from __future__ import annotations

from typing import Any

from agents.challenger import Challenge
from brief import FounderBrief
from gates import MIN_SUPPORTING_FINDINGS, MIN_SUPPORTING_SOURCES, GateResult

NO_GUARANTEE = ("New evidence can strengthen or weaken the case. Running these experiments does not "
                "guarantee a GO decision, customers or income.")
NOT_DEMAND = ("Desk research cannot establish demand or willingness to pay; only experiments with target "
              "customers can.")
SET_PASS_MARK = "Write down the pass mark before you start, as a validation condition in the brief."
PHASE1 = "phase1_evidence_gate (run again with the new evidence)"
PHASE2 = "phase2 validation gate, against the founder's predefined validation conditions"


def _interviews(brief: FounderBrief, problem: str | None = None) -> dict[str, str]:
    subject = f"the problem: {problem}" if problem else "this problem"
    return {
        "name": "Problem interviews" if not problem else "Interviews on the alternative problem",
        "assumption": "A1",
        "method": f"Talk to people who match '{brief.target_customer}' about the last time they dealt with "
                  f"{subject}. Ask what happened and what they did; do not pitch the idea.",
        "support_if": "Most interviewees describe a recent, specific occurrence without being prompted. "
                      + SET_PASS_MARK,
        "weaken_if": "Most cannot recall a recent occurrence, or say it is minor or already solved.",
        "origin": "default",
    }


def _search_again() -> dict[str, str]:
    return {
        "name": "Wider desk research",
        "assumption": "A1",
        "method": "Re-run the investigation with public pages where target customers discuss the problem "
                  "(forums, communities, reviews of existing tools), added as source URLs in the brief.",
        "support_if": "Several different people describe the problem in their own words; these become "
                      "established, relevant findings.",
        "weaken_if": "Relevant sources exist but people describe the problem as rare, minor or solved.",
        "origin": "default",
    }


def _waitlist() -> dict[str, str]:
    return {
        "name": "Honest interest test (Validate phase)",
        "assumption": "A6",
        "method": "A plain page that describes the planned product as not yet built and invites people to "
                  "join a waitlist. No payment, no countdowns, no testimonials.",
        "support_if": "Visitors from the target group join at a rate above the pass mark you set. "
                      + SET_PASS_MARK,
        "weaken_if": "Few visitors join, or those who join are not in the target group.",
        "origin": "default",
    }


def explain(gate: GateResult, brief: FounderBrief, challenge: Challenge | None) -> dict[str, Any]:
    e = gate.evidence
    rule = gate.rule.id
    proposed = [x | {"origin": "challenger"} for x in (challenge.experiments if challenge else [])]
    missing: list[str] = []
    experiments: list[dict[str, Any]] = []
    reconsidered_by = PHASE1
    alternative: dict[str, Any] | None = None

    if rule == "STOP_PROHIBITED_CATEGORY":
        matches = gate.checks[0]["inputs"]["matches"]
        found = "; ".join(k + ": " + ", ".join(v) for k, v in matches.items())
        missing.append(f"Not an evidence question: the product category is not allowed ({found}).")
        reconsidered_by = ("phase1 brief screen, only for a different product outside the prohibited "
                           "categories; no evidence can reverse this decision")
    elif rule == "STOP_FAILED_VALIDATION_CONDITION":
        for c in gate.failed_conditions:
            missing.append(f"Condition '{c['id']}' failed: {c['metric']} = {c['result']:g}, "
                           f"pass mark was {c['minimum']:g}.")
        missing.append("A new hypothesis (different segment or problem); the same test should not be "
                       "re-run until it passes.")
        reconsidered_by = "phase1_evidence_gate, only with a new brief describing a different hypothesis"
    elif rule == "STOP_CONTRADICTED":
        missing.append(f"Sources contradicting the problem statement: {', '.join(e.contradicting_sources)}. "
                       "Missing: any established finding that the problem, or a related one, exists.")
        missing.append("Evidence from the target customers themselves; public comments may not represent them.")
        experiments = [_interviews(brief)]
    elif rule == "PIVOT_ALTERNATIVE_SUPPORTED":
        alt = e.alternatives[0]
        alternative = {"hypothesis": alt["claim"], "based_on": [a["finding"] for a in e.alternatives],
                       "sources": sorted({u for a in e.alternatives for u in a["sources"]})}
        missing.append(f"The founder's statement is contradicted by {', '.join(e.contradicting_sources)} "
                       "and has no established support.")
        missing.append(f"Evidence that the alternative problem is common: so far one finding "
                       f"({alt['finding']}) from {len(alt['sources'])} source(s).")
        experiments = [_interviews(brief, alt["claim"])] + proposed
    elif rule == "REPEAT_MIXED_EVIDENCE":
        missing.append(f"Why sources disagree: supported by {', '.join(e.supporting)}, contradicted by "
                       f"{', '.join(e.contradicting_sources)}. Who has the problem and who does not?")
        experiments = [_interviews(brief)] + proposed
    elif rule == "REPEAT_NO_READABLE_SOURCES":
        missing.append("Any relevant, readable public source: every source was unavailable, empty or "
                       "off-topic. This says nothing about the idea itself.")
        experiments = [_search_again()]
    elif rule == "REPEAT_CLARIFY_AVAILABILITY":
        missing.append("How much time the founder can give: the brief says 0 hours a week.")
        reconsidered_by = "phase1_evidence_gate, with a brief that states the available time"
    else:  # GO_TO_FURTHER_VALIDATION or REPEAT_INSUFFICIENT_EVIDENCE
        if rule == "REPEAT_INSUFFICIENT_EVIDENCE":
            missing.append(
                f"Established, relevant problem findings: {len(e.supporting)} of {MIN_SUPPORTING_FINDINGS} "
                f"needed, from {len(e.supporting_sources)} of {MIN_SUPPORTING_SOURCES} sources needed.")
            if e.needs_review or e.partial:
                missing.append(
                    f"{len(e.needs_review)} needs-review and {len(e.partial)} partial findings do not count. "
                    "A person may check them against their quotes; they never count automatically.")
            if e.off_topic:
                missing.append(f"{len(e.off_topic)} findings were off-topic for this brief and were not counted.")
            experiments = proposed + [_interviews(brief), _search_again()]
        else:
            reconsidered_by = PHASE2
            experiments = proposed + [_interviews(brief), _waitlist()]
        missing.append("Demand and willingness to pay (A6): " + NOT_DEMAND)
        if not brief.validation_conditions:
            missing.append("Validation conditions: none set. Set pass marks before running any experiment.")
    for c in gate.unmeasured_conditions:
        missing.append(f"Condition '{c['id']}' not yet measured ({c['metric']} >= {c['minimum']:g}).")

    seen, unique = set(), []
    for x in experiments:
        if x["name"].lower() not in seen:
            seen.add(x["name"].lower())
            unique.append(x)
    return {
        "decision": gate.decision.value,
        "rule": rule,
        "missing_evidence": missing,
        "alternative_hypothesis": alternative,
        "feasibility_notes": gate.feasibility_notes,
        "experiments": unique[:4],
        "reconsidered_by": reconsidered_by,
        "no_guarantee": NO_GUARANTEE,
    }
