"""Generate preset documentation and preset-powered quick-start examples.

Usage:
    python scripts/build_preset_docs.py
    python scripts/build_preset_docs.py --check
    python scripts/build_preset_docs.py --format json
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
DOCS_PATH = ROOT / "docs" / "presets.md"
DOCS_INDEX_PATH = ROOT / "docs" / "index.md"
README_PATH = ROOT / "README.md"
SRC_PATH = ROOT / "src"
PRESET_NAMES_PATH = SRC_PATH / "datamodel_code_generator" / "preset_names.py"
QUICK_START_SCHEMA_PATH = ROOT / "tests" / "data" / "jsonschema" / "tutorial_pet.json"
QUICK_START_SCHEMA_NAME = "schema.json"
QUICK_START_OUTPUT_NAME = "model.py"
QUICK_START_TARGET_PYTHON_VERSION = "3.12"
QUICK_START_GENERATION_TIMEOUT_SECONDS = 30
PRESET_VERSION_DATE_LENGTH = 8
QUICK_START_BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED PRESET QUICK START -->"
QUICK_START_END_MARKER = "<!-- END AUTO-GENERATED PRESET QUICK START -->"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from datamodel_code_generator.preset import get_preset_names, render_presets  # noqa: E402

PresetDocsFormat = Literal["markdown", "json"]


@dataclass(frozen=True, slots=True)
class GeneratedDoc:
    """Generated file content."""

    path: Path
    content: str


def build_docs(*, check: bool) -> int:
    """Generate or check preset documentation outputs."""
    preset_names_doc = GeneratedDoc(PRESET_NAMES_PATH, _render_preset_names_module())
    if check:
        if not _doc_is_current(preset_names_doc):
            _print_out_of_date((preset_names_doc.path,))
            return 1
    else:
        preset_names_doc.path.write_text(preset_names_doc.content, encoding="utf-8")

    docs = _generate_docs(preset_names_doc)
    if not check:
        for doc in docs:
            doc.path.write_text(doc.content, encoding="utf-8")
        return 0

    out_of_date = [doc.path for doc in docs if not _doc_is_current(doc)]
    if not out_of_date:
        return 0

    _print_out_of_date(tuple(out_of_date))
    return 1


def _doc_is_current(doc: GeneratedDoc) -> bool:
    return doc.path.exists() and doc.path.read_text(encoding="utf-8") == doc.content


def _print_out_of_date(paths: tuple[Path, ...]) -> None:
    for path in paths:
        print(f"Preset docs are out of date: {path.relative_to(ROOT)}", file=sys.stderr)
    print("Run 'python scripts/build_preset_docs.py' to update.", file=sys.stderr)


def _generate_docs(preset_names_doc: GeneratedDoc) -> tuple[GeneratedDoc, ...]:
    standard_preset_name = _get_latest_preset_name_by_prefix(
        "standard",
        target_python_version=QUICK_START_TARGET_PYTHON_VERSION,
    )
    practical_preset_name = _get_latest_preset_name_by_prefix(
        "practical",
        target_python_version=QUICK_START_TARGET_PYTHON_VERSION,
    )
    standard_model_output = _generate_quick_start_model(standard_preset_name)
    practical_model_output = _generate_quick_start_model(practical_preset_name)
    return (
        preset_names_doc,
        GeneratedDoc(DOCS_PATH, render_presets("markdown")),
        GeneratedDoc(
            README_PATH,
            _replace_quick_start_section(
                README_PATH.read_text(encoding="utf-8"),
                _render_readme_quick_start(
                    standard_preset_name,
                    standard_model_output,
                    practical_preset_name,
                    practical_model_output,
                ),
            ),
        ),
        GeneratedDoc(
            DOCS_INDEX_PATH,
            _replace_quick_start_section(
                DOCS_INDEX_PATH.read_text(encoding="utf-8"),
                _render_docs_index_quick_start(
                    standard_preset_name,
                    standard_model_output,
                    practical_preset_name,
                    practical_model_output,
                ),
            ),
        ),
    )


def _get_latest_preset_name_by_prefix(prefix: str, *, target_python_version: str) -> str:
    target = target_python_version.replace(".", "")
    prefix_with_separator = f"{prefix}-py{target}-"
    matching_names = tuple(name for name in get_preset_names() if name.startswith(prefix_with_separator))
    if not matching_names:  # pragma: no cover
        msg = f"No built-in preset starts with {prefix_with_separator!r}"
        raise RuntimeError(msg)
    return max(matching_names, key=_preset_version_sort_key)


def _preset_version_sort_key(name: str) -> tuple[str, str]:
    prefix, separator, version = name.rpartition("-")
    if separator and version.isdecimal():
        return prefix, version
    return name, ""  # pragma: no cover


def _render_preset_names_module() -> str:
    preset_names = get_preset_names()
    if len(preset_names) == 1:
        names_literal = f'("{preset_names[0]}",)'
    else:
        names = "\n".join(f'    "{name}",' for name in preset_names)
        names_literal = f"(\n{names}\n)"
    return f'''"""Generated built-in preset names for CLI choices.

