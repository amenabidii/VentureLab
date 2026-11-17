"""Milestone 2 -> Milestone 3 adapter: a finished Discover run becomes a BuilderInput.

Reads the run's recorded outputs (brief, investigation, challenge, gate) and maps
them field by field. Nothing is invented:
- the founder's own words are used for idea, customer, problem and constraints;
- assumptions are the Challenger's numbered founder assumptions, each tagged with
  the code-computed basis and stance (uncertainty stays visible in the kit);
- evidence references are verified quotations only, tagged with their standing;
  every EvidenceReference is UNVERIFIED_CONTEXT by Milestone 3's contract;
- the gate outcome is passed as GateContext, so Milestone 3's own rules apply:
  STOP blocks the Builder, REPEAT and PIVOT get an experiment kit only, and a
  landing page is prepared only after GO.
A landing-page spec is built only for GO, from the founder's own text, with a
neutral product name rather than an invented brand.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from brief import FounderBrief
from builder_models import BuilderInput, EvidenceReference, GateContext, LandingPageSpec
from gates import RULESET_VERSION

EVIDENCE_STANDINGS = ("established", "needs_review", "partial_evidence", "contradicted", "unsupported")
MAX_QUOTE = 600


class BuilderBlocked(RuntimeError):
    """The Builder must not run for this run (with the reason)."""


@dataclass
class Adapted:
    builder_input: BuilderInput
    landing_page: LandingPageSpec | None
    notes: list[str] = field(default_factory=list)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_outputs(out_dir: Path) -> dict[str, Any]:
    """The recorded outputs of one run (missing files are missing, not empty)."""
    names = {"brief": "phase1_step1_founder_brief.json", "investigation": "phase1_step2_investigation.json",
             "challenge": "phase1_step3_challenge.json", "gate": "phase1_gate_decision.json"}
    return {key: _read(out_dir / name) for key, name in names.items() if (out_dir / name).exists()}


def adapt(run_id: str, outputs: dict[str, Any]) -> Adapted:
    if "gate" not in outputs or "brief" not in outputs:
        raise BuilderBlocked("The run has no recorded gate decision yet")
    gate = outputs["gate"]
    outcome, rule = gate["decision"], gate["rule"]
    if outcome == "STOP":
        raise BuilderBlocked(f"The gate decided STOP ({rule}); the Builder is blocked for this run")
    version = gate.get("ruleset_version")
    if version != RULESET_VERSION:
        raise BuilderBlocked(
            f"This run's {outcome} decision was made by superseded gate rules (version {version or 1}; "
            f"current version {RULESET_VERSION}). The recorded decision is kept as history, but the Builder "
            "cannot use it: run the analysis again to get a decision under the current rules")
    brief = FounderBrief.model_validate(outputs["brief"]["brief"])
    notes: list[str] = []

    reviews = (outputs.get("challenge") or {}).get("reviews") or []
    assumptions: list[str] = []
    if outcome == "PIVOT" and gate.get("counterfactual", {}).get("alternative_hypothesis"):
        alt = gate["counterfactual"]["alternative_hypothesis"]
        assumptions.append(f"Alternative to test (from finding {', '.join(alt['based_on'])}): {alt['hypothesis']}")
    for r in reviews:
        assumptions.append(f"{r['assumption']} ({r['basis']}; stance {r['stance']}): {r['assumption_text']}")
    if not reviews:
        assumptions.append(f"A1 (not reviewed by the Challenger): {brief.problem_statement}")
        notes.append("Challenger output unavailable: only the founder's problem statement is used as an assumption.")

    evidence: list[EvidenceReference] = []
    skipped = 0
    for f in (outputs.get("investigation") or {}).get("findings", []):
        if f.get("standing") not in EVIDENCE_STANDINGS or f.get("relevance") == "off_topic":
            continue
        for q in f.get("quotes", []):
            if q.get("status") != "verified" or not q.get("url") or len(evidence) >= 20:
                continue
            text = q["text"].strip()
            text = text if len(text) <= MAX_QUOTE else text[:MAX_QUOTE].rsplit(" ", 1)[0] + " [...]"
            try:
                evidence.append(EvidenceReference(statement=f"{f['id']} [{f['standing'].upper()}] {text}",
                                                  source_url=q["url"]))
            except ValidationError:
                skipped += 1
    if skipped:
        notes.append(f"{skipped} quotation(s) were left out because they fail the Builder's content policy.")

    constraints = [*brief.values_and_constraints,
                   f"Available time: {brief.hours_per_week:g} hours per week",
                   f"Budget: {brief.budget_eur:g} {brief.budget_currency}",
                   f"Gate decision {outcome} by rule {rule}; this kit tests assumptions, it does not confirm them"]
    try:
        builder_input = BuilderInput(
            run_id=run_id, business_idea=brief.idea, target_customer=brief.target_customer,
            core_problem=brief.problem_statement, main_assumptions=tuple(assumptions[:12]),
            supporting_evidence=tuple(evidence), founder_constraints=tuple(constraints[:12]),
            product_category="digital_product",
            gate_context=GateContext(decision_id=run_id, outcome=outcome),
        )
    except ValidationError as exc:
        reasons = "; ".join(sorted({e.get("msg", "invalid") for e in exc.errors()}))[:300]
        raise BuilderBlocked(f"The run's content cannot be passed to the Builder: {reasons}") from exc

    landing = None
    if outcome == "GO":
        try:
            landing = LandingPageSpec(product_name="Proposed concept", headline=brief.problem_statement,
                                      value_proposition=brief.idea, target_audience=brief.target_customer,
                                      problem=brief.problem_statement, proposed_solution=brief.idea,
                                      features=(brief.idea,))
        except ValidationError as exc:
            raise BuilderBlocked("The brief cannot be rendered as a local landing page under the content policy") from exc
    else:
        notes.append(f"No landing page: the gate decided {outcome}, and a landing page is only prepared after GO.")
    return Adapted(builder_input, landing, notes)
