import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.0a2/full/pyodide.mjs";

const PYODIDE_VERSION = "314.0.0-alpha.2";
const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v314.0.0a2/full/";
const PYPI_JSON_BASE = "https://pypi.org/pypi";
const MICROPIP_VERSION = "0.11.1";

let pyodideReadyPromise;

function postStatus(message) {
  self.postMessage({ type: "status", message });
}

async function findWheelUrl(project, version, matcher) {
  const response = await fetch(`${PYPI_JSON_BASE}/${project}/${version}/json`);
  if (!response.ok) {
    throw new Error(`Could not load PyPI metadata for ${project} ${version}: ${response.status}`);
  }
  const metadata = await response.json();
  const wheel = metadata.urls.find((item) => item.packagetype === "bdist_wheel" && matcher(item.filename));
  if (!wheel) {
    throw new Error(`No compatible wheel found for ${project} ${version}`);
  }
  return wheel.url;
}

async function initPyodide() {
  postStatus("Loading Pyodide...");
  const pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });

  postStatus("Loading micropip...");
  const micropipWheel = await findWheelUrl("micropip", MICROPIP_VERSION, (filename) =>
    filename.endsWith("-py3-none-any.whl"),
  );
  await pyodide.loadPackage(micropipWheel);

  postStatus("Installing generator and tdom from PyPI...");
  await pyodide.runPythonAsync(`
import micropip
await micropip.install([
    "datamodel-code-generator[graphql]",
    "tdom",
])
`);

  const appSource = await (await fetch("./app.py")).text();
  const metadataJson = await (await fetch("./generated/codegen-ui-metadata.json")).text();
  pyodide.runPython(appSource);
  pyodide.globals.get("set_ui_metadata")(metadataJson);

  self.postMessage({
    type: "render",
    html: pyodide.globals.get("render_app")("", "", false),
  });
  self.postMessage({
    type: "metadata",
    json: metadataJson,
  });
  self.postMessage({
    type: "ready",
    pyodideVersion: PYODIDE_VERSION,
    pythonVersion: pyodide.runPython("import sys; sys.version.split()[0]"),
  });
  return pyodide;
}

pyodideReadyPromise = initPyodide().catch((error) => {
  self.postMessage({ type: "error", error: error?.stack || String(error) });
  throw error;
});

self.addEventListener("message", async (event) => {
  const message = event.data;
  try {
    const pyodide = await pyodideReadyPromise;
    if (message.type === "sample") {
      self.postMessage({
        type: "sample",
        schema: pyodide.globals.get("sample_schema")(message.inputType || ""),
      });
      return;
    }
    if (message.type === "cli") {
      const text = pyodide.globals.get("build_cli_options")(
        JSON.stringify(message.options || {}),
        message.inputType || "",
      );
      self.postMessage({ type: "cli", requestId: message.requestId, text });
      return;
    }
    if (message.type !== "generate") {
      return;
    }
    const resultJson = pyodide.globals.get("generate_in_browser")(
      message.schema,
      message.inputType,
      JSON.stringify(message.options || {}),
    );
    const result = JSON.parse(resultJson);
    if (result.ok) {
      self.postMessage({ type: "result", output: result.output });
    } else {
      self.postMessage({ type: "error", error: result.error });
    }
  } catch (error) {
    self.postMessage({ type: "error", error: error?.stack || String(error) });
  }
});
