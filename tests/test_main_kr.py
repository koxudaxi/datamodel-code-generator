"""Tests for main CLI functionality with Korean locale settings."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import black
import pydantic
import pytest
from packaging import version

from datamodel_code_generator import MIN_VERSION, chdir, inferred_message
from datamodel_code_generator.__main__ import Exit, main
from datamodel_code_generator.arguments import arg_parser
from tests.conftest import create_assert_file_content, freeze_time
from tests.main.conftest import run_main_and_assert, run_main_with_args

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

DATA_PATH: Path = Path(__file__).parent / "data"
OPEN_API_DATA_PATH: Path = DATA_PATH / "openapi"
JSON_SCHEMA_DATA_PATH: Path = DATA_PATH / "jsonschema"
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


def test_main_modular_no_file(capsys: pytest.CaptureFixture[str]) -> None:
    """Test main function on modular file with no output name outputs to stdout."""
    run_main_with_args(["--input", str(OPEN_API_DATA_PATH / "modular.yaml")], expected_exit=Exit.OK)
    captured = capsys.readouterr()
    assert "class Chocolate" in captured.out
    assert "class Source" in captured.out


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


@pytest.mark.cli_doc(
    options=["--use-schema-description"],
    input_schema="openapi/api_multiline_docstrings.yaml",
    cli_args=["--use-schema-description"],
    golden_output="main_kr/main_use_schema_description/output.py",
    related_options=["--use-field-description", "--use-inline-field-description"],
)
@freeze_time("2019-07-26")
def test_main_use_schema_description(output_file: Path) -> None:
    """Use schema description as class docstring.

    The `--use-schema-description` flag extracts the `description` property from
    schema definitions and adds it as a docstring to the generated class. This is
    useful for preserving documentation from your schema in the generated code.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_schema_description" / "output.py",
        extra_args=["--use-schema-description"],
    )


@freeze_time("2019-07-26")
def test_main_docstring_special_chars(output_file: Path) -> None:
    """Escape special characters in docstrings.

    Backslashes and triple quotes in schema descriptions must be escaped
    to prevent Python syntax errors and type checker warnings. See GitHub
    issue #1808.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "docstring_special_chars.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_docstring_special_chars" / "output.py",
        extra_args=["--use-schema-description", "--use-field-description"],
    )


@pytest.mark.cli_doc(
    options=["--use-field-description"],
    input_schema="openapi/api_multiline_docstrings.yaml",
    cli_args=["--use-field-description"],
    golden_output="main_kr/main_use_field_description/output.py",
    related_options=["--use-schema-description", "--use-inline-field-description"],
)
@freeze_time("2022-11-11")
def test_main_use_field_description(output_file: Path) -> None:
    """Add field descriptions using Pydantic Field().

    The `--use-field-description` flag adds the `description` property from
    schema fields as the `description` parameter in Pydantic Field(). This
    provides documentation that is accessible via model schema and OpenAPI docs.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_field_description" / "output.py",
        extra_args=["--use-field-description"],
    )


@pytest.mark.cli_doc(
    options=["--use-inline-field-description"],
    input_schema="openapi/api_multiline_docstrings.yaml",
    cli_args=["--use-inline-field-description"],
    golden_output="main_kr/main_use_inline_field_description/output.py",
    related_options=["--use-field-description", "--use-schema-description"],
)
@freeze_time("2022-11-11")
def test_main_use_inline_field_description(output_file: Path) -> None:
    """Add field descriptions as inline comments.

    The `--use-inline-field-description` flag adds the `description` property from
    schema fields as inline comments after each field definition. This provides
    documentation without using Field() wrappers.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "api_multiline_docstrings.yaml",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_inline_field_description" / "output.py",
        extra_args=["--use-inline-field-description"],
    )


@pytest.mark.cli_doc(
    options=["--use-field-description-example"],
    input_schema="jsonschema/extras.json",
    cli_args=["--use-field-description-example"],
    golden_output="main_kr/main_use_field_description_example/output.py",
    related_options=["--use-field-description", "--use-inline-field-description"],
)
@freeze_time("2022-11-11")
def test_main_use_field_description_example(output_file: Path) -> None:
    """Add field examples to docstrings.

    The `--use-field-description-example` flag adds the `example` or `examples`
    property from schema fields as docstrings. This provides documentation that
    is visible in IDE intellisense.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_field_description_example" / "output.py",
        extra_args=["--use-field-description-example"],
    )


