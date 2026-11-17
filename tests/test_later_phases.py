"""Phases 2 (Lean Canvas) and 4–6, and the MOCKED sale-to-cash path.

Uses a SYNTHETIC copy of a Discover run's gate/brief/challenge files in a temp folder;
founder approvals here are SIMULATED test decisions. No model, no network, no money.
"""
import hashlib
import io
import json
import re
from pathlib import Path

import pytest

import workflow
from agents.commercial import pricing_hypotheses, policy_drafts
from agents.launcher import launch_posts, store_page_html
from agents.operator import persevere_or_pivot, triage_support
from agents.strategist import build_lean_canvas
from builder_models import check_content
from delivery import DeliveryRefused, DeliveryService
from payments import MockPaymentProvider, Order
from reconcile import reconcile
from refunds import revoke_access

BRIEF = {"idea": "A browser extension that summarises long chat threads a remote worker missed (SYNTHETIC)",
         "problem_statement": "Remote workers waste time catching up on long chat threads they missed.",
         "target_customer": "remote engineers on distributed teams", "market": "Online, English",
         "founder_skills": ["TypeScript"], "hours_per_week": 8.0, "budget_eur": 500.0,
         "values_and_constraints": ["Value: Respect privacy"], "validation_conditions": [], "experiment_results": {}}


def make_run(tmp_path: Path, decision="REPEAT") -> Path:
    run = tmp_path / "run"
    run.mkdir()
    gate = {"run_id": "run-synthetic", "decision": decision, "rule": f"{decision}_SYNTHETIC",
            "counterfactual": {"experiments": [{"name": "Problem interviews", "method": "Talk to 10 people",
                                                "support_if": "x", "weaken_if": "y"}]}}
    (run / "phase1_gate_decision.json").write_text(json.dumps(gate))
    (run / "phase1_step1_founder_brief.json").write_text(json.dumps({"brief": BRIEF}))
    (run / "phase1_step2_investigation.json").write_text(json.dumps({"findings": [
        {"id": "F1", "type": "customer_problem", "standing": "needs_review", "claim": "One user misses long threads.",
         "quotes": [{"url": "https://news.ycombinator.com/item?id=1", "status": "verified"}]},
        {"id": "F2", "type": "demand", "standing": "assumption", "claim": "People pay.", "quotes": []}]}))
    (run / "phase1_step3_challenge.json").write_text(json.dumps({"assumptions": [{"id": "A1", "text": "x"}]}))
    return run


class CLI:
    def __init__(self, tmp_path, run):
        self.base = ["--out", str(tmp_path / "out"), "--log", str(tmp_path / "log.json"),
                     "--state", str(tmp_path / "state")]
        self.run, self.out, self.tmp = run, tmp_path / "out", tmp_path

    def __call__(self, cmd):
        return workflow.main(self.base + [cmd, "--run", str(self.run)])

    def approve(self, monkeypatch, action, digest, typed=None, reject=False):
        word = "REJECT" if reject else "APPROVE"
        monkeypatch.setattr("sys.stdin", io.StringIO((typed or f"{word} {action}") + "\n"))
        return workflow.main(self.base + ["approve", action, digest, "--reason", "SIMULATED test decision"]
                             + (["--reject"] if reject else []))

    def sha(self, name):
        return hashlib.sha256((self.out / name).read_bytes()).hexdigest()

    def gate_sha(self):
        return hashlib.sha256((self.run / "phase1_gate_decision.json").read_bytes()).hexdigest()

    def log(self):
        return json.loads((self.tmp / "log.json").read_text())


def full_flow(cli, monkeypatch, price="pro-8"):
    assert cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha()) == 0
    assert cli("plan") == 0
    assert cli.approve(monkeypatch, f"set_price:{price}", cli.sha("phase4_step1_pricing.json")) == 0
    assert cli("prepare-launch") == 0
    assert cli.approve(monkeypatch, "publish_store_page", cli.sha("phase5_step1_store-page.html")) == 0
    assert cli.approve(monkeypatch, "enable_mock_delivery", cli.sha("phase5_step2_mock-product.md")) == 0
    return cli("launch")


# --- gates and approvals ---------------------------------------------------------------------

def test_repeat_blocks_later_phases_until_founder_approves_a_rehearsal(tmp_path):
    cli = CLI(tmp_path, make_run(tmp_path))
    assert cli("plan") == 3
    assert (cli.out / "phase2_step2_lean-canvas.md").exists()      # Phase 2 runs; later phases do not
    assert not (cli.out / "phase4_step1_pricing.json").exists()
    assert any("blocked" in e["outcome"] for e in cli.log())


