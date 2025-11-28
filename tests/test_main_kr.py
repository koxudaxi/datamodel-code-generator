"""Tests for main CLI functionality with Korean locale settings."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import black
import pytest

from datamodel_code_generator import MIN_VERSION, chdir, inferred_message
from datamodel_code_generator.__main__ import Exit
from tests.conftest import create_assert_file_content, freeze_time
from tests.main.conftest import run_main_and_assert, run_main_with_args

DATA_PATH: Path = Path(__file__).parent / "data"
OPEN_API_DATA_PATH: Path = DATA_PATH / "openapi"
EXPECTED_MAIN_KR_PATH = DATA_PATH / "expected" / "main_kr"

assert_file_content = create_assert_file_content(EXPECTED_MAIN_KR_PATH)


TIMESTAMP = "1985-10-26T01:21:00-07:00"


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset argument namespace before each test."""
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace_)
    monkeypatch.setattr("datamodel_code_generator.arguments.namespace", namespace_)


@pytest.fixture
def output_file(tmp_path: Path) -> Path:
    """Return standard output file path."""
    return tmp_path / "output.py"


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Return standard output directory path."""
    return tmp_path / "model"


@freeze_time("2019-07-26")
def test_main(output_file: Path) -> None:
    """Test basic main function with OpenAPI input."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="main/output.py",
    )


@freeze_time("2019-07-26")
def test_main_base_class(output_file: Path, tmp_path: Path) -> None:
    """Test main function with custom base class."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_base_class" / "output.py",
        extra_args=["--base-class", "custom_module.Base"],
        copy_files=[(DATA_PATH / "pyproject.toml", tmp_path / "pyproject.toml")],
    )


@freeze_time("2019-07-26")
def test_target_python_version(output_file: Path) -> None:
    """Test main function with target Python version."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "target_python_version" / "output.py",
        extra_args=["--target-python-version", f"3.{MIN_VERSION}"],
    )


def test_main_modular(output_dir: Path) -> None:
    """Test main function on modular file."""
    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "modular.yaml",
            output_path=output_dir,
            expected_directory=EXPECTED_MAIN_KR_PATH / "main_modular",
        )


def test_main_modular_no_file() -> None:
    """Test main function on modular file with no output name."""
    run_main_with_args(["--input", str(OPEN_API_DATA_PATH / "modular.yaml")], expected_exit=Exit.ERROR)


def test_main_modular_filename(output_file: Path) -> None:
    """Test main function on modular file with filename."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_file,
        expected_exit=Exit.ERROR,
    )


def test_main_no_file(capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test main function on non-modular file with no output name."""
    monkeypatch.chdir(tmp_path)

    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=None,
            expected_stdout_path=EXPECTED_MAIN_KR_PATH / "main_no_file" / "output.py",
            capsys=capsys,
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


def test_main_custom_template_dir(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test main function with custom template directory."""
    monkeypatch.chdir(tmp_path)

    custom_template_dir = DATA_PATH / "templates"
    extra_template_data = OPEN_API_DATA_PATH / "extra_data.json"

    with freeze_time(TIMESTAMP):
        run_main_and_assert(
            input_path=OPEN_API_DATA_PATH / "api.yaml",
            output_path=None,
            expected_stdout_path=EXPECTED_MAIN_KR_PATH / "main_custom_template_dir" / "output.py",
            capsys=capsys,
            extra_args=[
                "--custom-template-dir",
                str(custom_template_dir),
                "--extra-template-data",
                str(extra_template_data),
            ],
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


@pytest.mark.skipif(
    black.__version__.split(".")[0] >= "24",
    reason="Installed black doesn't support the old style",
)
@freeze_time("2019-07-26")
def test_pyproject(output_file: Path, tmp_path: Path) -> None:
    """Test main function with pyproject.toml configuration."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file="pyproject/output.py",
        copy_files=[(DATA_PATH / "project" / "pyproject.toml", tmp_path / "pyproject.toml")],
    )


@pytest.mark.parametrize("language", ["UK", "US"])
def test_pyproject_respects_both_spellings_of_capitalize_enum_members_flag(language: str, tmp_path: Path) -> None:
    """Test that both UK and US spellings of capitalise are accepted."""
    pyproject_toml_data = f"""
[tool.datamodel-codegen]
capitali{"s" if language == "UK" else "z"}e-enum-members = true
enable-version-header = false
input-file-type = "jsonschema"
"""
    with (tmp_path / "pyproject.toml").open("w") as f:
        f.write(pyproject_toml_data)

        input_data = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "MyEnum": {
      "enum": [
        "MEMBER_1",
        "member_2"
      ]
    }
  }
}
"""
    input_file = tmp_path / "schema.json"
    with input_file.open("w") as f:
        f.write(input_data)

    expected_output = """# generated by datamodel-codegen:
#   filename:  schema.json

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class Model(BaseModel):
    __root__: Any


class MyEnum(Enum):
    MEMBER_1 = 'MEMBER_1'
    member_2 = 'member_2'
