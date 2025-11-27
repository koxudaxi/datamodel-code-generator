"""Tests for main CLI functionality with Korean locale settings."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import black
import pytest
from freezegun import freeze_time

from datamodel_code_generator import MIN_VERSION, chdir, inferred_message
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_directory_content, assert_output, create_assert_file_content
from tests.main.conftest import run_main, run_main_and_assert_stdout, run_main_with_args

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


@freeze_time("2019-07-26")
def test_main(tmp_path: Path) -> None:
    """Test basic main function with OpenAPI input."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        OPEN_API_DATA_PATH / "api.yaml",
        output_file,
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, "main/output.py")


@freeze_time("2019-07-26")
def test_main_base_class(tmp_path: Path) -> None:
    """Test main function with custom base class."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        OPEN_API_DATA_PATH / "api.yaml",
        output_file,
        extra_args=["--base-class", "custom_module.Base"],
        copy_files=[(DATA_PATH / "pyproject.toml", tmp_path / "pyproject.toml")],
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, EXPECTED_MAIN_KR_PATH / "main_base_class" / "output.py")


@freeze_time("2019-07-26")
def test_target_python_version(tmp_path: Path) -> None:
    """Test main function with target Python version."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        OPEN_API_DATA_PATH / "api.yaml",
        output_file,
        extra_args=["--target-python-version", f"3.{MIN_VERSION}"],
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, EXPECTED_MAIN_KR_PATH / "target_python_version" / "output.py")


def test_main_modular(tmp_path: Path) -> None:
    """Test main function on modular file."""
    input_filename = OPEN_API_DATA_PATH / "modular.yaml"
    output_path = tmp_path / "model"

    with freeze_time(TIMESTAMP):
        run_main(input_filename, output_path)
    assert_directory_content(output_path, EXPECTED_MAIN_KR_PATH / "main_modular")


def test_main_modular_no_file() -> None:
    """Test main function on modular file with no output name."""
    input_filename = OPEN_API_DATA_PATH / "modular.yaml"

    assert run_main_with_args(["--input", str(input_filename)]) == Exit.ERROR


def test_main_modular_filename(tmp_path: Path) -> None:
    """Test main function on modular file with filename."""
    input_filename = OPEN_API_DATA_PATH / "modular.yaml"
    output_filename = tmp_path / "model.py"

    assert run_main(input_filename, output_filename) == Exit.ERROR


def test_main_no_file(capsys: pytest.CaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test main function on non-modular file with no output name."""
    monkeypatch.chdir(tmp_path)

    input_filename = OPEN_API_DATA_PATH / "api.yaml"

    with freeze_time(TIMESTAMP):
        run_main_and_assert_stdout(
            input_path=input_filename,
            expected_output_path=EXPECTED_MAIN_KR_PATH / "main_no_file" / "output.py",
            capsys=capsys,
            expected_stderr=inferred_message.format("openapi") + "\n",
        )


def test_main_custom_template_dir(
    capsys: pytest.CaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test main function with custom template directory."""
    monkeypatch.chdir(tmp_path)

    input_filename = OPEN_API_DATA_PATH / "api.yaml"
    custom_template_dir = DATA_PATH / "templates"
    extra_template_data = OPEN_API_DATA_PATH / "extra_data.json"

    with freeze_time(TIMESTAMP):
        run_main_and_assert_stdout(
            input_path=input_filename,
            expected_output_path=EXPECTED_MAIN_KR_PATH / "main_custom_template_dir" / "output.py",
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
def test_pyproject(tmp_path: Path) -> None:
    """Test main function with pyproject.toml configuration."""
    pyproject_toml = DATA_PATH / "project" / "pyproject.toml"
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        OPEN_API_DATA_PATH / "api.yaml",
        output_file,
        copy_files=[(pyproject_toml, tmp_path / "pyproject.toml")],
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, "pyproject/output.py")


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
    return_code: Exit = run_main(
        input_file,
        output_file,
        extra_args=["--disable-timestamp"],
    )
    assert return_code == Exit.OK
    assert output_file.read_text(encoding="utf-8") == expected_output, (
        f"\nExpected  output:\n{expected_output}\n\nGenerated output:\n{output_file.read_text(encoding='utf-8')}"
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "19",
    reason="Installed black doesn't support the old style",
)
@freeze_time("2019-07-26")
def test_pyproject_with_tool_section(tmp_path: Path) -> None:
    """Test that a pyproject.toml with [tool.datamodel-codegen] section is found and applied."""
    pyproject_toml = """
[tool.datamodel-codegen]
target-python-version = "3.10"
strict-types = ["str"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)
    output_file: Path = tmp_path / "output.py"

    with chdir(tmp_path):
        return_code: Exit = run_main(
            (OPEN_API_DATA_PATH / "api.yaml").resolve(),
            output_file.resolve(),
        )

    assert return_code == Exit.OK
    assert_file_content(output_file, EXPECTED_MAIN_KR_PATH / "pyproject" / "output.strictstr.py")


@freeze_time("2019-07-26")
def test_main_use_schema_description(tmp_path: Path) -> None:
    """Test --use-schema-description option."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_file,
        extra_args=["--use-schema-description"],
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, EXPECTED_MAIN_KR_PATH / "main_use_schema_description" / "output.py")


