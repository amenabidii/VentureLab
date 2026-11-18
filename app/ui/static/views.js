/** Workspace views.
 *
 * Organised around the founder's questions, not the system's components:
 *   Projects            — which ideas exist, where each stands, what to do next
 *   Analysis            — the result in plain words, why, the evidence, what would change it
 *   Build & validate    — the six-phase journey, approvals, artifacts and recorded results
 *   History & details   — audit trail, agent internals, rule checks and identifiers
 *
 * The older section names (evidence, decision, challenger, ...) remain as reusable
 * components and as URL aliases. Every value shown comes from the backend (or labelled
 * MOCKED fixtures); plain-language labels are a fixed mapping of recorded codes and
 * never upgrade a standing or a decision. The codes stay visible under "details".
 */
import { safeURL, STANDINGS, OUTCOMES, filterFindings } from "./contracts.js";
import { approvalBlock } from "./normalize.js";

// --- navigation ------------------------------------------------------------------------------

export const pages = [
  ["projects", "Projects", "▦"],
  ["analysis", "Analysis", "◎"],
  ["build", "Build & validate", "▲"],
  ["details", "History & details", "☰"],
];
/** Older links still work: each opens the page and section that now holds that content. */
export const ALIASES = {
  dashboard: ["projects", ""],
  workflow: ["analysis", "steps"],
  evidence: ["analysis", "evidence"],
  challenger: ["analysis", "concerns"],
  decision: ["analysis", "decision"],
  counterfactual: ["analysis", "next"],
  artifacts: ["build", "artifacts"],
  approvals: ["build", "approvals"],
  history: ["details", "audit"],
  roadmap: ["build", "journey"],
};
export const TITLES = {
  projects: "Projects",
  brief: "New idea",
  analysis: "Analysis",
  build: "Build & validate",
  details: "History & details",
};

// --- primitives -------------------------------------------------------------------------------

export const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const e = escape;
const TONES = {
  good: ["ESTABLISHED", "GO", "Completed", "Working", "Executed"],
  bad: /STOP|Failed|Contradictory|CONTRADICTED|Rejected/,
  warn: /REPEAT|REVIEW|ASSUMPTION|Blocked|Pending|PIVOT|PARTIAL/,
};
export function badge(text) {
  const tone = TONES.good.includes(text)
    ? "green"
    : TONES.bad.test(text)
      ? "red"
      : TONES.warn.test(text)
        ? "amber"
        : "neutral";
  return `<span class="badge ${tone}">${e(text)}</span>`;
}
/** A status chip that never relies on colour alone: icon + words. */
const chip = (tone, icon, label) =>
  `<span class="chip ${e(tone)}"><span aria-hidden="true">${e(icon)}</span><span>${e(label)}</span></span>`;
export const link = (route, label, cls = "button") =>
  `<a class="${e(cls)}" href="#${e(route)}">${e(label)}</a>`;
export function source(url, label) {
  const safe = safeURL(url);
  return safe
    ? `<a href="${e(safe)}" target="_blank" rel="noopener noreferrer">${e(label || safe)} ↗</a>`
    : `<span class="muted">${e((label ? label + " · " : "") + (url ? "Unsafe or malformed source URL — link disabled" : "No source URL provided"))}</span>`;
}
const list = (values, none = "Not provided.") =>
  values?.length
    ? `<ul class="detail-list">${values.map((x) => `<li>${e(x)}</li>`).join("")}</ul>`
    : `<p class="muted">${e(none)}</p>`;
const refs = (ids, findings = []) =>
  ids?.length
    ? ids
        .map((id) =>
          findings.some((f) => f.id === id)
            ? `<a class="reference" href="#evidence/${e(encodeURIComponent(id))}">Evidence ${e(id)}</a>`
            : `<span class="badge amber">${e(id)} · Reference unavailable</span>`,
        )
        .join(" ")
    : '<span class="muted">No evidence references.</span>';
export const empty = (title, copy, action = "") =>
  `<section class="empty"><div class="empty-icon" aria-hidden="true">◇</div><h2>${e(title)}</h2><p>${e(copy)}</p>${action}</section>`;
const heading = (eyebrow, title, description, action = "") =>
  `<div class="page-heading"><div><div class="eyebrow">${e(eyebrow)}</div><h1>${e(title)}</h1>${description ? `<p>${e(description)}</p>` : ""}</div>${action}</div>`;
const section = (id, title, intro, body, extra = "") =>
  `<section class="section" id="sec-${e(id)}" aria-labelledby="h-${e(id)}" tabindex="-1"><div class="section-head"><h2 id="h-${e(id)}">${e(title)}</h2>${extra}</div>${intro ? `<p class="section-intro">${e(intro)}</p>` : ""}${body}</section>`;
export const loading = () =>
  '<section class="empty" role="status" aria-live="polite"><span class="spinner" aria-hidden="true"></span><h2>Reading workspace…</h2><p>Long-running model operations may take several minutes. Completion is shown only when reported by the backend.</p></section>';
export const errorView = () =>
  '<section class="empty" role="alert"><h2>We couldn’t load this view</h2><p>Your brief remains in this browser tab. Check the local service and try again.</p><button data-action="retry">Try again</button></section>';

// --- plain-language mappings of recorded codes (display only) --------------------------------

