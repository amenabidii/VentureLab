import { WorkspaceService, getModelStatus } from "./service.js";
import { validateBrief } from "./contracts.js";
import { normalize, approvalBlock, BriefValidationError } from "./normalize.js";
import { inertPreview } from "./preview.js";
import { pages, ALIASES, TITLES, renderers, loading, errorView, escape } from "./views.js";
const blankData = () => ({
  agents: [],
  findings: [],
  challenges: [],
  decision: null,
  counterfactual: null,
  artifacts: [],
  approvals: [],
  audit: [],
  validation: [],
  brief: null,
  journey: null,
});
const state = {
  demo: false,
  recorded: false,
  service: new WorkspaceService(),
  runs: [],
  runId: null,
  data: blankData(),
  brief: { currency: "EGP", sources: [] },
  errors: {},
  review: false,
  busy: false,
  standing: "",
  claimType: "",
  auditAgent: "",
  focusFinding: "",
  evidencePage: 0,
  loading: false,
  loadError: false,
  sectionErrors: {},
  message: "",
  approvalLocks: new Set(),
  submitLocked: false,
  submittedRunId: null,
  founderKey: "",
  quick: false,
  runDetail: null,
  section: "",
};
const main = document.querySelector("#main");
let epoch = 0,
  poll,
  previewTrigger;
