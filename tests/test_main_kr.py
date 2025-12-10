"""Tests for main CLI functionality with Korean locale settings."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import black
import pytest
from packaging import version

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


def test_generate_pyproject_config_with_enum_option(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-pyproject-config with Enum option."""
    run_main_with_args(
        [
            "--generate-pyproject-config",
            "--input",
            "schema.yaml",
            "--read-only-write-only-model-type",
            "all",
        ],
        capsys=capsys,
        expected_stdout_path=EXPECTED_GENERATE_PYPROJECT_CONFIG_PATH / "enum_option.txt",
    )


EXPECTED_GENERATE_CLI_COMMAND_PATH = EXPECTED_MAIN_KR_PATH / "generate_cli_command"


def test_generate_cli_command_basic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with basic options."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "schema.yaml"
output = "model.py"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "basic.txt",
        )


def test_generate_cli_command_with_boolean_options(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with boolean options."""
    pyproject_toml = """
[tool.datamodel-codegen]
snake-case-field = true
use-annotated = true
collapse-root-models = true
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "boolean_options.txt",
        )


def test_generate_cli_command_with_list_options(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with list options."""
    pyproject_toml = """
[tool.datamodel-codegen]
strict-types = ["str", "int"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "list_options.txt",
        )


def test_generate_cli_command_with_multiple_options(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with various option types."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "schema.yaml"
output = "model.py"
output-model-type = "pydantic_v2.BaseModel"
target-python-version = "3.11"
snake-case-field = true
strict-types = ["str", "bytes"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "multiple_options.txt",
        )


def test_generate_cli_command_no_config(tmp_path: Path) -> None:
    """Test --generate-cli-command when no config found."""
    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            expected_exit=Exit.ERROR,
        )


def test_generate_cli_command_with_no_use_specialized_enum(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with use-specialized-enum = false."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "schema.yaml"
use-specialized-enum = false
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "no_use_specialized_enum.txt",
        )


def test_generate_cli_command_with_spaces_in_values(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with spaces in values."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "my schema.yaml"
output = "my model.py"
http-headers = ["Authorization: Bearer token", "X-Custom: value"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "spaces_in_values.txt",
        )


def test_generate_cli_command_with_false_boolean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with regular boolean set to false (should be skipped)."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "schema.yaml"
snake-case-field = false
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "false_boolean.txt",
        )


def test_generate_cli_command_excludes_excluded_options(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command excludes options like debug, version, etc."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "schema.yaml"
debug = true
version = true
no-color = true
disable-warnings = true
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_GENERATE_CLI_COMMAND_PATH / "excluded_options.txt",
        )


EXPECTED_PYPROJECT_PROFILE_PATH = EXPECTED_MAIN_KR_PATH / "pyproject_profile"


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.0.0"),
    reason="black 22.x doesn't support Python 3.11 target version",
)
@freeze_time("2019-07-26")
def test_pyproject_with_profile(output_file: Path, tmp_path: Path) -> None:
    """Test loading a named profile from pyproject.toml."""
    pyproject_toml = """
[tool.datamodel-codegen]
target-python-version = "3.9"
enable-version-header = false

[tool.datamodel-codegen.profiles.api]
target-python-version = "3.11"
snake-case-field = true
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    input_data = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "firstName": {"type": "string"},
    "lastName": {"type": "string"}
  }
}
"""
    input_file = tmp_path / "schema.json"
    input_file.write_text(input_data)

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=input_file,
            output_path=output_file.resolve(),
            assert_func=assert_file_content,
            expected_file=EXPECTED_PYPROJECT_PROFILE_PATH / "with_profile.py",
            extra_args=["--profile", "api", "--disable-timestamp"],
        )


def test_pyproject_profile_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test error when profile is not found."""
    pyproject_toml = """
[tool.datamodel-codegen]
target-python-version = "3.9"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    input_file = tmp_path / "schema.json"
    input_file.write_text('{"type": "object"}')

    output_file = tmp_path / "output.py"

    with chdir(tmp_path):
        return_code = run_main_with_args(
            ["--input", str(input_file), "--output", str(output_file), "--profile", "nonexistent"],
            expected_exit=Exit.ERROR,
            capsys=capsys,
        )
        assert return_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "Profile 'nonexistent' not found in pyproject.toml" in captured.err


@freeze_time("2019-07-26")
def test_ignore_pyproject_option(output_file: Path, tmp_path: Path) -> None:
    """Test --ignore-pyproject ignores pyproject.toml configuration."""
    pyproject_toml = """
[tool.datamodel-codegen]
snake-case-field = true
enable-version-header = true
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    input_data = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "firstName": {"type": "string"},
    "lastName": {"type": "string"}
  }
}
"""
    input_file = tmp_path / "schema.json"
    input_file.write_text(input_data)

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=input_file,
            output_path=output_file.resolve(),
            assert_func=assert_file_content,
            expected_file=EXPECTED_PYPROJECT_PROFILE_PATH / "ignore_pyproject.py",
            extra_args=["--ignore-pyproject", "--disable-timestamp"],
        )