export const VERDICTS = {
  GO: {
    icon: "▲",
    tone: "good",
    title: "Ready for the next validation step",
    short: "Ready to test with customers",
    summary:
      "The evidence clears the bar for testing with real customers. This is permission to test — not proof of demand, of a market or of future sales.",
  },
  REPEAT: {
    icon: "↻",
    tone: "warn",
    title: "More evidence needed",
    short: "More evidence needed",
    summary:
      "Nothing rules the idea out, but there is not yet enough reliable evidence to recommend moving forward. Missing evidence is not evidence that the problem isn’t real.",
  },
  PIVOT: {
    icon: "⤳",
    tone: "warn",
    title: "Consider changing direction",
    short: "Consider a different problem",
    summary:
      "The evidence points to a different problem for the same customers that may be worth testing instead.",
  },
  STOP: {
    icon: "■",
    tone: "bad",
    title: "Do not proceed under current conditions",
    short: "Do not proceed",
    summary:
      "VentureLab recommends not proceeding with this idea as it stands. This applies to current conditions; it does not predict inevitable failure.",
  },
};
/** Why the recorded rule fired, in plain words. Unknown rules fall back to the backend's text. */
export const RULE_REASONS = {
  STOP_PROHIBITED_CATEGORY: [
    "Policy",
    "This idea falls in a category VentureLab must not help build, or depends on a practice it must never support (such as fake reviews, fake urgency or impersonation). This is a policy decision, not a judgement of the evidence.",
  ],
  STOP_FAILED_VALIDATION_CONDITION: [
    "Pass mark missed",
    "A pass mark you set before testing was not met. Lowering it after seeing the result would not be an honest test.",
  ],
  STOP_CONTRADICTED: [
    "Evidence against",
    "Independent sources contradict the problem, and nothing established supports it or an alternative.",
  ],
  PIVOT_ALTERNATIVE_SUPPORTED: [
    "Alternative found",
    "Your stated problem is contradicted, but an established finding points to a different problem for the same customers.",
  ],
  REPEAT_MIXED_EVIDENCE: [
    "Mixed evidence",
    "Some sources support the problem and some contradict it. More evidence is needed to tell which is right.",
  ],
  REPEAT_NO_READABLE_SOURCES: [
    "Sources unavailable",
    "Not enough public sources could be read to judge the problem. This says nothing about whether the problem is real.",
  ],
  REPEAT_CLARIFY_AVAILABILITY: [
    "Time unclear",
    "Your available time needs clarifying before a realistic plan can be made.",
  ],
  REPEAT_INSUFFICIENT_EVIDENCE: [
    "Not enough evidence",
    "We found some discussions related to your problem, but not enough reliable, independent evidence to recommend moving forward yet.",
  ],
  GO_TO_FURTHER_VALIDATION: [
    "Enough to test",
    "At least two independent sources support the problem and nothing contradicts it.",
  ],
};
export const STANDING_GROUPS = [
  [
    "ESTABLISHED",
    "Strong evidence",
    "✓",
    "good",
    "An exact quotation was verified and the statement stays within what it says. Counts toward the decision.",
  ],
  [
    "PARTIAL_EVIDENCE",
    "Partial evidence",
    "◐",
    "warn",
    "The source supports only part of the statement.",
  ],
  [
    "CONTRADICTED",
    "Contradicts the idea",
    "✕",
    "bad",
    "The source says the opposite of the statement.",
  ],
  [
    "NEEDS_REVIEW",
    "Needs verification",
    "?",
    "warn",
    "The quotation is real, but the statement goes further than it, or who is speaking is unclear. Not counted until reviewed.",
  ],
  [
    "UNSUPPORTED",
    "Not supported by its source",
    "–",
    "neutral",
    "The quoted text does not back the statement.",
  ],
  [
    "ASSUMPTION",
    "Assumption",
    "○",
    "neutral",
    "No verified quotation. Treated as an assumption, never as evidence.",
  ],
];
const GROUP = Object.fromEntries(STANDING_GROUPS.map((g) => [g[0], g]));
const standingChip = (standing) => {
  const g = GROUP[standing];
  return g ? chip(g[3], g[2], g[1]) : badge(standing);
};
const verdictChip = (outcome) => {
  const v = VERDICTS[outcome];
  return v ? chip(v.tone, v.icon, v.short) : badge(outcome);
};
const AGENTS = {
  Investigator: ["Research", "Finds public discussions and checks every quotation word for word.", "evidence"],
  Challenger: ["Challenge", "Questions your assumptions against what was found.", "challenger"],
  Judge: ["Decide", "Fixed rules (no AI) turn the evidence into a recommendation.", "decision"],
  Builder: ["Prepare next steps", "Prepares an interview kit and plan — only when you ask, written only after you approve.", "artifacts"],
};
const STATUS_ICON = {
  Completed: ["good", "✓"],
  Running: ["info", "●"],
  Waiting: ["neutral", "…"],
  "Not started": ["neutral", "○"],
  Failed: ["bad", "✕"],
  Blocked: ["warn", "⊘"],
  STUBBED: ["neutral", "◇"],
};
const statusChip = (status) => {
  const [tone, icon] = STATUS_ICON[status] || ["neutral", "·"];
  return chip(tone, icon, status);
};
const verdictOf = (run) => {
  const m = /\b(GO|REPEAT|PIVOT|STOP)\b/.exec(run?.phase || "");
  return m ? m[1] : null;
};
const NEXT_FOR = {
  GO: "Prepare your validation kit and interview real customers.",
  REPEAT: "Collect the missing evidence: interview customers or revise the idea.",
  PIVOT: "Look at the alternative problem the evidence points to.",
  STOP: "Do not continue this idea as it stands; start a different one.",
};

// --- Projects ---------------------------------------------------------------------------------

export function dashboard(s) {
  const mode = s.recorded
    ? chip("neutral", "◷", "Recorded examples · read-only")
    : s.demo
      ? chip("warn", "◇", "MOCKED demo data")
      : chip("good", "●", "Your local workspace");
  const runs = s.runs || [];
  const cards = runs
    .map((r) => {
      const v = verdictOf(r);
      const active = /queued|running/i.test(r.status);
      const superseded = /superseded/i.test(r.status);
      const next = active
        ? "Analysis in progress — results appear when the backend reports them."
        : superseded
          ? "Historical record only: decided under older rules. Run a new analysis to continue this idea."
          : v
            ? NEXT_FOR[v]
          : /failed|blocked/i.test(r.status)
            ? "The analysis did not finish. Open it to see why."
            : "Open the project to see where it stands.";
      return `<article class="project ${r.id === s.runId ? "current" : ""}"><div class="project-main"><h2>${e(r.title)}</h2><p class="project-meta">${superseded ? chip("neutral", "◷", `Superseded${v ? ` (was ${v})` : ""}`) : v ? verdictChip(v) : statusChip(active ? "Running" : r.status === "Failed" ? "Failed" : "Waiting")}<span>${e(r.status)}</span>${r.recordedAt ? `<span>Last analysed ${e(r.recordedAt.slice(0, 10))}</span>` : ""}</p><p class="project-next"><strong>Next:</strong> ${e(next)}</p></div><button data-run="${e(r.id)}" ${r.id === s.runId ? 'aria-current="true"' : ""}>Open project <span aria-hidden="true">→</span></button></article>`;
    })
    .join("");
  return (
    heading(
      "VENTURELAB",
      "Your projects",
      "Each project is one idea, analysed against public evidence. Open one to see what was found and what to do next.",
      s.demo || s.recorded ? "" : link("brief", "＋ New idea"),
    ) +
    `<div class="mode-line">${mode}</div>` +
    (runs.length
      ? `<div class="projects">${cards}</div>`
      : empty(
          "No venture runs yet.",
          "Describe an idea and VentureLab will research it, challenge it and recommend a next step. Or open the recorded examples from the top bar.",
          s.demo || s.recorded ? "" : link("brief", "Describe your first idea"),
        )) +
    `<p class="fine tool-line">Also available: <a href="/mvp">Try the working thread digest</a> — the one MVP VentureLab ships as working code (paste any discussion; nothing leaves your computer).</p>` +
    `<section class="how" aria-labelledby="how-title"><h2 id="how-title">How VentureLab works</h2><ol class="how-steps"><li><strong>Describe your idea</strong><span>Who has the problem, what you can build, your time and budget.</span></li><li><strong>We research and challenge it</strong><span>Public discussions are searched, every quotation is checked word for word, and your assumptions are questioned.</span></li><li><strong>You get a clear recommendation</strong><span>Ready to test, more evidence needed, change direction, or stop — with the reasons and the evidence.</span></li><li><strong>You stay in control</strong><span>Nothing is written, published, sent or paid without your explicit approval.</span></li></ol></section>`
  );
}

// --- New idea (founder brief) -----------------------------------------------------------------

