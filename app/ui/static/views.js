import { safeURL, STANDINGS, OUTCOMES, filterFindings } from "./contracts.js";
import { approvalBlock } from "./normalize.js";
export const pages = [
  ["dashboard", "Overview", "◈"],
  ["brief", "Founder brief", "＋"],
  ["workflow", "Agent workflow", "◇"],
  ["evidence", "Evidence explorer", "▤"],
  ["challenger", "Challenger analysis", "⚑"],
  ["decision", "Decision dashboard", "◎"],
  ["counterfactual", "Counterfactual challenge", "↗"],
  ["artifacts", "Builder artifacts", "▧"],
  ["approvals", "Founder approval", "✓"],
  ["history", "Decision history", "◷"],
  ["roadmap", "Six-phase roadmap", "⊞"],
];
export const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const e = escape;
export function badge(text) {
  const tone = [
    "ESTABLISHED",
    "GO",
    "Completed",
    "Working",
    "Executed",
  ].includes(text)
    ? "green"
    : /STOP|Failed|Contradictory|CONTRADICTED|Rejected/.test(text)
      ? "red"
      : /REPEAT|REVIEW|ASSUMPTION|Blocked|Pending/.test(text)
        ? "amber"
        : "neutral";
  return `<span class="badge ${tone}">${e(text)}</span>`;
}
export const link = (route, label, cls = "button") =>
  `<a class="${e(cls)}" href="#${e(route)}">${e(label)}</a>`;
export function source(url, label) {
  const safe = safeURL(url);
  return safe
    ? `<a href="${e(safe)}" target="_blank" rel="noopener noreferrer">${e(label || safe)} ↗</a>`
    : `<span class="muted">${e((label ? label + " · " : "") + (url ? "Unsafe or malformed source URL — link disabled" : "No source URL provided"))}</span>`;
}
const list = (values) =>
  values?.length
    ? `<ul class="detail-list">${values.map((x) => `<li>${e(x)}</li>`).join("")}</ul>`
    : '<p class="muted">Not provided.</p>';
const refs = (ids, findings = []) =>
  ids?.length
    ? ids
        .map((id) =>
          findings.some((f) => f.id === id)
            ? link(`evidence/${encodeURIComponent(id)}`, id, "reference")
            : `<span class="badge amber">${e(id)} · Reference unavailable</span>`,
        )
        .join(" ")
    : '<span class="muted">No evidence references.</span>';
export const empty = (title, copy, action = "") =>
  `<section class="empty"><div class="empty-icon">◇</div><h2>${e(title)}</h2><p>${e(copy)}</p>${action}</section>`;
const heading = (eyebrow, title, description, action = "") =>
  `<div class="page-heading"><div><div class="eyebrow">${e(eyebrow)}</div><h1>${e(title)}</h1><p>${e(description)}</p></div>${action}</div>`;
export const loading = () =>
  '<section class="empty" role="status" aria-live="polite"><span class="spinner"></span><h2>Reading workspace…</h2><p>Long-running model operations may take several minutes. Completion is shown only when reported by the backend.</p></section>';
export const errorView = () =>
  '<section class="empty" role="alert"><h2>We couldn’t load this view</h2><p>Your brief remains in this browser tab. Check the local service and try again.</p><button data-action="retry">Try again</button></section>';
