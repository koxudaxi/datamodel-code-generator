"""E2E recipe tests for the datamodel-code-generator agent skill."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.conftest import assert_directory_content, create_assert_file_content

if TYPE_CHECKING:
    from collections.abc import Sequence

FIXTURES = Path(__file__).parent / "fixtures"
EXPECTED = Path(__file__).parents[2] / "data" / "expected" / "skills" / "datamodel-code-generator"
TARGET_PYTHON = "3.10"
COMMON_ARGS = (
    "--output-model-type",
    "pydantic_v2.BaseModel",
    "--target-python-version",
    TARGET_PYTHON,
    "--formatters",
    "black",
    "isort",
    "--disable-timestamp",
)
assert_file_content = create_assert_file_content(EXPECTED)


def _run_codegen(args: Sequence[str]) -> None:
    """Run datamodel-codegen and fail with captured output on errors."""
    try:
        result = subprocess.run(
            ["datamodel-codegen", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        msg = "datamodel-codegen not found; ensure the CLI is installed in the test environment"
        raise AssertionError(msg) from error
    if result.returncode != 0:
        pytest.fail(f"datamodel-codegen failed\nargs: {args!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")


@pytest.mark.parametrize(
    ("fixture_name", "input_type", "expected_file", "extra_args"),
    [
        ("openapi.yaml", "openapi", "single_file/openapi.py", ()),
        ("asyncapi.yaml", "asyncapi", "single_file/asyncapi.py", ()),
        ("jsonschema.json", "jsonschema", "single_file/jsonschema.py", ()),
        ("sample.json", "json", "single_file/json.py", ("--class-name", "SampleJson")),
        ("sample.yaml", "yaml", "single_file/yaml.py", ("--class-name", "SampleYaml")),
        ("sample.csv", "csv", "single_file/csv.py", ("--class-name", "SampleCsv")),
    ],
)
def test_skill_single_file_recipes_match_expected_output(
    tmp_path: Path,
    fixture_name: str,
    input_type: str,
    expected_file: str,
    extra_args: tuple[str, ...],
) -> None:
    """Representative single-file recipes match checked-in expected output."""
    output = tmp_path / "models.py"
    _run_codegen([
        "--input",
        str(FIXTURES / fixture_name),
        "--input-file-type",
        input_type,
        "--output",
        str(output),
        *COMMON_ARGS,
        *extra_args,
    ])
    assert_file_content(output, expected_file)


def test_skill_graphql_recipe_matches_expected_output(tmp_path: Path) -> None:
    """GraphQL recipe matches checked-in expected output."""
    pytest.importorskip("graphql", reason="GraphQL optional dependency is not installed")

    output = tmp_path / "graphql_models.py"
    _run_codegen([
        "--input",
        str(FIXTURES / "schema.graphql"),
        "--input-file-type",
        "graphql",
        "--output",
        str(output),
        *COMMON_ARGS,
    ])
    assert_file_content(output, "graphql.py")


def test_skill_input_model_recipe_matches_expected_output(tmp_path: Path) -> None:
    """Python model input retargeting matches checked-in expected output."""
    output = tmp_path / "input_model.py"
    _run_codegen([
        "--input-model",
        f"{FIXTURES / 'python_models.py'}:SkillInputUser",
        "--output",
        str(output),
        *COMMON_ARGS,
    ])
    assert_file_content(output, "input_model.py")


def test_skill_directory_output_recipe_matches_expected_package(tmp_path: Path) -> None:
    """Directory output matches checked-in expected package files."""
    output = tmp_path / "skill_models"
    _run_codegen([
        "--input",
        str(FIXTURES / "schemas"),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(output),
        *COMMON_ARGS,
        "--all-exports-scope",
        "recursive",
    ])
    assert_directory_content(output, EXPECTED / "directory_output")


def test_skill_recipe_check_mode_matches_expected_output(tmp_path: Path) -> None:
    """The documented --check workflow matches checked-in expected output."""
    output = tmp_path / "checked_models.py"
    base_args = [
        "--input",
        str(FIXTURES / "jsonschema.json"),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(output),
        *COMMON_ARGS,
    ]
    _run_codegen(base_args)
    assert_file_content(output, "check_mode.py")
    _run_codegen([*base_args, "--check"])