export const fields = [
  ["idea", "Business idea", "What will you build, and how does it help?", "textarea"],
  ["market", "Target market", "For example: independent design studios in Egypt.", "text"],
  ["customer", "Target customer", "Who experiences the problem and who decides to adopt?", "text"],
  ["problem", "Core problem", "Describe a specific situation and the current workaround.", "textarea"],
  ["skills", "Founder skills", "What can you build or investigate yourself?", "text"],
  ["hours", "Available weekly time", "Hours per week, from 1 to 168.", "number"],
  ["budget", "Available budget", "Your constraint, not a payment. Zero is valid.", "number"],
  ["values", "Values", "What principles should guide the venture?", "textarea"],
  ["constraints", "Constraints", "Limits on scope, access, resources or execution. Use “None” if applicable.", "textarea"],
  ["sources", "Supporting sources", "Optional. Up to 10 HTTP/HTTPS URLs, one per line.", "textarea"],
];
const GROUPS = [
  ["The idea", ["idea", "problem"]],
  ["Who it is for", ["customer", "market"]],
  ["You and your constraints", ["skills", "hours", "budget", "values", "constraints"]],
  ["Optional", ["sources"]],
];
export function brief(s) {
  const review = s.review;
  const field = ([key, label, help, type]) =>
    `<div class="field ${type === "textarea" ? "full" : ""}"><label for="${key}">${label} <span>${key === "sources" ? "Optional" : "Required"}</span></label>${type === "textarea" ? `<textarea id="${key}" name="${key}" rows="${key === "idea" || key === "problem" ? 3 : 2}" maxlength="4000"` : `<input id="${key}" name="${key}" type="${type}" ${type === "number" ? `min="${key === "hours" ? 1 : 0}" ${key === "hours" ? 'max="168"' : ""} step="any"` : 'maxlength="4000"'}`} aria-describedby="${key}-help ${key}-error" ${s.errors?.[key] ? 'aria-invalid="true"' : ""} ${key !== "sources" ? "required" : ""}${type === "textarea" ? `>${e(key === "sources" ? (s.brief?.sources || []).join("\n") : s.brief?.[key] || "")}</textarea>` : ` value="${e(s.brief?.[key] ?? "")}">`}<small id="${key}-help">${help}</small><span id="${key}-error" class="field-error">${e(s.errors?.[key] || "")}</span></div>`;
  const byKey = Object.fromEntries(fields.map((f) => [f[0], f]));
  const can = s.service?.capabilities?.createRun;
  return (
    heading(
      "NEW IDEA",
      review ? "Review your founder brief" : "Start with what you know.",
      "Be specific about the problem. Be honest about what is still an assumption.",
    ) +
    `<ol class="mini-steps" aria-label="Progress"><li ${review ? "" : 'aria-current="step"'}>Describe</li><li ${review && !s.submittedRunId ? 'aria-current="step"' : ""}>Review</li><li ${s.submittedRunId ? 'aria-current="step"' : ""}>Analyse</li></ol>` +
    `<div class="brief-layout"><section class="card">${
      review
        ? `<div class="section-head"><h2>Ready for your review</h2>${badge(s.submittedRunId ? "Submitted to backend" : "Not submitted")}</div><dl class="review">${fields.map(([key, label]) => `<dt>${label}</dt><dd>${e(key === "sources" ? (s.brief?.sources || []).join("\n") : s.brief?.[key]) || "Not provided"}${key === "budget" ? " " + e(s.brief?.currency) : ""}</dd>`).join("")}</dl><div class="notice">${can ? "VentureLab checks this brief, then researches it with the local model. A full analysis usually takes two to four minutes." : "Demo mode never starts research."}</div>${can ? `<label class="check"><input type="checkbox" id="quick-run" ${s.quick ? "checked" : ""}> Shorter demonstration run (one search, fewer claims; every step still runs live)</label>` : ""}<div class="actions"><button data-action="${s.submittedRunId || s.submitLocked ? "new-brief" : "edit"}" class="secondary" ${s.busy ? "disabled" : ""}>${s.submittedRunId || s.submitLocked ? "Prepare another brief" : "← Edit brief"}</button><button data-action="submit" ${!can || s.demo || s.busy || s.submitLocked || s.submittedRunId ? "disabled" : ""}>${s.busy ? "Submitting…" : "Submit and start analysis"}</button></div>`
        : `<form id="brief-form" novalidate><div id="validation-summary" role="alert">${Object.keys(s.errors || {}).length ? '<p class="field-error">Please correct the highlighted fields.</p>' : ""}</div>${GROUPS.map(([title, keys]) => `<fieldset><legend>${title}</legend><div class="form-grid">${keys.map((k) => field(byKey[k])).join("")}${title === "You and your constraints" ? `<div class="field"><label for="currency">Budget currency</label><select id="currency" name="currency" aria-describedby="currency-error" ${s.errors?.currency ? 'aria-invalid="true"' : ""}>${["EGP", "USD", "EUR"].map((c) => `<option ${s.brief?.currency === c ? "selected" : ""}>${c}</option>`).join("")}</select><span id="currency-error" class="field-error">${e(s.errors?.currency || "")}</span></div>` : ""}</div></fieldset>`).join("")}<div class="actions"><span class="muted">Kept in this tab only. Reloading clears it.</span><button type="submit">Review brief →</button></div></form>`
    }</section><aside><article class="card tip"><h2>A useful brief is specific, not perfect.</h2><p>Name a customer you can reach. Describe a problem you can observe. Include the constraints that matter.</p><p>VentureLab may recommend gathering evidence, changing direction, or stopping. It will never promise success.</p></article><article class="card"><h3>Your control comes first</h3><p>Nothing is written, published, sent or paid without your approval.</p><p>Never include passwords, payment credentials or private customer records.</p></article></aside></div>`
  );
}

// --- shared: project header -------------------------------------------------------------------

function currentRun(s) {
  return (s.runs || []).find((r) => r.id === s.runId) || null;
}
function projectHeader(s, page) {
  const run = currentRun(s);
  const b = s.data?.brief;
  const title = b?.idea || run?.title || "No project selected";
  const mode = s.recorded
    ? chip("neutral", "◷", "Recorded example · read-only")
    : s.demo
      ? chip("warn", "◇", "MOCKED demo data")
      : "";
  return `<header class="project-header"><div><div class="eyebrow">${e(TITLES[page] || "")}</div><h1>${e(title)}</h1>${b ? `<p class="for">For <strong>${e(b.customer)}</strong> · ${e(b.market)}</p>` : ""}</div><div class="project-header-side">${mode}${run ? `<span class="muted">${e(run.status)}</span>` : ""}<a class="text-link" href="#projects">Switch project</a></div></header>`;
}
const noProject = () =>
  empty(
    "Choose a project first.",
    "Open a project from Projects, or describe a new idea.",
    `${link("projects", "Go to projects", "button secondary")} ${link("brief", "＋ New idea")}`,
  );

// --- Analysis: workflow stepper ---------------------------------------------------------------

