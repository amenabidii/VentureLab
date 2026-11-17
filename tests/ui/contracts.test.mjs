import test from "node:test";
import assert from "node:assert/strict";
import {
  WorkspaceService,
  getModelStatus,
  UnavailableError,
} from "../../app/ui/static/service.js";
import {
  validateBrief,
  safeURL,
  filterFindings,
} from "../../app/ui/static/contracts.js";
import { demo } from "../../app/ui/static/fixtures.js";
import {
  renderers,
  escape,
  source,
  loading,
  errorView,
} from "../../app/ui/static/views.js";
const valid = {
  idea: "A digital checklist for design handoffs",
  market: "Egypt",
  customer: "Design studios",
  problem: "Missing handoff context",
  skills: "Design",
  hours: 5,
  budget: 0,
  currency: "EGP",
  values: "Privacy",
  constraints: "None",
  sources: [],
};
const makeState = async (mode) => {
  const service = new WorkspaceService(mode);
  return {
    service,
    demo: mode === "demo",
    runs: await service.listRuns(),
    data: {
      ...demo,
      agents: await service.getRunStatus("fixture-01"),
      findings: await service.getFindings("fixture-01"),
      challenges: await service.getChallenges("fixture-01"),
      decision: await service.getDecision("fixture-01"),
      counterfactual: await service.getCounterfactual("fixture-01"),
      artifacts: await service.listArtifacts("fixture-01"),
      approvals: await service.getApprovals("fixture-01"),
      audit: await service.getAudit("fixture-01"),
    },
    brief: valid,
    errors: {},
    review: false,
    standing: "",
    claimType: "",
    auditAgent: "",
  };
};
test("brief validates required fields, bounds and URLs without domain decisions", () => {
  assert.deepEqual(validateBrief(valid), {});
  for (const hours of ["", -1, 169, "bad"])
    assert.ok(validateBrief({ ...valid, hours }).hours);
  assert.ok(validateBrief({ ...valid, budget: -1 }).budget);
  assert.ok(validateBrief({ ...valid, idea: "short" }).idea);
  assert.ok(
    validateBrief({ ...valid, sources: ["file:///etc/passwd"] }).sources,
  );
  assert.ok(validateBrief({ ...valid, values: "" }).values);
});
test("safe sources reject script, file, credentials and malformed protocols", () => {
  for (const url of [
    "javascript:alert(1)",
    "data:text/html,x",
    "file:///a",
    "//example.org",
    "https://user:secret@example.org",
  ])
    assert.equal(safeURL(url), null);
  assert.equal(safeURL("https://example.org"), "https://example.org/");
  assert.ok(!source("javascript:alert(1)", "source").includes("href"));
});
test("live adapter never fabricates data or approvals", async () => {
  const s = new WorkspaceService();
  assert.deepEqual(await s.listRuns(), []);
  assert.equal(await s.getDecision("x"), null);
  for (const method of [
    "getRunStatus",
    "getFindings",
    "getChallenges",
    "listArtifacts",
    "getApprovals",
    "getAudit",
  ])
    assert.deepEqual(await s[method]("x"), []);
  assert.equal(await s.getCounterfactual("x"), null);
  await assert.rejects(s.createRun(valid), UnavailableError);
  await assert.rejects(s.decideApproval({}, "approve"), UnavailableError);
  assert.equal(s.capabilities.approvals, false);
});
test("demo mode is explicit, isolated, and cannot approve", async () => {
  const s = new WorkspaceService("demo");
  assert.match((await s.listRuns())[0].status, /MOCKED/);
  const findings = await s.getFindings("fixture-01");
  findings[0].claim = "mutated";
  assert.notEqual((await s.getFindings("fixture-01"))[0].claim, "mutated");
  assert.deepEqual(await s.getFindings("unknown"), []);
  await assert.rejects(s.decideApproval({}, "approve"));
});
test("model health uses only the inspected M1 endpoint and supports 503", async () => {
  let called;
  const status = await getModelStatus(async (url) => {
    called = url;
    return { ok: false, status: 503, json: async () => ({ ready: false }) };
  });
  assert.equal(called, "/health/model");
  assert.equal(status.ready, false);
  await assert.rejects(
    getModelStatus(async () => ({ ok: false, status: 500 })),
  );
});
test("evidence filters preserve independent standing and relationship", () => {
  assert.equal(filterFindings(demo.findings, "ASSUMPTION", "Demand").length, 1);
  assert.equal(
    filterFindings(demo.findings, "ESTABLISHED", "Demand").length,
    0,
  );
  assert.equal(
    demo.findings.find((f) => f.relationship === "Contradictory").standing,
    "NEEDS_REVIEW",
  );
});
test("all screens render empty or labeled fixture states", async () => {
  for (const mode of ["live", "demo"]) {
    const state = await makeState(mode);
    for (const [name, render] of Object.entries(renderers)) {
      const html = render(state);
      assert.ok(html.length > 100, name);
      assert.ok(!html.includes("undefined"), name);
    }
  }
  const state = await makeState("live");
  assert.match(renderers.dashboard(state), /No venture runs/);
  assert.match(renderers.approvals(state), /No approval requests/);
});
test("rich data displays rules, references, counterfactuals, artifacts and audit labels", async () => {
  const s = await makeState("demo");
  assert.match(renderers.challenger(s), /#evidence\/F-03/);
  assert.match(renderers.decision(s), /MOCKED_DEMAND_EVIDENCE_MISSING/);
  for (const outcome of ["GO", "REPEAT", "PIVOT", "STOP"]) {
    s.data.decision = { ...demo.decision, outcome };
    assert.match(renderers.decision(s), new RegExp(outcome));
  }
  assert.match(
    renderers.counterfactual(s),
    /No experiment automatically guarantees GO/,
  );
  assert.match(renderers.artifacts(s), /Read-only preview/);
  assert.match(renderers.history(s), /not an execution log/);
  assert.match(renderers.approvals(s), /disabled/);
});
test("untrusted text is escaped throughout rendering", async () => {
  const payload = '<img src=x onerror="alert(1)">';
  assert.equal(
    escape(payload),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
  );
  const s = await makeState("demo");
  s.data.findings = [
    {
      ...demo.findings[0],
      claim: payload,
      quote: payload,
      url: "javascript:alert(1)",
    },
  ];
  const html = renderers.evidence(s);
  assert.ok(!html.includes("<img"));
  assert.ok(!html.includes("javascript:"));
  s.brief = { ...valid, idea: payload };
  s.review = true;
  assert.ok(!renderers.brief(s).includes("<img"));
});
test("loading and errors provide actionable truthful feedback", () => {
  assert.match(loading(), /role="status"/);
  assert.match(errorView(), /Try again/);
});
