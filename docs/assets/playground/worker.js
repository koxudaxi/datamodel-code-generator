import { expose } from "https://cdn.jsdelivr.net/npm/comlink@4.4.2/dist/esm/comlink.mjs";
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.0a2/full/pyodide.mjs";

const PYODIDE_VERSION = "314.0.0-alpha.2";
const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v314.0.0a2/full/";
const PYPI_JSON_BASE = "https://pypi.org/pypi";
const MICROPIP_VERSION = "0.11.1";
const PYTHON_RUNTIME_PACKAGES = [
  "genson>=1.2.1,<2",
  "graphql-core>=3.2.3",
  "inflect>=4.1,<8",
  "jinja2>=2.10.1,<4",
  "pydantic>=2.12,<3",
  "pyyaml>=6.0.1",
  "tdom",
];

let pyodideReadyPromise = null;
let bootInfo = null;
let statusCallback = null;

function postStatus(message) {
  statusCallback?.(message);
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
  const metadataJson = await (await fetch("./generated/codegen-ui-metadata.json")).text();
  const metadata = JSON.parse(metadataJson);

  postStatus("Loading Pyodide...");
  const pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });

  postStatus("Loading micropip...");
  const micropipWheel = await findWheelUrl("micropip", MICROPIP_VERSION, (filename) =>
    filename.endsWith("-py3-none-any.whl"),
  );
  await pyodide.loadPackage(micropipWheel);

  postStatus("Installing generator runtime from PyPI...");
  await pyodide.runPythonAsync(`
import micropip
await micropip.install(${JSON.stringify(PYTHON_RUNTIME_PACKAGES)})
`);

  const packageSource = metadata.package_wheel
    ? `./generated/${metadata.package_wheel}`
    : "datamodel-code-generator";
  postStatus("Installing datamodel-code-generator...");
  pyodide.globals.set("package_source", packageSource);
  await pyodide.runPythonAsync(`
import micropip
await micropip.install(package_source, deps=False)
`);
  pyodide.globals.delete("package_source");

  const appSource = await (await fetch("./app.py")).text();
  pyodide.runPython(appSource);
  pyodide.globals.get("set_ui_metadata")(metadataJson);

  bootInfo = {
    html: pyodide.globals.get("render_app")(),
    metadataJson,
    pyodideVersion: PYODIDE_VERSION,
    pythonVersion: pyodide.runPython("import sys; sys.version.split()[0]"),
  };
  return pyodide;
}

async function ensurePyodide(onStatus = null) {
  statusCallback = onStatus;
  pyodideReadyPromise ??= initPyodide();
  return pyodideReadyPromise;
}

const api = {
  async init(onStatus) {
    await ensurePyodide(onStatus);
    return bootInfo;
  },

  async sample(inputType) {
    const pyodide = await ensurePyodide();
    return pyodide.globals.get("sample_schema")(inputType || "");
  },

  async buildCliOptions(options, inputType) {
    const pyodide = await ensurePyodide();
    return pyodide.globals.get("build_cli_options")(JSON.stringify(options || {}), inputType || "");
  },

  async exportConfigToml(options, inputType) {
    const pyodide = await ensurePyodide();
    return pyodide.globals.get("export_config_toml")(JSON.stringify(options || {}), inputType || "");
  },

  async importConfigToml(configToml) {
    const pyodide = await ensurePyodide();
    return JSON.parse(pyodide.globals.get("import_config_toml")(configToml || ""));
  },

  async generate(schema, inputType, options) {
    const pyodide = await ensurePyodide();
    const resultJson = pyodide.globals.get("generate_in_browser")(
      schema,
      inputType,
      JSON.stringify(options || {}),
    );
    return JSON.parse(resultJson);
  },
};

expose(api);