export function workflow(s) {
  if (s.sectionErrors?.agents) return errorView();
  const byRole = Object.fromEntries((s.data?.agents || []).map((a) => [a.agent, a]));
  const roles = ["Investigator", "Challenger", "Judge", "Builder"];
  const steps = roles
    .map((role, i) => {
      const a = byRole[role];
      const [name, about, target] = AGENTS[role];
      const status = a?.status || "Not started";
      return `<li class="step ${e(String(status).toLowerCase().replace(/\s+/g, "-"))}"><span class="step-dot" aria-hidden="true">${status === "Completed" ? "✓" : i + 1}</span><div class="step-body"><div class="step-title"><strong>${e(name)}</strong>${statusChip(status)}</div><p>${e(about)}</p>${a ? `<details class="step-more"><summary>What the ${e(role)} recorded</summary><p>${e(a.task)}</p><a class="text-link" href="#${e(target)}">${a.status === "Blocked" ? "See why →" : "Open the result →"}</a></details>` : ""}</div></li>`;
    })
    .join("");
  const error = s.runDetail?.error ? `<p class="notice error">Run message: ${e(s.runDetail.error)}</p>` : "";
  const stage =
    s.runDetail && ["Queued", "Running"].includes(s.runDetail.status) && s.runDetail.stage
      ? `<p class="notice" role="status">Current step reported by the backend: ${e(s.runDetail.stage)}</p>`
      : "";
  return `<ol class="stepper" aria-label="Analysis steps">${steps}</ol>${stage}${error}<p class="fine">Statuses come from backend records${s.service?.capabilities?.workflow ? " and refresh every 5 seconds while a run is active" : ""}. Nothing here is simulated. The decision step uses fixed rules, not AI, and cannot be overridden.</p>`;
}

// --- Analysis: verdict and reasoning ----------------------------------------------------------

export function decision(s) {
  if (s.sectionErrors?.decision) return errorView();
  const d = s.data?.decision;
  if (!d)
    return empty(
      "No recommendation yet.",
      "A recommendation appears only after the backend has evaluated the evidence.",
    );
  const v = VERDICTS[d.outcome] || { icon: "·", tone: "neutral", title: d.outcome, summary: "" };
  const [reasonTag, reason] = RULE_REASONS[d.rule] || ["Recorded rule", d.explanation];
  const superseded =
    d.rulesetVersion && d.currentRulesetVersion && d.rulesetVersion !== d.currentRulesetVersion
      ? `<p class="notice error" role="note"><strong>Historical decision, now superseded.</strong> It was made under rule version ${e(d.rulesetVersion)}; the current version is ${e(d.currentRulesetVersion)}. It is kept as history and cannot authorise any new work. Run a new analysis to continue.</p>`
      : "";
  const live = s.service?.capabilities?.builder && !s.demo && !s.recorded;
  const actions = [];
  if (live && d.builderAllowed && d.outcome !== "STOP")
    actions.push(
      `<button data-action="prepare-builder" ${s.busy ? "disabled" : ""}>Ask the Builder to prepare a validation kit</button>`,
    );
  if (!s.demo && !s.recorded && s.runId && /^run-[0-9a-f]{16}$/.test(s.runId) && d.outcome !== "STOP")
    actions.push(`<a class="button secondary" href="#build">See your six-phase path</a>`);
  if (!s.demo && !s.recorded)
    actions.push(link("brief", d.outcome === "STOP" ? "Start a different idea" : "Revise the idea and analyse again", "button secondary"));
  actions.push(link("evidence", "Review the evidence", "text-link"));
  return `<section class="verdict ${e(v.tone)}" data-outcome="${e(d.outcome)}" aria-labelledby="verdict-title">${superseded}<div class="verdict-top"><span class="verdict-icon" aria-hidden="true">${e(v.icon)}</span><div><div class="eyebrow">${s.recorded ? "Recorded recommendation · prior execution" : s.demo ? "MOCKED recommendation" : "Recommendation"}</div><h2 id="verdict-title">${e(v.title)}</h2><p class="lead">${e(v.summary)}</p></div></div><div class="verdict-reason"><span class="reason-tag">${e(reasonTag)}</span><p><strong>Main reason:</strong> ${e(reason)}</p></div>${d.action ? `<p class="verdict-action"><strong>${s.recorded || s.demo ? "About this record:" : "What you can do:"}</strong> ${e(d.action)}</p>` : ""}<div class="actions">${actions.join("")}</div><details class="tech"><summary>Technical details: rule, explanation and checks</summary><dl class="kv"><dt>Gate outcome</dt><dd><code>${e(d.outcome)}</code></dd><dt>Precise rule triggered</dt><dd><code>${e(d.rule)}</code></dd><dt>Backend explanation</dt><dd>${e(d.explanation)}</dd><dt>Evidence the gate referenced</dt><dd>${refs(d.findings, s.data?.findings)}</dd><dt>When it would be reconsidered</dt><dd>${e(d.next)}</dd></dl>${gateTrace(d)}</details></section>`;
}

/** The backend joins proposed experiments as "(1) … (2) …"; show them as a list, text unchanged. */
const steps = (text) => {
  const parts = String(text).split(/\s*\(\d+\)\s+/).filter(Boolean);
  return parts.length > 1
    ? `<ol class="plain-list">${parts.map((x) => `<li>${e(x)}</li>`).join("")}</ol>`
    : `<p>${e(text)}</p>`;
};
/** The four plain questions, answered only from recorded data. */
function reasoning(s) {
  const d = s.data?.decision;
  if (!d) return "";
  const findings = s.data?.findings || [];
  const strong = findings.filter((f) => f.standing === "ESTABLISHED");
  const against = findings.filter((f) => f.standing === "CONTRADICTED");
  const review = findings.filter((f) => f.standing === "NEEDS_REVIEW");
  const risks = (s.data?.challenges || []).filter((c) => /^R\d+$/.test(c.id));
  const item = (f) =>
    `<li><a href="#evidence/${e(encodeURIComponent(f.id))}">${e(f.claim)}</a></li>`;
  const c = s.data?.counterfactual;
  return `<div class="qa">
<section class="qa-card" aria-labelledby="qa-1"><h3 id="qa-1"><span aria-hidden="true">✓</span> What supports your idea?</h3>${strong.length ? `<p>${strong.length} finding${strong.length === 1 ? "" : "s"} with strong evidence.</p><ul class="link-list">${strong.slice(0, 3).map(item).join("")}</ul>` : "<p>No finding is strong enough to count yet.</p>"}</section>
<section class="qa-card" aria-labelledby="qa-2"><h3 id="qa-2"><span aria-hidden="true">!</span> What concerns us?</h3>${against.length || risks.length || d.risks?.length ? `<ul class="link-list">${against.slice(0, 2).map(item).join("")}${risks.slice(0, 2).map((r) => `<li><a href="#challenger">${e(r.claim)}</a></li>`).join("")}${(d.risks || []).slice(0, 2).map((r) => `<li>${e(r)}</li>`).join("")}</ul>` : "<p>No contradicting evidence or recorded risks.</p>"}</section>
<section class="qa-card" aria-labelledby="qa-3"><h3 id="qa-3"><span aria-hidden="true">?</span> What’s still unknown?</h3>${d.missing?.length ? `<ul class="plain-list">${d.missing.map((m) => `<li>${e(m)}</li>`).join("")}</ul>` : "<p>Nothing recorded as missing.</p>"}${review.length ? `<p class="fine">${review.length} finding${review.length === 1 ? " needs" : "s need"} verification and do not count yet.</p>` : ""}</section>
<section class="qa-card next" aria-labelledby="qa-4"><h3 id="qa-4"><span aria-hidden="true">→</span> What should you do next?</h3>${c && c.experiment && c.experiment !== "Not provided" ? steps(c.experiment) : `<p>${e(d.action || "Not provided.")}</p>`}<a class="text-link" href="#counterfactual">What could change this recommendation? →</a></section>
</div>`;
}

