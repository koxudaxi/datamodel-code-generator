"""Recipe smoke tests for the datamodel-code-generator agent skill."""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence

FIXTURES = Path(__file__).parent / "fixtures"
TARGET_PYTHON = f"{sys.version_info[0]}.{sys.version_info[1]}"


def _run_codegen(args: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["datamodel-codegen", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"datamodel-codegen failed\nargs: {args!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def _import_file(path: Path, module_name: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        pytest.fail(f"Unable to import generated file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(module_name, None)
    spec.loader.exec_module(module)
    return module


def _import_package(tmp_path: Path, package_name: str) -> object:
    sys.path.insert(0, str(tmp_path))
    try:
        sys.modules.pop(package_name, None)
        return importlib.import_module(package_name)
    finally:
        sys.path.remove(str(tmp_path))


@pytest.mark.parametrize(
    ("fixture_name", "input_type", "module_name", "expected_name", "extra_args"),
    [
        ("openapi.yaml", "openapi", "skill_openapi_models", "SkillPet", ()),
        ("asyncapi.yaml", "asyncapi", "skill_asyncapi_models", "SkillPetCreated", ()),
        ("jsonschema.json", "jsonschema", "skill_jsonschema_models", "SkillUser", ()),
        ("sample.json", "json", "skill_json_models", "SampleJson", ("--class-name", "SampleJson")),
        ("sample.yaml", "yaml", "skill_yaml_models", "SampleYaml", ("--class-name", "SampleYaml")),
        ("sample.csv", "csv", "skill_csv_models", "SampleCsv", ("--class-name", "SampleCsv")),
    ],
)
def test_skill_single_file_recipes_generate_importable_models(
    tmp_path: Path,
    fixture_name: str,
    input_type: str,
    module_name: str,
    expected_name: str,
    extra_args: tuple[str, ...],
) -> None:
    """Representative single-file recipes generate importable models."""
    output = tmp_path / f"{module_name}.py"
    _run_codegen([
        "--input",
        str(FIXTURES / fixture_name),
        "--input-file-type",
        input_type,
        "--output",
        str(output),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        TARGET_PYTHON,
        *extra_args,
    ])

    module = _import_file(output, module_name)
    assert hasattr(module, expected_name)


def test_skill_graphql_recipe_generates_importable_models(tmp_path: Path) -> None:
    """GraphQL recipe runs when the optional dependency is installed."""
    if importlib.util.find_spec("graphql") is None:
        pytest.skip("GraphQL optional dependency is not installed")

    output = tmp_path / "graphql_models.py"
    _run_codegen([
        "--input",
        str(FIXTURES / "schema.graphql"),
        "--input-file-type",
        "graphql",
        "--output",
        str(output),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        TARGET_PYTHON,
    ])

    module = _import_file(output, "skill_graphql_models")
    assert hasattr(module, "SkillGraphPet")


def test_skill_input_model_recipe_generates_importable_models(tmp_path: Path) -> None:
    """Python model input can be retargeted to Pydantic v2 output."""
    output = tmp_path / "input_model.py"
    _run_codegen([
        "--input-model",
        f"{FIXTURES / 'python_models.py'}:SkillInputUser",
        "--output",
        str(output),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        TARGET_PYTHON,
    ])

    module = _import_file(output, "skill_input_model")
    assert hasattr(module, "SkillInputUser")


def test_skill_directory_output_recipe_generates_importable_package(tmp_path: Path) -> None:
    """Directory output creates an importable package."""
    output = tmp_path / "skill_models"
    _run_codegen([
        "--input",
        str(FIXTURES / "schemas"),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(output),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        TARGET_PYTHON,
        "--all-exports-scope",
        "recursive",
    ])

    package = _import_package(tmp_path, "skill_models")
    assert hasattr(package, "SkillProduct")


def test_skill_recipe_check_mode_passes_for_stable_fixture(tmp_path: Path) -> None:
    """The documented --check workflow passes after generation."""
    output = tmp_path / "checked_models.py"
    base_args = [
        "--input",
        str(FIXTURES / "jsonschema.json"),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(output),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        TARGET_PYTHON,
        "--disable-timestamp",
    ]
    _run_codegen(base_args)
    _run_codegen([*base_args, "--check"])
    module = _import_file(output, "skill_checked_models")
    assert hasattr(module, "SkillUser")