@freeze_time("2022-11-11")
def test_main_use_field_description(tmp_path: Path) -> None:
    """Test --use-field-description option."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_file,
        extra_args=["--use-field-description"],
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, EXPECTED_MAIN_KR_PATH / "main_use_field_description" / "output.py")


@freeze_time("2022-11-11")
def test_main_use_inline_field_description(tmp_path: Path) -> None:
    """Test --use-inline-field-description option."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = run_main(
        OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_file,
        extra_args=["--use-inline-field-description"],
    )
    assert return_code == Exit.OK
    assert_file_content(output_file, EXPECTED_MAIN_KR_PATH / "main_use_inline_field_description" / "output.py")


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
    return_code: Exit = run_main(
        input_file,
        output_file,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--disable-timestamp",
            "--capitalise-enum-members",
            "--snake-case-field",
        ],
    )
    assert return_code == Exit.OK
    output_file_read_text = output_file.read_text(encoding="utf_8")
    assert output_file_read_text == expected_output, (
        f"\nExpected  output:\n{expected_output}\n\nGenerated output:\n{output_file_read_text}"
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
    return_code: Exit = run_main(
        input_file,
        output_file,
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--disable-timestamp",
            "--capitalise-enum-members",
            "--snake-case-field",
            "--use-subclass-enum",
        ],
    )
    assert return_code == Exit.OK
    output_file_read_text = output_file.read_text(encoding="utf_8")
    assert output_file_read_text == expected_output, (
        f"\nExpected  output:\n{expected_output}\n\nGenerated output:\n{output_file_read_text}"
    )


EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH = EXPECTED_MAIN_KR_PATH / "generate_pyproject_config"


def test_generate_pyproject_config_basic(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with basic options."""
    return_code: Exit = run_main_with_args([
        "--generate-pyproject-config",
        "--input",
        "schema.yaml",
        "--output",
        "model.py",
    ])
    assert return_code == Exit.OK
    captured = capsys.readouterr()
    assert_output(captured.out, EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "basic.txt")


def test_generate_pyproject_config_with_boolean_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with boolean options."""
    return_code: Exit = run_main_with_args([
        "--generate-pyproject-config",
        "--snake-case-field",
        "--use-annotated",
        "--collapse-root-models",
    ])
    assert return_code == Exit.OK
    captured = capsys.readouterr()
    assert_output(captured.out, EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "boolean_options.txt")


def test_generate_pyproject_config_with_list_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with list options."""
    return_code: Exit = run_main_with_args([
        "--generate-pyproject-config",
        "--strict-types",
        "str",
        "int",
    ])
    assert return_code == Exit.OK
    captured = capsys.readouterr()
    assert_output(captured.out, EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "list_options.txt")


def test_generate_pyproject_config_with_multiple_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with various option types."""
    return_code: Exit = run_main_with_args([
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
    ])
    assert return_code == Exit.OK
    captured = capsys.readouterr()
    assert_output(captured.out, EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "multiple_options.txt")


def test_generate_pyproject_config_excludes_meta_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that meta options are excluded from generated config."""
    return_code: Exit = run_main_with_args([
        "--generate-pyproject-config",
        "--input",
        "schema.yaml",
    ])
    assert return_code == Exit.OK
    captured = capsys.readouterr()
    assert_output(captured.out, EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "excludes_meta_options.txt")
