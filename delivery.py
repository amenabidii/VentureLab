"""MOCKED automatic delivery (Phase 5, core step "Open the store; deliver automatically").

A verified `payment.succeeded` event grants the buyer access to the digital product.
Rules enforced in code:
- delivery only runs after the founder approved enabling it for this exact product
  file (fingerprint-bound approval checked by `workflow.py`);
- events must carry a valid signature (forged events are refused);
- each event and each order is processed at most once (idempotency): a duplicate
  webhook never delivers twice;
- failed payments deliver nothing; refunds revoke access (see `refunds.py`).
Nothing is sent to anyone: the "delivery" is an access grant recorded locally, MOCKED.
"""
from __future__ import annotations

import hashlib

from payments import MockPaymentProvider


class DeliveryRefused(RuntimeError):
    pass


class DeliveryService:
    def __init__(self, provider: MockPaymentProvider, product_sha256: str, *, founder_approved: bool):
        if not founder_approved:
            raise DeliveryRefused("Automatic delivery needs founder approval for this exact product file")
        self.provider = provider
        self.product_sha256 = product_sha256
        self.grants: dict[str, dict] = {}      # order_id -> grant
        self.processed: set[str] = set()       # event ids already handled
        self.log: list[dict] = []

    def _record(self, event: dict, result: str) -> str:
        self.log.append({"event_id": event.get("id"), "type": event.get("type"),
                         "order_id": event.get("order_id"), "result": result, "mocked": True})
        return result

    def handle(self, event: dict, signature: str) -> str:
        if not self.provider.verify(event, signature):
            return self._record(event, "rejected_bad_signature")
        if event["id"] in self.processed:
            return self._record(event, "duplicate_event_ignored")
        self.processed.add(event["id"])
        order_id = event["order_id"]
        if event["type"] == "payment.failed":
            return self._record(event, "no_delivery_payment_failed")
        if event["type"] == "payment.succeeded":
            if order_id in self.grants:
                return self._record(event, "already_delivered_ignored")
            token = hashlib.sha256(f"{order_id}:{self.product_sha256}".encode()).hexdigest()[:24]
            self.grants[order_id] = {"order_id": order_id, "access": "active", "access_token": f"mock_{token}",
                                     "product_sha256": self.product_sha256, "mocked": True}
            return self._record(event, "delivered")
        if event["type"] == "charge.refunded":
            from refunds import revoke_access
            return self._record(event, revoke_access(self.grants, order_id))
        return self._record(event, "ignored_unknown_event")
