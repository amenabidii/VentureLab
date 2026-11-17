import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { demo } from "../../app/ui/static/fixtures.js";
import fs from "node:fs";
const clone = () => structuredClone(demo);
// Test-only mock transport: never shipped as a production integration.
async function mockService(page, data = clone(), options = {}) {
  // Opt-in mutation check: alter only the test-served script, never production files.
  if (options.badConfirmation && process.env.VENTURELAB_TEST_DISABLE_CONFIRMATION === "1") {
    await page.route("**/app.js", async route => {
      const response = await route.fetch();
      const body = await response.text();
      const guard = 'throw new Error("Mismatched confirmation");';
      if (!body.includes(guard)) throw new Error("Mutation target missing");
      await route.fulfill({response, body: body.replace(guard, "void 0;")});
    });
  }
  await page.route("**/service.js", (route) =>
    route.fulfill({
      contentType: "text/javascript",
      body: `
 import { BriefValidationError } from "/workspace/assets/normalize.js";
 const data=${JSON.stringify(data)},options=${JSON.stringify(options)};
 globalThis.__qa={calls:[],reads:0,fail:!!options.fail,mode:'live'};
 export class WorkspaceService {
 constructor(mode='live'){this.mode=mode;}
 get capabilities(){return {createRun:!!options.createRun,approvals:!!options.approvals,workflow:!!options.workflow,builder:!!options.builder};}
 async listRuns(){__qa.reads++;if(options.delay)await new Promise(r=>setTimeout(r,options.delay));__qa.completed=(__qa.completed||0)+1;if(options.emptyLive && this.mode==='live')return [];return structuredClone(data.runs);}
 async getRunStatus(){return structuredClone(data.agents);}
 async getFindings(){if(options.badFindings)throw new Error('MOCKED failed evidence read');return structuredClone(data.findings);}
 async getChallenges(){return structuredClone(data.challenges);}
 async getDecision(){return structuredClone(data.decision);}
 async getCounterfactual(){return structuredClone(data.counterfactual);}
 async listArtifacts(){return structuredClone(data.artifacts);}
 async getApprovals(){return structuredClone(data.approvals);}
 async getAudit(){return structuredClone(data.audit);}
 async createRun(brief){__qa.calls.push({brief});await new Promise(r=>setTimeout(r,200));if(options.validation)throw new BriefValidationError({market:'MOCKED backend: specify a reachable market.'});if(__qa.fail)throw new Error('MOCKED network failure');return options.badRun?{}:options.unlistedRun?{...data.runs[0],id:'new-unlisted'}:data.runs[0];}
 async decideApproval(request,choice,decisionOptions){__qa.calls.push({request,choice,options:decisionOptions});await new Promise(r=>setTimeout(r,200));if(__qa.fail)throw new Error('MOCKED network failure');const row=data.approvals.find(a=>a.id===request.id);row.status=choice==='approve'?'Approved':'Rejected';const response={...row,fingerprint:options.badConfirmation?'changed':row.fingerprint};__qa.response=response;return response;}
 }
 export async function getModelStatus(){return {ready:false,model:'MOCKED QA model'};}
 `,
    }),
  );
  await page.goto("/workspace");
}
const go = async (page, route) => {
  await page.evaluate((route) => (location.hash = route), route);
  await expect(page.locator("nav a[aria-current]")).toHaveAttribute(
    "href",
    "#" + route.split("/")[0],
  );
};
const pending = () => {
  const data = clone();
  data.approvals[0].status = "Pending";
  return data;
};
test("unknown and prototype hash names do not crash; skip link preserves current screen", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/workspace#constructor");
  await expect(page.locator("h1")).toHaveText(
    "Good ideas deserve hard questions.",
  );
  for (const value of ["__proto__", "toString", "evidence/%E0%A4%A"]) {
    await page.evaluate((v) => (location.hash = v), value);
    await expect(page.locator("h1")).toBeVisible();
  }
  await go(page, "brief");
  await page.locator(".skip").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
  await expect(page.locator("h1")).toHaveText("Start with what you know.");
  expect(errors).toEqual([]);
});
test("slow mode changes never reveal demo records in live mode through navigation", async ({
  page,
}) => {
  await mockService(page, clone(), { delay: 700, emptyLive: true });
  await expect(
    page.getByText("No venture runs are available.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore demo" }).click();
  await expect(
    page.getByText("A calmer handoff for small design teams", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Exit demo" }).click();
  await go(page, "evidence");
  await expect(page.locator("main")).not.toContainText(
    "Teams would adopt a separate tool.",
  );
  await expect(
    page.locator("h2").filter({ hasText: "No evidence collected yet." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore demo" }).click();
  await page.getByRole("button", { name: "Exit demo" }).click();
  await expect(page.locator("#mode-banner")).toContainText("Live workspace");
  await expect(page.locator("main")).not.toContainText("MOCKED GATE RESULT");
});
test("a failed section stays an error across navigation while other outputs remain readable", async ({
  page,
}) => {
  await mockService(page, clone(), { badFindings: true });
  await go(page, "evidence");
  await expect(
    page.getByRole("heading", { name: "We couldn’t load this view" }),
  ).toBeVisible();
  await go(page, "artifacts");
  await expect(
    page.getByRole("button", { name: "Read-only preview" }),
  ).toHaveCount(3);
  await go(page, "evidence");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});
test("all outcomes, sparse records, missing references and unordered agents", async ({
  page,
}) => {
  for (const outcome of ["GO", "REPEAT", "PIVOT", "STOP"]) {
    const data = clone();
    data.decision = { outcome, rule: "MOCKED_RULE_" + outcome };
    data.agents = [data.agents[3], data.agents[0]];
    data.audit = [{ agent: "Judge", action: "MOCKED sparse entry" }];
    data.challenges[0].findings = ["missing"];
    await page.unrouteAll();
    await mockService(page, data);
    await go(page, "decision");
    await expect(page.locator(".decision h2")).toHaveText(outcome);
    await expect(page.locator(".decision code")).toHaveText(
      "MOCKED_RULE_" + outcome,
    );
    await go(page, "workflow");
    await expect(
      page.locator(".agent").first().getByRole("link"),
    ).toHaveAttribute("href", "#decision");
    await go(page, "history");
    await expect(page.locator("tbody")).toContainText("Not reported");
    await go(page, "challenger");
    await expect(
      page.getByText("missing · Reference unavailable"),
    ).toBeVisible();
  }
});
test("approval statuses, changed artifact and expiry block all mutation calls", async ({
  page,
}) => {
  for (const scenario of [
    "Approved",
    "Rejected",
    "Expired",
    "Invalid",
    "changed",
    "expired-date",
    "missing",
  ]) {
    const data = pending();
    if (["Approved", "Rejected", "Expired", "Invalid"].includes(scenario))
      data.approvals[0].status = scenario;
    if (scenario === "changed") data.artifacts[1].fingerprint = "changed";
    if (scenario === "expired-date")
      data.approvals[0].expiresAt = "2020-01-01T00:00:00Z";
    if (scenario === "missing") data.artifacts = [];
    await page.unrouteAll();
    await mockService(page, data, { approvals: true });
    await go(page, "approvals");
    await expect(
      page.getByRole("button", { name: "Approve this action" }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Reject", exact: true }),
    ).toBeDisabled();
    expect(await page.evaluate(() => __qa.calls.length)).toBe(0);
  }
});
test("approval confirmation is backend-bound, duplicate clicks are guarded and failure requires refresh", async ({
  page,
}) => {
  await mockService(page, pending(), { approvals: true, fail: true });
  await go(page, "approvals");
  const approve = page.getByRole("button", { name: "Approve this action" });
  await expect(approve).toBeEnabled();
  await approve.evaluate((b) => {
    b.click();
    b.click();
  });
  await expect(page.locator("[role=alert]")).toContainText("did not confirm");
  await expect(approve).toBeDisabled();
  expect(await page.evaluate(() => __qa.calls.length)).toBe(1);
  await page.evaluate(() => (__qa.fail = false));
  await page.getByRole("button", { name: "Refresh requests" }).click();
  await expect(approve).toBeEnabled();
  await approve.click();
  await expect(page.getByText("Approved", { exact: true })).toBeVisible();
  await expect(approve).toBeDisabled();
  const calls = await page.evaluate(() => __qa.calls);
  expect(calls[1].request.fingerprint).toBe("fixture-v1-not-a-real-hash");
  expect(calls[1].request.artifactId).toBe("A-02");
});
test("mismatched approval acknowledgment never displays success", async ({
  page,
}) => {
  await mockService(page, pending(), {
    approvals: true,
    badConfirmation: true,
    builder: true,
  });
  await go(page, "approvals");
  await page.getByRole("button", { name: "Approve this action" }).click();
  await expect(page.locator("[role=alert]")).toContainText("did not confirm");
  await expect(page.getByText("Approved", { exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => __qa.response.fingerprint)).toBe("changed");
  await expect(page.getByRole("button", {name: "Write the approved files locally"})).toHaveCount(0);
});
test("rejected approval response is rendered only after authoritative refresh", async ({
  page,
}) => {
  await mockService(page, pending(), { approvals: true });
  await go(page, "approvals");
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByText("Rejected", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve this action" }),
  ).toBeDisabled();
});
async function fillBrief(page) {
  await go(page, "brief");
  for (const [key, value] of Object.entries({
    idea: "<script>alert(1)</script> فكرة رقمية",
    market: "مصر",
    customer: "مصممون",
    problem: "وصف المشكلة",
    skills: "تصميم",
    hours: "1.5",
    budget: "0",
    values: "خصوصية",
    constraints: "None",
  }))
    await page.locator("#" + key).fill(value);
  await page.getByRole("button", { name: "Review brief" }).click();
}
test("Unicode brief survives navigation, refresh clears it honestly, and ambiguous submission locks retries", async ({
  page,
}) => {
  await mockService(page, clone(), { createRun: true, fail: true });
  await fillBrief(page);
  await expect(
    page.getByText("<script>alert(1)</script> فكرة رقمية"),
  ).toBeVisible();
  await expect(page.locator("main script")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Submit and start analysis" })
    .evaluate((b) => {
      b.click();
      b.click();
    });
  await expect(page.locator("[role=alert]")).toContainText(
    "Submission was not confirmed",
  );
  await expect(
    page.getByRole("button", { name: "Submit and start analysis" }),
  ).toBeDisabled();
  expect(await page.evaluate(() => __qa.calls.length)).toBe(1);
  await page.reload();
  await go(page, "brief");
  await expect(page.locator("#idea")).toHaveValue("");
  await expect(
    page.getByText("Kept in this tab only. Reloading clears it."),
  ).toBeVisible();
});
test("successful run creation cannot be resubmitted by revisiting review", async ({
  page,
}) => {
  await mockService(page, clone(), { createRun: true });
  await fillBrief(page);
  await page.getByRole("button", { name: "Submit and start analysis" }).click();
  await expect(page.locator("nav a[aria-current]")).toHaveAttribute(
    "href",
    "#workflow",
  );
  await go(page, "brief");
  await expect(
    page.getByText("Submitted to backend", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Submit and start analysis" }),
  ).toBeDisabled();
});
test("hostile artifact markup cannot fetch, execute, navigate or access local paths", async ({
  page,
}) => {
  const data = clone();
  data.artifacts[1].content =
    '<script>alert(1)</script><img src="https://attacker.invalid/probe"><iframe src="file:///etc/passwd"></iframe><svg onload="alert(1)"></svg><meta http-equiv="refresh" content="0;url=https://attacker.invalid"><form action="/health"><button>send</button></form><a href="javascript:alert(1)">bad</a><h1>Safe content</h1><template><img src="https://attacker.invalid/template"></template>';
  const requests = [];
  page.on("request", (r) => requests.push(r.url()));
  let dialogs = 0;
  page.on("dialog", async (d) => {
    dialogs++;
    await d.dismiss();
  });
  await mockService(page, data);
  await go(page, "artifacts");
  const trigger = page
    .getByRole("button", { name: "Read-only preview" })
    .nth(1);
  await trigger.click();
  const frame = page.frameLocator("iframe");
  await expect(frame.getByRole("heading")).toHaveText("Safe content");
  await expect(
    frame.locator("[src],[href],script,form,iframe,svg"),
  ).toHaveCount(0);
  expect(
    requests.some(
      (u) => u.includes("attacker.invalid") || u.startsWith("file:"),
    ),
  ).toBe(false);
  expect(dialogs).toBe(0);
  await page.getByRole("button", { name: "Close preview" }).click();
  await expect(trigger).toBeFocused();
});
test("long quotations and artifacts fit a narrow viewport; 5000 findings stay paged", async ({
  page,
}) => {
  const data = clone();
  data.findings = Array.from({ length: 5000 }, (_, i) => ({
    ...data.findings[2],
    id: "F-" + i,
    claim: "MOCKED claim " + i,
  }));
  data.findings[0].quote = "ق".repeat(100000);
  data.artifacts[0].content = "x".repeat(400000);
  await page.setViewportSize({ width: 390, height: 844 });
  await mockService(page, data);
  await go(page, "evidence");
  await expect(page.locator("details")).toHaveCount(50);
  await page.locator("summary").first().click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Next findings" }).click();
  await expect(page.locator("details").first()).toHaveAttribute(
    "id",
    "finding-F-50",
  );
  await go(page, "evidence/F-4999");
  await expect(page.locator("#finding-F-4999")).toHaveAttribute("open", "");
  await go(page, "artifacts");
  await page.getByRole("button", { name: "Read-only preview" }).first().click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
test("WCAG automated semantics and contrast across all views", async ({
  page,
}) => {
  test.setTimeout(90000);
  await page.goto("/workspace");
  await page.getByRole("button", { name: "Explore demo" }).click();
  const violations = [];
  for (const route of [
    "dashboard",
    "brief",
    "workflow",
    "evidence",
    "challenger",
    "decision",
    "counterfactual",
    "artifacts",
    "approvals",
    "history",
    "roadmap",
  ]) {
    await go(page, route);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    for (const v of result.violations)
      violations.push({ route, id: v.id, nodes: v.nodes.map((n) => n.target) });
  }
  expect(violations).toEqual([]);
});
test("measure local navigation, large-list filtering and retained heap", async ({
  page,
  context,
}) => {
  test.setTimeout(60000);
  const data = clone();
  data.findings = Array.from({ length: 5000 }, (_, i) => ({
    ...data.findings[i % 4],
    id: "F-" + i,
  }));
  await mockService(page, data);
  await expect(
    page.getByText(data.runs[0].title, { exact: true }),
  ).toBeVisible();
  const metrics = {
    browser: "Microsoft Edge, local headless, no CPU throttling",
    findings: 5000,
    initialDOMReadyMs: await page.evaluate(
      () =>
        performance.getEntriesByType("navigation")[0].domContentLoadedEventEnd,
    ),
  };
  const cdp = await context.newCDPSession(page);
  await cdp.send("Performance.enable");
  await cdp.send("HeapProfiler.collectGarbage");
  const heap = async () => {
    const r = await cdp.send("Performance.getMetrics");
    return r.metrics.find((m) => m.name === "JSHeapUsedSize").value;
  };
  metrics.heapBefore = await heap();
  const samples = [];
  for (let i = 0; i < 20; i++) {
    const start = performance.now();
    await go(page, i % 2 ? "dashboard" : "evidence");
    samples.push(performance.now() - start);
  }
  await go(page, "evidence");
  const start = performance.now();
  await page.locator("#standing").selectOption("NEEDS_REVIEW");
  await expect(page.locator("details")).toHaveCount(50);
  metrics.filterMs = performance.now() - start;
  samples.sort((a, b) => a - b);
  metrics.navigationMedianMs = samples[10];
  metrics.navigationP95Ms = samples[18];
  metrics.renderedFindings = await page.locator("details").count();
  await go(page, "dashboard");
  await cdp.send("HeapProfiler.collectGarbage");
  metrics.heapAfter = await heap();
  fs.mkdirSync("../../.pytest_cache", { recursive: true });
  fs.writeFileSync(
    "../../.pytest_cache/audit-metrics.json",
    JSON.stringify(metrics, null, 2),
  );
  console.log("QA_METRICS " + JSON.stringify(metrics));
  expect(metrics.navigationP95Ms).toBeLessThan(3000);
  expect(metrics.renderedFindings).toBe(50);
});

test("backend brief validation is shown without discarding values", async ({
  page,
}) => {
  await mockService(page, clone(), { createRun: true, validation: true });
  await fillBrief(page);
  await page.getByRole("button", { name: "Submit and start analysis" }).click();
  await expect(page.locator("#market")).toBeFocused();
  await expect(page.locator("#market-error")).toHaveText(
    "MOCKED backend: specify a reachable market.",
  );
  await expect(page.locator("#idea")).toHaveValue(
    "<script>alert(1)</script> فكرة رقمية",
  );
  expect(await page.evaluate(() => __qa.calls.length)).toBe(1);
});
test("new run not yet listed never falls back to another venture output", async ({
  page,
}) => {
  await mockService(page, clone(), { createRun: true, unlistedRun: true });
  await fillBrief(page);
  await page.getByRole("button", { name: "Submit and start analysis" }).click();
  await expect(
    page
      .locator("[role=alert]")
      .filter({ hasText: "No other run has been substituted" }),
  ).toBeVisible();
  await go(page, "decision");
  await expect(
    page.getByText("MOCKED_DEMAND_EVIDENCE_MISSING", { exact: true }),
  ).toHaveCount(0);
});
test("delayed workspace reads do not reset a brief being typed", async ({
  page,
}) => {
  await mockService(page, clone(), { delay: 600 });
  await go(page, "brief");
  await page.locator("#idea").fill("A new digital idea with a clear customer");
  await page.locator("#idea").focus();
  await expect(page.locator("#idea")).toBeFocused();
  await page.waitForFunction(() => __qa.completed > 0);
  await expect(page.locator("#idea")).toHaveValue(
    "A new digital idea with a clear customer",
  );
});

test("health failures clear readiness styling and navigation makes no extra model requests", async ({
  page,
}) => {
  await page.clock.install();
  let calls = 0;
  await page.route("**/health/model", (r) => {
    calls++;
    return r.fulfill({
      json:
        calls === 1
          ? { ready: true, model: "qwen3:4b" }
          : { ready: "true", model: "malformed" },
    });
  });
  const requests = [];
  page.on("request", (r) => requests.push(r.url()));
  await page.goto("/workspace");
  await expect(page.locator("#model-status")).toHaveText(
    "qwen3:4b · Available",
  );
  await expect(page.locator("#model-status")).toHaveClass("ready");
  for (const route of [
    "brief",
    "evidence",
    "artifacts",
    "approvals",
    "dashboard",
  ])
    await go(page, route);
  expect(calls).toBe(1);
  expect(requests.some((u) => u.includes("/health/inference"))).toBe(false);
  expect(requests.every((u) => u.startsWith("http://127.0.0.1:8765"))).toBe(
    true,
  );
  await page.clock.fastForward(30000);
  await expect(page.locator("#model-status")).toHaveText(
    "Model status unavailable",
  );
  await expect(page.locator("#model-status")).not.toHaveClass("ready");
});

test("slow status reads do not overlap or multiply on repeated workflow navigation", async ({
  page,
}) => {
  await page.clock.install();
  await mockService(page, clone(), { workflow: true, delay: 6000 });
  await go(page, "workflow");
  await page.clock.fastForward(5000);
  expect(await page.evaluate(() => __qa.reads)).toBe(1);
  await page.clock.fastForward(1100);
  await expect(page.locator(".agent")).toHaveCount(4);
  await go(page, "dashboard");
  await go(page, "workflow");
  await page.clock.fastForward(5000);
  expect(await page.evaluate(() => __qa.reads)).toBe(2);
  await go(page, "dashboard");
  await go(page, "workflow");
  await page.clock.fastForward(5000);
  expect(await page.evaluate(() => __qa.reads)).toBe(2);
  await page.clock.fastForward(1100);
  await go(page, "dashboard");
  await page.clock.fastForward(10000);
  expect(await page.evaluate(() => __qa.reads)).toBe(2);
});
test("the Builder's real landing-page markup is readable in the preview and stays inert", async ({
  page,
}) => {
  // SYNTHETIC spec, rendered by the real landing_page.py renderer (see landing_fixture.json).
  const { html } = JSON.parse(
    fs.readFileSync(new URL("./landing_fixture.json", import.meta.url), "utf8"),
  );
  const data = clone();
  data.artifacts[1].content =
    html.replace(
      "</main>",
      '<section><script>alert(1)</script><style>body{display:none}</style><form action="/x"><input></form><a href="javascript:alert(1)">link text</a><p onclick="alert(1)" onmouseover="alert(1)">handler text</p><details open ontoggle="alert(1)"><summary>more</summary></details><img src="https://attacker.invalid/p"></section></main>',
    );
  const requests = [];
  page.on("request", (r) => requests.push(r.url()));
  let dialogs = 0;
  page.on("dialog", async (d) => {
    dialogs++;
    await d.dismiss();
  });
  await mockService(page, data);
  await go(page, "artifacts");
  await page.getByRole("button", { name: "Read-only preview" }).nth(1).click();
  const frame = page.frameLocator("iframe");
  await expect(frame.getByRole("heading", { level: 1 })).toHaveText(
    "Screen reader users struggle with PDFs",
  );
  await expect(frame.getByText("Convert PDFs to accessible HTML.")).toBeVisible();
  await expect(frame.getByText("link text")).toBeVisible(); // links are flattened to text
  await expect(
    frame.locator("[src],[href],[style],[class],script,form,input,iframe,svg,img,a"),
  ).toHaveCount(0);
  await expect(frame.locator("style")).toHaveCount(0);
  await frame.getByText("handler text").hover();
  const withAttributes = await frame
    .locator("body *")
    .evaluateAll((els) => els.filter((el) => el.attributes.length > 0).length);
  expect(withAttributes).toBe(0); // no attribute survives: no event handlers, links or styles
  expect(requests.some((u) => u.includes("attacker.invalid"))).toBe(false);
  expect(dialogs).toBe(0);
});


test("approval preserves the founder's typed reason", async ({ page }) => {
  await mockService(page, pending(), { approvals: true });
  await go(page, "approvals");
  await page.locator('[id^="reason-"]').first().fill("Reviewed the interview scope; no outreach is authorized.");
  await page.getByRole("button", {name: "Approve this action"}).click();
  await expect.poll(async () => page.evaluate(() => __qa.calls.length)).toBe(1);
  expect(await page.evaluate(() => __qa.calls[0].options.reason)).toBe("Reviewed the interview scope; no outreach is authorized.");
});

test("genuine recordings load without a model, remain read-only and fit mobile", async ({ page }) => {
  const errors = [];
  const mutations = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => { if(request.method() === "POST") mutations.push(request.url()); });
  await page.setViewportSize({width: 375, height: 812});
  await page.goto("/workspace");
  await page.locator("#recordings-toggle").click();
  await expect(page.locator("#recordings-toggle")).toHaveText("Return to live");
  await go(page, "decision");
  await expect(page.locator(".gate-trace summary")).toBeVisible();
  await page.locator(".gate-trace summary").click();
  await expect(page.getByRole("table", {name: "Recorded deterministic gate trace"})).toBeVisible();
  expect(await page.locator('[data-action="prepare-builder"]').count()).toBe(0);
  await go(page, "evidence");
  await page.locator(".finding summary").first().click();
  await expect(page.locator("blockquote").first()).toBeVisible();
  await go(page, "history");
  await expect(page.locator("tbody tr").first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const axe = await new AxeBuilder({page}).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(axe.violations).toEqual([]);
  await page.locator("#mode-toggle").click();
  await expect(page.locator("#mode-toggle")).toHaveText("Exit demo");
  await page.locator("#mode-toggle").click();
  await expect(page.locator("#recordings-toggle")).toHaveText("Recorded executions");
  expect(mutations).toEqual([]);
  expect(errors).toEqual([]);
});


test("blank optional reason stays blank for explicit rejection", async ({page}) => {
  await mockService(page, pending(), {approvals: true});
  await go(page, "approvals");
  await expect(page.locator('[id^="reason-"]').first()).toHaveValue("");
  expect(await page.evaluate(() => __qa.calls.length)).toBe(0);
  await page.getByRole("button", {name: "Reject", exact: true}).click();
  await expect(page.getByText("Rejected", {exact: true})).toBeVisible();
  expect(await page.evaluate(() => __qa.calls[0].options.reason)).toBe("");
  expect(await page.evaluate(() => __qa.calls[0].choice)).toBe("reject");
});
