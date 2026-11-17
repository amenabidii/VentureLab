import test from "node:test";
import assert from "node:assert/strict";
import {
  normalize,
  ContractError,
  approvalBlock,
  modelStatus,
} from "../../app/ui/static/normalize.js";
import { validateBrief, safeURL } from "../../app/ui/static/contracts.js";
import { renderers, source } from "../../app/ui/static/views.js";
import { demo } from "../../app/ui/static/fixtures.js";
const valid = {
  idea: "فكرة رقمية لتسهيل تسليم التصميم",
  market: "مصر",
  customer: "فرق صغيرة",
  problem: "نقص المعلومات",
  skills: "تصميم",
  hours: 1.5,
  budget: 0,
  currency: "EGP",
  values: "خصوصية",
  constraints: "None",
};
test("brief accepts Unicode and absent optional sources but rejects unsafe numeric coercions", () => {
  assert.deepEqual(validateBrief(valid), {});
  assert.doesNotThrow(() => validateBrief());
  for (const value of [null, true, [], {}, " ", "Infinity", "0x10", -1, 1e20])
    assert.ok(validateBrief({ ...valid, budget: value }).budget, String(value));
  assert.ok(validateBrief({ ...valid, sources: {} }).sources);
  assert.ok(validateBrief({ ...valid, idea: "x".repeat(4001) }).idea);
  assert.deepEqual(validateBrief({ ...valid, idea: "x".repeat(4000) }), {});
});
test("strict URL handling rejects browser-normalized malformed URLs", () => {
  for (const url of [
    "https:example.org",
    "https:///example.org",
    "https://example.org\n/a",
    "https://example.org\\evil",
    {},
    123,
  ])
    assert.equal(safeURL(url), null, String(url));
  assert.match(source("javascript:alert(1)", "Source"), /link disabled/);
  assert.match(source("", "Named source"), /No source URL/);
});
test("sparse optional fields are explicit and safe without invented approvals or costs", () => {
  const finding = normalize("findings", [
    { id: "F", claim: "Hypothesis", standing: "ASSUMPTION" },
  ])[0];
  assert.equal(finding.relationship, "Not provided");
  assert.equal(finding.url, "");
  const audit = normalize("audit", [{ agent: "Judge", action: "gate" }])[0];
  assert.deepEqual(audit.sources, []);
  assert.equal(audit.cost, null);
  assert.equal(audit.approved_by, null);
  assert.deepEqual(normalize("artifacts", null), []);
  assert.equal(normalize("decision", null), null);
  const decision = normalize("decision", { outcome: "STOP", rule: "gate-1" });
  assert.deepEqual(decision.risks, []);
});
test("critical classifications and identities fail closed", () => {
  for (const [kind, value] of [
    ["findings", [{ id: "F", claim: "X", standing: "verified" }]],
    ["decision", { outcome: "MAYBE", rule: "x" }],
    ["decision", { outcome: "GO" }],
    ["approvals", [{ id: "P" }]],
    ["audit", [{ cost: "0" }]],
    ["artifacts", [{ id: "A", format: "url", content: "file:///secret" }]],
    ["runs", [{ id: "r", recordedAt: "yesterday" }]],
  ])
    assert.throws(() => normalize(kind, value), ContractError);
  assert.throws(
    () => normalize("runs", [{ id: "r" }, { id: "r" }]),
    /Duplicate/,
  );
  assert.throws(() => normalize("findings", [null]), ContractError);
  assert.throws(() => normalize("__proto__", []), ContractError);
  assert.throws(() => normalize("findings", "bad"), ContractError);
});
test("size limits reject oversized payloads rather than silently truncating evidence", () => {
  assert.throws(
    () =>
      normalize("artifacts", [
        { id: "A", format: "text", content: "x".repeat(500001) },
      ]),
    ContractError,
  );
  assert.throws(
    () =>
      normalize(
        "runs",
        Array.from({ length: 5001 }, (_, i) => ({ id: String(i) })),
      ),
    ContractError,
  );
});
test("approval display guard binds status, run, artifact, fingerprint and expiry", () => {
  const request = {
    id: "P",
    runId: "r",
    artifactId: "a",
    fingerprint: "v1",
    status: "Pending",
  };
  const artifacts = [{ id: "a", fingerprint: "v1" }];
  assert.equal(approvalBlock(request, artifacts, "r"), "");
  for (const status of [
    "Approved",
    "Rejected",
    "Expired",
    "Invalid",
    "Unknown",
  ])
    assert.ok(approvalBlock({ ...request, status }, artifacts, "r"));
  assert.match(approvalBlock(request, artifacts, "another"), /different run/);
  assert.match(
    approvalBlock(request, [{ id: "a", fingerprint: "v2" }], "r"),
    /fingerprint/,
  );
  assert.match(approvalBlock(request, [], "r"), /missing/);
  assert.match(
    approvalBlock(
      { ...request, expiresAt: "2020-01-01T00:00:00Z" },
      artifacts,
      "r",
    ),
    /expired/,
  );
});
test("malformed model health cannot imply readiness", () => {
  for (const value of [null, {}, { ready: "false" }, { ready: true }])
    assert.throws(() => modelStatus(value), ContractError);
  assert.deepEqual(modelStatus({ ready: false }), {
    ready: false,
    model: "Local model",
  });
});
test("agent output navigation is keyed by role, not backend array position", () => {
  const html = renderers.workflow({
    data: {
      agents: [{ agent: "Judge", status: "Completed", task: "Explain gate" }],
    },
    service: { capabilities: { workflow: true } },
  });
  assert.match(html, /href="#decision"/);
  assert.ok(!html.includes('href="#evidence"'));
});
test("missing evidence references are explicit instead of broken links", () => {
  const html = renderers.challenger({
    data: {
      challenges: [{ ...demo.challenges[0], findings: ["missing"] }],
      findings: [],
    },
  });
  assert.match(html, /Reference unavailable/);
  assert.ok(!html.includes("#evidence/missing"));
});
test("large evidence collections are paged and direct references select the containing page", () => {
  const findings = Array.from({ length: 1001 }, (_, i) => ({
    ...demo.findings[0],
    id: "F" + i,
  }));
  const state = {
    data: { findings },
    standing: "",
    claimType: "",
    focusFinding: "F999",
  };
  const html = renderers.evidence(state);
  assert.equal((html.match(/<details/g) || []).length, 50);
  assert.match(html, /id="finding-F999" open/);
  assert.equal(state.evidencePage, 19);
});
