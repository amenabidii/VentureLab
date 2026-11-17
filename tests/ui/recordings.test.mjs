import test from "node:test";
import assert from "node:assert/strict";
import { WorkspaceService } from "../../app/ui/static/service.js";
import { quoteDetails } from "../../app/ui/static/views.js";

test("recorded service shares reads, retries failure, and refuses every mutation", async () => {
  const original = globalThis.fetch;
  let reads = 0;
  globalThis.fetch = async () => {
    reads++;
    return {ok: reads > 1, status: 409, json: async () => reads === 1 ? {detail: "Integrity failed"} : {findings: [], decision: {outcome: "REPEAT"}}};
  };
  try {
    const service = new WorkspaceService("recorded");
    await assert.rejects(service.getFindings("record-example"), /Integrity failed/);
    const [findings, decision] = await Promise.all([service.getFindings("record-example"), service.getDecision("record-example")]);
    assert.deepEqual(findings, []);
    assert.equal(decision.outcome, "REPEAT");
    assert.equal(reads, 2);
    for (const operation of [() => service.createRun({}), () => service.prepareBuilder("x"), () => service.decideApproval({}, "approve"), () => service.executeApproval({}, "x")]) {
      await assert.rejects(operation(), /Read-only/);
    }
    assert.equal(reads, 2);
  } finally { globalThis.fetch = original; }
});

test("each exact quotation retains its own source and hostile content stays inert", () => {
  const html = quoteDetails({quotations: [
    {text: "First line\nsecond line", url: "https://one.example/source", sourceName: "one.example"},
    {text: "<script>bad()</script>", url: "javascript:bad()", sourceName: "untrusted"},
    {text: "Third quote", url: "https://three.example/source", sourceName: "three.example"},
  ]});
  assert.match(html, /First line\nsecond line<\/blockquote><a href="https:\/\/one.example\/source"/);
  assert.match(html, /Third quote<\/blockquote><a href="https:\/\/three.example\/source"/);
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes('href="javascript:'));
});