let activeReads = 0;
const PAGES = ["projects", "brief", "analysis", "build", "details"];
/** Resolves the URL to a page; older section names open the page that now holds them. */
function route() {
  const [name, id] = location.hash.slice(1).split("/");
  try {
    state.focusFinding = name === "evidence" ? decodeURIComponent(id || "") : "";
  } catch {
    state.focusFinding = "";
  }
  if (Object.hasOwn(ALIASES, name)) {
    state.section = ALIASES[name][1];
    return ALIASES[name][0];
  }
  state.section = "";
  return PAGES.includes(name) ? name : "projects";
}
/** Applies chart values recorded in data attributes (the page policy forbids inline styles). */
function applyMeasures() {
  for (const el of main.querySelectorAll("[data-flex]"))
    el.style.flexGrow = el.dataset.flex;
  for (const el of main.querySelectorAll("[data-width]"))
    el.style.width = el.dataset.width + "%";
  for (const el of main.querySelectorAll("[data-left]"))
    el.style.left = el.dataset.left + "%";
}
function render(focus = false) {
  const page = route();
  const waiting = state.data.approvals.filter((a) => a.status === "Pending").length;
  document.querySelector("#nav").innerHTML = pages
    .map(
      ([id, label, icon]) =>
        `<a href="#${id}" ${page === id ? 'aria-current="page"' : ""}><span class="nav-icon" aria-hidden="true">${icon}</span><span>${label}</span>${id === "build" && waiting ? `<span class="nav-count" aria-label="${waiting} waiting for your decision">${waiting}</span>` : ""}</a>`,
    )
    .join("");
  const project = state.runs.find((r) => r.id === state.runId);
  document.querySelector("#breadcrumb").textContent =
    TITLES[page] + (project && !["projects", "brief"].includes(page) ? ` · ${project.title}` : "");
  document.title = `${TITLES[page]} · VentureLab`;
  const newIdea = document.querySelector(".new-idea");
  if (page === "brief") newIdea.setAttribute("aria-current", "page");
  else newIdea.removeAttribute("aria-current");
  const independent = page === "brief";
  if (!independent && state.loading) main.innerHTML = loading();
  else if (!independent && state.loadError) main.innerHTML = errorView();
  else main.innerHTML = renderers[page](state);
  applyMeasures();
  if (page === "projects" && Object.keys(state.sectionErrors).length)
    main.insertAdjacentHTML(
      "afterbegin",
      '<p class="notice error" role="alert">Some outputs could not be read. Open the relevant view to retry; missing data is not a gate result.</p>',
    );
  if (state.message) {
    const notice = document.createElement("p");
    notice.className = "notice error";
    notice.setAttribute("role", "alert");
    notice.textContent = state.message;
    main.prepend(notice);
  }
  document.querySelector("#mode-toggle").disabled = state.busy;
  document.querySelector("#recordings-toggle").disabled = state.busy;
  if (focus) {
    const target =
      (state.focusFinding && document.getElementById(`finding-${state.focusFinding}`)) ||
      (state.section && document.getElementById(`sec-${state.section}`));
    if (target) {
      target.scrollIntoView({ block: "start" });
      (target.matches("details") ? target.querySelector("summary") : target).focus({ preventScroll: true });
    } else {
      main.focus();
      window.scrollTo(0, 0);
    }
  }
}
function schedulePoll() {
  clearTimeout(poll);
  // Poll on the workflow view, and on any view while the selected run is still queued or
  // running, so results that arrive later are never hidden behind stale data.
  const active = ["Queued", "Running"].includes(state.runDetail?.status);
  if (
    state.service.capabilities.workflow &&
    (route() === "analysis" || active) &&
    activeReads === 0 &&
    !state.busy &&
    !document.hidden
  )
    poll = setTimeout(() => load(false, true), 5000);
}
async function load(focus = false, background = false) {
  activeReads++;
  const ticket = ++epoch,
    service = state.service;
  clearTimeout(poll);
  state.loading = !background;
  state.loadError = false;
  if (!background) render();
  try {
    const rawRuns = await service.listRuns();
    const runs = normalize("runs", rawRuns);
    const runId = state.runId ?? runs[0]?.id;
    const data = blankData(),
      errors = {};
    const missingRun = runId && !runs.some((r) => r.id === runId);
    if (missingRun) {
      for (const key of Object.keys(data)) errors[key] = true;
    } else if (runId) {
      const methods = {
        agents: "getRunStatus",
        findings: "getFindings",
        challenges: "getChallenges",
        decision: "getDecision",
        counterfactual: "getCounterfactual",
        artifacts: "listArtifacts",
        approvals: "getApprovals",
        audit: "getAudit",
        validation: "getValidation",
        brief: "getBrief",
        journey: "getJourney",
      };
      await Promise.all(
        Object.entries(methods).map(async ([key, method]) => {
          try {
            data[key] = normalize(key, await service[method](runId));
          } catch {
            errors[key] = true;
          }
        }),
      );
    }
    if (ticket !== epoch || service !== state.service) return false;
    if (missingRun)
      state.message =
        "The selected run is not in the backend run list. Refresh its status or select another run from Overview. No other run has been substituted.";
    Object.assign(state, {
      runs,
      runId,
      runDetail: Array.isArray(rawRuns)
        ? (rawRuns.find((r) => r && r.id === runId) ?? null)
        : null,
      data,
      loading: false,
      sectionErrors: errors,
    });
    if (!errors.approvals && !errors.artifacts) state.approvalLocks.clear();
    // A slow read must not destroy the caret or reset a brief being edited.
    if (route() !== "brief") render(focus);
    schedulePoll();
    return true;
  } catch {
    if (ticket !== epoch) return false;
    state.loading = false;
    state.loadError = true;
    state.data = blankData();
    state.runs = [];
    if (route() !== "brief") render();
    schedulePoll();
    return false;
  } finally {
    activeReads--;
    schedulePoll();
  }
}
function readBrief(form) {
  const values = Object.fromEntries(new FormData(form));
  values.sources = values.sources
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
  return values;
}
main.addEventListener("input", (event) => {
  if (event.target.closest("#brief-form"))
    state.brief = readBrief(event.target.form);
});
main.addEventListener("submit", (event) => {
  if (event.target.id !== "brief-form") return;
  event.preventDefault();
  state.brief = readBrief(event.target);
  state.errors = validateBrief(state.brief);
  state.review = !Object.keys(state.errors).length;
  render();
  if (!state.review) document.querySelector('[aria-invalid="true"]')?.focus();
  else main.focus();
});
main.addEventListener("change", (event) => {
  if (event.target.id === "quick-run") state.quick = event.target.checked;
  if (event.target.id === "founder-key")
    state.founderKey = event.target.value.trim();
  if (event.target.closest("#brief-form"))
    state.brief = readBrief(event.target.form);
  const key = {
    standing: "standing",
    "claim-type": "claimType",
    "audit-agent": "auditAgent",
  }[event.target.id];
  if (key) {
    const id = event.target.id;
    state[key] = event.target.value;
    state.evidencePage = 0;
    state.focusFinding = "";
    if (location.hash.includes("/"))
      history.replaceState(null, "", "#evidence");
    render();
    document.getElementById(id)?.focus();
  }
});
function readKey() {
  const input = document.querySelector("#founder-key");
  if (input) state.founderKey = input.value.trim();
  return state.founderKey;
}
function failure(message) {
  state.message = message;
  render();
}
main.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button || button.disabled) return;
  if (button.dataset.run) {
    state.runId = button.dataset.run;
    state.data = blankData();
    state.message = "";
    location.hash = "analysis";
    await load();
  }
  if (
    button.dataset.action === "retry" ||
    button.dataset.action === "refresh-approvals"
  ) {
    state.message = "";
    await load();
  }
  if (button.dataset.action === "edit" && !state.busy) {
    state.review = false;
    state.message = "";
    render();
    document.getElementById("idea")?.focus();
  }
  if (button.dataset.action === "new-brief" && !state.busy) {
    state.brief = { currency: "EGP", sources: [] };
    state.review = false;
    state.submitLocked = false;
    state.submittedRunId = null;
    state.message = "";
    render();
  }
  if (button.dataset.page) {
    state.evidencePage += Number(button.dataset.page);
    state.focusFinding = "";
    history.replaceState(null, "", "#evidence");
    render();
    main.querySelector(".finding summary")?.focus();
  }
  if (button.dataset.action === "submit") {
    if (
      !state.service.capabilities.createRun ||
      state.demo ||
      state.busy ||
      state.submitLocked ||
      state.submittedRunId
    )
      return;
    state.errors = validateBrief(state.brief);
    if (Object.keys(state.errors).length) {
      state.review = false;
      render();
      return;
    }
    state.busy = true;
    state.message = "";
    render();
    try {
      const [run] = normalize("runs", [
        await state.service.createRun({
          ...state.brief,
          hours: Number(state.brief.hours),
          budget: Number(state.brief.budget),
          effort: state.quick ? "quick" : "full",
        }),
      ]);
      state.submittedRunId = run.id;
      state.runId = run.id;
      location.hash = "analysis";
      await load();
    } catch (error) {
      if (error instanceof BriefValidationError) {
        state.errors = error.fields;
        state.review = false;
        state.message =
          "The backend rejected this brief. Correct the highlighted fields; no run was confirmed.";
      } else {
        // A transport failure may occur after server acceptance; prevent a blind duplicate retry.
        state.submitLocked = true;
        state.message =
          "Submission was not confirmed. Your brief is preserved. Check backend run records before preparing another submission; this action will not be retried automatically.";
      }
    } finally {
      state.busy = false;
      render();
      if (!state.review) main.querySelector('[aria-invalid="true"]')?.focus();
      schedulePoll();
    }
  }
  if (button.dataset.action === "prepare-builder") {
    if (
      !state.service.capabilities.builder ||
      state.demo ||
      state.busy ||
      !state.runId
    )
      return;
    state.busy = true;
    state.message = "";
    render();
    try {
      const result = await state.service.prepareBuilder(state.runId);
      state.message = [
        result.created
          ? "The Builder prepared a request. Review it, then approve or reject it."
          : "A request is already open for this run.",
        ...(result.notes || []),
      ].join(" ");
      location.hash = "approvals";
      await load();
    } catch (error) {
      state.message = `The Builder did not prepare a request: ${error?.message || "unknown error"}`;
    } finally {
      state.busy = false;
      render();
    }
  }
  if (button.dataset.action === "record-result") {
    if (!state.service.capabilities.approvals || state.demo || state.busy)
      return;
    const request = state.data.approvals.find(
      (a) => a.id === button.dataset.request,
    );
    const kit = state.data.validation.find((v) => v.id === button.dataset.request);
    if (!request || request.status !== "Executed" || !kit || kit.final) return;
    const value = (name) =>
      document.querySelector(`#${name}-${CSS.escape(request.id)}`)?.value ?? "";
    // Read every input before re-rendering: render() replaces the form.
    const participants = Number(value("participants")),
      successes = Number(value("successes")),
      notes = value("notes"),
      key = readKey();
    if (
      !Number.isInteger(participants) ||
      !Number.isInteger(successes) ||
      participants < 1 ||
      successes < 0 ||
      successes > participants
    )
      return failure(
        "Enter whole numbers: at least one participant, and no more successes than participants. Nothing was recorded.",
      );
    state.busy = true;
    state.message = "";
    render();
    try {
      const result = await state.service.recordResult(
        { ...request },
        { participants, successes, notes, key },
      );
      state.message = `Recorded as founder-reported. Validation gate: ${result.outcome.decision} (${result.outcome.rule}).`;
    } catch (error) {
      state.message = `The result was not recorded: ${error?.message || "unknown error"}`;
    } finally {
      state.busy = false;
      await load();
    }
  }
  if (button.dataset.action === "execute") {
    if (!state.service.capabilities.approvals || state.demo || state.busy)
      return;
    const request = state.data.approvals.find(
      (a) => a.id === button.dataset.request,
    );
    if (!request || request.status !== "Approved") return;
    state.busy = true;
    state.message = "";
    render();
    try {
      await state.service.executeApproval({ ...request }, readKey());
      state.message =
        "The backend wrote the approved files locally. Nothing was published or sent.";
      location.hash = "artifacts";
    } catch (error) {
      state.message = `Execution was refused: ${error?.message || "unknown error"} No files are reported as written.`;
    } finally {
      state.busy = false;
      await load();
    }
  }
  if (button.dataset.preview) {
    const artifact = state.data.artifacts.find(
      (a) => a.id === button.dataset.preview,
    );
    if (!artifact) return;
    previewTrigger = artifact.id;
    const panel = document.querySelector("#preview-panel");
    panel.innerHTML = `<article class="card"><div class="section-title"><h2>${escape(artifact.title)} · Read-only preview</h2><button data-action="close-preview" class="quiet">Close preview</button></div><p>${state.demo ? "MOCKED synthetic fixture. " : ""}Scripts, forms, links and network access are disabled in HTML previews.</p><div id="preview-content"></div></article>`;
    const content = panel.querySelector("#preview-content");
    if (artifact.format === "html")
      content.append(inertPreview(artifact.content, artifact.title));
    else {
      const pre = document.createElement("pre");
      pre.textContent = artifact.content;
      content.append(pre);
    }
    panel.scrollIntoView({ block: "nearest" });
    panel.querySelector("button").focus();
  }
  if (button.dataset.action === "close-preview") {
    document.querySelector("#preview-panel").replaceChildren();
    [...main.querySelectorAll("[data-preview]")]
      .find((b) => b.dataset.preview === previewTrigger)
      ?.focus();
  }
  if (button.dataset.approval) {
    if (
      !state.service.capabilities.approvals ||
      state.demo ||
      state.busy ||
      state.approvalLocks.has(button.dataset.approval)
    )
      return;
    const request = state.data.approvals.find(
      (a) => a.id === button.dataset.approval,
    );
    if (!request) return;
    const block = approvalBlock(request, state.data.artifacts, state.runId);
    if (block) {
      failure(block);
      return;
    }
    const approvalKey = readKey();
    const approvalReason = document.querySelector(
      `#reason-${CSS.escape(request.id)}`,
    )?.value;
    if (button.dataset.choice === "approve") {
      confirmApproval(request, approvalKey, approvalReason, button);
      return;
    }
    await decideRequest(request, "reject", approvalKey, approvalReason);
  }
});
/** Sends a founder decision and shows only what the backend confirms. */
async function decideRequest(request, choice, approvalKey, approvalReason) {
  {
    state.busy = true;
    state.message = "";
    state.approvalLocks.add(request.id);
    render();
    try {
      const [result] = normalize("approvals", [
        await state.service.decideApproval(
          { ...request },
          choice,
          {
            key: approvalKey,
            reason: approvalReason,
          },
        ),
      ]);
      if (
        ["id", "runId", "artifactId", "fingerprint", "action"].some(
          (key) => result[key] !== request[key],
        ) ||
        result.status !==
          (choice === "approve" ? "Approved" : "Rejected")
      )
        throw new Error("Mismatched confirmation");
      await load(); // Render only authoritative refreshed records, never an optimistic local status.
    } catch (error) {
      state.message = `The backend did not confirm this decision${error?.message ? ": " + error.message : "."} No successful approval is being reported. Refresh the request before retrying.`;
    } finally {
      state.busy = false;
      render();
      schedulePoll();
    }
  }
}
const dialog = document.querySelector("#confirm-dialog");
let pendingApproval = null;
/** Explains the consequences before an approval is sent; nothing is sent until confirmed. */
function confirmApproval(request, approvalKey, approvalReason, trigger) {
  if (dialog.open) return;
  const files = state.data.artifacts.filter((a) => a.id.startsWith(request.id + ":"));
  pendingApproval = { request, approvalKey, approvalReason, trigger };
  dialog.querySelector("#confirm-body").innerHTML =
    `<p>You are approving this exact request. After approval:</p><ul><li>Nothing is written yet. You then choose “Write the approved files locally”.</li><li>Nothing is published, sent or paid.</li><li>The approval covers only these files, unchanged, until ${escape(request.expiresAt || "the request expires")}.</li></ul>` +
    (files.length
      ? `<p><strong>Files it covers</strong></p><ul>${files.map((f) => `<li>${escape(f.title)}</li>`).join("")}</ul>`
      : "") +
    `<p class="fine">Fingerprint <code>${escape(request.fingerprint)}</code></p>`;
  dialog.showModal();
  dialog.querySelector("[data-confirm]").focus();
}
dialog.addEventListener("close", async () => {
  const pending = pendingApproval;
  pendingApproval = null;
  if (!pending) return;
  if (dialog.returnValue === "confirm")
    await decideRequest(pending.request, "approve", pending.approvalKey, pending.approvalReason);
  else pending.trigger?.isConnected && pending.trigger.focus();
});
async function switchMode(mode) {
  if (state.busy) return;
  ++epoch;
  clearTimeout(poll);
  state.demo = mode === "demo";
  state.recorded = mode === "recorded";
  state.service = new WorkspaceService(mode);
  Object.assign(state, {
    runId: null,
    runDetail: null,
    founderKey: "",
    runs: [],
    data: blankData(),
    sectionErrors: {},
    standing: "",
    claimType: "",
    auditAgent: "",
    evidencePage: 0,
    message: "",
  });
  state.approvalLocks.clear();
  document.querySelector("#mode-toggle").textContent = state.demo
    ? "Exit demo"
    : "Explore demo";
  document.querySelector("#recordings-toggle").textContent = state.recorded
    ? "Return to live"
    : "Recorded executions";
  const banner = document.querySelector("#mode-banner");
  banner.classList.toggle("demo", state.demo);
  banner.textContent = state.recorded
    ? "RECORDED EXECUTIONS · Read-only prior runs, not current research. Historical decisions may be superseded; no approval authority is restored."
    : state.demo
      ? "MOCKED · Synthetic UI preview. No research, execution, generated artifacts or approvals are real."
      : "";
  banner.hidden = !state.recorded && !state.demo;
  await load();
}
document
  .querySelector("#mode-toggle")
  .addEventListener("click", () => switchMode(state.demo ? "live" : "demo"));
document
  .querySelector("#recordings-toggle")
  .addEventListener("click", () =>
    switchMode(state.recorded ? "live" : "recorded"),
  );
document.querySelector(".skip").addEventListener("click", (event) => {
  event.preventDefault();
  main.focus();
  main.scrollIntoView();
});
window.addEventListener("hashchange", () => {
  if (location.hash.startsWith("#evidence/")) {
    state.standing = "";
    state.claimType = "";
  }
  render(true);
  schedulePoll();
});
document.addEventListener("visibilitychange", schedulePoll);
async function refreshModel() {
  if (document.hidden) return;
  const status = document.querySelector("#model-status");
  try {
    const model = await getModelStatus();
    status.textContent = model.ready
      ? `${model.model} · Available`
      : `${model.model} · Not ready`;
    status.className = model.ready ? "ready" : "";
  } catch {
    status.textContent = "Model status unavailable";
    status.className = "";
  }
}
render();
load();
refreshModel();
setInterval(refreshModel, 30000);
