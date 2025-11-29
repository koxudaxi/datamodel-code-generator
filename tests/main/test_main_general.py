"""General integration tests for main code generation functionality."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import (
    DataModelType,
    Error,
    InputFileType,
    generate,
    snooper_to_methods,
)
from datamodel_code_generator.__main__ import Config, Exit
from datamodel_code_generator.format import PythonVersion
from tests.conftest import create_assert_file_content, freeze_time
from tests.main.conftest import (
    DATA_PATH,
    EXPECTED_MAIN_PATH,
    PYTHON_DATA_PATH,
    TIMESTAMP,
    run_main_and_assert,
    run_main_with_args,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

assert_file_content = create_assert_file_content(EXPECTED_MAIN_PATH)


def test_debug(mocker: MockerFixture) -> None:
    """Test debug flag functionality."""
    with pytest.raises(expected_exception=SystemExit):
        run_main_with_args(["--debug", "--help"])

    mocker.patch("datamodel_code_generator.pysnooper", None)
    with pytest.raises(expected_exception=SystemExit):
        run_main_with_args(["--debug", "--help"])


def test_snooper_to_methods_without_pysnooper(mocker: MockerFixture) -> None:
    """Test snooper_to_methods function without pysnooper installed."""
    mocker.patch("datamodel_code_generator.pysnooper", None)
    mock = mocker.Mock()
    assert snooper_to_methods()(mock) == mock


@pytest.mark.parametrize(argnames="no_color", argvalues=[False, True])
def test_show_help(no_color: bool, capsys: pytest.CaptureFixture[str]) -> None:
    """Test help output with and without color."""
    args = ["--no-color"] if no_color else []
    args += ["--help"]

    with pytest.raises(expected_exception=SystemExit) as context:
        run_main_with_args(args)
    assert context.value.code == Exit.OK

    output = capsys.readouterr().out
    assert ("\x1b" not in output) == no_color


def test_show_help_when_no_input(mocker: MockerFixture) -> None:
    """Test help display when no input is provided."""
    print_help_mock = mocker.patch("datamodel_code_generator.__main__.arg_parser.print_help")
    isatty_mock = mocker.patch("sys.stdin.isatty", return_value=True)
    return_code: Exit = run_main_with_args([], expected_exit=Exit.ERROR)
    assert return_code == Exit.ERROR
    assert isatty_mock.called
    assert print_help_mock.called


def test_no_args_has_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """No argument should have a default value set because it would override pyproject.toml values.

    Default values are set in __main__.Config class.
    """
    namespace = Namespace()
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace)
    run_main_with_args([], expected_exit=Exit.ERROR)
    for field in Config.get_fields():
        assert getattr(namespace, field, None) is None


def test_space_and_special_characters_dict(output_file: Path) -> None:
    """Test dict input with space and special characters."""
    run_main_and_assert(
        input_path=PYTHON_DATA_PATH / "space_and_special_characters_dict.py",
        output_path=output_file,
        input_file_type="dict",
        assert_func=assert_file_content,
    )


@freeze_time("2024-12-14")
def test_direct_input_dict(tmp_path: Path) -> None:
    """Test direct dict input code generation."""
    output_file = tmp_path / "output.py"
    generate(
        {"foo": 1, "bar": {"baz": 2}},
        input_file_type=InputFileType.Dict,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
        snake_case_field=True,
    )
    assert_file_content(output_file)


@freeze_time(TIMESTAMP)
def test_frozen_dataclasses(tmp_path: Path) -> None:
    """Test --frozen-dataclasses flag functionality."""
    output_file = tmp_path / "output.py"
    generate(
        DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.DataclassesDataclass,
        frozen_dataclasses=True,
    )
    assert_file_content(output_file)


@freeze_time(TIMESTAMP)
def test_frozen_dataclasses_with_keyword_only(tmp_path: Path) -> None:
    """Test --frozen-dataclasses with --keyword-only flag combination."""
    output_file = tmp_path / "output.py"
    generate(
        DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.DataclassesDataclass,
        frozen_dataclasses=True,
        keyword_only=True,
        target_python_version=PythonVersion.PY_310,
    )
    assert_file_content(output_file, "frozen_dataclasses_keyword_only.py")


@freeze_time(TIMESTAMP)
def test_frozen_dataclasses_command_line(output_file: Path) -> None:
    """Test --frozen-dataclasses flag via command line."""
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="frozen_dataclasses.py",
        extra_args=["--output-model-type", "dataclasses.dataclass", "--frozen-dataclasses"],
    )


@freeze_time(TIMESTAMP)
def test_frozen_dataclasses_with_keyword_only_command_line(output_file: Path) -> None:
    """Test --frozen-dataclasses with --keyword-only flag via command line."""
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="frozen_dataclasses_keyword_only.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--frozen-dataclasses",
            "--keyword-only",
            "--target-python-version",
            "3.10",
        ],
    )


def test_filename_with_newline_injection(tmp_path: Path) -> None:
    """Test that filenames with newlines cannot inject code into generated files."""
    schema_content = """{"type": "object", "properties": {"name": {"type": "string"}}}"""

    malicious_filename = """schema.json
