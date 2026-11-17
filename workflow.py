"""Phases 2 (Lean Canvas) and 4–6 for a completed Discover run, with founder gates.

    python workflow.py plan    --run outputs/runs/<run-id>
    python workflow.py approve <action> <sha256> --reason "..."   (founder types: APPROVE <action>)
    python workflow.py prepare-launch --run outputs/runs/<run-id>
    python workflow.py launch  --run outputs/runs/<run-id>

Gates, enforced in code:
- STOP from the Discover gate blocks every later phase.
- REPEAT or PIVOT allows later phases only as a REHEARSAL, after an explicit founder
  approval (`rehearse_after_<decision>`); every rehearsal artifact is labelled.
- Phase 4: the price is the founder's approved choice (`set_price:<option>`), never a model's.
- Phase 5: publishing the store page (MOCKED) needs approval of the exact page fingerprint;
  automatic delivery (MOCKED) needs approval of the exact product file fingerprint.
- Phase 6: the persevere-or-pivot memo uses fixed rules over real evidence only.

Approvals live in `<state>/workflow_approvals.json`, each signed with a founder key in
`<state>/workflow.founder` (created on first approval, mode 600). A hand-edited or
re-used approval for different content fails verification. Every action is appended to
`decision_log.json`. Nothing is published, sent, spent or signed: those steps are MOCKED.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents.commercial import pricing_hypotheses, pricing_markdown, policy_drafts, product_name
from agents.launcher import launch_posts, store_page_html
from agents.operator import memo_markdown, mocked_metrics, persevere_or_pivot, triage_support
from agents.product import acceptance_checks, mvp_scope, user_guide
from agents.strategist import build_lean_canvas, lean_canvas_markdown, score_opportunities, scorecard_markdown
from audit import AuditLog
from config import get_settings
from delivery import DeliveryService
from payments import MockPaymentProvider, Order
from reconcile import reconcile

AGENTS = {1: "strategist", 2: "strategist", 3: "product", 4: "commercial", 5: "launcher", 6: "operator"}


class GateBlocked(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- founder approvals ------------------------------------------------------------------

class Approvals:
    def __init__(self, state_dir: Path):
        self.state = state_dir
        self.file = state_dir / "workflow_approvals.json"
        self.key_file = state_dir / "workflow.founder"

    def _key(self, create: bool) -> bytes:
        if self.key_file.is_symlink():
            raise GateBlocked("Founder key file must not be a symlink")
        if not self.key_file.exists():
            if not create:
                raise GateBlocked("No founder approvals exist yet")
            self.state.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_hex(32))
        return self.key_file.read_text().strip().encode()

    def _mac(self, key: bytes, record: dict) -> str:
        body = json.dumps({k: record[k] for k in ("action", "sha256", "decision", "reason", "at")}, sort_keys=True)
        return hmac.new(key, body.encode(), hashlib.sha256).hexdigest()

    def records(self) -> list[dict]:
        return json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else []

    def record(self, action: str, digest: str, decision: str, reason: str) -> dict:
        key = self._key(create=True)
        rec = {"action": action, "sha256": digest, "decision": decision, "reason": reason, "at": now(),
               "decided_by": "founder"}
        rec["mac"] = self._mac(key, rec)
        self.file.write_text(json.dumps(self.records() + [rec], indent=1), encoding="utf-8")
        return rec

    def approved(self, action: str, digest: str) -> bool:
        if not self.key_file.exists():
            return False
        key = self._key(create=False)
        latest = None
        for rec in self.records():
            if rec.get("action") == action and rec.get("sha256") == digest:
                if not hmac.compare_digest(rec.get("mac", ""), self._mac(key, rec)):
                    raise GateBlocked(f"Approval record for {action} failed verification")
                latest = rec
        return bool(latest and latest["decision"] == "approve")

    def chosen(self, prefix: str, digest: str) -> str | None:
        for rec in reversed(self.records()):
            if rec["action"].startswith(prefix) and rec["sha256"] == digest and self.approved(rec["action"], digest):
                return rec["action"][len(prefix):]
        return None


# --- run context ----------------------------------------------------------------------------

class Context:
    def __init__(self, run_dir: Path, out: Path, log: Path, state: Path):
        self.run_dir, self.out = run_dir, out
        load = lambda name: (json.loads((run_dir / name).read_text(encoding="utf-8"))  # noqa: E731
                             if (run_dir / name).exists() else None)
        self.gate = load("phase1_gate_decision.json")
        brief_doc = load("phase1_step1_founder_brief.json")
        if not self.gate or not brief_doc:
            raise SystemExit(f"{run_dir} is not a completed Discover run (gate decision or brief missing)")
        self.brief = brief_doc["brief"]
        self.investigation = load("phase1_step2_investigation.json")
        self.challenge = load("phase1_step3_challenge.json")
        self.run_id = self.gate["run_id"]
        self.decision = self.gate["decision"]
        self.gate_sha = sha256((run_dir / "phase1_gate_decision.json").read_bytes())
        # The later phases are their own execution, linked to (not mixed into) the Discover run.
        self.log = AuditLog(log, f"{self.run_id}:phases-2-6")
        self.approvals = Approvals(state)
        self.rehearsal = self.decision != "GO"
        out.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, content: str | dict) -> tuple[str, str]:
        text = json.dumps(content, indent=1, ensure_ascii=False) + "\n" if isinstance(content, dict) else content
        data = text.encode("utf-8")
        (self.out / name).write_bytes(data)  # exact bytes: the printed fingerprint is the file's fingerprint
        return name, sha256(data)

    def rec(self, phase: int, action: str, outcome: str, *, approved=False, sources=None, **extra):
        self.log.record(AGENTS.get(phase, "gate"), action, sources=sources or [], model=None, cost=0,
                        approved_by="founder" if approved else None, outcome=outcome, phase=phase,
                        rehearsal=self.rehearsal, discover_run_id=self.run_id, **extra)

    def gate_file(self, phase: int, name: str, decision: str, checks: list[dict], approvals: list[str]):
        return self.write(f"phase{phase}_gate_{name}.json", {
            "run_id": self.run_id, "phase": phase, "decision": decision, "checks": checks,
            "founder_approvals": approvals, "discover_decision": self.decision,
            "rehearsal": self.rehearsal, "decided_by": "fixed rules in workflow.py"})

    def require_rehearsal_approval(self):
        if self.decision == "STOP":
            self.rec(4, "gate_check", "blocked: Discover gate decided STOP")
            raise GateBlocked("Discover gate decided STOP: later phases are blocked")
        if self.rehearsal:
            action = f"rehearse_after_{self.decision.lower()}"
            if not self.approvals.approved(action, self.gate_sha):
                self.rec(4, "gate_check", f"blocked: needs founder approval {action}")
                raise GateBlocked(f"Discover decided {self.decision}. To rehearse later phases anyway, the "
                                  f"founder must approve: {action} {self.gate_sha}")


# --- commands -------------------------------------------------------------------------------

def plan(ctx: Context) -> list[str]:
    """Phase 1 scorecard, Phase 2 Lean Canvas, then Phase 3 scope and Phase 4 drafts. Nothing is chosen."""
    card = score_opportunities(ctx.brief, ctx.gate, ctx.investigation, ctx.challenge)
    ctx.write("phase1_step4_opportunity-scorecard.json", card)
    ctx.write("phase1_step4_opportunity-scorecard.md", scorecard_markdown(card))
    ctx.rec(1, "score_against_alternatives", f"{len(card['options'])} options; test first: {card['test_first'][:80]}",
            sources=sorted({u for r in card["options"] for u in r["sources"]}))
    canvas = build_lean_canvas(ctx.brief, ctx.gate, ctx.investigation, ctx.challenge)
    sources = [s for box in canvas["canvas"].values() for e in box for s in e["sources"]]
    ctx.write("phase2_step2_lean-canvas.json", canvas)
    ctx.write("phase2_step2_lean-canvas.md", lean_canvas_markdown(canvas))
    ctx.rec(2, "build_lean_canvas", "drafted", sources=sources)
    complete = all(canvas["canvas"][b] for b in canvas["canvas"])
    ctx.gate_file(2, "lean-canvas", "REVIEW" if complete else "REPEAT",
                  [{"check": "every box filled or marked UNKNOWN", "passed": complete},
                   {"check": "revenue streams evidenced", "passed": "revenue_streams" not in canvas["summary"]["unknown_boxes"]}],
                  [])
    ctx.rec(2, "lean_canvas_gate", "founder review required; demand not evidenced")

    ctx.require_rehearsal_approval()
    scope = mvp_scope(ctx.brief, canvas)
    ctx.write("phase3_step2_mvp-scope.json", scope)
    ctx.write("phase3_step3_user-guide-draft.md", user_guide(ctx.brief, scope))
    ctx.rec(3, "define_mvp_scope_and_guide", "drafted; MVP code generation STUBBED")
    pricing = pricing_hypotheses(ctx.brief, ctx.decision)
    _, p_sha = ctx.write("phase4_step1_pricing.json", pricing)
    ctx.write("phase4_step1_pricing.md", pricing_markdown(pricing))
    ctx.rec(4, "draft_pricing_hypotheses", "drafted", options=[o["id"] for o in pricing["options"]])
    for kind, text in policy_drafts(ctx.brief).items():
        ctx.write(f"phase4_step2_{kind}-policy-draft.md", text)
    ctx.rec(4, "draft_policies", "drafted: terms, privacy, refund (DRAFT, not legal advice)")
    # The gate always reflects the recorded approval state, so re-running plan never contradicts it.
    choice = ctx.approvals.chosen("set_price:", p_sha)
    if choice:
        ctx.gate_file(4, "commercial", "REHEARSAL GO" if ctx.rehearsal else "GO (founder approved price)",
                      [{"check": "price chosen by founder", "passed": True, "choice": choice}], [f"set_price:{choice}"])
        return [f"price already approved by the founder: {choice}"]
    ctx.gate_file(4, "commercial", "AWAITING FOUNDER", [{"check": "price chosen by founder", "passed": False}], [])
    needed = [f"set_price:<{'|'.join(o['id'] for o in pricing['options'])}> {p_sha}"]
    return needed


def prepare_launch(ctx: Context) -> list[str]:
    ctx.require_rehearsal_approval()
    pricing_path = ctx.out / "phase4_step1_pricing.json"
    p_sha = sha256(pricing_path.read_bytes())
    choice = ctx.approvals.chosen("set_price:", p_sha)
    if not choice:
        ctx.rec(4, "commercial_gate", "blocked: no founder-approved price for this pricing file")
        raise GateBlocked(f"Founder must choose a price first: set_price:<option> {p_sha}")
    pricing = json.loads(pricing_path.read_text(encoding="utf-8"))
    option = next(o for o in pricing["options"] if o["id"] == choice)
    ctx.write("phase4_step1_pricing-decision.md",
              pricing_markdown({**pricing, "founder_choice": choice}))
    ctx.gate_file(4, "commercial", "GO (founder approved price)" if not ctx.rehearsal else "REHEARSAL GO",
                  [{"check": "price chosen by founder", "passed": True, "choice": choice}], [f"set_price:{choice}"])
    ctx.rec(4, "commercial_gate", f"price approved: {choice}", approved=True)

    product = product_name(ctx.brief)
    _, page_sha = ctx.write("phase5_step1_store-page.html", store_page_html(product, ctx.brief, option,
                                                                             rehearsal=ctx.rehearsal))
    ctx.write("phase5_step1_launch-posts.md", launch_posts(product, ctx.brief, option))
    ctx.rec(5, "draft_store_page_and_posts", "drafted; not published, not posted")
    package = (f"# {product}: early-access package (MOCKED digital product)\n\nThis file stands in for the "
               f"product a buyer receives after a (MOCKED) payment. It contains no real product yet.\n\n"
               f"Price option: `{choice}`. Rehearsal: {ctx.rehearsal}.\n")
    _, prod_sha = ctx.write("phase5_step2_mock-product.md", package)
    checks = acceptance_checks(ctx.out, "phase3_step3_user-guide-draft.md")
    ctx.write("phase3_step4_acceptance-checks.json", {"run_id": ctx.run_id, "checks": checks,
                                                      "scope": "VentureLab's generated artifacts; MVP code STUBBED"})
    passed = all(c["passed"] for c in checks)
    ctx.gate_file(3, "build", "ARTIFACTS PASSED (MVP code STUBBED)" if passed else "REPEAT", checks, [])
    ctx.rec(3, "run_acceptance_checks", f"{sum(c['passed'] for c in checks)}/{len(checks)} passed")
    return [f"publish_store_page {page_sha}", f"enable_mock_delivery {prod_sha}"]


def launch(ctx: Context) -> dict:
    ctx.require_rehearsal_approval()
    page = ctx.out / "phase5_step1_store-page.html"
    product_file = ctx.out / "phase5_step2_mock-product.md"
    if not page.exists() or not product_file.exists():
        raise GateBlocked("Run prepare-launch first")
    build_gate = ctx.out / "phase3_gate_build.json"
    if not build_gate.exists() or not all(c["passed"] for c in json.loads(build_gate.read_text(encoding="utf-8"))["checks"]):
        ctx.rec(5, "launch_gate", "blocked: Phase 3 acceptance checks have not all passed")
        raise GateBlocked("Phase 3 acceptance checks must pass before launch")
    page_sha, prod_sha = sha256(page.read_bytes()), sha256(product_file.read_bytes())
    missing = [a for a, d in (("publish_store_page", page_sha), ("enable_mock_delivery", prod_sha))
               if not ctx.approvals.approved(a, d)]
    if missing:
        ctx.rec(5, "launch_gate", f"blocked: missing founder approval {', '.join(missing)}")
        ctx.gate_file(5, "launch", "BLOCKED", [{"check": f"founder approved {m}", "passed": False} for m in missing], [])
        raise GateBlocked("Missing founder approval: " + ", ".join(
            f"{m} {page_sha if m == 'publish_store_page' else prod_sha}" for m in missing))
    ctx.rec(5, "publish_store_page", "MOCKED: published to local preview only, nothing online", approved=True,
            sha256=page_sha)

    # Sale-to-cash rehearsal with SIMULATED test buyers (no people, no money).
    provider = MockPaymentProvider()
    delivery = DeliveryService(provider, prod_sha, founder_approved=True)
    pricing = json.loads((ctx.out / "phase4_step1_pricing.json").read_text(encoding="utf-8"))
    choice = ctx.approvals.chosen("set_price:", sha256((ctx.out / "phase4_step1_pricing.json").read_bytes()))
    price = next(o for o in pricing["options"] if o["id"] == choice)["price_eur_per_month"]
    amount = max(price, 1) * 100
    orders = [Order(f"ord_test_{i}", f"test-buyer-{i}", "early-access", amount) for i in range(1, 5)]
    steps = []

    def deliver(event, signature=None, label=""):
        result = delivery.handle(event, signature or provider.sign(event))
        steps.append({"step": label, "event": event["id"], "type": event["type"], "order": event["order_id"],
                      "result": result})

    e1 = provider.checkout(orders[0])
    deliver(e1, label="paid order")
    deliver(e1, label="same webhook delivered twice")
    e2 = provider.checkout(orders[1])
    deliver(e2, label="paid order")
    deliver(provider.refund(orders[1]), label="refund")
    deliver(provider.checkout(orders[2], succeed=False), label="declined payment")
    forged = provider.checkout(orders[3])
    deliver(forged, signature="0" * 64, label="forged signature")
    deliver(forged, label="same event, valid signature")
    payout = provider.payout("payout_test_1")
    recon = reconcile(orders, provider.events, delivery.grants, payout)
    expected = ["delivered", "duplicate_event_ignored", "delivered", "access_revoked", "no_delivery_payment_failed",
                "rejected_bad_signature", "delivered"]
    checks = [{"check": s["step"], "expected": exp, "actual": s["result"], "passed": s["result"] == exp}
              for s, exp in zip(steps, expected)]
    checks.append({"check": "reconciliation balanced", "passed": recon["balanced"], "mismatches": recon["mismatches"]})
    passed = all(c["passed"] for c in checks)
    ctx.write("phase5_step3_reconciliation.json", recon)
    ctx.write("payment_test_log.md", payment_log_markdown(ctx, steps, recon, checks, price))
    for s in steps:
        ctx.rec(5, "mock_payment_event", s["result"], event=s["event"], order=s["order"])
    ctx.rec(5, "reconcile", "balanced" if recon["balanced"] else "mismatch", mismatches=recon["mismatches"])
    ctx.gate_file(5, "launch", ("REHEARSAL PASSED" if ctx.rehearsal else "GO") if passed else "REPEAT", checks,
                  ["publish_store_page", "enable_mock_delivery"])

    support = triage_support(ctx.run_dir / "support_inbox.json")
    ctx.write("phase6_step1_support.json", support)
    ctx.rec(6, "triage_support", f"{len(support['tickets'])} real requests")
    metrics = mocked_metrics(recon)
    ctx.write("phase6_step2_metrics.json", metrics)
    ctx.rec(6, "compute_metrics", "MOCKED metrics from test orders")
    vpath = ctx.run_dir / "phase2_gate_validation.json"
    validation = json.loads(vpath.read_text(encoding="utf-8")) if vpath.exists() else None
    memo = persevere_or_pivot(ctx.gate, ctx.brief, metrics, validation)
    ctx.write("phase6_step3_persevere-or-pivot-memo.json", memo)
    ctx.write("phase6_step3_persevere-or-pivot-memo.md", memo_markdown(memo, support))
    ctx.gate_file(6, "persevere-or-pivot", memo["recommendation"],
                  [{"check": "real experiment results available", "passed": bool(memo["real_experiment_results"])},
                   {"check": "mocked metrics excluded from evidence", "passed": True}], [])
    ctx.rec(6, "persevere_or_pivot", memo["recommendation"], rule=memo["rule"])
    return {"payment_tests_passed": passed, "memo": memo["recommendation"]}


def payment_log_markdown(ctx: Context, steps, recon, checks, price) -> str:
    rows = "\n".join(f"| {s['step']} | `{s['event']}` | {s['type']} | {s['order']} | {s['result']} |" for s in steps)
    crow = "\n".join(f"| {c['check']} | {'pass' if c['passed'] else 'FAIL'} |" for c in checks)
    return f"""# Payment and delivery test log (MOCKED)