export function counterfactual(s) {
  if (s.sectionErrors?.counterfactual) return errorView();
  const c = s.data?.counterfactual;
  return c
    ? `<div class="grid-two"><div class="card"><h3>What is missing</h3><p>${e(c.requirement)}</p><p class="fine">${e(c.limitation)}</p></div><div class="card"><h3>A proposed experiment <span class="fine">· not yet run</span></h3><p>${e(c.experiment)}</p></div></div><div class="grid-two"><div class="signal positive"><h3><span aria-hidden="true">↗</span> Would strengthen the case</h3><p>${e(c.strengthen)}</p></div><div class="signal negative"><h3><span aria-hidden="true">↘</span> Would weaken the case</h3><p>${e(c.weaken)}</p></div></div><p class="fine">Reconsidered by: <code>${e(c.gate)}</code>. New evidence must be assessed by the backend. No experiment automatically guarantees GO.</p>`
    : empty(
        "First, a decision. Then, a path to reconsider it.",
        "What could change the recommendation appears once the backend has explained its decision.",
      );
}

// --- Analysis: evidence ----------------------------------------------------------------------

function evidenceSummary(findings) {
  const counts = STANDING_GROUPS.map(([code, name, icon, tone]) => [
    code,
    name,
    icon,
    tone,
    findings.filter((f) => f.standing === code).length,
  ]);
  const sources = new Set(
    findings.flatMap((f) =>
      f.quotations?.length ? f.quotations.map((q) => q.url).filter(Boolean) : f.url ? [f.url] : [],
    ),
  );
  const total = findings.length || 1;
  return `<div class="evidence-summary"><p class="evidence-total"><strong>${findings.length}</strong> finding${findings.length === 1 ? "" : "s"} from <strong>${sources.size}</strong> distinct source link${sources.size === 1 ? "" : "s"}. Each finding is one statement; several can come from the same source.</p><div class="bar" aria-hidden="true">${counts
    .filter((c) => c[4])
    .map((c) => `<span class="seg ${e(c[3])}" data-flex="${(c[4] / total).toFixed(4)}"></span>`)
    .join("")}</div><ul class="counts">${counts
    .map(
      ([code, name, icon, tone, n]) =>
        `<li class="${n ? "" : "zero"}"><span class="chip ${e(tone)}"><span aria-hidden="true">${e(icon)}</span>${e(name)}</span><strong>${n}</strong></li>`,
    )
    .join("")}</ul></div>`;
}
const ORDER = Object.fromEntries(STANDING_GROUPS.map((g, i) => [g[0], i]));
export function evidence(s) {
  if (s.sectionErrors?.findings) return errorView();
  const all = s.data?.findings || [];
  const findings = filterFindings(all, s.standing, s.claimType)
    .map((f, i) => [f, i])
    .sort((a, b) => (ORDER[a[0].standing] ?? 99) - (ORDER[b[0].standing] ?? 99) || a[1] - b[1])
    .map(([f]) => f);
  const referenceIndex = findings.findIndex((f) => f.id === s.focusFinding);
  const page =
    referenceIndex >= 0
      ? Math.floor(referenceIndex / 50)
      : Math.max(0, Math.min(s.evidencePage || 0, Math.ceil(findings.length / 50) - 1));
  const visible = findings.slice(page * 50, (page + 1) * 50);
  s.evidencePage = page;
  const pager =
    findings.length > 50
      ? `<div class="actions pager" aria-label="Evidence pages"><span>Showing ${page * 50 + 1}–${Math.min((page + 1) * 50, findings.length)} of ${findings.length}</span><button class="secondary" data-page="-1" ${page === 0 ? "disabled" : ""}>Previous findings</button><button class="secondary" data-page="1" ${(page + 1) * 50 >= findings.length ? "disabled" : ""}>Next findings</button></div>`
      : "";
  let lastGroup = null;
  const rows = visible
    .map((f) => {
      const header =
        f.standing !== lastGroup
          ? `<h3 class="group-title">${standingChip(f.standing)}<span class="fine">${e(GROUP[f.standing]?.[4] || "")}</span></h3>`
          : "";
      lastGroup = f.standing;
      const check = f.type === "founder statement check";
      return `${header}<details class="finding" id="finding-${e(f.id)}" ${s.focusFinding === f.id ? "open" : ""}><summary><span class="finding-title">${check ? "Does this commenter describe the problem themselves?" : e(f.claim)}</span><span class="finding-meta">${standingChip(f.standing)}<span>${e(f.sourceName)}</span><span class="muted">${e(f.type)}</span></span></summary><div class="finding-body">${check ? `<p class="full-claim"><strong>Statement checked:</strong> ${e(f.claim)}</p>` : ""}<h4>Exact quotation</h4>${quoteDetails(f)}<div class="grid-two"><div><h4>Why it is classified this way</h4><p>${e(f.assessment)}</p></div><div><h4>Limits</h4><p>${e(f.limitations)}</p><h4>Linked assumption</h4><p>${e(f.assumption)}</p></div></div><dl class="kv tech-line"><dt>Finding ID</dt><dd><code>${e(f.id)}</code></dd><dt>Recorded standing</dt><dd><code>${e(f.standing)}</code></dd><dt>Quote supports the statement?</dt><dd>${e(f.relationship)}</dd></dl></div></details>`;
    })
    .join("");
  return (
    evidenceSummary(all) +
    `<div class="filters"><label>Evidence standing<select id="standing"><option value="">All evidence</option>${STANDINGS.map((v) => `<option value="${e(v)}" ${s.standing === v ? "selected" : ""}>${e(GROUP[v]?.[1] || v)}</option>`).join("")}</select></label><label>Claim type<select id="claim-type"><option value="">All claim types</option>${[...new Set(all.map((f) => f.type))].map((v) => `<option ${s.claimType === v ? "selected" : ""}>${e(v)}</option>`).join("")}</select></label><span role="status">${findings.length} findings</span></div>` +
    (s.focusFinding && referenceIndex < 0
      ? `<p class="notice" role="status">Referenced finding ${e(s.focusFinding)} is unavailable in this run.</p>`
      : "") +
    (findings.length
      ? `<div class="findings">${rows}</div>`
      : empty(
          all.length ? "No findings match these filters." : "No evidence collected yet.",
          all.length ? "Choose a different standing or claim type." : "Findings will appear here after actual Investigator execution.",
        )) +
    pager
  );
}

