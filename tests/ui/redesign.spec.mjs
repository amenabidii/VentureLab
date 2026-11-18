// The redesigned founder experience, tested on GENUINE committed recordings (read-only) and,
// for approval controls, on MOCKED fixtures through a test-only transport.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const REPEAT = "record-8f81b4814f1200c7"; // current rules, More evidence needed
const STOP = "record-0266961f4030be27"; // trick brief: fake reviews, policy STOP
const OLD_GO = "record-01170cc0bee3bdd4"; // historical GO, superseded

async function openRecording(page, id) {
  await page.goto("/workspace#projects");
  const toggle = page.locator("#recordings-toggle");
  if ((await toggle.textContent()).trim() !== "Return to live") await toggle.click();
  await expect(toggle).toHaveText("Return to live");
  await page.evaluate(() => (location.hash = "projects"));
  await page.locator(`button[data-run="${id}"]`).click();
  await expect(page.locator("nav a[aria-current]")).toHaveAttribute("href", "#analysis");
  await expect(page.locator(".verdict")).toBeVisible();
}

test("four destinations replace eleven, and every old link still lands on its content", async ({ page }) => {
  await page.goto("/workspace");
  await expect(page.locator("nav a > span:nth-child(2)")).toHaveText(["Projects", "Analysis", "Build & validate", "History & details"]);
  await openRecording(page, REPEAT);
  for (const [old, section] of [["evidence", "sec-evidence"], ["challenger", "sec-concerns"], ["counterfactual", "sec-next"],
    ["workflow", "sec-steps"], ["roadmap", "sec-journey"], ["approvals", "sec-approvals"], ["history", "sec-audit"]]) {
    await page.evaluate((h) => (location.hash = h), old);
    await expect(page.locator(`#${section}`)).toBeFocused();
  }
});

test("a beginner understands the result on one page: recommendation, reason, next step", async ({ page }) => {
  await openRecording(page, REPEAT);
  const verdict = page.locator(".verdict");
  await expect(verdict.locator("h2")).toHaveText("More evidence needed");
  await expect(verdict).toContainText("Main reason:");
  await expect(verdict).toContainText("Missing evidence is not evidence that the problem isn’t real.");
  for (const q of ["What supports your idea?", "What concerns us?", "What’s still unknown?", "What should you do next?"])
    await expect(page.getByRole("heading", { name: q })).toBeVisible();
  // Raw codes are not in the reading path; they stay one click away.
  await expect(verdict.locator("dl.kv code").getByText("REPEAT_INSUFFICIENT_EVIDENCE")).toBeHidden();
  await verdict.locator("details.tech > summary").click();
  await expect(verdict.locator("dl.kv code").getByText("REPEAT_INSUFFICIENT_EVIDENCE")).toBeVisible();
});

test("evidence counts match the recorded classifications, and nothing is upgraded", async ({ page }) => {
  await openRecording(page, REPEAT);
  const recorded = await page.evaluate(async (id) => (await (await fetch(`/api/recordings/${id}`)).json()).findings, REPEAT);
  const count = (s) => recorded.filter((f) => f.standing === s).length;
  const shown = async (name) =>
    Number(await page.locator(".counts li").filter({ hasText: name }).locator("strong").textContent());
  expect(await shown("Strong evidence")).toBe(count("ESTABLISHED"));
  expect(await shown("Needs verification")).toBe(count("NEEDS_REVIEW"));
  expect(await shown("Partial evidence")).toBe(count("PARTIAL_EVIDENCE"));
  expect(await shown("Assumption")).toBe(count("ASSUMPTION"));
  await expect(page.locator("details.finding")).toHaveCount(recorded.length);
  // "What supports your idea?" lists only established findings.
  await expect(page.locator(".qa-card").first()).toContainText(
    count("ESTABLISHED") ? `${count("ESTABLISHED")} finding` : "No finding is strong enough to count yet.");
});

test("a sceptic reaches the exact quotation, its source and the attribution limits in one click", async ({ page }) => {
  await openRecording(page, REPEAT);
  const recorded = await page.evaluate(async (id) => (await (await fetch(`/api/recordings/${id}`)).json()).findings, REPEAT);
  const withQuote = recorded.find((f) => f.quotations.length);
  const item = page.locator(`#finding-${withQuote.id}`);
  await item.locator("summary").click();
  await expect(item.locator("blockquote").first()).toHaveText(withQuote.quotations[0].text);
  await expect(item.locator(`a[href="${withQuote.quotations[0].url}"]`).first()).toHaveAttribute("rel", "noopener noreferrer");
  await expect(item).toContainText("Original author not verified");
  await expect(item).toContainText(withQuote.id);
});

