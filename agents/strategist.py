"""Phase 2 (Validate), core step "Design the business": a Lean Canvas.

Deterministic: every box is filled only from the founder's brief (FOUNDER-PROVIDED),
from Discover findings with their verified source URLs (ESTABLISHED or NEEDS_REVIEW,
labelled as such), or is written as an explicit ASSUMPTION to test. Nothing is invented:
boxes the inputs cannot fill say so and name the experiment that would fill them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FOUNDER = "FOUNDER-PROVIDED"
ASSUMPTION = "ASSUMPTION"
EVIDENCE = "SOURCED"
UNKNOWN = "UNKNOWN — needs evidence"

BOXES = ["problem", "customer_segments", "unique_value_proposition", "solution", "channels",
         "revenue_streams", "cost_structure", "key_metrics", "unfair_advantage"]


@dataclass
class Entry:
    text: str
    label: str
    sources: list[str] = field(default_factory=list)
    test: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "label": self.label, "sources": self.sources, "test": self.test}


def _verified_urls(finding: dict) -> list[str]:
    return [q["url"] for q in finding.get("quotes", []) if q.get("status") == "verified" and q.get("url")]


def build_lean_canvas(brief: dict, gate: dict, investigation: dict | None, challenge: dict | None) -> dict:
    findings = (investigation or {}).get("findings", [])
    problem_findings = [f for f in findings if f.get("type") == "customer_problem" and _verified_urls(f)]
    experiments = (gate.get("counterfactual") or {}).get("experiments", [])
    first_test = experiments[0]["name"] if experiments else "Problem interviews with target customers"

    canvas: dict[str, list[Entry]] = {box: [] for box in BOXES}
    canvas["problem"].append(Entry(brief["problem_statement"], FOUNDER, test=first_test))
    for f in problem_findings:
        standing = f.get("standing", "assumption")
        label = (f"{EVIDENCE}: ESTABLISHED" if standing == "established"
                 else f"{EVIDENCE}: {standing.upper()} (not established)")
        canvas["problem"].append(Entry(f["claim"], label, _verified_urls(f)))
    canvas["customer_segments"].append(Entry(brief["target_customer"], FOUNDER,
                                             test="Recruit 5–10 people who match this segment for interviews"))
    canvas["unique_value_proposition"].append(Entry(
        f"For {brief['target_customer']}: {brief['idea']}", ASSUMPTION,
        test="Ask interviewees how they handle the problem today before showing the concept"))
    canvas["solution"].append(Entry(brief["idea"], FOUNDER))
    canvas["channels"].append(Entry(f"Reach customers in: {brief['market']}", FOUNDER,
                                    test="Count how many qualified people one channel yields per hour of effort"))
    canvas["revenue_streams"].append(Entry(
        "Willingness to pay is unknown. Desk research cannot establish it.", UNKNOWN,
        test="Pricing questions in interviews, then a priced pre-order or waitlist test (Phase 4 hypotheses)"))
    canvas["cost_structure"].append(Entry(
        f"Founder time: {brief['hours_per_week']:g} hours a week; budget {brief['budget_eur']:g} "
        f"{brief.get('budget_currency') or 'EUR'}; local open-weight model, $0 API cost.", FOUNDER))
    canvas["key_metrics"].append(Entry(
        "Share of interviewees who describe a recent, specific occurrence of the problem; "
        "then waitlist sign-up rate from the landing page.", ASSUMPTION,
        test="Set pass marks in the brief's validation_conditions before running"))
    skills = ", ".join(brief.get("founder_skills", []))
    canvas["unfair_advantage"].append(Entry(
        f"Founder skills: {skills}. Not an advantage until compared with alternatives.", ASSUMPTION,
        test="List existing alternatives interviewees already use"))

    unsupported = [a["id"] for a in (challenge or {}).get("assumptions", [])]
    sourced = sum(1 for box in canvas.values() for e in box if e.label.startswith(EVIDENCE))
    established = sum(1 for box in canvas.values() for e in box if "ESTABLISHED" in e.label)
    return {
        "run_id": gate.get("run_id"),
        "discover_decision": gate.get("decision"),
        "canvas": {box: [e.to_dict() for e in entries] for box, entries in canvas.items()},
        "summary": {"boxes": len(BOXES), "sourced_entries": sourced, "established_entries": established,
                    "unknown_boxes": [b for b, es in canvas.items() if all(e.label == UNKNOWN for e in es)],
                    "founder_assumptions_under_test": unsupported},
        "note": "A Lean Canvas is a set of hypotheses. Labels show where each entry came from; "
                "nothing here is evidence of demand.",
    }


RUBRIC = {
    "problem_evidence": "2 = at least one ESTABLISHED finding cited; 1 = only NEEDS_REVIEW or partial findings "
                        "with verified quotes; 0 = no sourced finding",
    "founder_fit": "2 = the founder's own idea built with the stated skills; 1 = plausible with the stated "
                   "skills but unconfirmed (ASSUMPTION); 0 = no product to build",
    "open_risks": "minus 1 for each unresolved Challenger market risk; market risks apply equally to every "
                  "product option, not to the status quo (total not below 0)",
}


def _evidence_points(ids: list[str], findings: dict[str, dict]) -> tuple[int, list[str]]:
    cited = [findings[i] for i in ids if i in findings and _verified_urls(findings[i])]
    urls = list(dict.fromkeys(u for f in cited for u in _verified_urls(f)))
    if any(f.get("standing") == "established" for f in cited):
        return 2, urls
    return (1 if cited else 0), urls


def score_opportunities(brief: dict, gate: dict, investigation: dict | None, challenge: dict | None) -> dict:
    """Phase 1 core step: score the founder's idea against alternatives found in the run.

    Alternatives come only from the run's own records: the Challenger's new hypotheses,
    the gate's alternative problems (established findings about a different problem), and
    the status quo. A score ranks what to test first; it is never evidence of demand.
    """
    findings = {f["id"]: f for f in (investigation or {}).get("findings", [])}
    problem_ids = [f["id"] for f in findings.values() if f.get("type") == "customer_problem"]
    risks = (challenge or {}).get("risks", [])
    options = [{"option": brief["idea"], "origin": "founder's idea (FOUNDER-PROVIDED)", "evidence_ids": problem_ids,
                "fit": 2, "risk_count": len(risks)}]
    for h in (challenge or {}).get("new_hypotheses", []):
        options.append({"option": h["text"], "origin": f"raised by the Challenger ({h.get('basis', 'ASSUMPTION')})",
                        "evidence_ids": h.get("evidence", []), "fit": 1, "risk_count": len(risks)})
    for alt in (gate.get("evidence") or {}).get("alternatives", []):
        text = alt.get("claim") or alt.get("text") or str(alt)
        options.append({"option": text, "origin": "alternative problem from an established finding",
                        "evidence_ids": alt.get("findings", alt.get("ids", [])), "fit": 1, "risk_count": len(risks)})
    options.append({"option": "Status quo: target customers keep their current workaround",
                    "origin": "baseline", "evidence_ids": [], "fit": 0, "risk_count": 0})
    rows = []
    for o in options:
        ev, urls = _evidence_points(o["evidence_ids"], findings)
        total = max(0, ev + o["fit"] - o["risk_count"])
        rows.append({**o, "problem_evidence": ev, "sources": urls, "score": total})
    rows.sort(key=lambda r: -r["score"])
    best = rows[0]
    any_established = any(r["problem_evidence"] == 2 for r in rows)
    return {"run_id": gate.get("run_id"), "discover_decision": gate.get("decision"), "rubric": RUBRIC,
            "options": rows, "test_first": best["option"],
            "conclusion": ("No option has established evidence; the ranking only orders what to test first."
                           if not any_established else
                           "At least one option has established evidence; it is still not proof of demand."),
            "market": {"definition": brief["market"], "customer": brief["target_customer"], "label": FOUNDER,
                       "size": "UNKNOWN — no sourced market-size figure; none is estimated"}}


def scorecard_markdown(data: dict) -> str:
    rows = "\n".join(f"| {i} | {r['option']} | {r['origin']} | {r['problem_evidence']} | {r['fit']} | "
                     f"{r['risk_count']} | **{r['score']}** | {', '.join(r['sources']) or '—'} |"
                     for i, r in enumerate(data["options"], 1))
    rubric = "\n".join(f"- `{k}`: {v}" for k, v in data["rubric"].items())
    m = data["market"]
    return f"""# Phase 1, step 4: Opportunity scorecard

