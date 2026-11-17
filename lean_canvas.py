"""Lean Canvas for the Validate phase, built from the run without a model.

Every box says what it rests on, so the founder can see at a glance what is known and
what is still assumed:
- EVIDENCE: an ESTABLISHED finding from the research run supports it (with its source URLs);
- FOUNDER-STATED: taken from the founder's own brief, not checked;
- PROPOSED: fixed only when the founder approves the kit (the pass mark);
- ASSUMPTION: untested; the canvas says what would test it.

Nothing is invented: boxes with no input say so instead of being filled with plausible text.
The canvas is part of the Builder bundle, so it is fingerprinted and written only after
founder approval, like the kit.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import HttpUrl, field_validator

from builder_models import BuilderInput, Contract, ExperimentKit, Text, check_content

Basis = Literal["EVIDENCE", "FOUNDER-STATED", "PROPOSED", "ASSUMPTION"]
BOXES = ("Problem", "Customer segments", "Unique value proposition", "Solution", "Channels",
         "Revenue streams", "Cost structure", "Key metrics", "Unfair advantage")


class CanvasBox(Contract):
    name: Literal[BOXES]  # type: ignore[valid-type]
    content: Text
    basis: Basis
    sources: tuple[HttpUrl, ...] = ()
    next_test: Text

    _safe = field_validator("content", "next_test")(check_content)


class LeanCanvas(Contract):
    boxes: tuple[CanvasBox, ...]
    label: Literal["Lean Canvas — working hypotheses, not validated facts"] = (
        "Lean Canvas — working hypotheses, not validated facts")


def _assumption(brief: BuilderInput, marker: str) -> str | None:
    for a in brief.main_assumptions:
        if marker in a:
            return a.split(marker, 1)[1].strip().rstrip(".") or None
    return None


def build_canvas(brief: BuilderInput, kit: ExperimentKit) -> LeanCanvas:
    established = [e for e in brief.supporting_evidence if re.search(r"\[ESTABLISHED\]", e.statement)]
    related = len(brief.supporting_evidence)
    if established:
        problem = CanvasBox(
            name="Problem", content=brief.core_problem, basis="EVIDENCE",
            sources=tuple(dict.fromkeys(e.source_url for e in established))[:5],
            next_test="Confirm in interviews that it happens to the target customers themselves, recently.")
    else:
        problem = CanvasBox(
            name="Problem", content=brief.core_problem, basis="FOUNDER-STATED",
            next_test=(f"Not established by the research run ({related} related quotation(s) were found, none "
                       "established). The approved kit's interviews test it."))
    reach = _assumption(brief, "can be reached in:")
    budget = [c for c in brief.founder_constraints if c.startswith(("Available time:", "Budget:"))]
    criteria = kit.success_criteria
    boxes = (
        problem,
        CanvasBox(name="Customer segments", content=brief.target_customer, basis="FOUNDER-STATED",
                  next_test="Screen interview participants against this description before counting them."),
        CanvasBox(name="Unique value proposition", content="Not yet defined: no evidence yet on what the "
                  "target customers value or how they solve this today.", basis="ASSUMPTION",
                  next_test="Write it after the interviews, in the customers' own words about their current "
                            "workaround."),
        CanvasBox(name="Solution", content=brief.business_idea, basis="FOUNDER-STATED",
                  next_test="Do not show it during problem interviews; test it only after the problem passes."),
        CanvasBox(name="Channels", content=(f"Where the founder expects to reach them: {reach}" if reach else
                  "Not stated."), basis="ASSUMPTION",
                  next_test="Record where each interview participant was actually found; that is the first "
                            "channel evidence."),
        CanvasBox(name="Revenue streams", content="Unknown: no pricing or willingness-to-pay evidence exists.",
                  basis="ASSUMPTION",
                  next_test="Only after the problem passes: ask about what they spend on it today, then test a "
                            "price with a non-binding pre-order or waitlist (never a real or sandbox payment)."),
        CanvasBox(name="Cost structure", content="; ".join(budget) if budget else "Not stated.",
                  basis="FOUNDER-STATED",
                  next_test="List the tools and hours the MVP needs and compare them with this budget and time."),
        CanvasBox(name="Key metrics", content=(f"{criteria.threshold} of {criteria.sample_size}: {criteria.metric}"),
                  basis="PROPOSED",
                  next_test="Record the observed totals against this pass mark after the interviews."),
        CanvasBox(name="Unfair advantage", content="None established.", basis="ASSUMPTION",
                  next_test="Name an advantage only when evidence shows one (access, data, expertise customers "
                            "confirm)."),
    )
    return LeanCanvas(boxes=boxes)


def canvas_markdown(canvas: LeanCanvas) -> str:
    lines = [f"# {canvas.label}", "",
             "Each box states its basis: EVIDENCE (an established research finding, sources listed), "
             "FOUNDER-STATED (from the brief, unchecked), PROPOSED (fixed when the founder approves the kit) "
             "or ASSUMPTION (untested).", "",
             "| Box | Content | Basis | What would test it |", "|---|---|---|---|"]
    for b in canvas.boxes:
        cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
        sources = "".join(f" <{u}>" for u in b.sources)
        lines.append(f"| {b.name} | {cell(b.content)}{cell(sources)} | {b.basis} | {cell(b.next_test)} |")
    return "\n".join(lines) + "\n"