Generated by scripts/build_preset_docs.py. Do not edit manually.
"""

from __future__ import annotations

PRESET_NAMES: tuple[str, ...] = {names_literal}
'''


def _replace_quick_start_section(markdown_text: str, generated: str) -> str:
    start = markdown_text.find(QUICK_START_BEGIN_MARKER)
    end = markdown_text.find(QUICK_START_END_MARKER)
    if start == -1 or end == -1 or end < start:
        msg = f"Could not find quick-start markers: {QUICK_START_BEGIN_MARKER} / {QUICK_START_END_MARKER}"
        raise ValueError(msg)
    return (
        markdown_text[: start + len(QUICK_START_BEGIN_MARKER)] + "\n" + generated.rstrip() + "\n" + markdown_text[end:]
    )


def _quick_start_args(preset_name: str) -> tuple[str, ...]:
    return (
        "--input",
        QUICK_START_SCHEMA_NAME,
        "--input-file-type",
        "jsonschema",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--preset",
        preset_name,
        "--output",
        QUICK_START_OUTPUT_NAME,
    )


def _render_quick_start_command(preset_name: str) -> str:
    return _render_shell_command(("datamodel-codegen", *_quick_start_args(preset_name)))


def _render_shell_command(command: tuple[str, ...]) -> str:
    lines: list[str] = []
    index = 0
    while index < len(command):
        token = command[index]
        if index == 0:
            argument = token
            index += 1
        elif index + 1 < len(command) and token.startswith("-") and not command[index + 1].startswith("-"):
            argument = f"{token} {command[index + 1]}"
            index += 2
        else:
            argument = token
            index += 1

        indent = "" if not lines else "  "
        continuation = " \\" if index < len(command) else ""
        lines.append(f"{indent}{argument}{continuation}")
    return "\n".join(lines)


def _generate_quick_start_model(preset_name: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / QUICK_START_SCHEMA_NAME).write_text(
            QUICK_START_SCHEMA_PATH.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = _prepend_path(env.get("PYTHONPATH"), SRC_PATH)
        env["PYTHONWARNINGS"] = _prepend_warning_filter(env.get("PYTHONWARNINGS"))
        command = (sys.executable, "-m", "datamodel_code_generator", *_quick_start_args(preset_name))
        try:
            result = subprocess.run(
                command,
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=QUICK_START_GENERATION_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            _print_process_output(exc.stdout, exc.stderr)
            msg = (
                f"Timed out after {QUICK_START_GENERATION_TIMEOUT_SECONDS}s generating preset "
                f"quick-start example: {shlex.join(command)}"
            )
            raise RuntimeError(msg) from exc

        if result.returncode == 0:
            model_output = (tmp_path / QUICK_START_OUTPUT_NAME).read_text(encoding="utf-8").rstrip()
            return _normalize_quick_start_timestamp(model_output, preset_name)

        _print_process_output(result.stdout, result.stderr)
        msg = f"Failed to generate preset quick-start example (exit {result.returncode}): {shlex.join(command)}"
        raise RuntimeError(msg)


def _normalize_quick_start_timestamp(model_output: str, preset_name: str) -> str:
    """Pin generated quick-start timestamps when the selected preset emits one."""
    timestamp = _preset_timestamp(preset_name)
    normalized = re.sub(
        r"^#   timestamp: .+$",
        f"#   timestamp: {timestamp}",
        model_output,
        count=1,
        flags=re.MULTILINE,
    )
    if normalized != model_output:
        return normalized
    return model_output


def _preset_timestamp(preset_name: str) -> str:
    _prefix, separator, version = preset_name.rpartition("-")
    if separator and len(version) == PRESET_VERSION_DATE_LENGTH and version.isdecimal():
        return f"{version[:4]}-{version[4:6]}-{version[6:8]}T00:00:00+00:00"
    msg = f"Preset name does not end with YYYYMMDD: {preset_name}"
    raise RuntimeError(msg)


def _print_process_output(stdout: str | bytes | None, stderr: str | bytes | None) -> None:
    for stream in (stdout, stderr):
        if stream is None:
            continue
        output = stream.decode() if isinstance(stream, bytes) else stream
        print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")


def _prepend_path(current: str | None, path: Path) -> str:
    if current:
        return f"{path}{os.pathsep}{current}"
    return str(path)


def _prepend_warning_filter(current: str | None) -> str:
    filter_ = "ignore::FutureWarning"
    if current:
        return f"{filter_},{current}"
    return filter_


def _render_readme_quick_start(
    preset_name: str,
    model_output: str,
    practical_preset_name: str,
    practical_model_output: str,
) -> str:
    schema = QUICK_START_SCHEMA_PATH.read_text(encoding="utf-8").rstrip()
    command = _render_quick_start_command(preset_name)
    practical_command = _render_quick_start_command(practical_preset_name)
    return f"""```bash
{command}
```

