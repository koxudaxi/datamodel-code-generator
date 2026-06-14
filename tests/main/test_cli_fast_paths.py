"""CLI startup fast-path regressions."""

from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]
SRC = ROOT / "src"
MISSING = object()


def _run_probe(script: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=30,
    )
    return json.loads(result.stdout)


def _run_module_schema_fast_path_in_process(schema_options: list[str]) -> dict[str, Any]:
    return _run_module_fast_path_in_process(schema_options)


def _run_module_fast_path_in_process(options: list[str]) -> dict[str, Any]:
    module_name = "datamodel_code_generator.__main__"
    previous_module = sys.modules.pop(module_name, MISSING)
    original_argv = sys.argv[:]
    sys.argv = ["datamodel-codegen", *options]
    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            try:
                runpy.run_module("datamodel_code_generator.__main__", run_name="__main__", alter_sys=True)
            except SystemExit as exc:
                code = exc.code
            else:  # pragma: no cover
                code = None
    finally:
        sys.argv = original_argv
        sys.modules.pop(module_name, None)
        if previous_module is not MISSING:  # pragma: no branch
            sys.modules[module_name] = previous_module
    return {"code": code, "stdout": stdout.getvalue()}


def _run_module_schema_fast_path(schema_options: list[str]) -> dict[str, Any]:
    return _run_module_fast_path(schema_options)


def _run_module_fast_path(options: list[str]) -> dict[str, Any]:
    return _run_probe(
        textwrap.dedent(
            f"""
            import contextlib
            import io
            import json
            import runpy
            import sys

            sys.argv = ["datamodel-codegen", *{options!r}]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                try:
                    runpy.run_module("datamodel_code_generator.__main__", run_name="__main__", alter_sys=True)
                except SystemExit as exc:
                    code = exc.code
                else:
                    code = None

            print(json.dumps({{
                "code": code,
                "stdout": stdout.getvalue(),
                "imported_arguments": "datamodel_code_generator.arguments" in sys.modules,
            }}))
            """
        )
    )


def _run_parsed_schema_path(schema_name: str) -> dict[str, Any]:
    return _run_parsed_path(["--output-format-json-schema", schema_name])


def _run_parsed_path(options: list[str]) -> dict[str, Any]:
    return _run_probe(
        textwrap.dedent(
            f"""
            import contextlib
            import io
            import json

            from datamodel_code_generator.__main__ import main

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main({options!r})

            print(json.dumps({{"code": code, "stdout": stdout.getvalue()}}))
            """
        )
    )


@pytest.mark.allow_direct_assert
def test_output_format_json_schema_exact_fast_paths_skip_argument_parser_import() -> None:
    """Exact JSON Schema utility invocations bypass argparse without changing output."""
    for schema_name in ("generation", "structured-output"):
        parsed_path = _run_parsed_schema_path(schema_name)
        assert parsed_path["code"] == 0
        fast_paths = [
            _run_module_schema_fast_path([f"--output-format-json-schema={schema_name}"]),
            _run_module_schema_fast_path(["--output-format-json-schema", schema_name]),
        ]
        covered_fast_paths = [
            _run_module_schema_fast_path_in_process([f"--output-format-json-schema={schema_name}"]),
            _run_module_schema_fast_path_in_process(["--output-format-json-schema", schema_name]),
        ]

        for fast_path in fast_paths:
            assert fast_path["code"] == 0
            assert fast_path["imported_arguments"] is False
            assert fast_path["stdout"] == parsed_path["stdout"]
            schema = json.loads(fast_path["stdout"])
            assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        for fast_path in covered_fast_paths:
            assert fast_path["code"] == 0
            assert fast_path["stdout"] == parsed_path["stdout"]


@pytest.mark.allow_direct_assert
def test_list_utility_exact_fast_paths_skip_argument_parser_import() -> None:
    """Exact list utility invocations bypass argparse without changing output."""
    cases = [
        ["--list-deprecations"],
        ["--list-deprecations", "table"],
        ["--list-deprecations", "json"],
        ["--list-deprecations", "markdown"],
        ["--list-deprecations=table"],
        ["--list-deprecations=json"],
        ["--list-deprecations=markdown"],
        ["--list-experimental"],
        ["--list-experimental", "table"],
        ["--list-experimental", "json"],
        ["--list-experimental", "markdown"],
        ["--list-experimental=table"],
        ["--list-experimental=json"],
        ["--list-experimental=markdown"],
    ]

    for options in cases:
        parsed_path = _run_parsed_path(options)
        fast_path = _run_module_fast_path(options)
        covered_fast_path = _run_module_fast_path_in_process(options)

        assert parsed_path["code"] == 0
        assert fast_path["code"] == 0
        assert fast_path["imported_arguments"] is False
        assert fast_path["stdout"] == parsed_path["stdout"]
        assert covered_fast_path["code"] == 0
        assert covered_fast_path["stdout"] == parsed_path["stdout"]