@pytest.mark.cli_doc(
    options=["--use-field-description", "--use-field-description-example"],
    input_schema="jsonschema/extras.json",
    cli_args=["--use-field-description", "--use-field-description-example"],
    golden_output="main_kr/main_use_field_description_with_example/output.py",
    related_options=["--use-inline-field-description"],
)
@freeze_time("2022-11-11")
def test_main_use_field_description_with_example(output_file: Path) -> None:
    """Add field descriptions and examples to docstrings.

    When both `--use-field-description` and `--use-field-description-example` are used,
    the docstring includes both the description and example(s).
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "extras.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_field_description_with_example" / "output.py",
        extra_args=["--use-field-description", "--use-field-description-example"],
    )


@pytest.mark.cli_doc(
    options=["--use-inline-field-description", "--use-field-description-example"],
    input_schema="jsonschema/multiline_description_with_example.json",
    cli_args=["--use-inline-field-description", "--use-field-description-example"],
    golden_output="main_kr/main_use_inline_field_description_with_example/output.py",
    related_options=["--use-field-description"],
)
@freeze_time("2022-11-11")
def test_main_use_inline_field_description_with_example(output_file: Path) -> None:
    """Add field descriptions and examples to docstrings with inline description.

    When both `--use-inline-field-description` and `--use-field-description-example` are used,
    multi-line descriptions and examples are included in the docstring.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "multiline_description_with_example.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_inline_field_description_with_example" / "output.py",
        extra_args=["--use-inline-field-description", "--use-field-description-example"],
    )


@freeze_time("2022-11-11")
def test_main_use_inline_field_description_example_only(output_file: Path) -> None:
    """Test single-line description with use_inline_field_description and use_field_description_example.

    When both flags are used with a single-line description, only the example
    appears in the docstring (the single-line description stays in Field()).
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "single_line_description_with_example.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_inline_field_description_example_only" / "output.py",
        extra_args=["--use-inline-field-description", "--use-field-description-example"],
    )


@freeze_time("2022-11-11")
def test_main_use_field_description_example_multiple(output_file: Path) -> None:
    """Test multiple examples in docstring.

    When a field has multiple examples, they are formatted as a bulleted list.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "multiple_examples.json",
        output_path=output_file,
        input_file_type=None,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "main_use_field_description_example_multiple" / "output.py",
        extra_args=["--use-field-description-example"],
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


@pytest.mark.cli_doc(
    options=["--generate-pyproject-config"],
    cli_args=["--generate-pyproject-config", "--input", "schema.yaml", "--output", "model.py"],
    expected_stdout="main_kr/generate_pyproject_config/basic.txt",
)
def test_generate_pyproject_config_basic(capsys: pytest.CaptureFixture[str]) -> None:
    """Generate pyproject.toml configuration from CLI arguments.

    The `--generate-pyproject-config` flag outputs a pyproject.toml configuration
    snippet based on the provided CLI arguments. This is useful for converting
    a working CLI command into a reusable configuration file.
    """
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


