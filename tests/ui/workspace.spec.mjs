import { test, expect } from "@playwright/test";
test.beforeEach(async ({ page }) => {
  await page.route("**/health/model", (r) =>
    r.fulfill({ json: { ready: false, model: "qwen3:4b" }, status: 503 }),
  );
  await page.goto("/workspace");
});
test("empty live workspace, navigation, and demo isolation", async ({
  page,
}) => {
  await expect(
    page.getByText("No venture runs yet.", { exact: false }),
  ).toBeVisible();
  const labels = ["Projects", "Analysis", "Build & validate", "History & details"];
  for (const label of labels) {
    await page
      .getByRole("navigation")
      .getByRole("link", { name: label, exact: true })
      .click();
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("nav a[aria-current]")).toHaveText(
      new RegExp(label),
    );
  }
  await page.getByRole("button", { name: "Explore demo" }).click();
  await expect(page.locator("#mode-banner")).toContainText("MOCKED");
  await page.getByRole("button", { name: "Exit demo" }).click();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Projects", exact: true })
    .click();
  await expect(
    page.getByText("No venture runs yet.", { exact: false }),
  ).toBeVisible();
});
test("founder brief validation, review, persistence across navigation, disabled submit", async ({
  page,
}) => {
  await page.locator(".sidebar .new-idea").click();
  await page.getByRole("button", { name: "Review brief" }).click();
  await expect(page.locator("#idea")).toHaveAttribute("aria-invalid", "true");
  for (const [key, value] of Object.entries({
    idea: "A digital checklist for design handoffs",
    market: "Egypt",
    customer: "Design studios",
    problem: "Lost handoff context",
    skills: "Design",
    hours: "5",
    budget: "0",
    values: "Privacy",
    constraints: "None",
    sources: "https://example.org/",
  }))
    await page.locator("#" + key).fill(value);
  await page.getByRole("button", { name: "Review brief" }).click();
  await expect(
    page.getByRole("heading", { name: "Review your founder brief" }),
  ).toBeVisible();
  // Integrated build: submission is connected to the real backend (not clicked here).
  await expect(
    page.getByRole("button", { name: "Submit and start analysis" }),
  ).toBeEnabled();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Projects", exact: true })
    .click();
  await page.locator(".sidebar .new-idea").click();
  await expect(
    page.getByText("A digital checklist for design handoffs"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit brief" }).click();
  await expect(page.locator("#idea")).toHaveValue(
    "A digital checklist for design handoffs",
  );
});
test("evidence filters, source inspection, references, decision and counterfactual", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Explore demo" }).click();
  await page.goto("/workspace#evidence");
  await page.reload();
  // A reload returns to live mode; fixtures are never persisted as live data.
  await page.getByRole("button", { name: "Explore demo" }).click();
  await page.locator("#standing").selectOption("ASSUMPTION");
  await expect(page.locator("details.finding")).toHaveCount(1);
  await page.locator("#claim-type").selectOption("Demand");
  await expect(page.locator("details.finding")).toHaveCount(1);
  await page.locator("#standing").selectOption("");
  await page.locator("#claim-type").selectOption("");
  await page.locator("#finding-F-02 summary").click();
  await expect(page.locator("#finding-F-02 a")).toHaveAttribute(
    "href",
    "https://example.org/",
  );
  await expect(page.locator("#finding-F-02 a")).toHaveAttribute(
    "rel",
    "noopener noreferrer",
  );
  await page.evaluate(() => (location.hash = "challenger"));
  await page.locator(".concern summary").first().click();
  await page.getByRole("link", { name: "Evidence F-03", exact: true }).click();
  await expect(page.locator("#finding-F-03")).toHaveAttribute("open", "");
  await page.evaluate(() => (location.hash = "decision"));
  await page.locator(".verdict details.tech > summary").click();
  await expect(
    page.locator(".verdict").getByText("MOCKED_DEMAND_EVIDENCE_MISSING", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "What could change this recommendation?" })
    .click();
  await expect(
    page.getByText("No experiment automatically guarantees GO.", {
      exact: false,
    }),
  ).toBeVisible();
});
test("artifacts are sandboxed, approvals disabled, audit labeled", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Explore demo" }).click();
  await page.evaluate(() => (location.hash = "artifacts"));
  await page.getByRole("button", { name: "Read-only preview" }).nth(1).click();
  await expect(page.locator("iframe")).toHaveAttribute("sandbox", "");
  await expect(page.frameLocator("iframe").getByRole("heading")).toHaveText(
    "A clearer handoff starts with a checklist.",
  );
  await page.evaluate(() => (location.hash = "approvals"));
  await expect(
    page.getByRole("button", { name: "Approve this action" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Reject", exact: true }),
  ).toBeDisabled();
  await page.evaluate(() => (location.hash = "history"));
  await expect(page.locator("caption")).toContainText("MOCKED");
  await page.locator("#audit-agent").selectOption("Judge");
  await expect(page.locator("tbody tr")).toHaveCount(1);
});
test("malicious content remains inert in rendered text and artifact previews", async ({
  page,
}) => {
  await page.route("**/fixtures.js", async (route) => {
    const response = await route.fetch();
    let body = await response.text();
    body = body
      .replace(
        "The proposed product is a digital handoff checklist.",
        "<img src=x onerror=alert(1)>",
      )
      .replace(
        "<h1>A clearer handoff starts with a checklist.</h1>",
        "<script>parent.alert(1)</script><img src=https://example.org/probe onerror=alert(1)><a href=javascript:alert(1)>unsafe</a><h1>Inert preview</h1>",
      );
    await route.fulfill({ response, body });
  });
  await page.reload();
  let dialogs = 0;
  page.on("dialog", async (d) => {
    dialogs++;
    await d.dismiss();
  });
  await page.getByRole("button", { name: "Explore demo" }).click();
  await page.evaluate(() => (location.hash = "evidence"));
  await expect(page.locator("main img")).toHaveCount(0);
  await expect(page.locator(".finding-title").getByText("<img src=x onerror=alert(1)>")).toBeVisible();
  await page.evaluate(() => (location.hash = "artifacts"));
  await page.getByRole("button", { name: "Read-only preview" }).nth(1).click();
  const frame = page.frameLocator("iframe");
  await expect(frame.locator("script")).toHaveCount(0);
  await expect(frame.locator("[href], [src], [onerror]")).toHaveCount(0);
  expect(dialogs).toBe(0);
});
test("responsive layouts and keyboard navigation", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.locator("h1")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page.keyboard.press("Control+Home");
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
  await page.locator("h1").click();
  await page.screenshot({
    path: "../../.pytest_cache/ui-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "../../.pytest_cache/ui-desktop.png",
    fullPage: true,
  });
});
test("loading and failed adapter calls are truthful and retryable", async ({
  page,
}) => {
  await page.route("**/service.js", async (route) => {
    const response = await route.fetch();
    const body = (await response.text()).replace(
      "async listRuns() {",
      "async listRuns() { await new Promise(r=>setTimeout(r,700)); if (!globalThis.__retried) {globalThis.__retried=true; throw new Error('test failure');}",
    );
    await route.fulfill({ response, body });
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Reading workspace…" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "We couldn’t load this view" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByText("No venture runs yet.", { exact: false }),
  ).toBeVisible();
});

test("all demo screens fit a narrow viewport without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Explore demo" }).click();
  for (const route of [
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
    await page.evaluate((route) => (location.hash = route), route);
    await expect(page.locator("h1")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      route,
    ).toBe(true);
  }
});