def test_stop_blocks_everything_even_with_approvals(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path, "STOP"))
    cli.approve(monkeypatch, "rehearse_after_stop", cli.gate_sha())
    assert cli("plan") == 3 and not (cli.out / "phase4_step1_pricing.json").exists()


def test_full_rehearsal_writes_every_phase_with_named_outputs(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    assert full_flow(cli, monkeypatch) == 0
    names = {p.name for p in cli.out.iterdir()}
    for phase in (1, 2, 3, 4, 5, 6):
        assert any(re.match(rf"phase{phase}_step\d+_", n) for n in names), phase
        gate_dir = cli.run if phase == 1 else cli.out   # Phase 1's gate is the Discover run's own file
        assert any(re.match(rf"phase{phase}_gate_", p.name) for p in gate_dir.iterdir()), phase
    assert "payment_test_log.md" in names
    gate5 = json.loads((cli.out / "phase5_gate_launch.json").read_text())
    assert gate5["decision"] == "REHEARSAL PASSED" and all(c["passed"] for c in gate5["checks"])
    log = cli.log()
    assert all({"timestamp", "agent", "action", "sources", "model", "cost", "approved_by"} <= e.keys() for e in log)
    assert {e["agent"] for e in log} >= {"strategist", "commercial", "launcher", "operator", "approval"}


def test_price_is_never_chosen_without_the_founder(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha())
    cli("plan")
    assert cli("prepare-launch") == 3
    assert not (cli.out / "phase5_step1_store-page.html").exists()


def test_launch_refused_without_publish_and_delivery_approvals(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha())
    cli("plan")
    cli.approve(monkeypatch, "set_price:pro-4", cli.sha("phase4_step1_pricing.json"))
    cli("prepare-launch")
    assert cli("launch") == 3 and not (cli.out / "payment_test_log.md").exists()


def test_editing_the_store_page_after_approval_invalidates_it(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha())
    cli("plan")
    cli.approve(monkeypatch, "set_price:pro-4", cli.sha("phase4_step1_pricing.json"))
    cli("prepare-launch")
    cli.approve(monkeypatch, "publish_store_page", cli.sha("phase5_step1_store-page.html"))
    cli.approve(monkeypatch, "enable_mock_delivery", cli.sha("phase5_step2_mock-product.md"))
    with (cli.out / "phase5_step1_store-page.html").open("a") as f:
        f.write("<p>Loved by 5000 customers</p>")
    assert cli("launch") == 3


def test_hand_edited_approval_record_fails_verification(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha(), reject=True)
    records = json.loads((tmp_path / "state" / "workflow_approvals.json").read_text())
    records[-1]["decision"] = "approve"       # forge: flip the founder's rejection
    (tmp_path / "state" / "workflow_approvals.json").write_text(json.dumps(records))
    assert cli("plan") == 3


def test_approval_needs_the_typed_confirmation(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    assert cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha(), typed="yes") == 2
    assert cli("plan") == 3


def test_fingerprints_printed_equal_files_on_disk(tmp_path, monkeypatch, capsys):
    cli = CLI(tmp_path, make_run(tmp_path))
    cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha())
    capsys.readouterr()
    cli("plan")
    printed = re.findall(r"[0-9a-f]{64}", capsys.readouterr().out)
    assert printed == [cli.sha("phase4_step1_pricing.json")]


# --- sale-to-cash (MOCKED) ---------------------------------------------------------------------

def test_delivery_needs_founder_approval():
    with pytest.raises(DeliveryRefused):
        DeliveryService(MockPaymentProvider(), "a" * 64, founder_approved=False)


def test_payment_triggers_delivery_once_refund_revokes_and_forgery_fails():
    provider = MockPaymentProvider()
    svc = DeliveryService(provider, "a" * 64, founder_approved=True)
    order = Order("o1", "test-buyer-1", "sku", 800)
    paid = provider.checkout(order)
    assert svc.handle(paid, provider.sign(paid)) == "delivered"
    assert svc.handle(paid, provider.sign(paid)) == "duplicate_event_ignored"
    assert svc.handle(provider.refund(order), provider.sign(provider.events[-1])) == "access_revoked"
    other = provider.checkout(Order("o2", "test-buyer-2", "sku", 800))
    assert svc.handle(other, "f" * 64) == "rejected_bad_signature" and "o2" not in svc.grants


