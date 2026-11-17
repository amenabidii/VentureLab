"""Phase 3 (Build), core step "Build the product": MVP scope, user guide and executed checks.

What is real: a scope and acceptance criteria derived only from the brief and the Lean
Canvas (thresholds labelled ASSUMPTION), a DRAFT user guide, and acceptance checks that
actually execute against the files VentureLab generated (store page, policies, guide).
What is STUBBED: generating the MVP's own application code. A passing check here tests
VentureLab's artifacts, not a built product.
"""
from __future__ import annotations

import re
from pathlib import Path

from builder_models import check_content

BANNED = ("testimonial", "five-star", "5-star", "limited time", "only 3 left", "guaranteed", "act now")


def mvp_scope(brief: dict, canvas: dict) -> dict:
    values = brief.get("values_and_constraints", [])
    return {
        "core_job": brief["idea"], "for": brief["target_customer"], "label": "FOUNDER-STATED scope",
        "in_scope": [f"The single core job: {brief['idea']}"],
        "out_of_scope": ["Accounts, payments and integrations beyond the core job",
                         "Any feature not needed to test the riskiest assumption"],
        "constraints": values,
        "acceptance_criteria": [
            {"id": "AC1", "text": "A target customer completes the core job unaided in one session.",
             "label": "ASSUMPTION (threshold set by the founder before testing)"},
            {"id": "AC2", "text": "The output links every point back to its original source.",
             "label": "FOUNDER-STATED (from the idea)" if "link" in brief["idea"].lower() else "ASSUMPTION"},
            {"id": "AC3", "text": "No data is read outside what the user explicitly installs it for.",
             "label": "FOUNDER-STATED (from values/constraints)" if values else "ASSUMPTION"},
        ],
        "riskiest_assumption_first": (canvas.get("summary") or {}).get("founder_assumptions_under_test", [])[:1],
        "code_generation": "STUBBED — VentureLab does not yet generate the MVP's application code.",
    }


def user_guide(brief: dict, scope: dict) -> str:
    text = f"""# Phase 3, step 3: User guide (DRAFT)

> DRAFT for the founder to complete once the MVP exists. The MVP's code is STUBBED; this guide
> describes the intended core job, not delivered features.

## What it is for

{brief['target_customer']}: {brief['problem_statement']}

## Intended core job

{scope['core_job']}

## Getting started (intended)

1. Install or open the product.
2. Do the core job once on your own material.
3. Check every result against its original source before relying on it.

## Limits

- Results can be wrong; the original source is always the reference.
- Constraints honoured: {'; '.join(scope['constraints']) or 'none stated'}.
"""
    check_content(text)
    return text


def acceptance_checks(out: Path, guide_name: str) -> list[dict]:
    """Executed checks over generated artifacts; each records what was actually checked."""
    checks = []

    def add(name: str, passed: bool, detail: str):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    page = out / "phase5_step1_store-page.html"
    guide = (out / guide_name).read_text(encoding="utf-8")
    add("user guide marked DRAFT and code STUBBED", "DRAFT" in guide and "STUBBED" in guide, guide_name)
    add("user guide passes content rules", _passes(guide), "builder_models.check_content")
    for name in ("terms", "privacy", "refund"):
        path = out / f"phase4_step2_{name}-policy-draft.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            add(f"{name} policy is a labelled draft", "DRAFT" in text and "Not legal advice" in text, path.name)
    if page.exists():
        html = page.read_text(encoding="utf-8")
        add("store page has no form, script or external asset",
            not re.search(r"<(form|script|iframe|img)\b|https?://", html, re.I), page.name)
        add("store page checkout disabled and MOCKED", "disabled" in html and "MOCKED" in html, page.name)
        add("store page has no social proof or urgency", not any(b in html.lower() for b in BANNED), page.name)
    return checks


def _passes(text: str) -> bool:
    try:
        check_content(text)
        return True
    except ValueError:
        return False
