import {
  getInputValue,
  mountInputEditor,
  mountOutputViewer,
  setInputLanguage,
  setInputValue,
  setOutputValue,
} from "./editor.js";

const appEl = document.querySelector("#app");

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

const worker = new Worker("./worker.js", { type: "module" });

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

function collectOptions() {
  const options = {};
  for (const control of document.querySelectorAll("[data-option]")) {
    if (control.disabled) {
      continue;
    }
    const key = control.dataset.option;
    if (control.type === "checkbox") {
      if (control.checked) {
        options[key] = true;
      }
      continue;
    }
    let value = control.value;
    if (!value) {
      continue;
    }
    if (control.tagName === "TEXTAREA") {
      value = value
        .split(/\r?\n|,/)
        .map((item) => item.trim())
        .filter(Boolean);
      if (value.length === 0) {
        continue;
      }
    } else if (control.type === "number") {
      value = Number(value);
    } else if (value === "true") {
      value = true;
    } else if (value === "false") {
      value = false;
    }
    options[key] = value;
  }
  return options;
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

function refreshCliOptions() {
  if (!ready) {
    return;
  }
  cliOptionsDirty = true;
  setGenerateState();
  worker.postMessage({
    type: "cli",
    requestId: ++cliRequestId,
    inputType: currentInputType(),
    options: collectOptions(),
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

function requestGenerate(mode = "manual") {
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
  worker.postMessage({
    type: "generate",
    schema: currentSchema(),
    inputType: currentInputType(),
    options: collectOptions(),
  });
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

worker.addEventListener("message", (event) => {
  const message = event.data;
  if (message.type === "render") {
    const existingSchema = currentSchema();
    appShellMounted = true;
    appEl.innerHTML = message.html;
    if (existingSchema) {
      const schema = document.querySelector("#schema");
      if (schema) {
        schema.value = existingSchema;
      }
    }
    updateInputFormatState();
    mountEditor();
    if (ready) {
      setStatus("Ready: UI rendered by tdom.");
    }
    setGenerateState();
    return;
  }
  if (message.type === "ready") {
    ready = true;
    setStatus(`Ready: Pyodide ${message.pyodideVersion}, Python ${message.pythonVersion}, UI rendered by tdom`);
    setGenerateState();
    refreshCliOptions();
    return;
  }
  if (message.type === "metadata") {
    metadataJson = message.json;
    setGenerateState();
    return;
  }
  if (message.type === "cli") {
    if (message.requestId === cliRequestId) {
      cliOptionsText = message.text;
      cliOptionsDirty = false;
      setGenerateState();
    }
    return;
  }
  if (message.type === "sample") {
    setInputValue(message.schema);
    setStatus(`Loaded ${currentInputType()} sample.`);
    return;
  }
  if (message.type === "status") {
    setStatus(message.message);
    return;
  }
  if (message.type === "result") {
    const mode = activeGenerationMode;
    lastOutput = message.output;
    renderOutput(lastOutput, "python");
    document.querySelector("#copy").disabled = !lastOutput;
    setStatus(mode === "auto" ? "Auto generated with the built-in formatter." : "Generated with the built-in formatter.");
    finishGeneration();
    return;
  }
  if (message.type === "error") {
    if (activeGenerationMode === "auto") {
      setStatus("Auto generation failed; keeping the last successful output.", true);
    } else {
      lastOutput = message.error;
      renderOutput(message.error, "python");
      document.querySelector("#copy").disabled = true;
      setStatus("Generation failed.", true);
    }
    finishGeneration();
  }
});

worker.addEventListener("error", (event) => {
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
    worker.postMessage({ type: "sample", inputType: currentInputType() });
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
