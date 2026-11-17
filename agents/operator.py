"""Phase 6 (Operate and learn): support triage, metrics and a persevere-or-pivot memo.

Honesty rules enforced here:
- Support requests come only from a file the founder supplies (real requests). With
  none, the report says so; tickets are never generated.
- Metrics computed from the MOCKED sale-to-cash rehearsal are labelled MOCKED and are
  never used as demand evidence by the memo.
- The memo's recommendation is a fixed rule over recorded inputs (the Discover gate and
  any real experiment results in the brief), not a model's opinion.
"""
from __future__ import annotations

import json
from pathlib import Path

CATEGORIES = {"billing": ("refund", "charge", "invoice", "price"),
              "access": ("login", "access", "token", "download"),
              "bug": ("error", "broken", "crash", "bug"),
              "feedback": ()}


def triage_support(inbox: Path | None) -> dict:
    if inbox is None or not inbox.exists():
        return {"source": None, "tickets": [], "counts": {},
                "note": "No real support requests exist yet (the product has not launched). None were generated."}
    tickets = json.loads(inbox.read_text(encoding="utf-8"))
    out = []
    for t in tickets:
        text = str(t.get("text", "")).lower()
        cat = next((c for c, words in CATEGORIES.items() if any(w in text for w in words)), "feedback")
        out.append({"id": t.get("id"), "category": cat, "text": t.get("text")})
    counts: dict[str, int] = {}
    for t in out:
        counts[t["category"]] = counts.get(t["category"], 0) + 1
    return {"source": inbox.name, "tickets": out, "counts": counts, "note": "Real requests supplied by the founder."}


def mocked_metrics(reconciliation: dict) -> dict:
    rows = reconciliation["rows"]
    paid = [r for r in rows if r["paid"]]
    return {"label": "MOCKED — computed from simulated test orders, not customers. Not evidence of demand.",
            "test_orders": len(rows), "paid": len(paid),
            "refunded": sum(1 for r in paid if r["refunded"]),
            "failed": sum(1 for r in rows if not r["paid"]),
            "active_access": sum(1 for r in rows if r["access"] == "active"),
            "reconciliation_balanced": reconciliation["balanced"]}


def persevere_or_pivot(discover: dict, brief: dict, metrics: dict | None, validation: dict | None = None) -> dict:
    """Fixed rules, first match wins. Real customer evidence is the only input that can say PERSEVERE.

    `validation` is the Phase 2 validation gate (`phase2_gate_validation.json`): the founder's
    reported interview results against the threshold approved before any result existed.
    """
    decision = discover["decision"]
    results = brief.get("experiment_results") or {}
    conditions = brief.get("validation_conditions") or []
    failed = [c["id"] for c in conditions if c["metric"] in results and results[c["metric"]] < c["minimum"]]
    v = (validation or {}).get("decision")
    if decision == "STOP":
        rec, rule = "STOP", "Discover gate decided STOP; nothing downstream may proceed."
    elif v == "STOP":
        rec, rule = "PIVOT OR STOP", (f"Founder-reported validation failed the pre-approved threshold "
                                      f"({validation.get('rule')}); do not lower the threshold.")
    elif v == "GO":
        rec, rule = "PERSEVERE", (f"Founder-reported validation met the pre-approved threshold "
                                  f"({validation.get('successes')} of {validation.get('participants')} participants; "
                                  f"{validation.get('rule')}). Continue to Build; this is not proof of a market.")
    elif v == "REPEAT":
        rec, rule = "REPEAT", "The founder's validation experiment is still incomplete; continue it."
    elif failed:
        rec, rule = "PIVOT OR STOP", f"Real experiment results failed pre-set pass marks: {', '.join(failed)}."
    elif decision == "PIVOT":
        rec, rule = "PIVOT", "Discover gate found an established alternative problem to test instead."
    elif conditions and all(c["metric"] in results for c in conditions) and decision == "GO":
        rec, rule = "PERSEVERE", "Discover gate GO and every pre-set pass mark met by real results."
    else:
        rec, rule = "REPEAT", ("Not enough real evidence: the Discover gate decided "
                               f"{decision}, and no real experiment results exist yet.")
    next_steps = [f"{x['name']}: {x['method']}" for x in (discover.get("counterfactual") or {}).get("experiments", [])][:3]
    return {"recommendation": rec, "rule": rule, "discover_decision": decision,
            "validation_gate": ({k: validation.get(k) for k in ("decision", "rule", "participants", "successes",
                                                                 "result_source")} if validation else None),
            "real_experiment_results": results, "mocked_metrics_used_as_evidence": False,
            "mocked_metrics_reference": metrics, "next_steps": next_steps,
            "no_guarantee": "No recommendation here guarantees customers or income."}


def memo_markdown(memo: dict, support: dict) -> str:
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(memo["next_steps"], 1)) or "None recorded."
    m = memo["mocked_metrics_reference"] or {}
    return f"""# Phase 6, step 3: Persevere-or-pivot memo

**Recommendation: {memo['recommendation']}**

Rule applied: {memo['rule']}

## What the decision rests on

- Discover gate: **{memo['discover_decision']}** (fixed rules in `gates.py`).
- Real experiment results recorded: {json.dumps(memo['real_experiment_results']) if memo['real_experiment_results'] else 'none'}.
- Phase 2 validation gate (founder-reported results): {json.dumps(memo['validation_gate']) if memo['validation_gate'] else 'no results recorded yet'}.
- Real support requests: {len(support['tickets'])}. {support['note']}
- MOCKED sale-to-cash metrics were **not** used as evidence ({m.get('label', 'none')}).

## Next steps

{steps}

{memo['no_guarantee']}
"""
