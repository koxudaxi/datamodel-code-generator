import * as Comlink from "https://cdn.jsdelivr.net/npm/comlink@4.4.2/dist/esm/comlink.mjs";
import morphdom from "https://cdn.jsdelivr.net/npm/morphdom@2.7.7/+esm";

import {
  getInputValue,
  mountInputEditor,
  mountOutputViewer,
  refreshEditors,
  setInputLanguage,
  setInputValue,
  setOutputValue,
} from "./editor.js";

const appEl = document.querySelector("#app");
const rawWorker = new Worker("./worker.js", { type: "module" });
const worker = Comlink.wrap(rawWorker);

let ready = false;
let running = false;
let lastOutput = "";
let configToml = "";
let autoGenerate = true;
let autoTimer = null;
let pendingAutoGenerate = false;
let activeGenerationMode = "manual";
let cliCommandText = "";
let cliOptionsDirty = true;
let cliRequestId = 0;
let appShellMounted = false;
let workspaceResizeObserver = null;
let headerCompact = false;
let workspaceCollapsed = false;

function currentSchema() {
  return getInputValue();
}

function currentInputType() {
  return document.querySelector("#input-type")?.value ?? "jsonschema";
}

function renderOutput(value, language = "python") {
  const output = document.querySelector("#output");
  if (!output) {
    appEl.textContent = value;
    return;
  }
  setOutputValue(value, language);
}

function updateInputFormatState() {
  const inputType = currentInputType();
  document.querySelector("#schema")?.setAttribute("data-format", inputType);
  document.body.dataset.inputFormat = inputType;
  setInputLanguage(inputType);
}

function mountEditor() {
  mountInputEditor(document.querySelector("#schema"), currentInputType());
  mountOutputViewer(document.querySelector("#output"), "", "python");
  observeWorkspaceResize();
  refreshEditors();
}

function syncStickyOffsets() {
  const topbar = document.querySelector(".topbar");
  const height = topbar ? Math.ceil(topbar.getBoundingClientRect().height) : 0;
  document.documentElement.style.setProperty("--topbar-offset", `${height}px`);
}

function observeWorkspaceResize() {
  const workspace = document.querySelector(".workspace");
  if (!workspace || workspaceResizeObserver) {
    return;
  }
  workspaceResizeObserver = new ResizeObserver(() => refreshEditors());
  workspaceResizeObserver.observe(workspace);
}

function setLayoutState() {
  document.body.classList.toggle("header-compact", headerCompact);
  document.body.classList.toggle("workspace-collapsed", workspaceCollapsed);
  const headerButton = document.querySelector("#toggle-header");
  if (headerButton) {
    headerButton.textContent = headerCompact ? "Full Header" : "Compact Header";
    headerButton.setAttribute("aria-pressed", headerCompact ? "true" : "false");
  }
  const workspaceButton = document.querySelector("#toggle-workspace");
  if (workspaceButton) {
    workspaceButton.textContent = workspaceCollapsed ? "Show Editors" : "Hide Editors";
    workspaceButton.setAttribute("aria-pressed", workspaceCollapsed ? "true" : "false");
  }
  syncStickyOffsets();
  refreshEditors();
}

async function mountInitialShell() {
  const response = await fetch("./generated/app-shell.html");
  if (appShellMounted || !response.ok) {
    return;
  }
  const html = await response.text();
  if (appShellMounted) {
    return;
  }
  appEl.innerHTML = html;
  appEl.classList.remove("boot");
  appShellMounted = true;
  syncStickyOffsets();
  updateInputFormatState();
  mountEditor();
  setLayoutState();
}

function mountRenderedShell(html) {
  const existingSchema = currentSchema();
  const template = document.createElement("template");
  template.innerHTML = html;
  const nextShell = template.content.firstElementChild;
  appEl.classList.remove("boot");
  appShellMounted = true;
  if (appEl.firstElementChild && nextShell) {
    morphdom(appEl.firstElementChild, nextShell, {
      onBeforeElUpdated(fromEl, toEl) {
        if (fromEl.id === "schema" && existingSchema) {
          toEl.value = existingSchema;
        }
        return true;
      },
    });
  } else {
    appEl.innerHTML = html;
  }
  if (existingSchema) {
    const schema = document.querySelector("#schema");
    if (schema) {
      schema.value = existingSchema;
    }
  }
  updateInputFormatState();
  mountEditor();
  syncStickyOffsets();
  setLayoutState();
  setGenerateState();
}

function collectOptionEntries() {
  const form = document.querySelector("#options-form");
  return form ? Object.fromEntries(new FormData(form).entries()) : {};
}

