from __future__ import annotations

import json
import traceback
from typing import TYPE_CHECKING, Any

from tdom import html

from datamodel_code_generator import InputFileType, generate

if TYPE_CHECKING:
    from string.templatelib import Template

SAMPLE_SCHEMA = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Pet",
  "type": "object",
  "properties": {
    "id": { "type": "integer" },
    "name": { "type": "string" },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["id", "name"]
}"""

SAMPLE_SCHEMAS = {
    "auto": SAMPLE_SCHEMA,
    "jsonschema": SAMPLE_SCHEMA,
    "openapi": """{
  "openapi": "3.1.0",
  "info": {
    "title": "Pet API",
    "version": "1.0.0"
  },
  "paths": {},
  "components": {
    "schemas": {
      "Pet": {
        "type": "object",
        "properties": {
          "id": { "type": "integer" },
          "name": { "type": "string" },
          "tags": {
            "type": "array",
            "items": { "type": "string" }
          }
        },
        "required": ["id", "name"]
      }
    }
  }
}""",
    "json": """{
  "id": 1,
  "name": "Milo",
  "tags": ["cat", "indoor"]
}""",
    "yaml": """id: 1
name: Milo
tags:
  - cat
  - indoor
""",
    "dict": """{
  "id": 1,
  "name": "Milo",
  "tags": ["cat", "indoor"]
}""",
    "csv": """id,name,age