export function challenger(s) {
  if (s.sectionErrors?.challenges) return errorView();
  const items = s.data?.challenges || [];
  return items.length
    ? `<div class="concerns">${items
        .map(
          (c) =>
            `<details class="concern"><summary><span class="concern-title">${e(c.claim)}</span><span class="fine">${e(c.basis)}</span></summary><div class="concern-body"><p>${e(c.risk)}</p><div class="grid-two"><div><h4>Evidence it rests on</h4><p>${refs(c.findings, s.data?.findings)}</p><h4>What is missing</h4>${list(c.missing, "Nothing recorded.")}</div><div><h4>How to test it</h4><p>${e(c.experiment)}</p></div></div><p class="fine">Reference <code>${e(c.id)}</code>${c.severity ? ` · ${badge(c.severity)}` : ""}</p></div></details>`,
        )
        .join("")}</div>`
    : empty(
        "No Challenger analysis yet.",
        "Evidence-based concerns, assumptions and new hypotheses will appear separately after execution.",
      );
}

export function analysis(s) {
  if (!s.runId) return projectHeader(s, "analysis") + noProject();
  const b = s.data?.brief;
  return (
    projectHeader(s, "analysis") +
    decision(s) +
    reasoning(s) +
    section("steps", "How the analysis ran", "", workflow(s)) +
    (b
      ? section(
          "idea",
          "The idea that was analysed",
          "",
          `<dl class="kv idea-kv"><dt>Idea</dt><dd>${e(b.idea)}</dd><dt>Problem</dt><dd>${e(b.problem)}</dd><dt>Customer</dt><dd>${e(b.customer)}</dd><dt>Market</dt><dd>${e(b.market)}</dd><dt>Skills</dt><dd>${e(b.skills.join(", ") || "Not stated")}</dd><dt>Time and budget</dt><dd>${b.hours == null ? "Not stated" : e(b.hours) + " hours a week"} · ${b.budget == null ? "budget not stated" : e(b.budget) + " " + e(b.currency)}</dd><dt>Values and constraints</dt><dd>${e(b.constraints.join("; ") || "None stated")}</dd></dl>`,
        )
      : "") +
    section(
      "evidence",
      "The evidence",
      "Grouped by how strong it is. Open any finding to see the exact quotation, its source and why it was classified that way.",
      evidence(s),
    ) +
    section(
      "concerns",
      "Assumptions we challenged",
      "Each of your assumptions, checked against the findings. A model’s reasoning is advisory; the evidence links are checked by code.",
      challenger(s),
    ) +
    section("next", "What could change this recommendation", "", counterfactual(s))
  );
}

// --- Build & validate --------------------------------------------------------------------------

export const phases = [
  ["Discover", "Find out whether the problem is real for these customers.", "Research, challenge and a recommendation.", "Working"],
  ["Validate", "Test the riskiest assumption with real people.", "Lean Canvas, interview kit, pass mark set in advance, your recorded results.", "Working · real sign-up tests STUBBED"],
  ["Build", "Make something testable.", "Local landing page (after GO), MVP scope, user guide and checks; a working MVP only for thread-digest ideas.", "Working · general MVP code STUBBED"],
  ["Commercial setup", "Set a test price and draft policies.", "Price options (assumptions) and DRAFT terms, privacy and refund policies — not legal advice.", "Working · no payments of any kind"],
  ["Launch", "Prepare the store and launch posts.", "Store page and post drafts; publishing and automatic delivery are simulated.", "MOCKED · publishing and sale to cash"],
  ["Operate & learn", "Decide whether to persevere or pivot.", "Support summary, metrics and a persevere-or-pivot memo from real evidence only.", "Working · rehearsal metrics MOCKED"],
];
function phaseState(s, i) {
  const d = s.data?.decision;
  const j = s.data?.journey;
  if (i === 0) {
    if (d) {
      const superseded = d.rulesetVersion && d.currentRulesetVersion && d.rulesetVersion !== d.currentRulesetVersion;
      if (superseded) return [`Superseded (was ${d.outcome})`, "neutral", "◷"];
      const v = VERDICTS[d.outcome];
      return [v?.short || d.outcome, v?.tone || "neutral", v?.icon || "·"];
    }
    if (["Queued", "Running"].includes(s.runDetail?.status)) return ["In progress", "info", "●"];
    return ["Not started", "neutral", "○"];
  }
  if (j?.blocked) return ["Blocked", "bad", "⊘"];
  if (i === 1) {
    const kits = s.data?.validation || [];
    const latest = kits.map((k) => k.latest).filter(Boolean).at(-1);
    if (latest) return [`Validation result: ${VERDICTS[latest.decision]?.short || latest.decision}`, latest.decision === "GO" ? "good" : latest.decision === "STOP" ? "bad" : "warn", "✓"];
    if (kits.length) return ["Kit ready — run your interviews", "info", "●"];
    if ((s.data?.approvals || []).some((a) => a.status === "Pending")) return ["Waiting for your approval", "warn", "…"];
  }
  const p = j?.phases?.find((x) => x.phase === i + 1);
  if (p?.gates?.length) {
    const g = p.gates.at(-1);
    if (!g.outcome) return ["Waiting for your approval", "warn", "…"];
    return [`${g.rehearsal ? "Rehearsal · " : ""}gate ${g.outcome}`, g.rehearsal ? "neutral" : g.outcome === "GO" ? "good" : "warn", g.rehearsal ? "◇" : "✓"];
  }
  if (p?.files?.length) return ["Drafts prepared", "info", "●"];
  return ["Not started", "neutral", "○"];
}
export function roadmap(s) {
  const j = s.data?.journey;
  const cards = phases
    .map(([name, purpose, outputs, status], i) => {
      const [label, tone, icon] = phaseState(s, i);
      const p = j?.phases?.find((x) => x.phase === i + 1);
      const files = p?.files?.length
        ? `<details class="phase-files"><summary>${p.files.length} file${p.files.length === 1 ? "" : "s"} prepared</summary><ul>${p.files.map((f) => `<li><a href="${e(f.url)}" target="_blank" rel="noopener">${e(f.name)}</a></li>`).join("")}</ul></details>`
        : "";
      const launch = p?.gates?.at(-1)?.launch ? `<p class="fine">${e(p.gates.at(-1).launch)}</p>` : "";
      return `<li class="phase"><div class="phase-head"><span class="phase-number" aria-hidden="true">${i + 1}</span><div><h3>${e(name)}</h3><p>${e(purpose)}</p></div>${chip(tone, icon, label)}</div><p class="fine">${e(outputs)} <span class="impl">${e(status)}</span></p>${files}${launch}</li>`;
    })
    .join("");
  const runner = j?.runner
    ? `<div class="notice">${j.blocked ? e(j.blocked) + " " : ""}${j.rehearsal && !j.blocked ? "Phases 3–6 can run only as a labelled <strong>rehearsal</strong> until Discover says GO and your validation passes; a rehearsal is never a reason to launch. " : ""}Phases 2–6 are generated and approved on the phase runner page, one step at a time.</div><div class="actions"><a class="button secondary" href="${e(j.runner)}">Open the phase runner →</a></div>`
    : `<p class="fine">${s.recorded ? "Recorded examples are read-only: later phases cannot be run from them." : s.demo ? "Demo mode does not run later phases." : j?.reason ? e(j.reason) : "Later-phase status appears for live projects with a recommendation."}</p>`;
  const pending = j?.pending?.length
    ? `<div class="waiting"><h3>Waiting for you on the phase runner</h3><ul>${j.pending.map((x) => `<li>${e(x.what)}${x.file ? ` · <span class="fine">${e(x.file)}</span>` : ""}</li>`).join("")}</ul></div>`
    : "";
  return `<ol class="journey" aria-label="Six-phase journey">${cards}</ol>${pending}${runner}<p class="fine">GO at any phase means “go on to the next test”, never proof of demand. Nothing is published, sent or paid.</p>`;
}