function filterOptions(query) {
  const needle = query.trim().toLowerCase();
  document.querySelectorAll("#options-form .option-group").forEach((group) => {
    let matches = 0;
    group.querySelectorAll(".option-row").forEach((row) => {
      const label = row.querySelector(".option-label")?.textContent.toLowerCase() ?? "";
      const hit = !needle || label.includes(needle);
      row.classList.toggle("is-hidden", !hit);
      if (hit) {
        matches += 1;
      }
    });
    group.classList.toggle("is-hidden", matches === 0);
    if (needle) {
      group.open = matches > 0;
    }
  });
}

function setAutoGenerate(enabled) {
  autoGenerate = enabled;
  if (!enabled) {
    cancelAutoGenerate();
  }
  setGenerateState();
  setStatus(enabled ? "Auto Generate enabled." : "Auto Generate disabled.");
}

function cancelAutoGenerate() {
  clearTimeout(autoTimer);
  autoTimer = null;
  pendingAutoGenerate = false;
}

function scheduleAutoGenerate(delay = 650) {
  if (!autoGenerate || !ready || !currentSchema().trim()) {
    return;
  }
  clearTimeout(autoTimer);
  autoTimer = setTimeout(() => requestGenerate("auto"), delay);
}

async function refreshCliOptions() {
  if (!ready) {
    return;
  }
  const requestId = ++cliRequestId;
  cliOptionsDirty = true;
  setGenerateState();
  const [commandText, tomlText] = await Promise.all([
    worker.buildCliOptions(collectOptionEntries(), currentInputType()),
    worker.exportConfigToml(collectOptionEntries(), currentInputType()),
  ]);
  if (requestId === cliRequestId) {
    cliCommandText = commandText;
    configToml = tomlText;
    cliOptionsDirty = false;
    setGenerateState();
  }
}

function openConfigDialog() {
  const dialog = document.querySelector("#config-dialog");
  const textarea = document.querySelector("#config-toml");
  if (!dialog || !textarea) {
    return;
  }
  textarea.value = configToml;
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
  textarea.focus();
}

function closeConfigDialog() {
  const dialog = document.querySelector("#config-dialog");
  if (!dialog) {
    return;
  }
  if (typeof dialog.close === "function") {
    dialog.close();
  } else {
    dialog.removeAttribute("open");
  }
}

function clearOptionControls() {
  document.querySelectorAll("[data-option]").forEach((control) => {
    if (control.type === "checkbox") {
      control.checked = false;
    } else {
      control.value = "";
    }
  });
}

