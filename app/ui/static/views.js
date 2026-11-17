import { safeURL, STANDINGS, OUTCOMES, filterFindings } from "./contracts.js";
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
  const tone = ["ESTABLISHED", "GO", "Completed", "Working"].includes(text)
    ? "green"
    : /STOP|Failed|Contradictory/.test(text)
      ? "red"
      : /REPEAT|REVIEW|ASSUMPTION|Blocked|Pending/.test(text)
        ? "amber"
        : "neutral";
  return `<span class="badge ${tone}">${e(text)}</span>`;
}
export const link = (route, label, cls = "button") =>
  `<a class="${cls}" href="#${route}">${e(label)}</a>`;
export function source(url, label) {
  const safe = safeURL(url);
  return safe
    ? `<a href="${e(safe)}" target="_blank" rel="noopener noreferrer">${e(label || safe)} ↗</a>`
    : `<span class="muted">${e(label || "No source URL provided")}</span>`;
}
const list = (values) =>
  values?.length
    ? `<ul class="detail-list">${values.map((x) => `<li>${e(x)}</li>`).join("")}</ul>`
    : '<p class="muted">Not provided.</p>';
const refs = (ids) =>
  ids?.length
    ? ids
        .map((id) =>
          link(`evidence/${encodeURIComponent(id)}`, id, "reference"),
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
    "In progress",
    "brief",
  ],
  [
    "Validate",
    "Challenge the assumptions",
    "Critical analysis and a validation plan",
    "Observed problem and demand evidence",
    "STUBBED",
    "evidence",
  ],
  [
    "Build",
    "Create a testable artifact",
    "Experiment kits and local prototypes",
    "Backend approval for the exact action and artifact",
    "STUBBED",
    "artifacts",
  ],
  [
    "Commercial Setup",
    "Plan responsible operations",
    "Future setup checklist",
    "Future compliance and founder review",
    "Future · STUBBED",
    "",
  ],
  [
    "Launch",
    "Plan a controlled introduction",
    "Future launch plan",
    "Future founder authorization; no external publishing",
    "Future · STUBBED",
    "",
  ],
  [
    "Operate & Learn",
    "Learn from observed outcomes",
    "Future experiment review",
    "Future measured evidence and reassessment",
    "Future · STUBBED",
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
    `<div class="section-title"><h2>Venture runs</h2>${s.demo ? badge("MOCKED fixtures") : badge("Live workspace")}</div>` +
    (s.runs.length
      ? `<div class="cards">${s.runs.map((r) => `<article class="card"><span class="eyebrow">${e(r.phase)}</span><h2>${e(r.title)}</h2>${badge(r.status)}${r.recordedAt ? `<p>Recorded run · ${e(r.recordedAt)}</p>` : ""}<p>Run ${e(r.id)}</p><button data-run="${e(r.id)}">Open workspace →</button></article>`).join("")}</div>`
      : empty(
          "Your first investigation starts here.",
          "No venture runs are available. Prepare a brief now; submission becomes available when the workflow backend is connected.",
          link("brief", "Create founder brief"),
        )) +
    `<div class="grid-two"><article class="card"><span class="eyebrow">RECENT DECISION</span>${s.data.decision ? `<h2>${badge(s.data.decision.outcome)}</h2><p>${e(s.data.decision.explanation)}</p>${link("decision", "Inspect the rule →", "text-link")}` : "<h2>No decisions yet</h2><p>A recommendation appears only after a backend gate evaluation.</p>"}</article><article class="card"><span class="eyebrow">WORKSPACE READINESS</span><h2>Built around founder control</h2><p>Local model health is connected. Research and Builder integrations are STUBBED on this branch.</p>${link("approvals", "Review approval boundary →", "text-link")}</article></div>`
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
        ? `<div class="section-title"><h2>Ready for your review</h2>${badge("Not submitted")}</div><dl class="review">${fields.map(([key, label]) => `<dt>${label}</dt><dd>${e(key === "sources" ? s.brief.sources.join("\n") : s.brief[key]) || "Not provided"}${key === "budget" ? " " + e(s.brief.currency) : ""}</dd>`).join("")}</dl><div class="notice">${s.service.capabilities.createRun ? "The backend will validate this brief before starting research." : "STUBBED — submission requires the Milestone 2 backend. This brief has not been researched."}</div><div class="actions"><button data-action="edit" class="secondary">← Edit brief</button><button data-action="submit" ${!s.service.capabilities.createRun || s.busy ? "disabled" : ""}>${s.busy ? "Submitting…" : "Submit and start analysis"}</button></div>`
        : `<form id="brief-form" novalidate><div id="validation-summary" role="alert">${Object.keys(s.errors).length ? '<p class="field-error">Please correct the highlighted fields.</p>' : ""}</div><div class="form-grid">${fields.map(([key, label, help, type]) => `<div class="field ${type === "textarea" ? "full" : ""}"><label for="${key}">${label} <span>${key === "sources" ? "Optional" : "Required"}</span></label>${type === "textarea" ? `<textarea id="${key}" name="${key}" rows="${key === "idea" || key === "problem" ? 3 : 2}" maxlength="4000"` : `<input id="${key}" name="${key}" type="${type}" ${type === "number" ? `min="${key === "hours" ? 1 : 0}" ${key === "hours" ? 'max="168"' : ""} step="any"` : 'maxlength="4000"'}`} aria-describedby="${key}-help ${key}-error" ${s.errors[key] ? 'aria-invalid="true"' : ""} ${key !== "sources" ? "required" : ""}${type === "textarea" ? `>${e(key === "sources" ? s.brief.sources.join("\n") : s.brief[key] || "")}</textarea>` : ` value="${e(s.brief[key] ?? "")}">`}<small id="${key}-help">${help}</small><span id="${key}-error" class="field-error">${e(s.errors[key] || "")}</span></div>`).join("")}<div class="field"><label for="currency">Budget currency</label><select id="currency" name="currency">${["EGP", "USD", "EUR"].map((c) => `<option ${s.brief.currency === c ? "selected" : ""}>${c}</option>`).join("")}</select></div></div><div class="actions"><span class="muted">Kept in this tab only. Reloading clears it.</span><button type="submit">Review brief →</button></div></form>`
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
    `<div class="workflow">${agents.map((a, i) => `<article class="card agent"><div class="agent-number">0${i + 1}</div><div><h2>${e(a.agent)}</h2><p>${e(a.task)}</p>${link(["evidence", "challenger", "artifacts", "decision"][i], "View output →", "text-link")}</div>${badge(a.status)}</article>`).join("")}</div><div class="notice">The Judge explains deterministic gate results. It cannot override them. ${s.service.capabilities.workflow ? "Status refreshes every 5 seconds while this view is open." : "Live workflow updates are STUBBED."}</div>`
  );
}
export function evidence(s) {
  const findings = filterFindings(s.data.findings, s.standing, s.claimType);
  return (
    heading(
      "03 / INSPECT THE SOURCES",
      "Evidence, with its limits visible.",
      "Separate what is established from what needs review — and what remains an assumption.",
    ) +
    `<div class="legend">${STANDINGS.map((b) => badge(b)).join("")}<span>Standing and claim–source relationship are separate assessments.</span></div><div class="filters"><label>Evidence standing<select id="standing"><option value="">All standings</option>${STANDINGS.map((v) => `<option ${s.standing === v ? "selected" : ""}>${v}</option>`).join("")}</select></label><label>Claim type<select id="claim-type"><option value="">All claim types</option>${[...new Set(s.data.findings.map((f) => f.type))].map((v) => `<option ${s.claimType === v ? "selected" : ""}>${e(v)}</option>`).join("")}</select></label><span role="status">${findings.length} findings</span></div>` +
    (findings.length
      ? findings
          .map(
            (f) =>
              `<details class="finding card" id="finding-${e(f.id)}" ${s.focusFinding === f.id ? "open" : ""}><summary><span class="finding-id">${e(f.id)}</span><span class="finding-title">${e(f.claim)}<small>${e(f.type)} · ${e(f.sourceName)}</small></span>${badge(f.standing)}</summary><div class="finding-body"><div class="grid-two"><div><h3>Supporting quotation</h3><blockquote>${e(f.quote || "No supporting quotation provided.")}</blockquote>${source(f.url, f.sourceName)}</div><div><h3>Assessment</h3>${badge(f.relationship)}<p>${e(f.assessment)}</p></div></div><div class="grid-two"><div><h3>Limitations</h3><p>${e(f.limitations)}</p></div><div><h3>Associated assumption</h3><p>${e(f.assumption)}</p></div></div></div></details>`,
          )
          .join("")
      : empty(
          s.data.findings.length
            ? "No findings match these filters."
            : "No evidence collected yet.",
          s.data.findings.length
            ? "Choose a different standing or claim type."
            : "Findings will appear here after actual Investigator execution.",
        ))
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
              `<article class="card challenge"><div class="section-title"><span class="eyebrow">${e(c.id)} / ${e(c.basis)}</span>${c.severity ? badge(c.severity) : ""}</div><h2>${e(c.claim)}</h2><p>${e(c.risk)}</p><div class="grid-two"><div><h3>Evidence references</h3>${refs(c.findings)}<h3>Missing evidence</h3>${list(c.missing)}</div><div class="inset"><h3>Recommended experiment</h3><p>${e(c.experiment)}</p></div></div></article>`,
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
      ? `<section class="card decision"><span class="eyebrow">${s.demo ? "MOCKED GATE RESULT" : "BACKEND GATE RESULT"}</span><h2>${badge(d.outcome)}</h2><p class="lead">${e(d.explanation)}</p><h3>Precise rule triggered</h3><code>${e(d.rule)}</code><div class="grid-two"><div><h3>Supporting evidence</h3>${refs(d.findings)}<h3>Missing information</h3>${list(d.missing)}</div><div><h3>Relevant risks</h3>${list(d.risks)}</div></div><div class="inset"><h3>Recommended next step</h3><p>${e(d.next)}</p><strong>Founder action</strong><p>${e(d.action)}</p></div><div class="actions">${link("counterfactual", "What could change this recommendation? →")}</div></section>`
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
          "Validation kits, interview guides and local prototypes appear here when returned by the Builder backend.",
        ))
  );
}
export function approvals(s) {
  return (
    heading(
      "08 / STAY IN CONTROL",
      "Your approval. Precisely scoped.",
      "An approval applies to one action, run, artifact and fingerprint. Only the backend can confirm it.",
    ) +
    (s.data.approvals.length
      ? s.data.approvals
          .map(
            (a) =>
              `<article class="card"><div class="section-title"><h2>${e(a.action)}</h2>${badge(a.status)}</div><p>${e(a.description)}</p><dl class="review"><dt>Request</dt><dd>${e(a.id)}</dd><dt>Venture run</dt><dd>${e(a.runId)}</dd><dt>Artifact identity</dt><dd>${e(a.artifactId)}</dd><dt>Version / fingerprint</dt><dd><code>${e(a.fingerprint)}</code></dd></dl><div class="notice">${s.service.capabilities.approvals ? "Review the exact scope before responding." : "STUBBED — approval backend is disconnected. These controls cannot grant approval."}</div><div class="actions"><button class="secondary" data-approval="${e(a.id)}" data-choice="reject" ${!s.service.capabilities.approvals || s.busy || a.status !== "Pending" ? "disabled" : ""}>Reject</button><button data-approval="${e(a.id)}" data-choice="approve" ${!s.service.capabilities.approvals || s.busy || a.status !== "Pending" ? "disabled" : ""}>Approve this action</button></div></article>`,
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
      "Inspect recorded actions, sources and founder approvals without invented activity.",
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
      "The current focus is Discover, Validate and selected local artifacts. Later phases are architectural plans.",
    ) +
    `<div class="roadmap">${phases.map((p, i) => `<article class="card"><div class="section-title"><span class="phase-number">0${i + 1}</span>${badge(p[4])}</div><h2>${p[0]}</h2><p>${p[1]}</p><h3>Expected outputs</h3><p>${p[2]}</p><h3>Gate conditions</h3><p>${p[3]}</p>${p[5] ? link(p[5], i === 0 ? "Prepare a brief →" : "Inspect workspace →", "text-link") : '<p class="muted">No operational actions available.</p>'}</article>`).join("")}</div><div class="notice">Discover: intake UI is working; research integration is STUBBED. Validate and Build: UI is working; backend connections are STUBBED. Commercial Setup, Launch and Operate & Learn are future capabilities. No payment operations are implemented.</div>`
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
