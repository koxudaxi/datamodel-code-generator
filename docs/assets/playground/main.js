import * as Comlink from "https://cdn.jsdelivr.net/npm/comlink@4.4.2/dist/esm/comlink.mjs";
import morphdom from "https://cdn.jsdelivr.net/npm/morphdom@2.7.7/+esm";

import {
  getInputValue,
  mountInputEditor,
  mountOutputViewer,
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
let metadataJson = "";
let autoGenerate = false;
let autoTimer = null;
let pendingAutoGenerate = false;
let activeGenerationMode = "manual";
let cliOptionsText = "";
let cliOptionsDirty = true;
let cliRequestId = 0;
let appShellMounted = false;

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
  appShellMounted = true;
  updateInputFormatState();
  mountEditor();
}

function mountRenderedShell(html) {
  const existingSchema = currentSchema();
  const template = document.createElement("template");
  template.innerHTML = html;
  const nextShell = template.content.firstElementChild;
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
  setGenerateState();
}

function collectOptionEntries() {
  const form = document.querySelector("#options-form");
  return form ? Object.fromEntries(new FormData(form).entries()) : {};
}

function setAutoGenerate(enabled) {
  autoGenerate = enabled;
  if (!enabled) {
    clearTimeout(autoTimer);
    pendingAutoGenerate = false;
  }
  setGenerateState();
  setStatus(enabled ? "Auto Generate enabled." : "Auto Generate disabled.");
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
  const text = await worker.buildCliOptions(collectOptionEntries(), currentInputType());
  if (requestId === cliRequestId) {
    cliOptionsText = text;
    cliOptionsDirty = false;
    setGenerateState();
  }
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
  const metadataButton = document.querySelector("#metadata");
  if (metadataButton) {
    metadataButton.disabled = !metadataJson;
  }
  const autoButton = document.querySelector("#auto-generate");
  if (autoButton) {
    autoButton.disabled = !ready;
    autoButton.classList.toggle("is-active", autoGenerate);
    autoButton.setAttribute("aria-pressed", autoGenerate ? "true" : "false");
    autoButton.textContent = autoGenerate ? "Auto Generate: On" : "Auto Generate";
  }
}

function setStatus(text, isError = false) {
  const status = document.querySelector("#status");
  if (!status) {
    return;
  }
  status.textContent = text;
  status.classList.toggle("error", isError);
}

async function initWorker() {
  const info = await worker.init(Comlink.proxy((message) => setStatus(message)));
  mountRenderedShell(info.html);
  metadataJson = info.metadataJson;
  ready = true;
  setStatus(`Ready: Pyodide ${info.pyodideVersion}, Python ${info.pythonVersion}, UI rendered by tdom`);
  setGenerateState();
  await refreshCliOptions();
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
  } else if (action === "clear-input") {
    setInputValue("");
    setStatus("Cleared input.");
  } else if (action === "clear-output") {
    lastOutput = "";
    renderOutput("", "python");
    document.querySelector("#copy").disabled = true;
    setStatus("Cleared output.");
  } else if (action === "copy-cli") {
    await navigator.clipboard.writeText(cliOptionsText);
    setStatus(cliOptionsText ? "Copied CLI options." : "Copied empty CLI options.");
  } else if (action === "auto-generate") {
    setAutoGenerate(!autoGenerate);
    if (!autoGenerate) {
      return;
    }
    scheduleAutoGenerate(0);
  } else if (action === "metadata") {
    await navigator.clipboard.writeText(metadataJson);
    setStatus("Copied options metadata JSON.");
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
  if (event.target.id === "schema" || event.target.matches("[data-option]")) {
    if (event.target.matches("[data-option]")) {
      refreshCliOptions();
    }
    scheduleAutoGenerate();
  }
});