@pytest.mark.cli_doc(
    options=["--generate-cli-command"],
    cli_args=["--generate-cli-command"],
    config_content="""[tool.datamodel-codegen]
input = "schema.yaml"
output = "model.py"
""",
    expected_stdout="main_kr/generate_cli_command/basic.txt",
)
def test_generate_cli_command_basic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Generate CLI command from pyproject.toml configuration.

    The `--generate-cli-command` flag reads your pyproject.toml configuration
    and outputs the equivalent CLI command. This is useful for debugging
    configuration issues or sharing commands with others.
    """
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
target-python-version = "3.10"
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
target-python-version = "3.10"
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
target-python-version = "3.10"
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
target-python-version = "3.10"
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
target-python-version = "3.10"
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


@pytest.mark.cli_doc(
    options=["--use-decimal-for-multiple-of"],
    input_schema="jsonschema/use_decimal_for_multiple_of.json",
    cli_args=["--use-decimal-for-multiple-of"],
    golden_output="main_kr/use_decimal_for_multiple_of/output.py",
)
@freeze_time("2019-07-26")
def test_use_decimal_for_multiple_of(output_file: Path) -> None:
    """Generate Decimal types for fields with multipleOf constraint.

    The `--use-decimal-for-multiple-of` flag generates `condecimal` or `Decimal`
    types for numeric fields that have a `multipleOf` constraint. This ensures
    precise decimal arithmetic when validating values against the constraint.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_decimal_for_multiple_of.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "use_decimal_for_multiple_of" / "output.py",
        extra_args=["--use-decimal-for-multiple-of"],
    )


@pytest.mark.cli_doc(
    options=["--use-pendulum"],
    input_schema="jsonschema/use_pendulum.json",
    cli_args=["--use-pendulum"],
    golden_output="main_kr/use_pendulum/output.py",
)
@freeze_time("2019-07-26")
def test_use_pendulum(output_file: Path) -> None:
    """Use pendulum types for date/time fields instead of datetime module.

    The `--use-pendulum` flag generates pendulum library types (DateTime, Date,
    Time, Duration) instead of standard datetime types. This is useful when
    working with the pendulum library for enhanced timezone and date handling.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_pendulum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "use_pendulum" / "output.py",
        extra_args=["--use-pendulum"],
    )


@pytest.mark.cli_doc(
    options=["--use-non-positive-negative-number-constrained-types"],
    input_schema="jsonschema/use_non_positive_negative.json",
    cli_args=["--use-non-positive-negative-number-constrained-types"],
    golden_output="main_kr/use_non_positive_negative/output.py",
)
@pytest.mark.skipif(pydantic.VERSION < "2.0.0", reason="Require Pydantic version 2.0.0 or later")
@freeze_time("2019-07-26")
def test_use_non_positive_negative_number_constrained_types(output_file: Path) -> None:
    """Use NonPositive/NonNegative types for number constraints.

    The `--use-non-positive-negative-number-constrained-types` flag generates
    Pydantic's NonPositiveInt, NonNegativeInt, NonPositiveFloat, and NonNegativeFloat
    types for fields with minimum: 0 or maximum: 0 constraints, instead of using
    conint/confloat with ge/le parameters.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_non_positive_negative.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "use_non_positive_negative" / "output.py",
        extra_args=["--use-non-positive-negative-number-constrained-types"],
    )


@pytest.mark.cli_doc(
    options=["--include-path-parameters"],
    input_schema="openapi/include_path_parameters.yaml",
    cli_args=["--include-path-parameters", "--openapi-scopes", "schemas", "paths", "parameters"],
    golden_output="main_kr/include_path_parameters/output.py",
)
@freeze_time("2019-07-26")
def test_include_path_parameters(output_file: Path) -> None:
    """Include OpenAPI path parameters in generated parameter models.

    The `--include-path-parameters` flag adds path parameters (like /users/{userId})
    to the generated request parameter models. By default, only query parameters
    are included. Use this with `--openapi-scopes parameters` to generate parameter
    models that include both path and query parameters.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "include_path_parameters.yaml",
        output_path=output_file,
        input_file_type="openapi",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "include_path_parameters" / "output.py",
        extra_args=["--include-path-parameters", "--openapi-scopes", "schemas", "paths", "parameters"],
    )


@pytest.mark.cli_doc(
    options=["--no-alias"],
    input_schema="jsonschema/no_alias.json",
    cli_args=["--no-alias"],
    golden_output="main_kr/no_alias/with_option.py",
    comparison_output="main_kr/no_alias/without_option.py",
)
@freeze_time("2019-07-26")
def test_no_alias(output_file: Path) -> None:
    """Disable Field alias generation for non-Python-safe property names.

    The `--no-alias` flag disables automatic alias generation when JSON property
    names contain characters invalid in Python (like hyphens). Without this flag,
    fields are renamed to Python-safe names with `Field(alias='original-name')`.
    With this flag, only Python-safe names are used without aliases.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "no_alias.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "no_alias" / "with_option.py",
        extra_args=["--no-alias"],
    )


