"""MOCKED payment provider for the sale-to-cash rehearsal (Phase 5).

Everything here is a local simulation: no network, no payment provider (not even a
sandbox), no card data, no money. It exists to exercise the sale-to-cash logic that a
real launch would need: signed payment events trigger delivery, refunds revoke access,
duplicate events do nothing, and reconciliation matches orders, payments, fees and payouts.
Every object carries `mocked: true`; outputs are labelled MOCKED.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass

MOCKED = "MOCKED"
# Illustrative fee schedule for the simulation only (not any real provider's pricing).
MOCK_FEE_RATE = 0.029
MOCK_FEE_FIXED_CENTS = 30


@dataclass(frozen=True)
class Order:
    order_id: str
    buyer_ref: str           # a test reference such as "test-buyer-1", never personal data
    sku: str
    amount_cents: int
    currency: str = "EUR"
    mocked: bool = True


def mock_fee(amount_cents: int) -> int:
    return round(amount_cents * MOCK_FEE_RATE) + MOCK_FEE_FIXED_CENTS


class MockPaymentProvider:
    """Produces signed events like a provider webhook would. Holds no money."""

    def __init__(self, signing_secret: bytes | None = None):
        self._secret = signing_secret or secrets.token_bytes(32)  # per run; never written to disk
        self.events: list[dict] = []
        self._seq = 0

    def _event(self, kind: str, order: Order, **extra) -> dict:
        self._seq += 1
        event = {"id": f"evt_mock_{self._seq:04d}", "type": kind, "order_id": order.order_id,
                 "amount_cents": order.amount_cents, "currency": order.currency, "mocked": True, **extra}
        self.events.append(event)
        return event

    def sign(self, event: dict) -> str:
        body = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
        return hmac.new(self._secret, body, hashlib.sha256).hexdigest()

    def verify(self, event: dict, signature: str) -> bool:
        return isinstance(signature, str) and hmac.compare_digest(self.sign(event), signature)

    def checkout(self, order: Order, *, succeed: bool = True) -> dict:
        if succeed:
            return self._event("payment.succeeded", order, fee_cents=mock_fee(order.amount_cents))
        return self._event("payment.failed", order, reason="MOCKED card declined")

    def refund(self, order: Order) -> dict:
        return self._event("charge.refunded", order)

    def payout(self, batch_id: str) -> dict:
        """Net settlement of every event so far, as a provider payout report would show."""
        paid = [e for e in self.events if e["type"] == "payment.succeeded"]
        refunded = [e for e in self.events if e["type"] == "charge.refunded"]
        gross = sum(e["amount_cents"] for e in paid)
        fees = sum(e["fee_cents"] for e in paid)
        refunds = sum(e["amount_cents"] for e in refunded)
        return {"batch_id": batch_id, "gross_cents": gross, "fees_cents": fees, "refunds_cents": refunds,
                "net_cents": gross - fees - refunds, "event_ids": [e["id"] for e in paid + refunded],
                "mocked": True}


def as_dict(order: Order) -> dict:
    return asdict(order)