export const phases = [
  [
    "Discover",
    "Define the opportunity",
    "Founder brief and sourced findings",
    "Evidence quality and permitted scope",
    "Working",
    "brief",
  ],
  [
    "Validate",
    "Challenge the assumptions",
    "Critical analysis and a validation plan",
    "Observed problem and demand evidence",
    "Working · plan only; results entry STUBBED",
    "evidence",
  ],
  [
    "Build",
    "Create a testable artifact",
    "Experiment kits and local prototypes",
    "Backend approval for the exact action and artifact",
    "Working · local files only",
    "artifacts",
  ],
  [
    "Commercial Setup",
    "Set the price and policies",
    "Price hypotheses (ASSUMPTION) and DRAFT terms, privacy and refund policies",
    "The founder chooses the price; approval bound to the exact file",
    "Working · no payments",
    "",
  ],
  [
    "Launch",
    "Open the store; deliver automatically",
    "Store page, launch-post drafts, sale-to-cash test log",
    "Founder approves the exact page and product file; all checks must pass",
    "MOCKED · publishing and sale to cash",
    "",
  ],
  [
    "Operate & Learn",
    "Learn from observed outcomes",
    "Support triage, metrics, persevere-or-pivot memo",
    "Fixed rules over real evidence only; MOCKED metrics never count",
    "Working · real evidence only",
    "",
  ],
];
export function dashboard(s) {
  return (
    heading(
      "YOUR VENTURE, UNDER THE MICROSCOPE",
      "Good ideas deserve hard questions.",
      "Turn a promising idea into a clearer next step, with evidence you can inspect.",
      link("brief", "＋ Start new venture"),
    ) +
    `<section class="hero"><div><span class="eyebrow">A MORE RIGOROUS WAY FORWARD</span><h2>Conviction is a starting point.<br><span>Evidence is the next step.</span></h2><p>Investigate the opportunity. Challenge the assumptions.<br>Decide what is worth testing — and what isn’t.</p>${link("brief", "Shape your founder brief →", "button light")}</div><div class="hero-diagram" aria-label="Evidence informs challenge, then decision"><span>01 / INVESTIGATE</span><i>↓</i><span>02 / CHALLENGE</span><i>↓</i><span>03 / DECIDE</span><small>You stay in control.</small></div></section>` +
    `<div class="section-title"><h2>Your path forward</h2>${link("roadmap", "Explore all phases →", "text-link")}</div><div class="phase-strip">${phases.map((p, i) => `<a href="#${p[5] || "roadmap"}"><span class="phase-number">0${i + 1}</span><strong>${p[0]}</strong><small>${i === 0 ? "Brief available" : p[4]}</small></a>`).join("")}</div>` +
    `<div class="section-title"><h2>Venture runs</h2>${s.recorded ? badge("Recorded executions · read-only") : s.demo ? badge("MOCKED fixtures") : badge("Live workspace")}</div>` +
    (s.runs.length
      ? `<div class="cards">${s.runs.map((r) => `<article class="card"><span class="eyebrow">${e(r.phase)}</span><h2>${e(r.title)}</h2>${badge(r.status)}${r.recordedAt ? `<p>Recorded run (prior execution) · ${e(r.recordedAt)}</p>` : ""}<p>Run ${e(r.id)}</p><button data-run="${e(r.id)}">Open workspace →</button></article>`).join("")}</div>`
      : empty(
          "Your first investigation starts here.",
          "No venture runs are available. Submit a founder brief to start a real analysis.",
          link("brief", "Create founder brief"),
        )) +
    `<div class="grid-two"><article class="card"><span class="eyebrow">RECENT DECISION</span>${s.data.decision ? `<h2>${badge(s.data.decision.outcome)}</h2><p>${e(s.data.decision.explanation)}</p>${link("decision", "Inspect the rule →", "text-link")}` : "<h2>No decisions yet</h2><p>A recommendation appears only after a backend gate evaluation.</p>"}</article><article class="card"><span class="eyebrow">WORKSPACE READINESS</span><h2>Built around founder control</h2><p>Research, the deterministic gate, the Builder and founder approval are connected to the local backend. Commercial Setup, Launch and Operate &amp; Learn remain STUBBED.</p>${link("approvals", "Review approval boundary →", "text-link")}</article></div>`
  );
}
export const fields = [
  [
    "idea",
    "Business idea",
    "What will you build, and how does it help?",
    "textarea",
  ],
  [
    "market",
    "Target market",
    "For example: independent design studios in Egypt.",
    "text",
  ],
  [
    "customer",
    "Target customer",
    "Who experiences the problem and who decides to adopt?",
    "text",
  ],
  [
    "problem",
    "Core problem",
    "Describe a specific situation and the current workaround.",
    "textarea",
  ],
  [
    "skills",
    "Founder skills",
    "What can you build or investigate yourself?",
    "text",
  ],
  [
    "hours",
    "Available weekly time",
    "Hours per week, from 1 to 168.",
    "number",
  ],
  [
    "budget",
    "Available budget",
    "Your constraint, not a payment. Zero is valid.",
    "number",
  ],
  ["values", "Values", "What principles should guide the venture?", "textarea"],
  [
    "constraints",
    "Constraints",
    "Limits on scope, access, resources or execution. Use “None” if applicable.",
    "textarea",
  ],
  [
    "sources",
    "Supporting sources",
    "Optional. Up to 10 HTTP/HTTPS URLs, one per line.",
    "textarea",
  ],
];
export function brief(s) {
  const review = s.review;
  return (
    heading(
      "01 / DEFINE THE OPPORTUNITY",
      review ? "Review your founder brief" : "Start with what you know.",
      "Be specific about the problem. Be honest about what is still an assumption.",
    ) +
    `<div class="brief-layout"><section class="card">${
      review
        ? `<div class="section-title"><h2>Ready for your review</h2>${badge(s.submittedRunId ? "Submitted to backend" : "Not submitted")}</div><dl class="review">${fields.map(([key, label]) => `<dt>${label}</dt><dd>${e(key === "sources" ? s.brief.sources.join("\n") : s.brief[key]) || "Not provided"}${key === "budget" ? " " + e(s.brief.currency) : ""}</dd>`).join("")}</dl><div class="notice">${s.service.capabilities.createRun ? "The backend validates this brief, then runs real research with the local model. This usually takes two to four minutes." : "Demo mode never starts research."}</div>${s.service.capabilities.createRun ? `<label class="check"><input type="checkbox" id="quick-run" ${s.quick ? "checked" : ""}> Shorter demonstration run (one search, fewer claims; every step still runs live)</label>` : ""}<div class="actions"><button data-action="${s.submittedRunId || s.submitLocked ? "new-brief" : "edit"}" class="secondary" ${s.busy ? "disabled" : ""}>${s.submittedRunId || s.submitLocked ? "Prepare another brief" : "← Edit brief"}</button><button data-action="submit" ${!s.service.capabilities.createRun || s.demo || s.busy || s.submitLocked || s.submittedRunId ? "disabled" : ""}>${s.busy ? "Submitting…" : "Submit and start analysis"}</button></div>`
        : `<form id="brief-form" novalidate><div id="validation-summary" role="alert">${Object.keys(s.errors).length ? '<p class="field-error">Please correct the highlighted fields.</p>' : ""}</div><div class="form-grid">${fields.map(([key, label, help, type]) => `<div class="field ${type === "textarea" ? "full" : ""}"><label for="${key}">${label} <span>${key === "sources" ? "Optional" : "Required"}</span></label>${type === "textarea" ? `<textarea id="${key}" name="${key}" rows="${key === "idea" || key === "problem" ? 3 : 2}" maxlength="4000"` : `<input id="${key}" name="${key}" type="${type}" ${type === "number" ? `min="${key === "hours" ? 1 : 0}" ${key === "hours" ? 'max="168"' : ""} step="any"` : 'maxlength="4000"'}`} aria-describedby="${key}-help ${key}-error" ${s.errors[key] ? 'aria-invalid="true"' : ""} ${key !== "sources" ? "required" : ""}${type === "textarea" ? `>${e(key === "sources" ? s.brief.sources.join("\n") : s.brief[key] || "")}</textarea>` : ` value="${e(s.brief[key] ?? "")}">`}<small id="${key}-help">${help}</small><span id="${key}-error" class="field-error">${e(s.errors[key] || "")}</span></div>`).join("")}<div class="field"><label for="currency">Budget currency</label><select id="currency" name="currency" aria-describedby="currency-error" ${s.errors.currency ? 'aria-invalid="true"' : ""}>${["EGP", "USD", "EUR"].map((c) => `<option ${s.brief.currency === c ? "selected" : ""}>${c}</option>`).join("")}</select><span id="currency-error" class="field-error">${e(s.errors.currency || "")}</span></div></div><div class="actions"><span class="muted">Kept in this tab only. Reloading clears it.</span><button type="submit">Review brief →</button></div></form>`
    }</section><aside><article class="card dark"><span class="eyebrow">A STRONGER START</span><h2>A useful brief is specific, not perfect.</h2><p>Name a customer you can reach. Describe a problem you can observe. Include the constraints that matter.</p><hr><p>We may recommend gathering evidence, changing direction, or stopping under current conditions.</p></article><article class="card"><h3>Your control comes first</h3><p>Review before submission. Backend approval is required for gated actions.</p><p>Never include passwords, payment credentials or private customer records.</p></article></aside></div>`
  );
}
export function workflow(s) {
  const agents = s.data.agents.length
    ? s.data.agents
    : ["Investigator", "Challenger", "Builder", "Judge"].map((agent) => ({
        agent,
        status: "STUBBED",
        task: "Awaiting backend integration. No operation has started.",
      }));
  return (
    heading(
      "02 / FOLLOW THE WORK",
      "Four roles. One transparent process.",
      "Statuses reflect backend records. No animated or simulated execution.",
    ) +
    `<div class="workflow">${agents.map((a, i) => `<article class="card agent"><div class="agent-number">0${i + 1}</div><div><h2>${e(a.agent)}</h2><p>${e(a.task)}</p>${link({ Investigator: "evidence", Challenger: "challenger", Builder: "artifacts", Judge: "decision" }[a.agent], a.status === "Completed" ? "View output →" : "Open output view →", "text-link")}</div>${badge(a.status)}</article>`).join("")}</div><div class="notice">The Judge explains deterministic gate results. It cannot override them. ${s.service.capabilities.workflow ? "Status refreshes every 5 seconds while this view is open." : "Demo mode shows MOCKED statuses."}${s.runDetail?.error ? ` Run message: ${e(s.runDetail.error)}` : ""}</div>`
  );
}
export function evidence(s) {
  const findings = filterFindings(s.data.findings, s.standing, s.claimType);
  const referenceIndex = findings.findIndex((f) => f.id === s.focusFinding);
  const page =
    referenceIndex >= 0
      ? Math.floor(referenceIndex / 50)
      : Math.max(
          0,
          Math.min(s.evidencePage || 0, Math.ceil(findings.length / 50) - 1),
        );
  const visible = findings.slice(page * 50, (page + 1) * 50);
  const pager =
    findings.length > 50
      ? `<div class="actions" aria-label="Evidence pages"><span>Showing ${page * 50 + 1}–${Math.min((page + 1) * 50, findings.length)} of ${findings.length}</span><button data-page="-1" ${page === 0 ? "disabled" : ""}>Previous findings</button><button data-page="1" ${(page + 1) * 50 >= findings.length ? "disabled" : ""}>Next findings</button></div>`
      : "";
  s.evidencePage = page;
  return (
    heading(
      "03 / INSPECT THE SOURCES",
      "Evidence, with its limits visible.",
      "Separate what is established from what needs review — and what remains an assumption.",
    ) +
    `<div class="legend">${STANDINGS.map((b) => badge(b)).join("")}<span>Standing and claim–source relationship are separate assessments.</span></div><div class="filters"><label>Evidence standing<select id="standing"><option value="">All standings</option>${STANDINGS.map((v) => `<option ${s.standing === v ? "selected" : ""}>${v}</option>`).join("")}</select></label><label>Claim type<select id="claim-type"><option value="">All claim types</option>${[...new Set(s.data.findings.map((f) => f.type))].map((v) => `<option ${s.claimType === v ? "selected" : ""}>${e(v)}</option>`).join("")}</select></label><span role="status">${findings.length} findings</span></div>` +
    (s.focusFinding && referenceIndex < 0
      ? `<p class="notice" role="status">Referenced finding ${e(s.focusFinding)} is unavailable in this run.</p>`
      : "") +
    (findings.length
      ? visible
          .map(
            (f) =>
              `<details class="finding card" id="finding-${e(f.id)}" ${s.focusFinding === f.id ? "open" : ""}><summary><span class="finding-id">${e(f.id)}</span><span class="finding-title">${e(f.claim)}<small>${e(f.type)} · ${e(f.sourceName)}</small></span>${badge(f.standing)}</summary><div class="finding-body"><div class="grid-two"><div><h3>Supporting quotation</h3>${quoteDetails(f)}</div><div><h3>Assessment</h3>${badge(f.relationship)}<p>${e(f.assessment)}</p></div></div><div class="grid-two"><div><h3>Limitations</h3><p>${e(f.limitations)}</p></div><div><h3>Associated assumption</h3><p>${e(f.assumption)}</p></div></div></div></details>`,
          )
          .join("")
      : empty(
          s.data.findings.length
            ? "No findings match these filters."
            : "No evidence collected yet.",
          s.data.findings.length
            ? "Choose a different standing or claim type."
            : "Findings will appear here after actual Investigator execution.",
        )) +
    pager
  );
}
export function challenger(s) {
  return (
    heading(
      "04 / PRESSURE-TEST THE IDEA",
      "The questions worth asking.",
      "Concerns are labeled by their basis. A model opinion is not an established fact.",
    ) +
    (s.data.challenges.length
      ? s.data.challenges
          .map(
            (c) =>
              `<article class="card challenge"><div class="section-title"><span class="eyebrow">${e(c.id)} / ${e(c.basis)}</span>${c.severity ? badge(c.severity) : ""}</div><h2>${e(c.claim)}</h2><p>${e(c.risk)}</p><div class="grid-two"><div><h3>Evidence references</h3>${refs(c.findings, s.data.findings)}<h3>Missing evidence</h3>${list(c.missing)}</div><div class="inset"><h3>Recommended experiment</h3><p>${e(c.experiment)}</p></div></div></article>`,
          )
          .join("")
      : empty(
          "No Challenger analysis yet.",
          "Evidence-based concerns, assumptions and new hypotheses will appear separately after execution.",
        ))
  );
}
export function decision(s) {
  const d = s.data.decision;
  return (
    heading(
      "05 / UNDERSTAND THE GATE",
      "A recommendation you can inspect.",
      "The backend decides through deterministic rules. The interface explains the returned result.",
    ) +
    `<div class="outcomes">${OUTCOMES.map((o, i) => `<div>${badge(o)}<p>${["Proceed to further validation.", "Gather evidence and test again.", "Investigate a justified alternative.", "Do not proceed under current conditions."][i]}</p></div>`).join("")}</div>` +
    (d
      ? `<section class="card decision"><span class="eyebrow">${s.recorded ? "RECORDED GATE RESULT · PRIOR EXECUTION" : s.demo ? "MOCKED GATE RESULT" : "BACKEND GATE RESULT"}</span>${d.rulesetVersion && d.rulesetVersion !== d.currentRulesetVersion ? `<p class="notice error">Superseded historical decision: rule version ${e(d.rulesetVersion)}, current version ${e(d.currentRulesetVersion)}. Preserved as history; not permission to build.</p>` : ""}<h2>${badge(d.outcome)}</h2><p class="lead">${e(d.explanation)}</p><h3>Precise rule triggered</h3><code>${e(d.rule)}</code><div class="grid-two"><div><h3>Supporting evidence</h3>${refs(d.findings, s.data.findings)}<h3>Missing information</h3>${list(d.missing)}</div><div><h3>Relevant risks</h3>${list(d.risks)}</div></div><div class="inset"><h3>Recommended next step</h3><p>${e(d.next)}</p><strong>Founder action</strong><p>${e(d.action)}</p></div><div class="actions">${link("counterfactual", "What could change this recommendation? →")}${s.service.capabilities.builder && d.builderAllowed && d.outcome !== "STOP" ? `<button data-action="prepare-builder" ${s.busy ? "disabled" : ""}>Ask the Builder to prepare a validation kit</button>` : ""}</div>${gateTrace(d)}</section>`
      : empty(
          "No gate decision available.",
          "A recommendation appears only after the backend evaluates the evidence.",
        )) +
    '<p class="footnote">GO permits further validation; it is not proof of viability. STOP applies to current conditions and does not predict inevitable failure.</p>'
  );
}
export function counterfactual(s) {
  const c = s.data.counterfactual;
  return (
    heading(
      "06 / CHANGE THE QUESTION",
      "What evidence could change this?",
      "A recommendation is a checkpoint. Make the next experiment count.",
    ) +
    (c
      ? `<section class="counter-hero"><span class="eyebrow">THE UNMET REQUIREMENT</span><h2>${e(c.requirement)}</h2><p>${e(c.limitation)}</p></section><article class="card"><span class="eyebrow">A PROPOSED EXPERIMENT · NOT YET COLLECTED</span><h2>${e(c.experiment)}</h2><div class="grid-two"><div class="signal positive"><h3>↗ Would strengthen the hypothesis</h3><p>${e(c.strengthen)}</p></div><div class="signal negative"><h3>↘ Would weaken the hypothesis</h3><p>${e(c.weaken)}</p></div></div><h3>Gate to reconsider</h3><code>${e(c.gate)}</code><p>New evidence must be assessed by the backend. No experiment automatically guarantees GO.</p></article>`
      : empty(
          "First, a decision. Then, a path to reconsider it.",
          "Unmet requirements and proposed experiments appear when a backend counterfactual explanation is available.",
        ))
  );
}
export function artifacts(s) {
  return (
    heading(
      "07 / MAKE IT TESTABLE",
      "Artifacts with a clear purpose.",
      "Review local outputs before approving an action. Nothing is published automatically.",
    ) +
    (s.data.artifacts.length
      ? `<div class="cards">${s.data.artifacts.map((a) => `<article class="card"><div class="section-title"><span class="eyebrow">${e(a.type)}</span>${badge(a.status)}</div><h2>${e(a.title)}</h2><p>${e(a.description)}</p><dl><dt>Artifact identity</dt><dd>${e(a.id)}</dd><dt>Version / fingerprint</dt><dd><code>${e(a.fingerprint)}</code></dd><dt>Approval</dt><dd>${e(a.approval)}</dd></dl><button data-preview="${e(a.id)}" class="secondary">Read-only preview ↗</button></article>`).join("")}</div><section id="preview-panel" aria-live="polite"></section>`
      : empty(
          "No generated artifacts available.",
          "Validation kits, interview guides and local prototypes appear here once you ask the Builder for a request (Decision dashboard). Files are written only after your approval.",
        ))
  );
}
function approvalReason(s, a) {
  if (!s.service.capabilities.approvals || s.demo)
    return "Demo mode — these controls cannot grant approval.";
  if (s.approvalLocks?.has(a.id))
    return "Confirmation is uncertain. Refresh the request before retrying.";
  return approvalBlock(a, s.data.artifacts, s.runId);
}
function validationBlock(s, a) {
  const kit = (s.data.validation || []).find((v) => v.id === a.id);
  if (a.status !== "Executed" || !kit) return "";
  const p = kit.plan;
  const rows = kit.observations.length
    ? `<table class="compact"><caption>Recorded totals (cumulative, founder-reported)</caption><thead><tr><th scope="col">Recorded</th><th scope="col">Participants</th><th scope="col">Met the condition</th><th scope="col">Gate</th><th scope="col">Notes</th></tr></thead><tbody>${kit.observations.map((o) => `<tr><td>${e(o.recordedAt || "")}</td><td>${o.participants} of ${p.sampleSize}</td><td>${o.successes}</td><td>${o.outcome ? badge(o.outcome.decision) : ""}</td><td>${e(o.notes)}</td></tr>`).join("")}</tbody></table>`
    : `<p class="muted">No results recorded. The experiment has not been reported as run.</p>`;
  const latest = kit.latest
    ? `<div class="notice"><strong>Validation gate: ${e(kit.latest.decision)}</strong> (<code>${e(kit.latest.rule)}</code>). ${e(kit.latest.meaning)} <strong>Next:</strong> ${e(kit.latest.nextStep)}</div>`
    : "";
  const canRecord =
    s.service.capabilities.approvals && !s.demo && !kit.final;
  const form = canRecord
    ? `<div class="grid-two"><label class="field">Participants so far (of ${p.sampleSize})<input id="participants-${e(a.id)}" type="number" min="1" max="${p.sampleSize}" step="1" inputmode="numeric"></label><label class="field">Of those, met the condition<input id="successes-${e(a.id)}" type="number" min="0" max="${p.sampleSize}" step="1" inputmode="numeric"></label></div><label class="field full">Notes (optional)<input id="notes-${e(a.id)}" maxlength="500" placeholder="What you observed, in your words"></label><p class="muted">Enter cumulative totals from interviews you actually ran. VentureLab records them as founder-reported and does not verify them. Requires the founder key above.</p><div class="actions"><button data-action="record-result" data-request="${e(a.id)}" ${s.busy ? "disabled" : ""}>Record founder-reported result</button></div>`
    : kit.final
      ? `<p class="muted">This experiment's result is final. A new experiment needs a new approved kit.</p>`
      : "";
  return `<section class="validation" aria-label="Validation results"><h3>Validation results</h3><p><strong>Threshold approved before testing:</strong> ${p.threshold} of ${p.sampleSize} participants — ${e(p.metric)}. <span class="badge amber">FOUNDER-REPORTED results</span></p>${rows}${latest}${form}</section>`;
}
export function approvals(s) {
  return (
    heading(
      "08 / STAY IN CONTROL",
      "Your approval. Precisely scoped.",
      "An approval applies to one action, run, artifact and fingerprint. Only the backend can confirm it.",
    ) +
    (s.service.capabilities.approvals && !s.demo
      ? `<section class="card"><h2>Founder approval key</h2><p>Approving or executing requires the key stored on your machine in <code>.venturelab/approvals.sqlite3.founder</code>. It is kept in this tab's memory only and sent only with your decision. Approval authorizes writing local files; nothing is published or sent.</p><label class="field full">Founder key<input id="founder-key" type="password" autocomplete="off" spellcheck="false" maxlength="200" value="${e(s.founderKey || "")}"></label></section>`
      : "") +
    (s.data.approvals.length
      ? s.data.approvals
          .map(
            (a) =>
              `<article class="card"><div class="section-title"><h2>${e(a.action)}</h2>${badge(a.status)}</div><p>${e(a.description)}</p><dl class="review"><dt>Request</dt><dd>${e(a.id)}</dd><dt>Venture run</dt><dd>${e(a.runId)}</dd><dt>Artifact identity</dt><dd>${e(a.artifactId)}</dd><dt>Version / fingerprint</dt><dd><code>${e(a.fingerprint)}</code></dd></dl>${a.expiresAt ? `<p class="muted">Must be decided and executed before ${e(a.expiresAt)}.</p>` : ""}<div class="notice">${e(a.status === "Approved" ? "Approved. The files are written only when you execute this exact request." : approvalReason(s, a) || "Review the exact scope and the artifact preview before responding.")}</div>${a.status === "Pending" && !s.demo ? `<label class="field full">Reason for your decision (optional)<input id="reason-${e(a.id)}" maxlength="500" value="" placeholder="Optional explanation"></label>` : ""}<div class="actions">${s.service.capabilities.approvals && !s.demo ? `<button data-action="refresh-approvals" class="secondary" ${s.busy ? "disabled" : ""}>Refresh requests</button>` : ""}<button class="secondary" data-approval="${e(a.id)}" data-choice="reject" ${approvalReason(s, a) || s.busy ? "disabled" : ""}>Reject</button><button data-approval="${e(a.id)}" data-choice="approve" ${approvalReason(s, a) || s.busy ? "disabled" : ""}>Approve this action</button>${a.status === "Approved" && s.service.capabilities.builder && !s.demo ? `<button data-action="execute" data-request="${e(a.id)}" ${s.busy ? "disabled" : ""}>Write the approved files locally</button>` : ""}</div>${validationBlock(s, a)}</article>`,
          )
          .join("")
      : empty(
          "No approval requests pending.",
          "Requests will include the exact action and artifact fingerprint. No approvals have been granted by this interface.",
        ))
  );
}
export function history(s) {
  const rows = s.data.audit.filter(
    (a) => !s.auditAgent || a.agent === s.auditAgent,
  );
  return (
    heading(
      "09 / KEEP A CLEAR RECORD",
      "Every decision leaves a trail.",
      "Inspect recorded actions, sources and founder approvals without invented activity. Saved explanations are audit text; older records may contain a pre-filled default and do not establish independent authorship.",
    ) +
    `<div class="filters"><label>Agent<select id="audit-agent"><option value="">All agents</option>${[...new Set(s.data.audit.map((a) => a.agent))].map((v) => `<option ${s.auditAgent === v ? "selected" : ""}>${e(v)}</option>`).join("")}</select></label></div>` +
    (rows.length
      ? `<div class="table-wrap"><table><caption>${s.demo ? "MOCKED synthetic records — not an execution log" : "Backend audit records"}</caption><thead><tr>${["Timestamp", "Agent / action", "Model", "Sources", "Cost (USD)", "Approval", "Outcome"].map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead><tbody>${rows.map((a) => `<tr><td>${e(a.timestamp)}</td><td><strong>${e(a.agent)}</strong><br>${e(a.action)}</td><td>${e(a.model ?? "Not applicable")}</td><td>${a.sources.length ? a.sources.map((u) => source(u)).join("<br>") : "None recorded"}</td><td>${a.cost === null ? "Not reported" : e(a.cost)}</td><td>${e(a.approved_by ?? "Not approved")}</td><td>${e(a.outcome)}</td></tr>`).join("")}</tbody></table></div>`
      : empty(
          "No audit records available.",
          "Only backend execution records belong in the live history.",
        ))
  );
}
export function roadmap() {
  return (
    heading(
      "THE COMPLETE ARCHITECTURE",
      "Six phases. Evidence at every gate.",
      "Discover and the Builder run here; phases 2–6 run through workflow.py behind founder approvals. Their gates and outputs are on the Phases 1–6 page.",
    ) +
    `<div class="roadmap">${phases.map((p, i) => `<article class="card"><div class="section-title"><span class="phase-number">0${i + 1}</span>${badge(p[4])}</div><h2>${p[0]}</h2><p>${p[1]}</p><h3>Expected outputs</h3><p>${p[2]}</p><h3>Gate conditions</h3><p>${p[3]}</p>${p[5] ? link(p[5], i === 0 ? "Prepare a brief →" : "Inspect workspace →", "text-link") : '<p class="muted">Runs via <code>workflow.py</code> · <a class="text-link" href="/phases">Gates and outputs →</a></p>'}</article>`).join("")}</div><div class="notice">Discover is working end to end. Validate produces an experiment plan; entering experiment results is STUBBED. Build writes local files only after your approval; nothing is published. Commercial Setup, Launch and Operate &amp; Learn are STUBBED future capabilities. No payment operations are implemented.</div>`
  );
}
export const renderers = {
  dashboard,
  brief,
  workflow,
  evidence,
  challenger,
  decision,
  counterfactual,
  artifacts,
  approvals,
  history,
  roadmap,
};