@pytest.mark.cli_doc(
    options=["--custom-file-header"],
    input_schema="jsonschema/no_alias.json",
    cli_args=["--custom-file-header", "# Copyright 2024 MyCompany"],
    golden_output="main_kr/custom_file_header/with_option.py",
    comparison_output="main_kr/custom_file_header/without_option.py",
)
@freeze_time("2019-07-26")
def test_custom_file_header(output_file: Path) -> None:
    """Add custom header text to the generated file.

    The `--custom-file-header` flag replaces the default "generated by datamodel-codegen"
    header with custom text. This is useful for adding copyright notices, license
    headers, or other metadata to generated files.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "no_alias.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "custom_file_header" / "with_option.py",
        extra_args=["--custom-file-header", "# Copyright 2024 MyCompany"],
    )


@pytest.mark.cli_doc(
    options=["--url", "--http-headers"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--url", "https://api.example.com/schema.json", "--http-headers", "Authorization:Bearer token"],
    golden_output="main_kr/url_with_headers/output.py",
)
@freeze_time("2019-07-26")
def test_url_with_http_headers(mocker: MockerFixture, output_file: Path) -> None:
    """Fetch schema from URL with custom HTTP headers.

    The `--url` flag specifies a remote URL to fetch the schema from instead of
    a local file. The `--http-headers` flag adds custom HTTP headers to the request,
    useful for authentication (e.g., Bearer tokens) or custom API requirements.
    Format: `HeaderName:HeaderValue`.
    """
    mock_response = Mock()
    mock_response.text = JSON_SCHEMA_DATA_PATH.joinpath("pet_simple.json").read_text()

    mocker.patch("httpx.get", return_value=mock_response)

    return_code = main([
        "--url",
        "https://api.example.com/schema.json",
        "--output",
        str(output_file),
        "--input-file-type",
        "jsonschema",
        "--http-headers",
        "Authorization:Bearer token",
    ])
    assert return_code == 0
    assert_file_content(output_file, EXPECTED_MAIN_KR_PATH / "url_with_headers" / "output.py")


@pytest.mark.cli_doc(
    options=["--input"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--input", "pet_simple.json", "--output", "output.py"],
    golden_output="main_kr/input_output/output.py",
)
@freeze_time("2019-07-26")
def test_input_option(output_file: Path) -> None:
    """Specify the input schema file path.

    The `--input` flag specifies the path to the schema file (JSON Schema,
    OpenAPI, GraphQL, etc.). Multiple input files can be specified to merge
    schemas. Required unless using `--url` to fetch schema from a URL.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pet_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "input_output" / "output.py",
    )


@pytest.mark.cli_doc(
    options=["--output"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--input", "pet_simple.json", "--output", "output.py"],
    golden_output="main_kr/input_output/output.py",
)
@freeze_time("2019-07-26")
def test_output_option(output_file: Path) -> None:
    """Specify the destination path for generated Python code.

    The `--output` flag specifies where to write the generated Python code.
    It can be either a file path (single-file output) or a directory path
    (multi-file output for modular schemas). If omitted, the generated code
    is written to stdout.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pet_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "input_output" / "output.py",
    )


@pytest.mark.cli_doc(
    options=["--encoding"],
    input_schema="jsonschema/encoding_test.json",
    cli_args=["--encoding", "utf-8"],
    golden_output="main_kr/encoding/output.py",
)
@freeze_time("2019-07-26")
def test_encoding_option(output_file: Path) -> None:
    """Specify character encoding for input and output files.

    The `--encoding` flag sets the character encoding used when reading
    the schema file and writing the generated Python code. This is useful
    for schemas containing non-ASCII characters (e.g., Japanese, Chinese).
    Default is UTF-8, which is the standard encoding for JSON and most modern text files.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "encoding_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "encoding" / "output.py",
        extra_args=["--encoding", "utf-8"],
    )