function approvalReason(s, a) {
  if (!s.service?.capabilities?.approvals || s.demo)
    return "Demo mode — these controls cannot grant approval.";
  if (s.approvalLocks?.has(a.id))
    return "Confirmation is uncertain. Refresh the request before retrying.";
  return approvalBlock(a, s.data?.artifacts || [], s.runId);
}
const APPROVAL_WORDS = {
  Pending: ["Waiting for your decision", "warn", "…"],
  "Pending — MOCKED": ["MOCKED request", "neutral", "◇"],
  Approved: ["Approved — not written yet", "info", "●"],
  Executing: ["Writing files", "info", "●"],
  Executed: ["Files written", "good", "✓"],
  Rejected: ["Rejected", "bad", "✕"],
  Expired: ["Expired", "neutral", "⌛"],
  Failed: ["Failed", "bad", "✕"],
  Invalid: ["Invalid", "bad", "✕"],
  Unknown: ["Unknown", "neutral", "?"],
};
const ACTION_WORDS = {
  generate_local_artifacts: "Write the validation kit to your computer",
};
function validationBlock(s, a) {
  const kit = (s.data?.validation || []).find((v) => v.id === a.id);
  if (a.status !== "Executed" || !kit) return "";
  const p = kit.plan;
  const latest = kit.observations.at(-1);
  const meter = `<div class="meter" role="img" aria-label="${latest ? `${latest.successes} of ${p.threshold} needed successes recorded, ${latest.participants} of ${p.sampleSize} participants` : `No results yet; pass mark ${p.threshold} of ${p.sampleSize}`}"><div class="meter-track"><span class="meter-fill" data-width="${latest ? Math.min(100, (latest.successes / p.sampleSize) * 100).toFixed(2) : 0}"></span><span class="meter-mark" data-left="${((p.threshold / p.sampleSize) * 100).toFixed(2)}"></span></div><div class="meter-legend"><span>${latest ? latest.successes : 0} met the condition</span><span>Pass mark: ${p.threshold} of ${p.sampleSize}</span></div></div>`;
  const rows = kit.observations.length
    ? `<div class="table-wrap"><table class="compact"><caption>Recorded totals (cumulative, founder-reported)</caption><thead><tr><th scope="col">Recorded</th><th scope="col">Participants</th><th scope="col">Met the condition</th><th scope="col">Gate</th><th scope="col">Notes</th></tr></thead><tbody>${kit.observations.map((o) => `<tr><td>${e(o.recordedAt || "")}</td><td>${o.participants} of ${p.sampleSize}</td><td>${o.successes}</td><td>${o.outcome ? badge(o.outcome.decision) : ""}</td><td>${e(o.notes)}</td></tr>`).join("")}</tbody></table></div>`
    : `<p class="muted">No results recorded. The experiment has not been reported as run.</p>`;
  const latestNote = kit.latest
    ? `<div class="notice"><strong>Validation gate: ${e(kit.latest.decision)}</strong> (<code>${e(kit.latest.rule)}</code>). ${e(kit.latest.meaning)} <strong>Next:</strong> ${e(kit.latest.nextStep)}</div>`
    : "";
  const canRecord = s.service?.capabilities?.approvals && !s.demo && !kit.final;
  const form = canRecord
    ? `<div class="grid-two"><label class="field">Participants so far (of ${p.sampleSize})<input id="participants-${e(a.id)}" type="number" min="1" max="${p.sampleSize}" step="1" inputmode="numeric"></label><label class="field">Of those, met the condition<input id="successes-${e(a.id)}" type="number" min="0" max="${p.sampleSize}" step="1" inputmode="numeric"></label></div><label class="field full">Notes (optional)<input id="notes-${e(a.id)}" maxlength="500" placeholder="What you observed, in your words"></label><p class="muted">Enter cumulative totals from interviews you actually ran. VentureLab records them as founder-reported and does not verify them. Requires the founder key above.</p><div class="actions"><button data-action="record-result" data-request="${e(a.id)}" ${s.busy ? "disabled" : ""}>Record founder-reported result</button></div>`
    : kit.final
      ? `<p class="muted">This experiment's result is final. A new experiment needs a new approved kit.</p>`
      : "";
  return `<section class="validation" aria-label="Validation results"><h3>Validation results</h3><p><strong>Threshold approved before testing:</strong> ${p.threshold} of ${p.sampleSize} participants — ${e(p.metric)}. <span class="badge amber">FOUNDER-REPORTED results</span></p>${meter}${rows}${latestNote}${form}</section>`;
}
export function approvals(s) {
  if (s.sectionErrors?.approvals) return errorView();
  const live = s.service?.capabilities?.approvals && !s.demo;
  const requests = s.data?.approvals || [];
  const artifacts = s.data?.artifacts || [];
  const key = live
    ? `<div class="card key-card"><h3>Your founder key</h3><p>Approving, writing files or recording results needs the key stored on your computer in <code>.venturelab/approvals.sqlite3.founder</code>. It stays in this tab’s memory and is sent only with your decision.</p><label class="field full">Founder key<input id="founder-key" type="password" autocomplete="off" spellcheck="false" maxlength="200" value="${e(s.founderKey || "")}"></label></div>`
    : "";
  if (!requests.length)
    return (
      key +
      empty(
        "No approval requests pending.",
        "When you ask the Builder for a validation kit, the exact request appears here for your decision. No approvals have been granted by this interface.",
      )
    );
  const cards = requests
    .map((a) => {
      const [word, tone, icon] = APPROVAL_WORDS[a.status] || [a.status, "neutral", "·"];
      const files = artifacts.filter((x) => x.id.startsWith(a.id + ":"));
      const block = approvalReason(s, a);
      const after =
        a.status === "Approved"
          ? "Approved. The files are written only when you execute this exact request."
          : a.status === "Executed"
            ? "These files were written to your local outputs folder. Nothing was published or sent."
            : "If you approve, nothing is written yet: you then choose “Write the approved files locally”. Nothing is ever published, sent or paid.";
      return `<article class="request" aria-labelledby="req-${e(a.id)}"><div class="request-head"><h3 id="req-${e(a.id)}">${e(ACTION_WORDS[a.action] || a.action)}</h3>${chip(tone, icon, word)}</div><p>${e(a.description)}</p>${files.length ? `<h4>What will be created</h4><ul class="plain-list">${files.map((f) => `<li>${e(f.title)} <span class="fine">${e(f.type)}</span></li>`).join("")}</ul>` : ""}<p class="consequence"><strong>What happens next:</strong> ${e(after)}</p>${a.expiresAt ? `<p class="muted">Must be decided and executed before ${e(a.expiresAt)}.</p>` : ""}${block && a.status === "Pending" ? `<p class="notice" role="note">${e(block)}</p>` : ""}${a.status === "Pending" && !s.demo ? `<label class="field full">Reason for your decision (optional)<input id="reason-${e(a.id)}" maxlength="500" value="" placeholder="Optional explanation"></label>` : ""}<div class="actions">${live ? `<button data-action="refresh-approvals" class="quiet" ${s.busy ? "disabled" : ""}>Refresh requests</button>` : ""}<button class="secondary" data-approval="${e(a.id)}" data-choice="reject" ${block || s.busy ? "disabled" : ""}>Reject</button><button data-approval="${e(a.id)}" data-choice="approve" ${block || s.busy ? "disabled" : ""}>Approve this action</button>${a.status === "Approved" && s.service?.capabilities?.builder && !s.demo ? `<button data-action="execute" data-request="${e(a.id)}" ${s.busy ? "disabled" : ""}>Write the approved files locally</button>` : ""}</div><details class="tech"><summary>Technical details</summary><dl class="kv"><dt>Request</dt><dd><code>${e(a.id)}</code></dd><dt>Venture run</dt><dd><code>${e(a.runId)}</code></dd><dt>Artifact identity</dt><dd><code>${e(a.artifactId)}</code></dd><dt>Version / fingerprint</dt><dd><code>${e(a.fingerprint)}</code></dd></dl></details>${validationBlock(s, a)}</article>`;
    })
    .join("");
  return key + cards;
}
export function artifacts(s) {
  if (s.sectionErrors?.artifacts) return errorView();
  const items = s.data?.artifacts || [];
  return items.length
    ? `<div class="artifact-list">${items.map((a) => `<article class="artifact"><div><h3>${e(a.title)}</h3><p class="fine">${e(a.type)} · ${e(a.status)}</p><p>${e(a.description)}</p></div><div class="artifact-side"><button data-preview="${e(a.id)}" class="secondary">Read-only preview ↗</button><details class="tech"><summary>Details</summary><dl class="kv"><dt>Artifact identity</dt><dd><code>${e(a.id)}</code></dd><dt>Version / fingerprint</dt><dd><code>${e(a.fingerprint)}</code></dd><dt>Approval</dt><dd>${e(a.approval)}</dd></dl></details></div></article>`).join("")}</div><section id="preview-panel" aria-live="polite"></section>`
    : empty(
        "No generated artifacts available.",
        "Validation kits, interview guides and local prototypes appear here once you ask the Builder for a request. Files are written only after your approval.",
      );
}
export function build(s) {
  if (!s.runId) return projectHeader(s, "build") + noProject();
  const waiting = (s.data?.approvals || []).filter((a) => a.status === "Pending").length;
  return (
    projectHeader(s, "build") +
    section(
      "journey",
      "Your path through the six phases",
      "Where this project stands in each phase, what is real and what is simulated.",
      roadmap(s),
    ) +
    section(
      "approvals",
      "Decisions waiting for you",
      "Each request is bound to one run, one exact set of files and a time limit. Only the backend can confirm it.",
      approvals(s),
      waiting ? chip("warn", "…", `${waiting} waiting`) : "",
    ) +
    section(
      "artifacts",
      "Files for your validation",
      "Review anything before approving it. HTML previews run with scripts, forms and links disabled.",
      artifacts(s),
    )
  );
}