Discover gate: **{data['discover_decision']}** (run `{data['run_id']}`). {data['conclusion']}

| # | Option | Origin | Evidence | Founder fit | Open risks | Score | Sources |
|---|---|---|---|---|---|---|---|
{rows}

Test first: **{data['test_first']}**

## Rubric (fixed, deterministic)

{rubric}

## Market definition

- Customer: {m['customer']} ({m['label']})
- Market: {m['definition']} ({m['label']})
- Size: {m['size']}
"""


def lean_canvas_markdown(data: dict) -> str:
    lines = ["# Phase 2, step 2: Lean Canvas", "",
             f"Discover gate for this run: **{data['discover_decision']}** (run `{data['run_id']}`).",
             data["note"], ""]
    titles = {"problem": "Problem", "customer_segments": "Customer segments",
              "unique_value_proposition": "Unique value proposition", "solution": "Solution",
              "channels": "Channels", "revenue_streams": "Revenue streams", "cost_structure": "Cost structure",
              "key_metrics": "Key metrics", "unfair_advantage": "Unfair advantage"}
    for box, title in titles.items():
        lines += [f"## {title}", ""]
        for e in data["canvas"][box]:
            text = e["text"] if e["text"].endswith((".", "?", "!")) else e["text"] + "."
            src = f" Sources: {', '.join(e['sources'])}." if e["sources"] else ""
            test = f" Test: {e['test'].rstrip('.')}." if e["test"] else ""
            lines.append(f"- **{e['label']}**: {text}{src}{test}")
        lines.append("")
    s = data["summary"]
    lines += ["## Evidence summary", "",
              f"- Entries backed by a verified quote: {s['sourced_entries']} "
              f"(established: {s['established_entries']})",
              f"- Boxes with no evidence at all: {', '.join(s['unknown_boxes']) or 'none'}", ""]
    return "\n".join(lines)
