/** Presentation-boundary validation only. Never evaluates venture gates or grants approval. */
import { OUTCOMES, STANDINGS } from "./contracts.js";
export class ContractError extends Error {}
/** A transport adapter maps authoritative backend field errors into this UI error. */
export class BriefValidationError extends Error {
  constructor(fields) {
    super("The backend rejected this brief.");
    const allowed = [
      "idea",
      "market",
      "customer",
      "skills",
      "hours",
      "budget",
      "currency",
      "problem",
      "values",
      "constraints",
      "sources",
    ];
    this.fields = Object.fromEntries(
      Object.entries(record(fields))
        .filter(([key]) => allowed.includes(key))
        .map(([key, value]) => [key, required(value).slice(0, 1000)]),
    );
    if (!Object.keys(this.fields).length)
      throw new ContractError("No recognized brief field errors.");
  }
}
const missing = "Not provided";
function record(value) {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new ContractError("Expected an object.");
  return value;
}
function text(value, fallback = missing, max = 20000) {
  if (value == null || value === "") return fallback;
  if (typeof value !== "string" || value.length > max)
    throw new ContractError("Invalid or oversized text.");
  return value;
}
function required(value) {
  const result = text(value, "");
  if (!result.trim())
    throw new ContractError("Required identity or content is missing.");
  return result;
}
function choice(value, values) {
  if (!values.includes(value))
    throw new ContractError("Unknown classification or outcome.");
  return value;
}
function array(value, convert) {
  if (value == null) return [];
  if (!Array.isArray(value) || value.length > 5000)
    throw new ContractError("Invalid or oversized collection.");
  return value.map(convert);
}
const strings = (value) => array(value, (x) => required(x));
function timestamp(value) {
  if (value == null || value === "") return null;
  if (
    typeof value !== "string" ||
    !/^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/.test(value) ||
    !Number.isFinite(Date.parse(value))
  )
    throw new ContractError("Invalid timestamp.");
  return value;
}
function nullableText(value) {
  return value == null ? null : text(value);
}
const schemas = {
  runs: (r) => ({
    id: required(r.id),
    title: text(r.title),
    status: text(r.status),
    phase: text(r.phase),
    recordedAt: timestamp(r.recordedAt),
  }),
  agents: (r) => ({
    agent: choice(r.agent, ["Investigator", "Challenger", "Builder", "Judge"]),
    status: choice(r.status, [
      "Not started",
      "Waiting",
      "Running",
      "Completed",
      "Failed",
      "Blocked",
      "STUBBED",
    ]),
    task: text(r.task),
  }),
  findings: (r) => ({
    id: required(r.id),
    claim: required(r.claim),
    type: text(r.type),
    standing: choice(r.standing, STANDINGS),
    relationship:
      r.relationship == null
        ? missing
        : choice(r.relationship, [
            "Supporting",
            "Partially supporting",
            "Unsupported",
            "Contradictory",
          ]),
    sourceName: text(r.sourceName),
    url: text(r.url, ""),
    quote: text(r.quote, "", 100000),
    assessment: text(r.assessment),
    limitations: text(r.limitations),
    assumption: text(r.assumption),
  }),
  challenges: (r) => ({
    id: required(r.id),
    basis: text(r.basis, "Basis not provided — unverified concern"),
    claim: required(r.claim),
    risk: text(r.risk),
    severity: nullableText(r.severity),
    findings: strings(r.findings),
    missing: strings(r.missing),
    experiment: text(r.experiment),
  }),
  decision: (r) => ({
    outcome: choice(r.outcome, OUTCOMES),
    rule: required(r.rule),
    explanation: text(r.explanation),
    findings: strings(r.findings),
    missing: strings(r.missing),
    risks: strings(r.risks),
    next: text(r.next),
    action: text(r.action),
  }),
  counterfactual: (r) =>
    Object.fromEntries(
      [
        "requirement",
        "limitation",
        "experiment",
        "strengthen",
        "weaken",
        "gate",
      ].map((k) => [k, text(r[k])]),
    ),
  artifacts: (r) => ({
    id: required(r.id),
    title: text(r.title),
    type: text(r.type),
    status: text(r.status),
    description: text(r.description),
    format: choice(r.format, ["text", "html"]),
    content: text(r.content, "", 500000),
    fingerprint: text(r.fingerprint, ""),
    approval: text(r.approval, "Not reported"),
  }),
  approvals: (r) => ({
    id: required(r.id),
    runId: required(r.runId),
    artifactId: required(r.artifactId),
    fingerprint: required(r.fingerprint),
    action: required(r.action),
    description: text(r.description),
    status:
      r.status == null
        ? "Unknown"
        : choice(r.status, [
            "Pending",
            "Pending — MOCKED",
            "Approved",
            "Rejected",
            "Expired",
            "Invalid",
            "Unknown",
          ]),
    expiresAt: timestamp(r.expiresAt),
  }),
  audit: (r) => {
    if (
      r.cost != null &&
      (typeof r.cost !== "number" || !Number.isFinite(r.cost) || r.cost < 0)
    )
      throw new ContractError("Invalid cost.");
    return {
      timestamp: timestamp(r.timestamp) || missing,
      agent: text(r.agent),
      action: text(r.action),
      model: nullableText(r.model),
      sources: strings(r.sources),
      cost: r.cost ?? null,
      approved_by: nullableText(r.approved_by),
      outcome: text(r.outcome),
    };
  },
};
export function normalize(kind, value) {
  if (!Object.hasOwn(schemas, kind))
    throw new ContractError("Unknown response type.");
  if (JSON.stringify(value)?.length > 8000000)
    throw new ContractError("Response exceeds the 8 MB presentation limit.");
  const convert = (r) => schemas[kind](record(r));
  if (kind === "decision" || kind === "counterfactual")
    return value == null ? null : convert(value);
  const rows = array(value, convert);
  const identities = rows.map((r) => r.id ?? r.agent);
  if (kind !== "audit" && new Set(identities).size !== identities.length)
    throw new ContractError("Duplicate identities.");
  return rows;
}
export function modelStatus(value) {
  const r = record(value);
  if (typeof r.ready !== "boolean")
    throw new ContractError("Invalid readiness.");
  return {
    ready: r.ready,
    model: r.ready ? required(r.model) : text(r.model, "Local model"),
  };
}
/** UI guard only; the backend must independently revalidate identity, version and authorization. */
export function approvalBlock(request, artifacts, runId, now = Date.now()) {
  if (request.status !== "Pending") return `Request is ${request.status}.`;
  if (request.runId !== runId) return "Request belongs to a different run.";
  if (request.expiresAt && Date.parse(request.expiresAt) <= now)
    return "Request has expired. Refresh for a current request.";
  const artifact = artifacts.find((a) => a.id === request.artifactId);
  if (
    !artifact ||
    !artifact.fingerprint ||
    artifact.fingerprint !== request.fingerprint
  )
    return "Artifact is missing or its fingerprint changed. Refresh before reviewing.";
  return "";
}
