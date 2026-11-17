"""MOCKED refunds: a refund revokes the buyer's access to the delivered product.

VentureLab never holds, moves or refunds money. In a real launch the payment provider
would refund; this module only reacts to the (MOCKED) refund event by revoking access,
and records refunds that arrive for orders that were never delivered.
"""
from __future__ import annotations


def revoke_access(grants: dict[str, dict], order_id: str) -> str:
    grant = grants.get(order_id)
    if grant is None:
        return "refund_for_undelivered_order_recorded"
    if grant["access"] == "revoked":
        return "already_revoked_ignored"
    grant["access"] = "revoked"
    return "access_revoked"