function applyImportedOptions(result) {
  if (result.inputType) {
    const inputType = document.querySelector("#input-type");
    if (inputType) {
      inputType.value = result.inputType;
      updateInputFormatState();
    }
  }
  clearOptionControls();
  Object.entries(result.options || {}).forEach(([key, value]) => {
    const control = document.querySelector(`[data-option="${CSS.escape(key)}"]`);
    if (!control) {
      return;
    }
    if (control.type === "checkbox") {
      control.checked = Boolean(value);
    } else if (Array.isArray(value)) {
      control.value = value.join("\n");
    } else {
      control.value = String(value);
    }
    control.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function finishGeneration() {
  running = false;
  activeGenerationMode = "manual";
  setGenerateState();
  if (pendingAutoGenerate) {
    pendingAutoGenerate = false;
    scheduleAutoGenerate(120);
  }
}

async function requestGenerate(mode = "manual") {
  if (!ready) {
    return;
  }
  if (running) {
    if (mode === "auto") {
      pendingAutoGenerate = true;
    }
    return;
  }
  if (!currentSchema().trim()) {
    if (mode === "manual") {
      setStatus("Input is empty.", true);
    }
    return;
  }

  running = true;
  activeGenerationMode = mode;
  if (mode === "manual") {
    renderOutput("", "python");
    document.querySelector("#copy").disabled = true;
  } else {
    setStatus("Auto generating...");
  }
  setGenerateState();

  try {
    const result = await worker.generate(currentSchema(), currentInputType(), collectOptionEntries());
    if (result.ok) {
      lastOutput = result.output;
      renderOutput(lastOutput, "python");
      document.querySelector("#copy").disabled = !lastOutput;
      setStatus(
        mode === "auto" ? "Auto generated with the built-in formatter." : "Generated with the built-in formatter.",
      );
    } else if (mode === "auto") {
      setStatus("Auto generation failed; keeping the last successful output.", true);
    } else {
      lastOutput = result.error;
      renderOutput(result.error, "python");
      document.querySelector("#copy").disabled = true;
      setStatus("Generation failed.", true);
    }
  } catch (error) {
    const message = error?.stack || String(error);
    if (mode === "auto") {
      setStatus("Auto generation failed; keeping the last successful output.", true);
    } else {
      lastOutput = message;
      renderOutput(message, "python");
      document.querySelector("#copy").disabled = true;
      setStatus("Generation failed.", true);
    }
  } finally {
    finishGeneration();
  }
}

function setGenerateState() {
  const button = document.querySelector("#generate");
  if (button) {
    button.disabled = !ready || running;
    button.textContent = running ? "Generating..." : "Generate";
  }
  const cliButton = document.querySelector("#copy-cli");
  if (cliButton) {
    cliButton.disabled = !ready || cliOptionsDirty;
  }
  const configButton = document.querySelector("#config");
  if (configButton) {
    configButton.disabled = !ready || cliOptionsDirty;
  }
  const autoButton = document.querySelector("#auto-generate");
  if (autoButton) {
    autoButton.disabled = !ready;
    autoButton.classList.toggle("is-active", autoGenerate);
    autoButton.setAttribute("aria-pressed", autoGenerate ? "true" : "false");
    autoButton.textContent = autoGenerate ? "Auto Generate: On" : "Auto Generate";
  }
}

function updateStatusTooltip() {
  const status = document.querySelector("#status");
  if (!status) {
    return;
  }
  // Reveal the full message on hover only when the text is visually truncated.
  status.title = status.scrollWidth > status.clientWidth ? status.textContent : "";
}

function setStatus(text, isError = false) {
  const status = document.querySelector("#status");
  if (!status) {
    return;
  }
  status.textContent = text;
  status.classList.toggle("error", isError);
  requestAnimationFrame(updateStatusTooltip);
}

async function initWorker() {
  const info = await worker.init(Comlink.proxy((message) => setStatus(message)));
  if (!appShellMounted) {
    mountRenderedShell(info.html);
  }
  ready = true;
  setStatus(`Ready: Pyodide ${info.pyodideVersion}, Python ${info.pythonVersion}, UI rendered by tdom`);
  setGenerateState();
  await refreshCliOptions();
  scheduleAutoGenerate(0);
}

rawWorker.addEventListener("error", (event) => {
  setStatus(event.message || "Worker failed.", true);
  finishGeneration();
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) {
    return;
  }
  const action = target.dataset.action;
  if (action === "generate") {
    requestGenerate("manual");
  } else if (action === "sample") {
    setInputValue(await worker.sample(currentInputType()));
    setStatus(`Loaded ${currentInputType()} sample.`);
    scheduleAutoGenerate();
  } else if (action === "clear-input") {
    setInputValue("");
    cancelAutoGenerate();
    setStatus("Cleared input.");
  } else if (action === "clear-output") {
    lastOutput = "";
    renderOutput("", "python");
    document.querySelector("#copy").disabled = true;
    setStatus("Cleared output.");
  } else if (action === "copy-cli") {
    await navigator.clipboard.writeText(cliCommandText);
    setStatus(cliCommandText ? "Copied CLI command." : "Copied empty CLI command.");
  } else if (action === "config") {
    openConfigDialog();
  } else if (action === "copy-config") {
    const textarea = document.querySelector("#config-toml");
    await navigator.clipboard.writeText(textarea?.value || configToml);
    setStatus("Copied pyproject.toml config.");
  } else if (action === "import-config") {
    const textarea = document.querySelector("#config-toml");
    const result = await worker.importConfigToml(textarea?.value || "");
    if (!result.ok) {
      setStatus(`Could not import pyproject.toml: ${result.error}`, true);
      return;
    }
    applyImportedOptions(result);
    await refreshCliOptions();
    closeConfigDialog();
    const ignored = result.ignored?.length ? ` Ignored: ${result.ignored.join(", ")}.` : "";
    setStatus(`Imported pyproject.toml config.${ignored}`);
    scheduleAutoGenerate();
  } else if (action === "close-config") {
    closeConfigDialog();
  } else if (action === "auto-generate") {
    setAutoGenerate(!autoGenerate);
    if (!autoGenerate) {
      return;
    }
    scheduleAutoGenerate(0);
  } else if (action === "toggle-header") {
    headerCompact = !headerCompact;
    setLayoutState();
  } else if (action === "toggle-workspace") {
    workspaceCollapsed = !workspaceCollapsed;
    setLayoutState();
  } else if (action === "copy" && lastOutput) {
    await navigator.clipboard.writeText(lastOutput);
    setStatus("Copied output.");
  }
});

mountInitialShell().catch((error) => {
  setStatus(error?.message || "Could not load the playground shell.", true);
});
initWorker().catch((error) => {
  setStatus(error?.stack || String(error), true);
});

window.addEventListener("resize", () => {
  syncStickyOffsets();
  refreshEditors();
  updateStatusTooltip();
});

document.addEventListener("change", (event) => {
  if (event.target.id === "input-type") {
    updateInputFormatState();
    refreshCliOptions();
    scheduleAutoGenerate();
  } else if (event.target.matches("[data-option]")) {
    refreshCliOptions();
    scheduleAutoGenerate();
  }
});

document.addEventListener("input", (event) => {
  if (event.target.id === "option-filter") {
    filterOptions(event.target.value);
    return;
  }
  if (event.target.id === "schema" || event.target.matches("[data-option]")) {
    if (event.target.matches("[data-option]")) {
      refreshCliOptions();
    }
    scheduleAutoGenerate();
  }
});