@pytest.mark.cli_doc(
    options=["--formatters"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--formatters", "isort"],
    golden_output="main_kr/formatters/output.py",
)
@freeze_time("2019-07-26")
def test_formatters_option(output_file: Path) -> None:
    """Specify code formatters to apply to generated output.

    The `--formatters` flag specifies which code formatters to apply to
    the generated Python code. Available formatters are: black, isort,
    ruff, yapf, autopep8, autoflake. Default is [black, isort].
    Use this to customize formatting or disable formatters entirely.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pet_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "formatters" / "output.py",
        extra_args=["--formatters", "isort"],
    )


@pytest.mark.cli_doc(
    options=["--custom-formatters-kwargs"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--custom-formatters-kwargs", "formatter_kwargs.json"],
    golden_output="main_kr/input_output/output.py",
)
@freeze_time("2019-07-26")
def test_custom_formatters_kwargs_option(output_file: Path) -> None:
    """Pass custom arguments to custom formatters via JSON file.

    The `--custom-formatters-kwargs` flag accepts a path to a JSON file containing
    custom configuration for custom formatters (used with --custom-formatters).
    The file should contain a JSON object mapping formatter names to their kwargs.

    Note: This option is primarily used with --custom-formatters to pass
    configuration to user-defined formatter modules.
    """
    # Simple test - the option is accepted. Full usage requires custom formatter module.
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pet_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "input_output" / "output.py",
        extra_args=["--custom-formatters-kwargs", str(DATA_PATH / "config" / "formatter_kwargs.json")],
    )


@pytest.mark.cli_doc(
    options=["--http-ignore-tls"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--url", "https://api.example.com/schema.json", "--http-ignore-tls"],
    golden_output="main_kr/url_with_headers/output.py",
)
@freeze_time("2019-07-26")
def test_http_ignore_tls(output_file: Path) -> None:
    """Disable TLS certificate verification for HTTPS requests.

    The `--http-ignore-tls` flag disables SSL/TLS certificate verification
    when fetching schemas from HTTPS URLs. This is useful for development
    environments with self-signed certificates. Not recommended for production.
    """
    mock_response = Mock()
    mock_response.text = JSON_SCHEMA_DATA_PATH.joinpath("pet_simple.json").read_text()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        return_code = main([
            "--url",
            "https://api.example.com/schema.json",
            "--output",
            str(output_file),
            "--input-file-type",
            "jsonschema",
            "--http-ignore-tls",
        ])
        assert return_code == 0
        # Verify that verify=False was passed to httpx.get
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("verify") is False


@pytest.mark.cli_doc(
    options=["--http-query-parameters"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--url", "https://api.example.com/schema.json", "--http-query-parameters", "version=v2", "format=json"],
    golden_output="main_kr/url_with_headers/output.py",
)
@freeze_time("2019-07-26")
def test_http_query_parameters(output_file: Path) -> None:
    """Add query parameters to HTTP requests for remote schemas.

    The `--http-query-parameters` flag adds query parameters to HTTP requests
    when fetching schemas from URLs. Useful for APIs that require version
    or format parameters. Format: `key=value`. Multiple parameters can be
    specified: `--http-query-parameters version=v2 format=json`.
    """
    mock_response = Mock()
    mock_response.text = JSON_SCHEMA_DATA_PATH.joinpath("pet_simple.json").read_text()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        return_code = main([
            "--url",
            "https://api.example.com/schema.json",
            "--output",
            str(output_file),
            "--input-file-type",
            "jsonschema",
            "--http-query-parameters",
            "version=v2",
            "format=json",
        ])
        assert return_code == 0
        # Verify query parameters were passed as list of tuples
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert "params" in call_kwargs
        # params is a list of tuples: [("version", "v2"), ("format", "json")]
        params = call_kwargs["params"]
        assert ("version", "v2") in params
        assert ("format", "json") in params


@pytest.mark.cli_doc(
    options=["--http-timeout"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--url", "https://api.example.com/schema.json", "--http-timeout", "60"],
    golden_output="main_kr/url_with_headers/output.py",
)
@freeze_time("2019-07-26")
def test_http_timeout(output_file: Path) -> None:
    """Set timeout for HTTP requests to remote hosts.

    The `--http-timeout` flag sets the timeout in seconds for HTTP requests
    when fetching schemas from URLs. Useful for slow servers or large schemas.
    Default is 30 seconds.
    """
    mock_response = Mock()
    mock_response.text = JSON_SCHEMA_DATA_PATH.joinpath("pet_simple.json").read_text()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        return_code = main([
            "--url",
            "https://api.example.com/schema.json",
            "--output",
            str(output_file),
            "--input-file-type",
            "jsonschema",
            "--http-timeout",
            "60",
        ])
        assert return_code == 0
        # Verify that timeout=60 was passed to httpx.get
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("timeout") == 60.0


@pytest.mark.cli_doc(
    options=["--ignore-pyproject"],
    input_schema="jsonschema/ignore_pyproject_example.json",
    cli_args=["--ignore-pyproject"],
    golden_output="main_kr/ignore_pyproject/output.py",
    comparison_output="main_kr/ignore_pyproject/without_option.py",
)
@freeze_time("2019-07-26")
def test_ignore_pyproject_cli_doc(output_file: Path, tmp_path: Path) -> None:
    """Ignore pyproject.toml configuration file.

    The `--ignore-pyproject` flag tells datamodel-codegen to ignore any
    [tool.datamodel-codegen] configuration in pyproject.toml. This is useful
    when you want to override project defaults with CLI arguments, or when
    testing without project configuration.
    """
    # Create a pyproject.toml with snake-case-field to demonstrate ignoring
    pyproject_toml = """
[tool.datamodel-codegen]
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
            expected_file=EXPECTED_MAIN_KR_PATH / "ignore_pyproject" / "output.py",
            extra_args=["--ignore-pyproject", "--disable-timestamp"],
        )