test("a policy STOP says why, and offers no way to build", async ({ page }) => {
  await openRecording(page, STOP);
  const verdict = page.locator(".verdict");
  await expect(verdict.locator("h2")).toHaveText("Do not proceed under current conditions");
  await expect(verdict.locator(".reason-tag")).toHaveText("Policy");
  await expect(verdict).toContainText("not a judgement of the evidence");
  await expect(page.locator('[data-action="prepare-builder"]')).toHaveCount(0);
  await page.evaluate(() => (location.hash = "build"));
  await expect(page.locator(".phase").first()).toContainText("Do not proceed");
});

test("a superseded historical GO is never presented as ready", async ({ page }) => {
  await page.goto("/workspace#projects");
  await page.locator("#recordings-toggle").click();
  const card = page.locator(".project").filter({ has: page.locator(`button[data-run="${OLD_GO}"]`) });
  await expect(card).toContainText("Superseded (was GO)");
  await expect(card).not.toContainText("Ready to test");
  await card.locator("button").click();
  await expect(page.locator(".verdict")).toContainText("Historical decision, now superseded");
  await page.evaluate(() => (location.hash = "build"));
  await expect(page.locator(".phase").first()).toContainText("Superseded (was GO)");
});

test("demo mode never approves, even with a permissive transport", async ({ page }) => {
  await page.route("**/service.js", async (route) => {
    const body = (await (await route.fetch()).text())
      .replace("get capabilities() {", "get capabilities() { if (globalThis.__live) return { createRun: true, approvals: true, workflow: true, builder: true };")
      .replace("async decideApproval(request, decision, { key, reason } = {}) {", "async decideApproval(request, decision, { key, reason } = {}) { (globalThis.__calls ||= []).push(decision);");
    await route.fulfill({ contentType: "text/javascript", body });
  });
  await page.addInitScript(() => (globalThis.__live = true));
  await page.goto("/workspace");
  // MOCKED fixtures, made approvable only inside this test transport.
  await page.evaluate(async () => {
    const { demo } = await import("/workspace/assets/fixtures.js");
    demo.approvals[0].status = "Pending";
  });
  await page.getByRole("button", { name: "Explore demo" }).click();
  await page.evaluate(() => (location.hash = "approvals"));
  const approve = page.getByRole("button", { name: "Approve this action" });
  await expect(approve).toBeDisabled(); // demo mode never approves, even with a permissive transport
});

