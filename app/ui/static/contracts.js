/** Provisional presentation contracts. Domain validation belongs to Milestones 2/3.
 * @typedef {{idea:string, market:string, customer:string, skills:string, hours:number, budget:number, currency:string, problem:string, values:string, constraints:string, sources:string[]}} FounderBrief
 * @typedef {{id:string, claim:string, type:string, standing:'ESTABLISHED'|'NEEDS_REVIEW'|'ASSUMPTION', relationship:string, sourceName:string, url:string, quote:string, assessment:string, limitations:string, assumption:string}} Finding
 * @typedef {{id:string, title:string, status:string, phase:string, recordedAt?:string}} Run
 * @typedef {{agent:string, status:'Not started'|'Waiting'|'Running'|'Completed'|'Failed'|'Blocked'|'STUBBED', task:string}} AgentStatus
 * @typedef {{id:string, basis:string, claim:string, risk:string, severity?:string, findings:string[], missing:string[], experiment:string}} Challenge
 * @typedef {{outcome:'GO'|'REPEAT'|'PIVOT'|'STOP', rule:string, explanation:string, findings:string[], missing:string[], risks:string[], next:string, action:string}} Decision
 * @typedef {{requirement:string, limitation:string, experiment:string, strengthen:string, weaken:string, gate:string}} Counterfactual
 * @typedef {{id:string, title:string, type:string, status:string, description:string, content:string, format:'text'|'html', fingerprint:string, approval:string}} Artifact
 * @typedef {{id:string, runId:string, artifactId:string, fingerprint:string, action:string, description:string, status:string}} Approval
 * @typedef {{timestamp:string, agent:string, action:string, model:string|null, sources:string[], cost:number|null, approved_by:string|null, outcome:string}} AuditEntry
 */
export const STANDINGS = ["ESTABLISHED", "NEEDS_REVIEW", "ASSUMPTION"];
export const OUTCOMES = ["GO", "REPEAT", "PIVOT", "STOP"];
export function safeURL(value) {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}
export function validateBrief(brief) {
  const errors = {};
  for (const key of [
    "idea",
    "market",
    "customer",
    "skills",
    "problem",
    "values",
    "constraints",
  ]) {
    if (!String(brief[key] ?? "").trim())
      errors[key] =
        "Please describe this field; use “None” if there are no constraints.";
    else if (brief[key].length > 4000)
      errors[key] = "Keep this field under 4,000 characters.";
  }
  if (String(brief.idea ?? "").trim().length < 20)
    errors.idea = "Describe your idea in at least 20 characters.";
  if (
    brief.hours === "" ||
    !Number.isFinite(Number(brief.hours)) ||
    Number(brief.hours) < 1 ||
    Number(brief.hours) > 168
  )
    errors.hours = "Enter between 1 and 168 hours per week.";
  if (
    brief.budget === "" ||
    !Number.isFinite(Number(brief.budget)) ||
    Number(brief.budget) < 0
  )
    errors.budget = "Enter a budget of zero or more.";
  if (!["EGP", "USD", "EUR"].includes(brief.currency))
    errors.currency = "Choose a supported budget currency.";
  if (brief.sources.length > 10 || brief.sources.some((url) => !safeURL(url)))
    errors.sources =
      "Use up to 10 complete HTTP or HTTPS source URLs, one per line, without credentials.";
  return errors;
}
export function filterFindings(findings, standing = "", type = "") {
  return findings.filter(
    (f) => (!standing || f.standing === standing) && (!type || f.type === type),
  );
}
