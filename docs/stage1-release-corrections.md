# Stage 1 release-blocker corrections

> Historical record, kept unchanged below. It describes an earlier state of the project: phases 2–6
> now run through `workflow.py` (with a clickable Phase 3 prototype), and test counts have grown.
> The current status is in the [README](../README.md) and [ARCHITECTURE.md](../ARCHITECTURE.md).

Scope: corrections to `codex/stage1-readiness` starting from `a840881`.
Main remains unchanged. No historical execution or evidence record was edited.

## Causes and corrections

1. The browser mock's decision parameter shadowed its configuration, suppressing
   `badConfirmation`. Renamed the parameter and exposed the actual response to the
   test. The negative test requires a changed fingerprint, an error, no success
   state and no execution control, with Builder capability enabled.
2. The approval UI supplied a factual review declaration by default. It now shows
   a blank optional explanation. API and domain validation allow omission/empty
   text without changing the required explicit approve/reject action. Supplied text
   is not trimmed or rewritten; existing content checks remain. Empty explanations
   are recorded as `[No reason provided]`, separate from the approval outcome.
   The history view warns that older saved text may have originated from a default.
3. The quotation view showed exact text and source links without distinguishing
   original authorship. It now separately labels source poster, original author,
   third-party material and independent verification. The persisted quotation
   contract has no reliable original-author or poster metadata, so these fields
   explicitly remain unknown/unverified. A first-person sentence never establishes
   personal experience or authorship. This does not newly identify historical authors.

## Files changed

- `app/api.py`: optional explanation input, maximum length retained.
- `builder_models.py`: optional explanation with exact whitespace preserved and
  existing content validation retained.
- `approval.py`: explicit absent-explanation marker; authorization unchanged.
- `app/ui/static/views.js`: blank optional field, historical-text caveat and
  quotation-attribution uncertainty display.
- `tests/test_integration_api.py`: omitted/blank/custom explanations for approve and
  reject, real audit mirroring, denied keys/fingerprints, rejection and single use.
- `tests/test_recordings.py`: all 56 quote/URL pairs, recorded audit outcomes and
  unchanged file hashes before/after read-only replay.
- `tests/ui/audit.spec.mjs`: mock scoping fix, stronger negative assertions,
  blank explicit rejection, and an opt-in test-only mutation hook.
- `tests/ui/recordings.test.mjs`: own words, government-report quotation,
  quotation of another individual, missing author and ambiguous attribution.
- This report.

## Final verification

| Suite | Result |
|---|---|
| Full Python, including compliance and backend authorization | 493 passed, 41 skipped |
| Interface unit tests | 27 passed |
| Full browser suite | 31 passed (all original 30 plus blank-reason rejection) |
| Docker build | Passed |
| Full Python suite inside Compose image | 492 passed, 42 skipped |
| Deliberately disabled confirmation guard | Negative browser test failed as required |
| Normal confirmation guard after mutation experiment | Passed |

Skipped tests are opt-in/environment-dependent; Docker additionally lacks Git
metadata. Existing dependency deprecation warnings remain. No new live model run
was needed or represented as performed.

The mutation uses `VENTURELAB_TEST_DISABLE_CONFIRMATION=1` only in the Playwright
harness. It changes the script served to that test, never the production file. It
removes the mismatch rejection; the same test then fails on the missing error.
With the flag absent the actual mismatch response is refused and execution is absent.

All nine indexed genuine runs remain readable. Superseded GO authorization tests
pass. Gate thresholds and traces equal recorded values. The README/architecture
headings, six-phase status documentation, LICENSE, Compose configuration, gate
rules, recorded output files, manifest and decision log are unchanged by this fix.
Historical audit outcomes and quotations are read verbatim, never reconstructed.
No unrelated feature, publishing, payment or review-generation action was added.

## Limitations

Original authors and third-party provenance cannot be recovered from the existing
quotation records alone. The UI deliberately reports uncertainty rather than
attributing words to a commenter or claiming independent verification. The saved
historical claims and judgments themselves are not rewritten. The existing
STUBBED product capabilities remain STUBBED.

Verdict: SAFE TO MERGE after explicit approval; feature branch only is published.
