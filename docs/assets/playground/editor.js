import { basicSetup, EditorView } from "https://cdn.jsdelivr.net/npm/codemirror@6.0.2/+esm";
import { HighlightStyle, syntaxHighlighting } from "https://cdn.jsdelivr.net/npm/@codemirror/language@6.11.1/+esm";
import { EditorState } from "https://cdn.jsdelivr.net/npm/@codemirror/state@6.5.2/+esm";
import { json } from "https://cdn.jsdelivr.net/npm/@codemirror/lang-json@6.0.2/+esm";
import { python } from "https://cdn.jsdelivr.net/npm/@codemirror/lang-python@6.2.1/+esm";
import { xml } from "https://cdn.jsdelivr.net/npm/@codemirror/lang-xml@6.1.0/+esm";
import { yaml } from "https://cdn.jsdelivr.net/npm/@codemirror/lang-yaml@6.1.3/+esm";
import { tags } from "https://cdn.jsdelivr.net/npm/@lezer/highlight@1.2.3/+esm";

let inputEditor = null;
let outputEditor = null;

const editorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "13px",
    backgroundColor: "#f6f8fb",
  },
  ".cm-scroller": {
    fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace',
    lineHeight: "1.5",
  },
  ".cm-content": {
    padding: "16px",
  },
  ".cm-gutters": {
    backgroundColor: "#edf2f7",
    color: "#6b7480",
    borderRight: "1px solid #d7dde6",
  },
  "&.cm-focused": {
    outline: "none",
  },
});

const playgroundHighlight = HighlightStyle.define([
  { tag: tags.keyword, color: "#7c3aed", fontWeight: "650" },
  { tag: [tags.atom, tags.bool], color: "#b4236a", fontWeight: "650" },
  { tag: tags.number, color: "#a16207" },
  { tag: tags.string, color: "#0f766e" },
  { tag: [tags.propertyName, tags.definition(tags.propertyName)], color: "#0b6bcb", fontWeight: "650" },
  { tag: tags.variableName, color: "#17202c" },
  { tag: [tags.definition(tags.variableName), tags.typeName, tags.className], color: "#0b6bcb", fontWeight: "650" },
  { tag: tags.comment, color: "#687385", fontStyle: "italic" },
  { tag: [tags.operator, tags.punctuation], color: "#5d6878" },
]);

function languageExtension(language) {
  switch ((language || "").toLowerCase()) {
    case "json":
    case "jsonschema":
    case "openapi":
    case "asyncapi":
      return json();
    case "yaml":
    case "avro":
      return yaml();
    case "xmlschema":
      return xml();
    case "python":
      return python();
    case "graphql":
      return [];
    default:
      return json();
  }
}

function editorExtensions(language, onChange = null, readOnly = false) {
  const extensions = [
    basicSetup,
    languageExtension(language),
    editorTheme,
    syntaxHighlighting(playgroundHighlight),
  ];
  if (readOnly) {
    extensions.push(EditorState.readOnly.of(true), EditorView.editable.of(false));
  }
  if (onChange) {
    extensions.push(
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          onChange(update.state.doc.toString());
        }
      }),
    );
  }
  return extensions;
}

export function mountInputEditor(textarea, language) {
  if (inputEditor && document.body.contains(inputEditor.dom)) {
    return;
  }
  inputEditor?.destroy();
  inputEditor = null;
  if (!textarea) {
    return;
  }
  const mount = document.createElement("div");
  mount.className = "editor-mount";
  textarea.classList.add("is-hidden");
  textarea.after(mount);
  inputEditor = new EditorView({
    parent: mount,
    state: EditorState.create({
      doc: textarea.value,
      extensions: editorExtensions(language, (value) => {
        textarea.value = value;
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      }),
    }),
  });
}

export function getInputValue() {
  return inputEditor?.state.doc.toString() ?? document.querySelector("#schema")?.value ?? "";
}

export function setInputValue(value) {
  const textarea = document.querySelector("#schema");
  if (textarea) {
    textarea.value = value;
  }
  if (inputEditor) {
    inputEditor.dispatch({
      changes: { from: 0, to: inputEditor.state.doc.length, insert: value },
    });
  }
}

export function setInputLanguage(language) {
  const value = getInputValue();
  inputEditor?.destroy();
  inputEditor = null;
  document.querySelector(".editor-mount")?.remove();
  const textarea = document.querySelector("#schema");
  if (!textarea) {
    return;
  }
  textarea.classList.remove("is-hidden");
  textarea.value = value;
  mountInputEditor(textarea, language);
}

export function mountOutputViewer(output, value = "", language = "python") {
  if (outputEditor && document.body.contains(outputEditor.dom)) {
    return;
  }
  outputEditor?.destroy();
  outputEditor = null;
  if (!output) {
    return;
  }
  const mount = document.createElement("div");
  mount.className = "output-editor-mount";
  output.classList.add("is-hidden");
  output.after(mount);
  outputEditor = new EditorView({
    parent: mount,
    state: EditorState.create({
      doc: value,
      extensions: editorExtensions(language, null, true),
    }),
  });
}

export function setOutputValue(value, language = "python") {
  const output = document.querySelector("#output");
  if (output) {
    output.textContent = value;
  }
  outputEditor?.destroy();
  outputEditor = null;
  document.querySelector(".output-editor-mount")?.remove();
  output?.classList.remove("is-hidden");
  mountOutputViewer(output, value, language);
}
