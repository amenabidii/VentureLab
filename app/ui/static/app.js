import { WorkspaceService, getModelStatus } from "./service.js";
import { validateBrief } from "./contracts.js";
import { pages, renderers, loading, errorView, escape } from "./views.js";
const blankData = () => ({
  agents: [],
  findings: [],
  challenges: [],
  decision: null,
  counterfactual: null,
  artifacts: [],
  approvals: [],
  audit: [],
});
const state = {
  demo: false,
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
};
const main = document.querySelector("#main");
let epoch = 0;
let poll;
function route() {
  const [page, id] = location.hash.slice(1).split("/");
  try {
    state.focusFinding = decodeURIComponent(id || "");
  } catch {
    state.focusFinding = "";
  }
  return renderers[page] ? page : "dashboard";
}
function render(focus = false) {
  const page = route();
  document.querySelector("#nav").innerHTML = pages
    .map(
      ([id, label, icon]) =>
        `<a href="#${id}" ${page === id ? 'aria-current="page"' : ""}><span aria-hidden="true">${icon}</span>${label}</a>`,
    )
    .join("");
  document.querySelector("#breadcrumb").textContent = pages.find(
    (p) => p[0] === page,
  )[1];
  document.title = `${pages.find((p) => p[0] === page)[1]} · VentureLab`;
  main.innerHTML = renderers[page](state);
  if (focus) {
    main.focus();
    window.scrollTo(0, 0);
  }
}
async function load(focus = false) {
  const ticket = ++epoch;
  main.innerHTML = loading();
  try {
    const service = state.service;
    const runs = await service.listRuns();
    const runId = runs.some((r) => r.id === state.runId)
      ? state.runId
      : runs[0]?.id;
    const data = blankData();
    if (runId) {
      const methods = {
        agents: "getRunStatus",
        findings: "getFindings",
        challenges: "getChallenges",
        decision: "getDecision",
        counterfactual: "getCounterfactual",
        artifacts: "listArtifacts",
        approvals: "getApprovals",
        audit: "getAudit",
      };
      await Promise.all(
        Object.entries(methods).map(async ([key, method]) => {
          data[key] = await service[method](runId);
        }),
      );
    }
    if (ticket !== epoch) return;
    Object.assign(state, { runs, runId, data });
    render(focus);
  } catch {
    if (ticket === epoch) main.innerHTML = errorView();
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
  state.review = Object.keys(state.errors).length === 0;
  render();
  if (!state.review) document.querySelector('[aria-invalid="true"]')?.focus();
  else main.focus();
});
main.addEventListener("change", (event) => {
  const key = {
    standing: "standing",
    "claim-type": "claimType",
    "audit-agent": "auditAgent",
  }[event.target.id];
  if (key) {
    const id = event.target.id;
    state[key] = event.target.value;
    render();
    document.getElementById(id)?.focus();
  }
});
function showFailure(message) {
  const node = document.createElement("div");
  node.className = "notice error";
  node.setAttribute("role", "alert");
  node.textContent = message;
  main.prepend(node);
}
main.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button || button.disabled) return;
  if (button.dataset.run) {
    state.runId = button.dataset.run;
    location.hash = "workflow";
    await load();
  }
  if (button.dataset.action === "retry") await load();
  if (button.dataset.action === "edit") {
    state.review = false;
    render();
  }
  if (button.dataset.action === "submit") {
    if (!state.service.capabilities.createRun || state.busy) return;
    state.busy = true;
    render();
    try {
      const run = await state.service.createRun({
        ...state.brief,
        hours: Number(state.brief.hours),
        budget: Number(state.brief.budget),
      });
      state.runId = run.id;
      location.hash = "workflow";
      await load();
    } catch {
      render();
      showFailure(
        "Submission was not confirmed. Your brief is preserved. Check the backend run list before retrying to avoid a duplicate run.",
      );
    } finally {
      state.busy = false;
      const submit = main.querySelector('[data-action="submit"]');
      if (submit) {
        submit.disabled = false;
        submit.textContent = "Submit and start analysis";
      }
    }
  }
  if (button.dataset.preview) {
    const artifact = state.data.artifacts.find(
      (a) => a.id === button.dataset.preview,
    );
    if (!artifact) return;
    const panel = document.querySelector("#preview-panel");
    panel.innerHTML = `<article class="card"><div class="section-title"><h2>${escape(artifact.title)} · Read-only preview</h2><button data-action="close-preview" class="quiet">Close preview</button></div><p>${state.demo ? "MOCKED synthetic fixture. " : ""}Scripts, forms, links and network access are disabled in HTML previews.</p><div id="preview-content"></div></article>`;
    const content = panel.querySelector("#preview-content");
    if (artifact.format === "html") {
      // Inert iframe: opaque origin, no scripts, no forms, no network and no navigation links.
      const frame = document.createElement("iframe");
      frame.setAttribute("sandbox", "");
      frame.referrerPolicy = "no-referrer";
      frame.title = artifact.title + " — inert preview";
      const parsed = new DOMParser().parseFromString(
        artifact.content,
        "text/html",
      );
      parsed
        .querySelectorAll(
          "script,style,link,meta,base,iframe,object,embed,form,input,button,textarea,select,svg,math",
        )
        .forEach((n) => n.remove());
      parsed.querySelectorAll("*").forEach((n) => {
        for (const attr of [...n.attributes]) n.removeAttribute(attr.name);
      });
      frame.srcdoc =
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; form-action &#39;none&#39;; base-uri &#39;none&#39;">' +
        parsed.body.innerHTML;
      content.append(frame);
    } else {
      const pre = document.createElement("pre");
      pre.textContent = artifact.content;
      content.append(pre);
    }
    panel.scrollIntoView({ block: "nearest" });
    panel.querySelector("button").focus();
  }
  if (button.dataset.action === "close-preview") {
    document.querySelector("#preview-panel").replaceChildren();
    main.querySelector("[data-preview]")?.focus();
  }
  if (button.dataset.approval) {
    if (!state.service.capabilities.approvals || state.busy) return;
    const request = state.data.approvals.find(
      (a) => a.id === button.dataset.approval,
    );
    if (!request) return;
    state.busy = true;
    render();
    try {
      await state.service.decideApproval(request, button.dataset.choice);
      await load();
    } catch {
      showFailure(
        "The backend did not confirm this decision. No successful approval is being reported. Refresh the request before retrying.",
      );
    } finally {
      state.busy = false;
      main.querySelectorAll("[data-approval]").forEach((b) => {
        const a = state.data.approvals.find((a) => a.id === b.dataset.approval);
        b.disabled =
          !state.service.capabilities.approvals || a?.status !== "Pending";
      });
    }
  }
});
document.querySelector("#mode-toggle").addEventListener("click", async () => {
  state.demo = !state.demo;
  state.service = new WorkspaceService(state.demo ? "demo" : "live");
  state.runId = null;
  state.standing = "";
  state.claimType = "";
  state.auditAgent = "";
  document.querySelector("#mode-toggle").textContent = state.demo
    ? "Exit demo"
    : "Explore demo";
  const banner = document.querySelector("#mode-banner");
  banner.classList.toggle("demo", state.demo);
  banner.textContent = state.demo
    ? "MOCKED · Synthetic UI preview. No research, execution, generated artifacts or approvals are real."
    : "Live workspace · Workflow integrations are STUBBED on this foundation branch.";
  await load();
});
window.addEventListener("hashchange", () => {
  if (location.hash.startsWith("#evidence/")) {
    state.standing = "";
    state.claimType = "";
  }
  render(true);
  clearInterval(poll);
  if (state.service.capabilities.workflow && route() === "workflow")
    poll = setInterval(() => load(), 5000);
});
async function refreshModel() {
  const status = document.querySelector("#model-status");
  try {
    const model = await getModelStatus();
    status.textContent = model.ready
      ? `${model.model} · Available`
      : `${model.model || "Local model"} · Not ready`;
    status.className = model.ready ? "ready" : "";
  } catch {
    status.textContent = "Model status unavailable";
  }
}
render();
load();
refreshModel();
setInterval(refreshModel, 30000);
