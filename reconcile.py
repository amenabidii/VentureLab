"""Reconciliation for the MOCKED sale-to-cash rehearsal.

Matches orders, payment events, fees, refunds, delivery grants and the payout report,
and lists every mismatch instead of hiding it. Checks:
- every succeeded, unrefunded payment has exactly one active access grant;
- refunded orders have their access revoked; failed payments have no access;
- no access grant exists without a succeeded payment;
- payout net == gross - fees - refunds, and the payout covers exactly the settled events.
"""
from __future__ import annotations

from payments import Order


def reconcile(orders: list[Order], events: list[dict], grants: dict[str, dict], payout: dict) -> dict:
    rows, mismatches = [], []
    by_order: dict[str, list[dict]] = {}
    for e in events:
        by_order.setdefault(e["order_id"], []).append(e)
    for order in orders:
        evs = by_order.get(order.order_id, [])
        paid = [e for e in evs if e["type"] == "payment.succeeded"]
        refunded = any(e["type"] == "charge.refunded" for e in evs)
        grant = grants.get(order.order_id)
        access = grant["access"] if grant else "none"
        expected = ("revoked" if refunded and paid else "active" if paid else "none")
        if len(paid) > 1:
            mismatches.append(f"{order.order_id}: charged {len(paid)} times")
        if paid and paid[0]["amount_cents"] != order.amount_cents:
            mismatches.append(f"{order.order_id}: paid amount differs from order amount")
        if access != expected:
            mismatches.append(f"{order.order_id}: access is {access}, expected {expected}")
        rows.append({"order_id": order.order_id, "amount_cents": order.amount_cents,
                     "paid": bool(paid), "fee_cents": sum(e.get("fee_cents", 0) for e in paid),
                     "refunded": refunded, "access": access, "expected_access": expected})
    known = {o.order_id for o in orders}
    for order_id in grants:
        if order_id not in known:
            mismatches.append(f"{order_id}: access granted for an unknown order")
    gross = sum(r["amount_cents"] for r in rows if r["paid"])
    fees = sum(r["fee_cents"] for r in rows)
    refunds = sum(r["amount_cents"] for r in rows if r["refunded"] and r["paid"])
    expected_net = gross - fees - refunds
    if payout["net_cents"] != expected_net:
        mismatches.append(f"payout net {payout['net_cents']} != expected {expected_net}")
    settled = {e["id"] for e in events if e["type"] in ("payment.succeeded", "charge.refunded")}
    if set(payout["event_ids"]) != settled:
        mismatches.append("payout does not cover exactly the settled events")
    return {"rows": rows, "gross_cents": gross, "fees_cents": fees, "refunds_cents": refunds,
            "expected_net_cents": expected_net, "payout_net_cents": payout["net_cents"],
            "mismatches": mismatches, "balanced": not mismatches, "mocked": True}
