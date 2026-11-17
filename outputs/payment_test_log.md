# Payment and delivery test log (MOCKED)

Run `run-64fdee373f244b81` · 2026-11-17T18:00:04Z · Discover gate **REPEAT** · REHEARSAL.

Everything below is a local simulation produced by `workflow.py launch`: a MOCKED payment provider
(`payments.py`), SIMULATED test buyers, signed webhook events, automatic delivery (`delivery.py`),
refunds that revoke access (`refunds.py`) and reconciliation (`reconcile.py`). No payment of any kind,
no sandbox, no card data, no money, no people. Test price: €8/month.

## Events

| Step | Event | Type | Order | Result |
|---|---|---|---|---|
| paid order | `evt_mock_0001` | payment.succeeded | ord_test_1 | delivered |
| same webhook delivered twice | `evt_mock_0001` | payment.succeeded | ord_test_1 | duplicate_event_ignored |
| paid order | `evt_mock_0002` | payment.succeeded | ord_test_2 | delivered |
| refund | `evt_mock_0003` | charge.refunded | ord_test_2 | access_revoked |
| declined payment | `evt_mock_0004` | payment.failed | ord_test_3 | no_delivery_payment_failed |
| forged signature | `evt_mock_0005` | payment.succeeded | ord_test_4 | rejected_bad_signature |
| same event, valid signature | `evt_mock_0005` | payment.succeeded | ord_test_4 | delivered |

## Reconciliation

Gross 2400 · fees 159 (MOCKED fee schedule) · refunds 800
· expected net 1441 · payout net 1441 (cents).
Mismatches: none.

## Checks

| Check | Result |
|---|---|
| paid order | pass |
| same webhook delivered twice | pass |
| paid order | pass |
| refund | pass |
| declined payment | pass |
| forged signature | pass |
| same event, valid signature | pass |
| reconciliation balanced | pass |
