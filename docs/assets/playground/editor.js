import {
  bracketMatching,
  foldGutter,
  HighlightStyle,
  indentOnInput,
  syntaxHighlighting,
} from "@codemirror/language";
import { EditorState } from "@codemirror/state";
import {
  crosshairCursor,
  drawSelection,
  dropCursor,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  highlightSpecialChars,
  lineNumbers,
  rectangularSelection,
} from "@codemirror/view";
import { json } from "@codemirror/lang-json";
import { python } from "@codemirror/lang-python";
import { xml } from "@codemirror/lang-xml";
import { yaml } from "@codemirror/lang-yaml";
import { tags } from "@lezer/highlight";

let inputEditor = null;
let outputEditor = null;

const editorTheme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "13px",
    backgroundColor: "#171c23",
    color: "#eef4fb",
  },
  ".cm-scroller": {
    fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace',
    lineHeight: "1.5",
  },
  ".cm-content": {
    padding: "16px",
  },
  ".cm-gutters": {
    backgroundColor: "#20252e",
    color: "#8a96a8",
    borderRight: "1px solid #303845",
  },
  ".cm-activeLine": {
    backgroundColor: "#202a35",
  },
  ".cm-activeLineGutter": {
    backgroundColor: "#26313d",
  },
  ".cm-selectionBackground, &.cm-focused .cm-selectionBackground": {
    backgroundColor: "#064f99",
  },
  ".cm-cursor": {
    borderLeftColor: "#eef4fb",
  },
  "&.cm-focused": {
    outline: "none",
  },
});

const playgroundHighlight = HighlightStyle.define([
  { tag: tags.keyword, color: "#b39ddb", fontWeight: "650" },
  { tag: tags.atom, color: "#f06292", fontWeight: "650" },
  { tag: tags.bool, color: "#f06292", fontWeight: "650" },
  { tag: tags.number, color: "#ffca28" },
  { tag: tags.string, color: "#80cbc4" },
  { tag: tags.propertyName, color: "#4fc3f7", fontWeight: "650" },
  { tag: tags.definition(tags.propertyName), color: "#4fc3f7", fontWeight: "650" },
  { tag: tags.variableName, color: "#eef4fb" },
  { tag: tags.definition(tags.variableName), color: "#4fc3f7", fontWeight: "650" },
  { tag: tags.typeName, color: "#4fc3f7", fontWeight: "650" },
  { tag: tags.className, color: "#4fc3f7", fontWeight: "650" },
  { tag: tags.comment, color: "#8a96a8", fontStyle: "italic" },
  { tag: tags.operator, color: "#a7b1bf" },
  { tag: tags.punctuation, color: "#a7b1bf" },
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
    lineNumbers(),
    highlightActiveLineGutter(),
    highlightSpecialChars(),
    foldGutter(),
    drawSelection(),
    dropCursor(),
    EditorState.allowMultipleSelections.of(true),
    indentOnInput(),
    bracketMatching(),
    rectangularSelection(),
    crosshairCursor(),
    highlightActiveLine(),
    EditorView.lineWrapping,
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