@pytest.mark.cli_doc(
    options=["--shared-module-name"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--shared-module-name", "my_shared"],
    golden_output="main_kr/input_output/output.py",
)
@freeze_time("2019-07-26")
def test_shared_module_name(output_file: Path) -> None:
    """Customize the name of the shared module for deduplicated models.

    The `--shared-module-name` flag sets the name of the shared module created
    when using `--reuse-model` with `--reuse-scope=tree`. This module contains
    deduplicated models that are referenced from multiple files. Default is
    `shared`. Use this if your schema already has a file named `shared`.

    Note: This option only affects modular output with tree-level model reuse.
    """
    # Simple test - the option is accepted but only affects modular output with reuse
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pet_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "input_output" / "output.py",
        extra_args=["--shared-module-name", "my_shared"],
    )


@pytest.mark.cli_doc(
    options=["--use-exact-imports"],
    input_schema="jsonschema/pet_simple.json",
    cli_args=["--use-exact-imports"],
    golden_output="main_kr/input_output/output.py",
)
@freeze_time("2019-07-26")
def test_use_exact_imports(output_file: Path) -> None:
    """Import exact types instead of modules.

    The `--use-exact-imports` flag changes import style from module imports
    to exact type imports. For example, instead of `from . import foo` then
    `foo.Bar`, it generates `from .foo import Bar`. This can make the generated
    code more explicit and easier to read.

    Note: This option primarily affects modular output where imports between
    modules are generated. For single-file output, the difference is minimal.
    """
    # Simple test - the option is accepted and works for single file output
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "pet_simple.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "input_output" / "output.py",
        extra_args=["--use-exact-imports"],
    )