// --- History & details -------------------------------------------------------------------------

export function history(s) {
  if (s.sectionErrors?.audit) return errorView();
  const audit = s.data?.audit || [];
  const rows = audit.filter((a) => !s.auditAgent || a.agent === s.auditAgent);
  return (
    `<div class="filters"><label>Agent<select id="audit-agent"><option value="">All agents</option>${[...new Set(audit.map((a) => a.agent))].map((v) => `<option ${s.auditAgent === v ? "selected" : ""}>${e(v)}</option>`).join("")}</select></label></div>` +
    (rows.length
      ? `<div class="table-wrap"><table><caption>${s.demo ? "MOCKED synthetic records — not an execution log" : "Backend audit records"}</caption><thead><tr>${["Timestamp", "Agent / action", "Model", "Sources", "Cost (USD)", "Approval", "Outcome"].map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead><tbody>${rows.map((a) => `<tr><td>${e(a.timestamp)}</td><td><strong>${e(a.agent)}</strong><br>${e(a.action)}</td><td>${e(a.model ?? "Not applicable")}</td><td>${a.sources.length ? a.sources.map((u) => source(u)).join("<br>") : "None recorded"}</td><td>${a.cost === null ? "Not reported" : e(a.cost)}</td><td>${e(a.approved_by ?? "Not approved")}</td><td>${e(a.outcome)}</td></tr>`).join("")}</tbody></table></div>`
      : empty("No audit records available.", "Only backend execution records belong in the live history."))
  );
}
export function details(s) {
  if (!s.runId) return projectHeader(s, "details") + noProject();
  const run = currentRun(s);
  const raw = s.runDetail || {};
  return (
    projectHeader(s, "details") +
    section(
      "run",
      "About this analysis",
      "",
      `<dl class="kv"><dt>Run identifier</dt><dd><code>${e(s.runId)}</code></dd><dt>Status</dt><dd>${e(run?.status || "Unknown")}</dd><dt>Recorded</dt><dd>${e(run?.recordedAt || "Not finished")}</dd>${raw.executionId ? `<dt>Original execution</dt><dd><code>${e(raw.executionId)}</code></dd>` : ""}${raw.provenance ? `<dt>Provenance</dt><dd>${e(raw.provenance)}</dd>` : ""}<dt>Data source</dt><dd>${s.recorded ? "Committed recording, checked against SHA-256 file fingerprints (consistency, not truth)." : s.demo ? "MOCKED synthetic fixtures." : "Your local backend."}</dd></dl><p class="fine">More: <a href="/diagnostics">system and model diagnostics</a> · <a href="/phases">all phase outputs</a></p>`,
    ) +
    section(
      "agents",
      "What each agent recorded",
      "",
      `<ul class="agent-log">${(s.data?.agents || []).map((a) => `<li><strong>${e(a.agent)}</strong> ${statusChip(a.status)}<p>${e(a.task)}</p></li>`).join("") || "<li>No agent records.</li>"}</ul>`,
    ) +
    section(
      "audit",
      "Audit trail",
      "Every recorded action, with its sources, model, cost and who approved it. Older records may contain a pre-filled default reason; saved explanations do not establish independent authorship.",
      history(s),
    )
  );
}

export const renderers = {
  // Pages
  projects: dashboard,
  brief,
  analysis,
  build,
  details,
  // Sections (also reachable through ALIASES)
  dashboard,
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

// --- evidence provenance ------------------------------------------------------------------------

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
  return `<div class="attribution"><h5>Who said this?</h5><dl class="quote-attribution"><dt>Source poster</dt><dd>Not recorded in the saved quotation metadata</dd><dt>Original author</dt><dd>Original author not verified</dd><dt>Third-party material</dt><dd>Unknown — this quotation may include someone else's words</dd><dt>Independent attribution verification</dt><dd>Not recorded. Exact-text verification does not verify authorship or personal experience.</dd></dl></div>`;
}