This quick start uses `{preset_name}`, the recommended immutable preset for modern Python output.

<details>
<summary>📄 {QUICK_START_SCHEMA_NAME} (input)</summary>

```json
{schema}
```

</details>

<details>
<summary>🐍 {QUICK_START_OUTPUT_NAME} (output)</summary>

```python
{model_output}
```

</details>

<details>
<summary>🧰 {practical_preset_name} variant</summary>

Use `{practical_preset_name}` when you also want schema-authored names, model reuse, and generated documentation.

```bash
{practical_command}
```

```python
{practical_model_output}
```

</details>"""


def _render_docs_index_quick_start(
    preset_name: str,
    model_output: str,
    practical_preset_name: str,
    practical_model_output: str,
) -> str:
    schema = QUICK_START_SCHEMA_PATH.read_text(encoding="utf-8").rstrip()
    command = _render_quick_start_command(preset_name)
    practical_command = _render_quick_start_command(practical_preset_name)
    return f"""### 1️⃣ Create a schema file

```json title="{QUICK_START_SCHEMA_NAME}"
{schema}
```

### 2️⃣ Run the generator

```bash
{command}
```

This quick start uses `{preset_name}`, the recommended immutable preset for modern Python output.

### 3️⃣ Use your models

```python title="{QUICK_START_OUTPUT_NAME}"
{model_output}
```

<details>
<summary>🧰 Use {practical_preset_name}</summary>

Use `{practical_preset_name}` when you also want schema-authored names, model reuse, and generated documentation.

```bash
{practical_command}
```

```python title="{QUICK_START_OUTPUT_NAME}"
{practical_model_output}
```

</details>

🎉 That's it! Your schema is now a fully-typed Python model."""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Build preset documentation")
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Check whether preset docs and preset-powered quick-start examples are up to date "
            "(docs/presets.md plus quick-start sections in README.md and docs/index.md)"
        ),
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default=None,
        help="Print presets in the selected format instead of writing docs",
    )
    return parser.parse_args()


def main() -> int:
    """Script entrypoint."""
    args = parse_args()
    if args.check and args.format:
        print("Error: --check cannot be used with --format", file=sys.stderr)
        return 2
    if args.format:
        match args.format:
            case "markdown" | "json":
                print(render_presets(args.format), end="")
            case _:  # pragma: no cover
                print(f"Error: unsupported format {args.format!r}", file=sys.stderr)
                return 2
        return 0
    return build_docs(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