@pytest.mark.cli_doc(
    options=["--target-python-version"],
    input_schema="jsonschema/person.json",
    cli_args=["--target-python-version", "3.10", "--use-standard-collections"],
    version_outputs={
        "3.10": "main_kr/target_python_version/py310.py",
    },
    primary=True,
)
@freeze_time("2019-07-26")
def test_target_python_version_outputs(output_file: Path) -> None:
    """Target Python version for generated code syntax and imports.

    The `--target-python-version` flag controls Python version-specific syntax:

    - **Python 3.10-3.11**: Uses `X | None` union operator, `TypeAlias` annotation
    - **Python 3.12+**: Uses `type` statement for type aliases

    This affects import statements and type annotation syntax in generated code.
    """
    # Test with Python 3.10 style
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "target_python_version" / "py310.py",
        extra_args=["--target-python-version", "3.10", "--use-standard-collections"],
    )


@pytest.mark.cli_doc(
    options=["--target-pydantic-version"],
    input_schema="jsonschema/person.json",
    cli_args=[
        "--target-pydantic-version",
        "2.11",
        "--allow-population-by-field-name",
        "--output-model-type",
        "pydantic_v2.BaseModel",
    ],
    golden_output="main_kr/target_pydantic_version/v2_11.py",
    primary=True,
)
@freeze_time("2019-07-26")
def test_target_pydantic_version(output_file: Path) -> None:
    """Target Pydantic version for generated code compatibility.

    The `--target-pydantic-version` flag controls Pydantic version-specific config:

    - **2**: Uses `populate_by_name=True` (compatible with Pydantic 2.0-2.10)
    - **2.11**: Uses `validate_by_name=True` (for Pydantic 2.11+)

    This prevents breaking changes when generated code is used on older Pydantic versions.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "person.json",
        output_path=output_file,
        assert_func=assert_file_content,
        expected_file=EXPECTED_MAIN_KR_PATH / "target_pydantic_version" / "v2_11.py",
        extra_args=[
            "--target-pydantic-version",
            "2.11",
            "--allow-population-by-field-name",
            "--output-model-type",
            "pydantic_v2.BaseModel",
        ],
    )


def test_generate_prompt_basic(capsys: pytest.CaptureFixture[str]) -> None:
    """Generate a prompt for consulting LLMs about CLI options.

    The `--generate-prompt` flag outputs a formatted prompt containing:
    - Current CLI options
    - Options organized by category with descriptions
    - Full help text

    This prompt can be copied to ChatGPT, Claude, or other LLMs to get
    recommendations for appropriate CLI options.
    """
    return_code = main(["--generate-prompt"])
    assert return_code == Exit.OK
    captured = capsys.readouterr()

    # Verify structure
    assert "# datamodel-code-generator CLI Options Consultation" in captured.out
    assert "## Current CLI Options" in captured.out
    assert "## Options by Category" in captured.out
    assert "## All Available Options (Full Help)" in captured.out
    assert "## Instructions" in captured.out
    assert "(No options specified)" in captured.out


def test_generate_prompt_with_question(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-prompt with a question argument."""
    question = "How do I convert enums to Literal types?"
    return_code = main(["--generate-prompt", question])
    assert return_code == Exit.OK
    captured = capsys.readouterr()

    assert "## Your Question" in captured.out
    assert question in captured.out


def test_generate_prompt_with_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-prompt with other CLI options set."""
    return_code = main([
        "--input",
        "schema.json",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--snake-case-field",
        "--generate-prompt",
        "What other options should I use?",
    ])
    assert return_code == Exit.OK
    captured = capsys.readouterr()

    # Verify options are shown
    assert "--input schema.json" in captured.out
    assert "--output-model-type pydantic_v2.BaseModel" in captured.out
    assert "--snake-case-field" in captured.out
    assert "What other options should I use?" in captured.out


def test_generate_prompt_with_list_options(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-prompt with list options (e.g., --strict-types)."""
    return_code = main([
        "--strict-types",
        "str",
        "int",
        "--generate-prompt",
    ])
    assert return_code == Exit.OK
    captured = capsys.readouterr()

    # Verify list options are formatted correctly
    assert "--strict-types str int" in captured.out