export function quoteDetails(f) {
  return f.quotations?.length
    ? f.quotations
        .map(
          (q) =>
            `<blockquote>${e(q.text)}</blockquote>${source(q.url, q.sourceName)}${attributionDetails()}`,
        )
        .join("")
    : `<blockquote>${e(f.quote || "No supporting quotation provided.")}</blockquote>${source(f.url, f.sourceName)}${attributionDetails()}`;
}
export function gateTrace(d) {
  if (!d.trace?.length)
    return '<p class="muted">No rule trace was recorded for this decision.</p>';
  return `<details class="gate-trace"><summary>Inspect the recorded rule checks and thresholds</summary><p>Checks run in order. The first matching rule decides; later rules are not evaluated. These are recorded inputs, not an explanation invented by a model.</p><p>Recorded rule version: ${e(d.rulesetVersion ?? "Not recorded")} · Current version: ${e(d.currentRulesetVersion ?? "Not provided")}</p><div class="table-wrap"><table><caption>Recorded deterministic gate trace</caption><thead><tr><th scope="col">Rule</th><th scope="col">Matched?</th><th scope="col">Decision trigger?</th><th scope="col">Recorded inputs</th></tr></thead><tbody>${d.trace.map((c) => `<tr><td>${e(c.rule)}</td><td>${c.applies ? "Yes" : "No"}</td><td>${c.decided ? "Yes" : "No"}</td><td><pre>${e(c.inputs)}</pre></td></tr>`).join("")}</tbody></table></div><h3>Recorded thresholds</h3><pre>${e(d.thresholds)}</pre></details>`;
}

// The persisted quote contract contains text, URL and verification status, not
// independently verified authorship. Never infer a speaker from first-person text.
export function attributionDetails() {
  return `<dl class="quote-attribution"><dt>Source poster</dt><dd>Not recorded in the saved quotation metadata</dd><dt>Original author</dt><dd>Original author not verified</dd><dt>Third-party material</dt><dd>Unknown — this quotation may include someone else's words</dd><dt>Independent attribution verification</dt><dd>Not recorded. Exact-text verification does not verify authorship or personal experience.</dd></dl>`;
}