# INJECTED CODE:
import os
os.system('echo INJECTED')
# END INJECTION"""

    output_path = tmp_path / "output.py"

    generate(
        input_=schema_content,
        input_filename=malicious_filename,
        input_file_type=InputFileType.JsonSchema,
        output=output_path,
    )

    generated_content = output_path.read_text()

    assert "#   filename:  schema.json # INJECTED CODE: import os" in generated_content, (
        "Filename not properly sanitized"
    )

    assert not any(
        line.strip().startswith("import os") and not line.strip().startswith("#")
        for line in generated_content.split("\n")
    )
    assert not any("os.system" in line and not line.strip().startswith("#") for line in generated_content.split("\n"))

    compile(generated_content, str(output_path), "exec")


def test_filename_with_various_control_characters(tmp_path: Path) -> None:
    """Test that various control characters in filenames are properly sanitized."""
    schema_content = """{"type": "object", "properties": {"test": {"type": "string"}}}"""

    test_cases = [
        ("newline", "schema.json\nimport os; os.system('echo INJECTED')"),
        ("carriage_return", "schema.json\rimport os; os.system('echo INJECTED')"),
        ("crlf", "schema.json\r\nimport os; os.system('echo INJECTED')"),
        ("tab_newline", "schema.json\t\nimport os; os.system('echo TAB')"),
        ("form_feed", "schema.json\f\nimport os; os.system('echo FF')"),
        ("vertical_tab", "schema.json\v\nimport os; os.system('echo VT')"),
        ("unicode_line_separator", "schema.json\u2028import os; os.system('echo U2028')"),
        ("unicode_paragraph_separator", "schema.json\u2029import os; os.system('echo U2029')"),
        ("multiple_newlines", "schema.json\n\n\nimport os; os.system('echo MULTI')"),
        ("mixed_characters", "schema.json\n\r\t\nimport os; os.system('echo MIXED')"),
    ]

    for test_name, malicious_filename in test_cases:
        output_path = tmp_path / "output.py"

        generate(
            input_=schema_content,
            input_filename=malicious_filename,
            input_file_type=InputFileType.JsonSchema,
            output=output_path,
        )

        generated_content = output_path.read_text()

        assert not any(
            line.strip().startswith("import ") and not line.strip().startswith("#")
            for line in generated_content.split("\n")
        ), f"Injection found for {test_name}"

        assert not any(
            "os.system" in line and not line.strip().startswith("#") for line in generated_content.split("\n")
        ), f"System call found for {test_name}"

        compile(generated_content, str(output_path), "exec")


def test_generate_with_nonexistent_file(tmp_path: Path) -> None:
    """Test that generating from a nonexistent file raises an error."""
    nonexistent_file = tmp_path / "nonexistent.json"
    output_file = tmp_path / "output.py"

    with pytest.raises(Error, match="File not found"):
        generate(
            input_=nonexistent_file,
            output=output_file,
        )


def test_generate_with_invalid_file_format(tmp_path: Path) -> None:
    """Test that generating from an invalid file format raises an error."""
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("this is not valid json or yaml or anything")
    output_file = tmp_path / "output.py"

    with pytest.raises(Error, match="Invalid file format"):
        generate(
            input_=invalid_file,
            output=output_file,
        )