1,Milo,3
2,Luna,2
""",
    "graphql": """type Pet {
  id: ID!
  name: String!
  tags: [String!]
}
""",
}

UI_METADATA: dict[str, Any] = {"formats": [], "options": [], "groups": []}
FORCED_OPTIONS = {
    "output": None,
}
SAFE_SHELL_CHARS = frozenset("_./:=,+@%-")


def set_ui_metadata(metadata_json: str) -> None:
    global UI_METADATA  # noqa: PLW0603
    UI_METADATA = json.loads(metadata_json)


def ActionButton(
    *,
    action: str,
    label: str,
    disabled: bool = False,
    children: Template = t"",
    **attrs: Any,
) -> Template:
    return t"""<button type="button" data-action="{action}" disabled={disabled} {attrs}>{label}{children}</button>"""


def InputTypeSelect(*, selected: str, children: Template = t"", **attrs: Any) -> Template:
    options = [
        t"""<option value="{item["value"]}" selected={item["value"] == selected} disabled={not item["browser_supported"]}>{item["label"]}</option>"""
        for item in UI_METADATA["formats"]
    ]
    return t"""
    <label class="input-type-control" {attrs}>
      Input
      <select id="input-type">{options}</select>
    </label>
    """


def Pane(
    *,
    title: str,
    action: str | None = None,
    action_label: str = "",
    extra: Template = t"",
    children: Template = t"",
) -> Template:
    action_button = t"""<{ActionButton} action="{action}" label="{action_label}" id="{action}" />""" if action else t""
    return t"""
    <div class="pane">
      <div class="pane-title">
        <span>{title}</span>
        <div class="pane-actions">{extra}{action_button}</div>
      </div>
      {children}
    </div>
    """


def OptionControl(*, option: dict[str, Any], children: Template = t"") -> Template:
    choices = option.get("choices") or []
    reason = option.get("unsupported_reason") or ""
    note = t"""<span class="option-note">{reason}</span>""" if reason else t""

    if option["control"] == "checkbox":
        control = t"""<input type="checkbox" name="{option["dest"]}" value="true" data-option="{option["dest"]}" />"""
    elif option["control"] == "boolean":
        control = t"""
        <select name="{option["dest"]}" data-option="{option["dest"]}">
          <option value="">Default</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
        """
    elif option["control"] == "select":
        control = t"""
        <select name="{option["dest"]}" data-option="{option["dest"]}">
          <option value="">Default</option>
          {[t'<option value="{choice}">{choice}</option>' for choice in choices]}
        </select>
        """
    elif option["control"] == "number":
        control = t"""<input type="number" name="{option["dest"]}" data-option="{option["dest"]}" />"""
    elif option["control"] == "list":
        control = t"""<textarea class="option-list" rows="2" name="{option["dest"]}" data-option="{option["dest"]}"></textarea>"""
    else:
        control = t"""<input type="text" name="{option["dest"]}" data-option="{option["dest"]}" />"""

    return t"""
    <label class="option-row option-control-{option["control"]}" title="{option["help"]}">
      <span class="option-label">
        <code>{option["name"]}</code>
        <span>{option["help"]}</span>
      </span>
      <span class="option-widget">{control}</span>
      {note}
    </label>
    """


def OptionGroup(*, group: dict[str, Any], open: bool = False, children: Template = t"") -> Template:
    options = [t"""<{OptionControl} option={option} />""" for option in group["options"] if not option.get("hidden")]
    if not options:
        return t""
    return t"""
    <details class="option-group" open={open}>
      <summary>
        <span>{group["category"]}</span>
        <span>{len(options)}</span>
      </summary>
      <div class="option-list-panel">{options}</div>
    </details>
    """


def OptionsPanel(*, groups: list[dict[str, Any]], children: Template = t"") -> Template:
    visible_count = sum(1 for option in UI_METADATA["options"] if not option.get("hidden"))
    rendered_groups = [
        t"""<{OptionGroup} group={group} open={index < 2} />"""
        for index, group in enumerate(groups)
        if any(not option.get("hidden") for option in group["options"])
    ]
    return t"""
    <section class="options-panel">
      <div class="options-head">
        <div>
          <h2>Options</h2>
          <span class="options-count">{visible_count} available</span>
        </div>
      </div>
      <form id="options-form">{rendered_groups}</form>
    </section>
    """


def App(
    *,
    schema: str,
    output: str,
    input_type: str,
    running: bool,
    status: str,
    children: Template = t"",
) -> Template:
    schema_actions = t"""
      <{InputTypeSelect} selected="{input_type}" />
      <{ActionButton} action="sample" label="Sample" id="sample" />
      <{ActionButton} action="clear-input" label="Clear" id="clear-input" />
    """
    output_actions = t"""
      <{ActionButton} action="copy" label="Copy" id="copy" />
      <{ActionButton} action="clear-output" label="Clear" id="clear-output" />
    """
    return t"""
    <main class="shell">
      <header class="topbar">
        <div class="topbar-title">
          <h1>
            <a href="https://github.com/koxudaxi/datamodel-code-generator" target="_blank" rel="noreferrer">datamodel-code-generator</a>
            <span>Browser</span>
          </h1>
          <p id="status">{status}</p>
          <p class="tech-note">
            UI rendered with <a href="https://github.com/t-strings/tdom" target="_blank" rel="noreferrer">tdom</a>
            using <a href="https://peps.python.org/pep-0750/" target="_blank" rel="noreferrer">PEP 750 t-strings</a>.
          </p>
        </div>
        <div class="controls">
          <{ActionButton} action="copy-cli" label="Copy CLI" id="copy-cli" disabled={True} />
          <{ActionButton} action="metadata" label="Copy Options JSON" id="metadata" disabled={True} />
          <{ActionButton} action="auto-generate" label="Auto Generate" id="auto-generate" disabled={True} />
          <{ActionButton} action="generate" label={(running and "Generating...") or "Generate"} disabled={running} id="generate" />
        </div>
      </header>

      <section class="workspace" aria-label="Generator workspace">
        <{Pane} title="Schema" extra={schema_actions}>
          <textarea id="schema" spellcheck="false">{schema}</textarea>
        </{Pane}>

        <{Pane} title="Output" extra={output_actions}>
          <pre id="output" aria-live="polite">{output}</pre>
        </{Pane}>
      </section>

      <{OptionsPanel} groups={UI_METADATA["groups"]} />
    </main>
    """


def default_input_type() -> str:
    for item in UI_METADATA["formats"]:
        if item["value"] == "jsonschema":
            return "jsonschema"
    return UI_METADATA["formats"][0]["value"] if UI_METADATA["formats"] else "jsonschema"


def render_app(
    schema: str = "",
    output: str = "",
    running: bool = False,
    input_type: str = "",
    status: str = "Loading Pyodide runtime...",
) -> str:
    return html(
        t"""<{App}
  schema={schema or SAMPLE_SCHEMA}
  output={output}
  input-type={input_type or default_input_type()}
  running={running}
  status={status}
 />"""
    )


def sample_schema(input_type: str = "") -> str:
    return SAMPLE_SCHEMAS.get(input_type or default_input_type(), SAMPLE_SCHEMA)


def export_ui_options() -> str:
    return json.dumps(UI_METADATA, ensure_ascii=False)


def _coerce_option_value(option: dict[str, Any], value: Any) -> Any:
    if value == "" or value is None or value == []:
        return None

    control = option["control"]
    result: Any = value
    if control in {"checkbox", "boolean"}:
        if value is True or value == "true":
            result = True
        elif value is False or value == "false":
            result = False
        else:
            result = None
    elif control == "list":
        if isinstance(value, list):
            result = value
        else:
            result = [item.strip() for item in str(value).replace(",", "\n").splitlines() if item.strip()]
    elif control == "number":
        text = str(value)
        result = float(text) if "." in text else int(text)
    return result


def _normalize_options(options: dict[str, Any], *, include_forced: bool = True) -> dict[str, Any]:
    options_by_dest = {option["dest"]: option for option in UI_METADATA["options"] if option["browser_supported"]}
    normalized: dict[str, Any] = {}
    for key, value in options.items():
        option = options_by_dest.get(key)
        if not option:
            continue
        normalized_value = _coerce_option_value(option, value)
        if normalized_value is None or normalized_value == []:
            continue
        normalized[key] = normalized_value
    if include_forced:
        normalized.update(FORCED_OPTIONS)
    return normalized


def _shell_quote(value: Any) -> str:
    text = str(value)
    if text and all(character.isalnum() or character in SAFE_SHELL_CHARS for character in text):
        return text
    return "'" + text.replace("'", "'\"'\"'") + "'"


def build_cli_options(options_json: str = "{}", input_type: str = "") -> str:
    options = json.loads(options_json) if options_json else {}
    normalized_options = _normalize_options(options, include_forced=False)
    options_by_dest = {option["dest"]: option for option in UI_METADATA["options"]}
    pieces: list[Any] = []

    if input_type and input_type != "auto":
        pieces.extend(["--input-file-type", input_type])

    for key, value in normalized_options.items():
        option = options_by_dest.get(key)
        if not option or not option.get("name"):
            continue
        if value is True:
            pieces.append(option["name"])
        elif value is False:
            pieces.extend(
                [option.get("negative_name") or option["name"], None if option.get("negative_name") else "false"]
            )
        elif isinstance(value, list):
            pieces.extend([option["name"], *value])
        else:
            pieces.extend([option["name"], value])

    return " ".join(_shell_quote(piece) for piece in pieces if piece is not None)


def generate_in_browser(schema: str, input_type: str, options_json: str = "{}") -> str:
    try:
        options = json.loads(options_json) if options_json else {}
        result = generate(
            schema,
            input_file_type=InputFileType(input_type),
            **_normalize_options(options),
            disable_timestamp=True,
        )
    except Exception:
        return json.dumps({"ok": False, "error": traceback.format_exc()})

    if isinstance(result, dict):
        sections = []
        for path, content in sorted(result.items()):
            name = "/".join(path) if isinstance(path, tuple) else str(path)
            sections.append(f"# file: {name}\n{content}")
        result = "\n\n".join(sections)
    return json.dumps({"ok": True, "output": result or ""})
