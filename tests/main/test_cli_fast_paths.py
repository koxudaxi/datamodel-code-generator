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
from types import ModuleType
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
    module_name = "datamodel_code_generator.__main__"
    previous_module = sys.modules.pop(module_name, MISSING)
    original_argv = sys.argv[:]
    sys.argv = ["datamodel-codegen", *schema_options]
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
        if isinstance(previous_module, ModuleType):  # pragma: no branch
            sys.modules[module_name] = previous_module
    return {"code": code, "stdout": stdout.getvalue()}


def _run_module_schema_fast_path(schema_options: list[str]) -> dict[str, Any]:
    return _run_probe(
        textwrap.dedent(
            f"""
            import contextlib
            import io
            import json
            import runpy
            import sys

            sys.argv = ["datamodel-codegen", *{schema_options!r}]
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


def _run_module_help_fast_path() -> dict[str, Any]:
    return _run_probe(
        textwrap.dedent(
            """
            import contextlib
            import io
            import json
            import runpy
            import sys

            sys.argv = ["datamodel-codegen", "--help"]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                try:
                    runpy.run_module("datamodel_code_generator.__main__", run_name="__main__", alter_sys=True)
                except SystemExit as exc:
                    code = exc.code
                else:
                    code = None

            print(json.dumps({
                "code": code,
                "stdout": stdout.getvalue(),
                "imported_arguments": "datamodel_code_generator.arguments" in sys.modules,
                "imported_format": "datamodel_code_generator.format" in sys.modules,
                "imported_json_config": "datamodel_code_generator.json_config" in sys.modules,
                "imported_pydantic": "pydantic" in sys.modules,
                "imported_validators": "datamodel_code_generator.validators" in sys.modules,
            }))
            """
        )
    )


def _run_argument_parser_json_option_parse() -> dict[str, Any]:
    return _run_probe(
        textwrap.dedent(
            """
            import json
            import sys

            from datamodel_code_generator.arguments import arg_parser, namespace

            vars(namespace).clear()
            namespace.no_color = False
            arg_parser.parse_args(["--model-name-map", '{"User": "Account"}'], namespace=namespace)

            print(json.dumps({
                "model_name_map": namespace.model_name_map,
                "imported_json_config": "datamodel_code_generator.json_config" in sys.modules,
                "imported_pydantic": "pydantic" in sys.modules,
            }))
            """
        )
    )


def _run_main_import_probe() -> dict[str, Any]:
    return _run_probe(
        textwrap.dedent(
            """
            import json
            import sys

            from datamodel_code_generator.__main__ import main

            print(json.dumps({
                "main_callable": callable(main),
                "imported_format": "datamodel_code_generator.format" in sys.modules,
                "imported_builtin_formatter": "datamodel_code_generator._builtin_formatter" in sys.modules,
            }))
            """
        )
    )


def _run_parsed_schema_path(schema_name: str) -> dict[str, Any]:
    return _run_probe(
        textwrap.dedent(
            f"""
            import contextlib
            import io
            import json

            from datamodel_code_generator.__main__ import main

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["--output-format-json-schema", {schema_name!r}])

            print(json.dumps({{"code": code, "stdout": stdout.getvalue()}}))
            """
        )
    )


@pytest.mark.allow_direct_assert
def test_output_format_json_schema_exact_fast_paths_skip_argument_parser_import() -> None:
    """Exact JSON Schema utility invocations bypass argparse without changing output."""
    for schema_name in ("config", "generation", "model-metadata", "structured-output"):
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
def test_help_fast_path_skips_json_config_and_formatter_imports() -> None:
    """--help builds argparse choices without importing validation or formatter runtimes."""
    fast_path = _run_module_help_fast_path()

    assert fast_path["code"] == 0
    assert "Generate Python data models" in fast_path["stdout"]
    assert fast_path["imported_arguments"] is True
    assert fast_path["imported_format"] is False
    assert fast_path["imported_json_config"] is False
    assert fast_path["imported_pydantic"] is False
    assert fast_path["imported_validators"] is False


@pytest.mark.allow_direct_assert
def test_argument_parser_json_option_loads_json_config_lazily() -> None:
    """JSON-backed argparse callbacks still load and validate only when invoked."""
    parsed = _run_argument_parser_json_option_parse()

    assert parsed["model_name_map"] == {"User": "Account"}
    assert parsed["imported_json_config"] is True
    assert parsed["imported_pydantic"] is True


@pytest.mark.allow_direct_assert
def test_main_import_skips_formatter_runtime() -> None:
    """Importing CLI main does not load formatter runtime until a black check is needed."""
    imported = _run_main_import_probe()

    assert imported["main_callable"] is True
    assert imported["imported_format"] is False
    assert imported["imported_builtin_formatter"] is False