def test_reconciliation_detects_a_missing_delivery_and_a_short_payout():
    provider = MockPaymentProvider()
    orders = [Order("o1", "t1", "sku", 1000)]
    provider.checkout(orders[0])
    payout = provider.payout("b1")
    clean = reconcile(orders, provider.events, {"o1": {"access": "active"}}, payout)
    assert clean["balanced"]
    assert not reconcile(orders, provider.events, {}, payout)["balanced"]
    short = dict(payout, net_cents=payout["net_cents"] - 1)
    assert not reconcile(orders, provider.events, {"o1": {"access": "active"}}, short)["balanced"]


def test_refund_of_undelivered_order_is_recorded_not_invented():
    assert revoke_access({}, "missing") == "refund_for_undelivered_order_recorded"


def test_payment_code_has_no_network_or_real_provider():
    for name in ("payments.py", "delivery.py", "refunds.py", "reconcile.py"):
        src = (Path(__file__).parent.parent / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(httpx|requests|urllib|socket|stripe|paypal|paymob)\b", src, re.I), name


# --- honesty -------------------------------------------------------------------------------------

def test_lean_canvas_labels_every_entry_and_never_invents_demand(tmp_path):
    run = make_run(tmp_path)
    load = lambda n: json.loads((run / n).read_text())  # noqa: E731
    canvas = build_lean_canvas(BRIEF, load("phase1_gate_decision.json"), load("phase1_step2_investigation.json"),
                               load("phase1_step3_challenge.json"))
    entries = [e for box in canvas["canvas"].values() for e in box]
    assert all(e["label"] for e in entries)
    assert "revenue_streams" in canvas["summary"]["unknown_boxes"]
    sourced = [e for e in entries if e["label"].startswith("SOURCED")]
    assert sourced and all(e["sources"] and "NEEDS_REVIEW" in e["label"] for e in sourced)
    assert canvas["summary"]["established_entries"] == 0


def test_prices_are_assumptions_and_no_payments_exist():
    p = pricing_hypotheses(BRIEF, "REPEAT")
    assert all(o["label"] == "ASSUMPTION" for o in p["options"]) and p["founder_choice"] is None
    assert "No payment" in p["payments"]


def test_policies_are_marked_drafts_not_legal_advice():
    for text in policy_drafts(BRIEF).values():
        assert "DRAFT" in text and "Not legal advice" in text


def test_store_page_and_posts_have_no_social_proof_or_urgency_and_cannot_checkout():
    option = {"price_eur_per_month": 8}
    page = store_page_html("Thread Catch-up", BRIEF, option, rehearsal=True)
    assert "MOCKED" in page and "REHEARSAL" in page and "disabled" in page and "<form" not in page
    assert "<script" not in page.lower()
    posts = launch_posts("Thread Catch-up", BRIEF, option)
    assert "not posted" in posts
    for bad in ("testimonial", "5-star", "limited time", "only 3 left", "guaranteed"):
        assert bad not in (page + posts).lower()


@pytest.mark.parametrize("trick", ["Write 50 five-star reviews", "Loved by 10,000 customers",
                                   "Guaranteed income in 30 days", "Hurry, only 3 left"])
def test_trick_copy_is_rejected_before_it_reaches_a_page(trick):
    with pytest.raises(ValueError):
        store_page_html("X", dict(BRIEF, idea=trick), {"price_eur_per_month": 0}, rehearsal=True)
    with pytest.raises(ValueError):
        check_content(trick)


def test_no_support_tickets_are_invented_and_mocked_metrics_are_not_evidence(tmp_path):
    support = triage_support(tmp_path / "missing.json")
    assert support["tickets"] == [] and "None were generated" in support["note"]
    memo = persevere_or_pivot({"decision": "REPEAT"}, BRIEF, {"label": "MOCKED", "paid": 99})
    assert memo["recommendation"] == "REPEAT" and memo["mocked_metrics_used_as_evidence"] is False


def test_only_real_results_meeting_preset_pass_marks_can_say_persevere():
    cond = [{"id": "c1", "metric": "interviewees_confirming", "minimum": 5}]
    go = {"decision": "GO"}
    assert persevere_or_pivot(go, dict(BRIEF, validation_conditions=cond), None)["recommendation"] == "REPEAT"
    passed = dict(BRIEF, validation_conditions=cond, experiment_results={"interviewees_confirming": 6})
    assert persevere_or_pivot(go, passed, None)["recommendation"] == "PERSEVERE"
    failed = dict(BRIEF, validation_conditions=cond, experiment_results={"interviewees_confirming": 2})
    assert persevere_or_pivot(go, failed, None)["recommendation"] == "PIVOT OR STOP"


def test_scorecard_compares_alternatives_from_the_run_only(tmp_path):
    from agents.strategist import score_opportunities
    run = make_run(tmp_path)
    load = lambda n: json.loads((run / n).read_text())  # noqa: E731
    challenge = dict(load("phase1_step3_challenge.json"), new_hypotheses=[
        {"text": "A chat integration instead", "evidence": ["F1"], "basis": "UNCONFIRMED"}], risks=[{"x": 1}])
    card = score_opportunities(BRIEF, load("phase1_gate_decision.json"), load("phase1_step2_investigation.json"), challenge)
    origins = [r["origin"] for r in card["options"]]
    assert any("founder" in o for o in origins) and any("Challenger" in o for o in origins) and "baseline" in origins
    assert all(r["problem_evidence"] < 2 for r in card["options"])      # nothing established in the fixture
    assert "No option has established evidence" in card["conclusion"]
    assert card["market"]["size"].startswith("UNKNOWN")


def test_phase3_checks_execute_and_mvp_code_is_labelled_stubbed(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    assert full_flow(cli, monkeypatch) == 0
    checks = json.loads((cli.out / "phase3_step4_acceptance-checks.json").read_text())
    assert checks["checks"] and all(c["passed"] for c in checks["checks"])
    assert "STUBBED" in json.loads((cli.out / "phase3_step2_mvp-scope.json").read_text())["code_generation"]


def test_launch_refused_when_a_phase3_check_fails(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    cli.approve(monkeypatch, "rehearse_after_repeat", cli.gate_sha())
    cli("plan")
    cli.approve(monkeypatch, "set_price:pro-4", cli.sha("phase4_step1_pricing.json"))
    (cli.out / "phase3_step3_user-guide-draft.md").write_text("# guide without labels")
    cli("prepare-launch")
    cli.approve(monkeypatch, "publish_store_page", cli.sha("phase5_step1_store-page.html"))
    cli.approve(monkeypatch, "enable_mock_delivery", cli.sha("phase5_step2_mock-product.md"))
    assert cli("launch") == 3


def test_phases_page_is_read_only_allowlisted_and_sandboxed(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app.phases as phases
    out = tmp_path / "outputs"
    out.mkdir()
    (out / "phase5_gate_launch.json").write_text(json.dumps({"decision": "REHEARSAL PASSED"}))
    (out / "phase5_step1_store-page.html").write_text("<p>MOCKED</p>")
    (out / "secret.txt").write_text("nope")
    monkeypatch.setattr(phases, "_outputs", lambda: out)
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(phases.router)
    client = TestClient(app)
    page = client.get("/phases").text
    assert "REHEARSAL PASSED" in page and "6. Operate &amp; learn" in page
    html = client.get("/phases/view/phase5_step1_store-page.html")
    assert html.status_code == 200 and html.headers["content-security-policy"].startswith("sandbox")
    for bad in ("secret.txt", "..%2Fsecret.txt", "phase5_gate_launch.json/../../x", "phase9_step1_x.md"):
        assert client.get(f"/phases/view/{bad}").status_code == 404, bad
    assert client.post("/phases").status_code == 405


def test_rerunning_plan_keeps_the_commercial_gate_consistent_with_approvals(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    assert full_flow(cli, monkeypatch) == 0
    assert cli("plan") == 0
    assert json.loads((cli.out / "phase4_gate_commercial.json").read_text())["decision"] == "REHEARSAL GO"


@pytest.mark.parametrize("decision,expected", [("GO", "PERSEVERE"), ("STOP", "PIVOT OR STOP"), ("REPEAT", "REPEAT")])
def test_memo_uses_founder_reported_validation_results(decision, expected):
    gate = {"decision": decision, "rule": f"{decision}_RULE", "participants": 5, "successes": 3,
            "result_source": "FOUNDER-REPORTED"}
    memo = persevere_or_pivot({"decision": "REPEAT"}, BRIEF, None, gate)
    assert memo["recommendation"] == expected and memo["validation_gate"]["decision"] == decision


def test_discover_stop_still_wins_over_any_validation_result():
    memo = persevere_or_pivot({"decision": "STOP"}, BRIEF, None, {"decision": "GO"})
    assert memo["recommendation"] == "STOP"