Run `{ctx.run_id}` · {now()} · Discover gate **{ctx.decision}**{' · REHEARSAL' if ctx.rehearsal else ''}.

Everything below is a local simulation produced by `workflow.py launch`: a MOCKED payment provider
(`payments.py`), SIMULATED test buyers, signed webhook events, automatic delivery (`delivery.py`),
refunds that revoke access (`refunds.py`) and reconciliation (`reconcile.py`). No payment of any kind,
no sandbox, no card data, no money, no people. Test price: €{price}/month.

## Events

| Step | Event | Type | Order | Result |
|---|---|---|---|---|
{rows}

## Reconciliation

Gross {recon['gross_cents']} · fees {recon['fees_cents']} (MOCKED fee schedule) · refunds {recon['refunds_cents']}
· expected net {recon['expected_net_cents']} · payout net {recon['payout_net_cents']} (cents).
Mismatches: {', '.join(recon['mismatches']) or 'none'}.

## Checks

| Check | Result |
|---|---|
{crow}
"""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=Path("outputs"))
    p.add_argument("--log", type=Path, default=Path("decision_log.json"))
    p.add_argument("--state", type=Path, default=Path(get_settings().state_dir))
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "prepare-launch", "launch"):
        sp = sub.add_parser(name)
        sp.add_argument("--run", type=Path, required=True)
    ap = sub.add_parser("approve", help="founder decision; confirm by typing 'APPROVE <action>'")
    ap.add_argument("action")
    ap.add_argument("sha256")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--reject", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.cmd == "approve":
            decision = "reject" if args.reject else "approve"
            typed = sys.stdin.readline().strip()
            if typed != f"{decision.upper()} {args.action}":
                print(f"Not recorded. Type exactly: {decision.upper()} {args.action}", file=sys.stderr)
                return 2
            rec = Approvals(args.state).record(args.action, args.sha256, decision, args.reason)
            AuditLog(args.log, "workflow-approvals").record(
                "approval", f"founder_{decision}", model=None, cost=0,
                approved_by="founder" if decision == "approve" else None,
                outcome=f"{decision}: {args.action}", sha256=args.sha256, reason=args.reason)
            print(json.dumps({k: rec[k] for k in ("action", "sha256", "decision", "at")}, indent=1))
            return 0
        ctx = Context(args.run, args.out, args.log, args.state)
        result = {"plan": plan, "prepare-launch": prepare_launch, "launch": launch}[args.cmd](ctx)
        print(json.dumps(result, indent=1))
        return 0
    except GateBlocked as exc:
        print(f"Gate blocked: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