"""

    output_file: Path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        expected_output=expected_output,
        extra_args=["--disable-timestamp"],
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@freeze_time("2019-07-26")
def test_pyproject_with_tool_section(output_file: Path, tmp_path: Path) -> None:
    """Test that a pyproject.toml with [tool.datamodel-codegen] section is found and applied."""
    pyproject_toml = """
[tool.datamodel-codegen]
target-python-version = "3.10"
strict-types = ["str"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=(OPEN_API_DATA_PATH / "api.yaml").resolve(),
            output_path=output_file.resolve(),
            input_file_type=None,
            assert_func=assert_file_content,
            expected_file=EXPECTED_MAIN_KR_PATH / "pyproject" / "output.strictstr.py",
        )


@freeze_time("2019-07-26")
def test_main_use_schema_description(output_file: Path) -> None:
    """Test --use-schema-description option."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_schema_description" / "output.py",
        extra_args=["--use-schema-description"],
    )


@freeze_time("2022-11-11")
def test_main_use_field_description(output_file: Path) -> None:
    """Test --use-field-description option."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_field_description" / "output.py",
        extra_args=["--use-field-description"],
    )


@freeze_time("2022-11-11")
def test_main_use_inline_field_description(output_file: Path) -> None:
    """Test --use-inline-field-description option."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_inline_field_description" / "output.py",
        extra_args=["--use-inline-field-description"],
    )


def test_capitalise_enum_members(tmp_path: Path) -> None:
    """Test capitalise-enum-members option (issue #2370)."""
    input_data = """
openapi: 3.0.3
info:
  version: X.Y.Z
  title: example schema
servers:
  - url: "https://acme.org"
paths: {}
components:
  schemas:
    EnumSystems:
      type: enum
      enum:
        - linux
        - osx
        - windows
"""
    input_file = tmp_path / "myschema.yaml"
    input_file.write_text(input_data, encoding="utf_8")

    expected_output = """# generated by datamodel-codegen:
#   filename:  myschema.yaml

from __future__ import annotations

from enum import Enum


class EnumSystems(Enum):
    LINUX = 'linux'
    OSX = 'osx'
    WINDOWS = 'windows'
"""

    output_file: Path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        expected_output=expected_output,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--disable-timestamp",
            "--capitalise-enum-members",
            "--snake-case-field",
        ],
    )


def test_capitalise_enum_members_and_use_subclass_enum(tmp_path: Path) -> None:
    """Test combination of capitalise-enum-members and use-subclass-enum (issue #2395)."""
    input_data = """
openapi: 3.0.3
info:
  version: X.Y.Z
  title: example schema
servers:
  - url: "https://acme.org"
paths: {}
components:
  schemas:
    EnumSystems:
      type: string
      enum:
        - linux
        - osx
        - windows
"""
    input_file = tmp_path / "myschema.yaml"
    input_file.write_text(input_data, encoding="utf_8")

    expected_output = """# generated by datamodel-codegen:
#   filename:  myschema.yaml

from __future__ import annotations

from enum import Enum


class EnumSystems(str, Enum):
    LINUX = 'linux'
    OSX = 'osx'
    WINDOWS = 'windows'
"""

    output_file: Path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=input_file,
        output_path=output_file,
        expected_output=expected_output,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--disable-timestamp",
            "--capitalise-enum-members",
            "--snake-case-field",
            "--use-subclass-enum",
        ],
    )


EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH = EXPECTED_MAIN_KR_PATH / "generate_pyproject_config"


def test_generate_pyproject_config_basic(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with basic options."""
    run_main_with_args(
        [
            "--generate-pyproject-config",
            "--input",
            "schema.yaml",
            "--output",
            "model.py",
        ],
        capsys=capsys,
        expected_stdout_path=EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "basic.txt",
    )


def test_generate_pyproject_config_with_boolean_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with boolean options."""
    run_main_with_args(
        [
            "--generate-pyproject-config",
            "--snake-case-field",
            "--use-annotated",
            "--collapse-root-models",
        ],
        capsys=capsys,
        expected_stdout_path=EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "boolean_options.txt",
    )


def test_generate_pyproject_config_with_list_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with list options."""
    run_main_with_args(
        [
            "--generate-pyproject-config",
            "--strict-types",
            "str",
            "int",
        ],
        capsys=capsys,
        expected_stdout_path=EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "list_options.txt",
    )


def test_generate_pyproject_config_with_multiple_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with various option types."""
    run_main_with_args(
        [
            "--generate-pyproject-config",
            "--input",
            "schema.yaml",
            "--output",
            "model.py",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.11",
            "--snake-case-field",
            "--strict-types",
            "str",
            "bytes",
        ],
        capsys=capsys,
        expected_stdout_path=EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "multiple_options.txt",
    )


def test_generate_pyproject_config_excludes_meta_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that meta options are excluded from generated config."""
    run_main_with_args(
        [
            "--generate-pyproject-config",
            "--input",
            "schema.yaml",
        ],
        capsys=capsys,
        expected_stdout_path=EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "excludes_meta_options.txt",
    )