@freeze_time("2019-07-26")
def test_profile_overrides_base_config_shallow_merge(output_file: Path, tmp_path: Path) -> None:
    """Test that profile settings shallow-merge (replace) base settings for lists."""
    pyproject_toml = """
[tool.datamodel-codegen]
strict-types = ["str", "int"]
target-python-version = "3.9"
enable-version-header = false

[tool.datamodel-codegen.profiles.api]
strict-types = ["bytes"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    input_data = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "data": {"type": "string", "format": "binary"}
  }
}
"""
    input_file = tmp_path / "schema.json"
    input_file.write_text(input_data)

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=input_file,
            output_path=output_file.resolve(),
            assert_func=assert_file_content,
            expected_file=EXPECTED_PYPROJECT_PROFILE_PATH / "shallow_merge.py",
            extra_args=["--profile", "api", "--disable-timestamp"],
        )


def test_generate_cli_command_with_profile(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command reflects merged profile settings."""
    pyproject_toml = """
[tool.datamodel-codegen]
target-python-version = "3.9"
snake-case-field = true

[tool.datamodel-codegen.profiles.api]
input = "api.yaml"
target-python-version = "3.11"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--profile", "api", "--generate-cli-command"],
            capsys=capsys,
        )
        captured = capsys.readouterr()
        # Profile value should override base
        assert "--target-python-version 3.11" in captured.out
        # Base value should be inherited
        assert "--snake-case-field" in captured.out
        # Profile-specific value (no quotes when no spaces in value)
        assert "--input api.yaml" in captured.out


def test_help_shows_new_options() -> None:
    """Test that --profile and --ignore-pyproject appear in help."""
    from datamodel_code_generator.arguments import arg_parser  # noqa: PLC0415

    help_text = arg_parser.format_help()
    assert "--profile" in help_text
    assert "--ignore-pyproject" in help_text
    assert "pyproject.toml" in help_text


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.0.0"),
    reason="black 22.x doesn't support Python 3.11 target version",
)
def test_pyproject_profile_inherits_base_settings(output_file: Path, tmp_path: Path) -> None:
    """Test that profile inherits settings from base config."""
    pyproject_toml = """
[tool.datamodel-codegen]
snake-case-field = true
enable-version-header = false

[tool.datamodel-codegen.profiles.api]
target-python-version = "3.11"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    input_data = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "firstName": {"type": "string"}
  }
}
"""
    input_file = tmp_path / "schema.json"
    input_file.write_text(input_data)

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=input_file,
            output_path=output_file.resolve(),
            assert_func=assert_file_content,
            expected_file=EXPECTED_PYPROJECT_PROFILE_PATH / "inherits_base.py",
            extra_args=["--profile", "api", "--disable-timestamp"],
        )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("23.0.0"),
    reason="black 22.x doesn't support Python 3.11 target version",
)
@freeze_time("2019-07-26")
def test_cli_args_override_profile_and_base(output_file: Path, tmp_path: Path) -> None:
    """Test that CLI arguments take precedence over profile and base settings."""
    pyproject_toml = """
[tool.datamodel-codegen]
target-python-version = "3.9"
enable-version-header = false

[tool.datamodel-codegen.profiles.api]
target-python-version = "3.10"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    input_data = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "firstName": {"type": "string"}
  }
}
"""
    input_file = tmp_path / "schema.json"
    input_file.write_text(input_data)

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=input_file,
            output_path=output_file.resolve(),
            assert_func=assert_file_content,
            expected_file=EXPECTED_PYPROJECT_PROFILE_PATH / "cli_override.py",
            extra_args=[
                "--profile",
                "api",
                "--disable-timestamp",
                "--target-python-version",
                "3.11",
                "--use-union-operator",
            ],
        )


def test_ignore_pyproject_with_profile(tmp_path: Path) -> None:
    """Test that --ignore-pyproject ignores --profile as well."""
    pyproject_toml = """
[tool.datamodel-codegen]
snake-case-field = true

[tool.datamodel-codegen.profiles.api]
target-python-version = "3.11"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    input_data = """
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "firstName": {"type": "string"}
  }
}
"""
    input_file = tmp_path / "schema.json"
    input_file.write_text(input_data)
    output_file = tmp_path / "output.py"

    with chdir(tmp_path):
        run_main_with_args(
            [
                "--input",
                str(input_file),
                "--output",
                str(output_file),
                "--ignore-pyproject",
                "--profile",
                "api",
                "--disable-timestamp",
            ],
        )
        output_content = output_file.read_text()
        assert "firstName" in output_content
        assert "first_name" not in output_content


def test_profile_without_pyproject_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --profile without pyproject.toml raises an error."""
    input_file = tmp_path / "schema.json"
    input_file.write_text('{"type": "object"}')
    output_file = tmp_path / "output.py"

    with chdir(tmp_path):
        return_code = run_main_with_args(
            ["--input", str(input_file), "--output", str(output_file), "--profile", "api"],
            expected_exit=Exit.ERROR,
            capsys=capsys,
        )
        assert return_code == Exit.ERROR
        captured = capsys.readouterr()
        assert "no [tool.datamodel-codegen] section found" in captured.err.lower()


@freeze_time("2019-07-26")
def test_allof_with_description_generates_class_not_alias(output_file: Path) -> None:
    """Test that allOf with description generates class definition, not alias."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "allof_with_description_only.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_allof_with_description_only" / "output.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-schema-description",
        ],
    )
