import { demo } from "./fixtures.js";
import { modelStatus } from "./normalize.js";
export class UnavailableError extends Error {}
/** Override this adapter at integration. No speculative HTTP endpoints are called.
 * Each method returns a Promise; binding implementations must normalize to contracts.js.
 * createRun returns a persisted Run, never a locally fabricated completion.
 * decideApproval must bind request + run + artifact + fingerprint on the server.
 */
export class WorkspaceService {
  constructor(mode = "live") {
    this.mode = mode;
  }
  get capabilities() {
    return { createRun: false, approvals: false, workflow: false };
  }
  async listRuns() {
    return this.mode === "demo" ? structuredClone(demo.runs) : [];
  }
  async getRunStatus(id) {
    return this.read(id, "agents");
  }
  async getFindings(id) {
    return this.read(id, "findings");
  }
  async getChallenges(id) {
    return this.read(id, "challenges");
  }
  async getDecision(id) {
    return this.read(id, "decision", null);
  }
  async getCounterfactual(id) {
    return this.read(id, "counterfactual", null);
  }
  async listArtifacts(id) {
    return this.read(id, "artifacts");
  }
  async getApprovals(id) {
    return this.read(id, "approvals");
  }
  async getAudit(id) {
    return this.read(id, "audit");
  }
  read(id, key, empty = []) {
    return this.mode === "demo" && id === demo.runs[0].id
      ? structuredClone(demo[key])
      : empty;
  }
  async createRun(_brief) {
    throw new UnavailableError(
      "STUBBED — Milestone 2 run creation is not connected. No research was started.",
    );
  }
  async decideApproval(_request, _decision) {
    throw new UnavailableError(
      "STUBBED — Milestone 3 approval backend is not connected. No approval was granted.",
    );
  }
}
/** Real, existing M1 endpoint. This check never starts inference. */
export async function getModelStatus(fetcher = fetch) {
  const response = await fetcher("/health/model", {
    signal: AbortSignal.timeout(15000),
    cache: "no-store",
  });
  if (!response.ok && response.status !== 503)
    throw new Error("Model status could not be read.");
  const status = modelStatus(await response.json());
  if (!response.ok && status.ready)
    throw new Error("Contradictory readiness response.");
  return status;
}
