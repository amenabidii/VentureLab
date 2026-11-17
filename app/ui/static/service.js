import { demo } from "./fixtures.js";
import { modelStatus, BriefValidationError } from "./normalize.js";
export class UnavailableError extends Error {}
/** Error returned by the local backend, carrying its explanation. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    if (response.status === 422 && body && body.fields)
      throw new BriefValidationError(body.fields);
    const detail =
      body && typeof body.detail === "string"
        ? body.detail
        : `The backend refused the request (HTTP ${response.status}).`;
    throw new ApiError(detail, response.status);
  }
  return body;
}
const run = (id, part) => `/api/runs/${encodeURIComponent(id)}/${part}`;
/** Live mode calls the integrated backend (Milestones 2 and 3). Demo mode reads the
 * MOCKED fixtures only and can never create runs, approve or execute anything.
 * Every result is normalized against contracts.js before it is rendered.
 */
export class WorkspaceService {
  constructor(mode = "live") {
    this.mode = mode;
    this.recordings = new Map();
  }
  get live() {
    return this.mode === "live";
  }
  get capabilities() {
    return this.live
      ? { createRun: true, approvals: true, workflow: true, builder: true }
      : { createRun: false, approvals: false, workflow: false, builder: false };
  }
  async listRuns() {
    return this.mode === "recorded"
      ? api("/api/recordings")
      : this.live
        ? api("/api/runs")
        : structuredClone(demo.runs);
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
  async getValidation(id) {
    return this.read(id, "validation");
  }
  async read(id, key, empty = []) {
    if (this.mode === "recorded") {
      if (!this.recordings.has(id))
        this.recordings.set(
          id,
          api(`/api/recordings/${encodeURIComponent(id)}`).catch((error) => {
            this.recordings.delete(id);
            throw error;
          }),
        );
      return structuredClone((await this.recordings.get(id))[key] ?? empty);
    }
    if (this.live) {
      const path = {
        agents: "agents",
        findings: "findings",
        challenges: "challenges",
        decision: "decision",
        counterfactual: "counterfactual",
        artifacts: "artifacts",
        approvals: "approvals",
        audit: "audit",
        validation: "validation",
      }[key];
      return api(run(id, path));
    }
    return id === demo.runs[0].id ? structuredClone(demo[key] ?? empty) : empty;
  }
  async createRun(brief) {
    if (!this.live)
      throw new UnavailableError("Read-only mode never starts research.");
    const body = await api("/api/runs", {
      method: "POST",
      body: JSON.stringify(brief),
    });
    return body.run;
  }
  async prepareBuilder(runId) {
    if (!this.live)
      throw new UnavailableError("Read-only mode never prepares artifacts.");
    return api(run(runId, "builder"), { method: "POST" });
  }
  async decideApproval(request, decision, { key, reason } = {}) {
    if (!this.live)
      throw new UnavailableError("Read-only mode can never grant approval.");
    return api(`/api/approvals/${encodeURIComponent(request.id)}/decision`, {
      method: "POST",
      body: JSON.stringify({
        run_id: request.runId,
        fingerprint: request.fingerprint,
        decision,
        reason: reason || "",
        founder_key: key || "",
      }),
    });
  }
  async recordResult(request, { participants, successes, notes, key }) {
    if (!this.live)
      throw new UnavailableError("Read-only mode can never record results.");
    return api(`/api/approvals/${encodeURIComponent(request.id)}/results`, {
      method: "POST",
      body: JSON.stringify({
        run_id: request.runId,
        founder_key: key || "",
        participants,
        successes,
        notes: notes || "",
      }),
    });
  }
  async executeApproval(request, key) {
    if (!this.live)
      throw new UnavailableError("Read-only mode can never execute an action.");
    return api(`/api/approvals/${encodeURIComponent(request.id)}/execute`, {
      method: "POST",
      body: JSON.stringify({ run_id: request.runId, founder_key: key || "" }),
    });
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