test("confirmation dialog: cancel sends nothing, Escape closes, focus returns", async ({ page }) => {
  await page.route("**/service.js", (route) =>
    route.fulfill({
      contentType: "text/javascript",
      body: `import { demo } from "/workspace/assets/fixtures.js";
      const data = structuredClone(demo); data.approvals[0].status = "Pending";
      globalThis.__calls = [];
      export class WorkspaceService { constructor(m='live'){this.mode=m;}
        get capabilities(){return {createRun:false,approvals:true,workflow:false,builder:true};}
        async listRuns(){return data.runs;} async getRunStatus(){return data.agents;} async getFindings(){return data.findings;}
        async getChallenges(){return data.challenges;} async getDecision(){return data.decision;} async getCounterfactual(){return data.counterfactual;}
        async listArtifacts(){return data.artifacts;} async getApprovals(){return data.approvals;} async getAudit(){return data.audit;}
        async getValidation(){return [];} async getBrief(){return data.brief;} async getJourney(){return null;}
        async decideApproval(r,c){__calls.push(c); throw new Error('MOCKED: not sent');} }
      export async function getModelStatus(){return {ready:false,model:'MOCKED'};}`,
    }),
  );
  await page.goto("/workspace#approvals");
  const approve = page.getByRole("button", { name: "Approve this action" });
  await expect(approve).toBeEnabled();
  await approve.click();
  const dialog = page.getByRole("dialog", { name: "Approve this request?" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Nothing is published, sent or paid.");
  await expect(dialog.getByRole("button", { name: "Confirm approval" })).toBeFocused();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(approve).toBeFocused();
  await approve.click();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  expect(await page.evaluate(() => __calls)).toEqual([]);
});

test("accessible in light and dark themes, and on a phone without horizontal scrolling", async ({ page }) => {
  test.setTimeout(120000);
  const violations = [];
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await openRecording(page, REPEAT);
    for (const route of ["projects", "analysis", "build", "details", "brief"]) {
      await page.evaluate((h) => (location.hash = h), route);
      await page.waitForTimeout(150);
      const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      for (const v of r.violations) violations.push({ scheme, route, id: v.id, nodes: v.nodes.map((n) => n.target) });
    }
  }
  expect(violations).toEqual([]);
  await page.emulateMedia({ colorScheme: "light" });
  await page.setViewportSize({ width: 360, height: 780 });
  for (const id of [REPEAT, STOP, OLD_GO])
    for (const route of ["analysis", "build", "details"]) {
      await openRecording(page, id);
      await page.evaluate((h) => (location.hash = h), route);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${id} ${route}`).toBe(true);
    }
});

test("the six-phase journey reports only real states: rehearsal, waiting, blocked, files", async ({ page }) => {
  // MOCKED journey payloads in the shape GET /api/runs/<run>/journey returns (tested in Python).
  const journey = (extra) => JSON.stringify({ available: true, discover: "REPEAT", superseded: false, blocked: null,
    rehearsal: true, validated: false, runner: "/phases/run/run-0123456789abcdef", pending: [],
    phases: [2, 3, 4, 5, 6].map((n) => ({ phase: n, title: "P" + n, files: [], gates: [] })), ...extra });
  const serve = (payload) => page.route("**/service.js", (route) => route.fulfill({ contentType: "text/javascript", body: `
    import { demo } from "/workspace/assets/fixtures.js";
    import { normalize } from "/workspace/assets/normalize.js";
    const data = structuredClone(demo); data.runs[0].id = "run-0123456789abcdef";
    export class WorkspaceService { constructor(m='live'){this.mode=m;}
      get capabilities(){return {createRun:false,approvals:false,workflow:false,builder:false};}
      async listRuns(){return data.runs;} async getRunStatus(){return data.agents;} async getFindings(){return data.findings;}
      async getChallenges(){return data.challenges;} async getDecision(){return data.decision;} async getCounterfactual(){return data.counterfactual;}
      async listArtifacts(){return data.artifacts;} async getApprovals(){return [];} async getAudit(){return data.audit;}
      async getValidation(){return [];} async getBrief(){return data.brief;} async getJourney(){return ${payload};} }
    export async function getModelStatus(){return {ready:false,model:'MOCKED'};}` }));
  await serve(journey({ pending: [{ action: "rehearse_after_repeat", what: "Run phases 2–6 as a labelled REHEARSAL", file: null, fingerprint: "a".repeat(64) }],
    phases: [2, 3, 4, 5, 6].map((n) => ({ phase: n, title: "P" + n,
      files: n === 4 ? [{ name: "phase4_step1_pricing.md", url: "/phases/run/run-0123456789abcdef/view/phase4_step1_pricing.md" }] : [],
      gates: n === 5 ? [{ name: "phase5_gate_launch.json", outcome: "GO", decision: "REHEARSAL PASSED", launch: "DO NOT LAUNCH: rehearsal only.", rehearsal: true }] : [] })) }));
  await page.goto("/workspace#build");
  const phases = page.locator(".phase");
  await expect(phases).toHaveCount(6);
  await expect(phases.nth(3)).toContainText("Drafts prepared");
  await expect(phases.nth(4)).toContainText("Rehearsal · gate GO");
  await expect(phases.nth(4)).toContainText("DO NOT LAUNCH: rehearsal only.");
  await expect(phases.nth(4)).toContainText("MOCKED · publishing and sale to cash");
  await expect(page.locator(".waiting")).toContainText("Run phases 2–6 as a labelled REHEARSAL");
  await expect(page.getByRole("link", { name: "Open the phase runner →" })).toHaveAttribute("href", "/phases/run/run-0123456789abcdef");
  await page.unrouteAll();
  await serve(journey({ blocked: "Discover decided STOP: phases 2–6 are blocked." }));
  await page.reload();
  await expect(page.locator(".phase").nth(2)).toContainText("Blocked");
  await expect(page.locator("#sec-journey .notice")).toContainText("Discover decided STOP");
  // A malformed runner link is refused by the normaliser, never rendered.
  await page.unrouteAll();
  await serve(journey({ runner: "https://attacker.invalid/x" }));
  await page.reload();
  await expect(page.locator('a[href*="attacker.invalid"]')).toHaveCount(0);
});
