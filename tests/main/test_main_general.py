"""General integration tests for main code generation functionality."""

from __future__ import annotations

from argparse import ArgumentTypeError, Namespace
from typing import TYPE_CHECKING

import black
import pytest
from inline_snapshot import snapshot

from datamodel_code_generator import (
    AllExportsScope,
    DataModelType,
    Error,
    GeneratedModules,
    InputFileType,
    SchemaParseError,
    chdir,
    generate,
    snooper_to_methods,
)
from datamodel_code_generator.__main__ import Config, Exit
from datamodel_code_generator.arguments import _dataclass_arguments
from datamodel_code_generator.format import CodeFormatter, PythonVersion
from datamodel_code_generator.parser.openapi import OpenAPIParser
from tests.conftest import assert_output, create_assert_file_content, freeze_time
from tests.main.conftest import (
    DATA_PATH,
    EXPECTED_MAIN_PATH,
    JSON_SCHEMA_DATA_PATH,
    OPEN_API_DATA_PATH,
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

    # Simulate pysnooper not being installed by making import fail
    mocker.patch.dict("sys.modules", {"pysnooper": None})
    with pytest.raises(expected_exception=SystemExit):
        run_main_with_args(["--debug", "--help"])


def test_snooper_to_methods_without_pysnooper(mocker: MockerFixture) -> None:
    """Test snooper_to_methods function without pysnooper installed."""
    # Simulate pysnooper not being installed by making import fail
    mocker.patch.dict("sys.modules", {"pysnooper": None})
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
@pytest.mark.parametrize(
    ("keyword_only", "target_python_version", "expected_file"),
    [
        (False, PythonVersion.PY_310, "frozen_dataclasses.py"),
        (True, PythonVersion.PY_310, "frozen_dataclasses_keyword_only.py"),
    ],
)
def test_frozen_dataclasses(
    tmp_path: Path,
    keyword_only: bool,
    target_python_version: PythonVersion,
    expected_file: str,
) -> None:
    """Test --frozen-dataclasses flag functionality."""
    output_file = tmp_path / "output.py"
    generate(
        DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.DataclassesDataclass,
        frozen_dataclasses=True,
        keyword_only=keyword_only,
        target_python_version=target_python_version,
    )
    assert_file_content(output_file, expected_file)


@pytest.mark.cli_doc(
    options=["--frozen-dataclasses"],
    input_schema="jsonschema/simple_frozen_test.json",
    cli_args=["--output-model-type", "dataclasses.dataclass", "--frozen-dataclasses"],
    golden_output="frozen_dataclasses.py",
    related_options=["--keyword-only", "--output-model-type"],
)
@freeze_time(TIMESTAMP)
@pytest.mark.parametrize(
    ("extra_args", "expected_file"),
    [
        (["--output-model-type", "dataclasses.dataclass", "--frozen-dataclasses"], "frozen_dataclasses.py"),
        (
            [
                "--output-model-type",
                "dataclasses.dataclass",
                "--frozen-dataclasses",
                "--keyword-only",
                "--target-python-version",
                "3.10",
            ],
            "frozen_dataclasses_keyword_only.py",
        ),
    ],
)
def test_frozen_dataclasses_command_line(output_file: Path, extra_args: list[str], expected_file: str) -> None:
    """Generate frozen dataclasses with optional keyword-only fields.

    The `--frozen-dataclasses` flag generates dataclass instances that are immutable
    (frozen=True). Combined with `--keyword-only` (Python 3.10+), all fields become
    keyword-only arguments.
    """
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=extra_args,
    )


@freeze_time(TIMESTAMP)
def test_class_decorators(tmp_path: Path) -> None:
    """Test --class-decorators flag functionality."""
    output_file = tmp_path / "output.py"
    generate(
        DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.DataclassesDataclass,
        class_decorators=["@dataclass_json"],
        additional_imports=["dataclasses_json.dataclass_json"],
    )
    assert_file_content(output_file, "class_decorators_dataclass.py")


@pytest.mark.cli_doc(
    options=["--class-decorators"],
    input_schema="jsonschema/simple_frozen_test.json",
    cli_args=[
        "--output-model-type",
        "dataclasses.dataclass",
        "--class-decorators",
        "@dataclass_json",
        "--additional-imports",
        "dataclasses_json.dataclass_json",
    ],
    golden_output="class_decorators_dataclass.py",
    related_options=["--additional-imports", "--output-model-type"],
)
@freeze_time(TIMESTAMP)
def test_class_decorators_command_line(output_file: Path) -> None:
    """Add custom decorators to generated model classes.

    The `--class-decorators` option adds custom decorators to all generated model classes.
    This is useful for integrating with serialization libraries like `dataclasses_json`.

    Use with `--additional-imports` to add the required imports for the decorators.
    The `@` prefix is optional and will be added automatically if missing.
    """
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="class_decorators_dataclass.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--class-decorators",
            "@dataclass_json",
            "--additional-imports",
            "dataclasses_json.dataclass_json",
        ],
    )


@freeze_time(TIMESTAMP)
def test_class_decorators_without_at_prefix(output_file: Path) -> None:
    """Test --class-decorators auto-adds @ prefix when missing."""
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="class_decorators_dataclass.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--class-decorators",
            "dataclass_json",
            "--additional-imports",
            "dataclasses_json.dataclass_json",
        ],
    )


@freeze_time(TIMESTAMP)
def test_class_decorators_with_empty_entries(output_file: Path) -> None:
    """Test --class-decorators filters out empty entries from comma-separated list."""
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="class_decorators_dataclass.py",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--class-decorators",
            "@dataclass_json, ,",
            "--additional-imports",
            "dataclasses_json.dataclass_json",
        ],
    )


@freeze_time(TIMESTAMP)
@pytest.mark.parametrize(
    ("output_model_type", "expected_file"),
    [
        ("pydantic.BaseModel", "class_decorators_pydantic_BaseModel.py"),
        ("pydantic_v2.BaseModel", "class_decorators_pydantic_v2_BaseModel.py"),
        ("pydantic_v2.dataclass", "class_decorators_pydantic_v2_dataclass.py"),
        ("dataclasses.dataclass", "class_decorators_dataclasses_dataclass.py"),
        ("msgspec.Struct", "class_decorators_msgspec_Struct.py"),
        # Note: TypedDict is excluded because its template doesn't support decorators
    ],
    ids=[
        "pydantic_v1",
        "pydantic_v2",
        "pydantic_v2_dataclass",
        "dataclasses",
        "msgspec",
    ],
)
def test_class_decorators_all_output_types(output_file: Path, output_model_type: str, expected_file: str) -> None:
    """Test --class-decorators works with all output model types that support decorators."""
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "simple_frozen_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file=expected_file,
        extra_args=[
            "--output-model-type",
            output_model_type,
            "--class-decorators",
            "@my_decorator",
            "--additional-imports",
            "my_module.my_decorator",
        ],
    )


@freeze_time(TIMESTAMP)
def test_use_attribute_docstrings(tmp_path: Path) -> None:
    """Test --use-attribute-docstrings flag functionality."""
    output_file = tmp_path / "output.py"
    generate(
        DATA_PATH / "jsonschema" / "use_attribute_docstrings_test.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
        use_field_description=True,
        use_attribute_docstrings=True,
    )
    assert_file_content(output_file)


@freeze_time(TIMESTAMP)
@pytest.mark.cli_doc(
    options=["--use-attribute-docstrings"],
    input_schema="jsonschema/use_attribute_docstrings_test.json",
    cli_args=[
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--use-field-description",
        "--use-attribute-docstrings",
    ],
    golden_output="use_attribute_docstrings.py",
    related_options=["--use-field-description"],
)
def test_use_attribute_docstrings_command_line(output_file: Path) -> None:
    """Generate field descriptions as attribute docstrings instead of Field descriptions.

    The `--use-attribute-docstrings` flag places field descriptions in Python docstring
    format (PEP 224 attribute docstrings) rather than in Field(..., description=...).
    This provides better IDE support for hovering over attributes. Requires
    `--use-field-description` to be enabled.
    """
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "use_attribute_docstrings_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="use_attribute_docstrings.py",
        extra_args=[
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-field-description",
            "--use-attribute-docstrings",
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


def test_schema_parse_error_includes_path(tmp_path: Path) -> None:
    """Test that schema parse errors include the schema path context."""
    invalid_schema = tmp_path / "invalid_schema.json"
    invalid_schema.write_text("""{
        "type": "object",
        "properties": {
            "myField": {
                "type": "integer",
                "minimum": "not_a_number"
            }
        }
    }""")
    output_file = tmp_path / "output.py"

    with pytest.raises(SchemaParseError, match="Error at schema path"):
        generate(
            input_=invalid_schema,
            output=output_file,
        )


def test_schema_parse_error_includes_nested_path(tmp_path: Path) -> None:
    """Test that schema parse errors include nested schema path context."""
    invalid_schema = tmp_path / "invalid_nested_schema.json"
    invalid_schema.write_text("""{
        "$defs": {
            "MyModel": {
                "type": "object",
                "properties": {
                    "nestedField": {
                        "type": "number",
                        "maximum": "invalid_value"
                    }
                }
            }
        },
        "type": "object",
        "properties": {
            "ref": {"$ref": "#/$defs/MyModel"}
        }
    }""")
    output_file = tmp_path / "output.py"

    with pytest.raises(SchemaParseError, match=r"\$defs/MyModel"):
        generate(
            input_=invalid_schema,
            output=output_file,
        )


def test_schema_parse_error_original_error(tmp_path: Path) -> None:
    """Test that SchemaParseError preserves the original error."""
    invalid_schema = tmp_path / "invalid_schema.json"
    invalid_schema.write_text("""{
        "type": "integer",
        "minimum": "not_a_number"
    }""")
    output_file = tmp_path / "output.py"

    with pytest.raises(SchemaParseError) as exc_info:
        generate(
            input_=invalid_schema,
            output=output_file,
        )

    assert exc_info.value.original_error is not None
    assert exc_info.value.path is not None


def test_schema_parse_error_without_path() -> None:
    """Test SchemaParseError message formatting without path."""
    error = SchemaParseError("Test error message")
    assert error.message == "Test error message"
    assert error.path == []
    assert error.original_error is None


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
            expected_stdout_path=EXPECTED_MAIN_PATH / "generate_cli_command" / "no_use_specialized_enum.txt",
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
            expected_stdout_path=EXPECTED_MAIN_PATH / "generate_cli_command" / "false_boolean.txt",
        )


def test_generate_cli_command_with_true_boolean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with boolean set to true."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "schema.yaml"
snake-case-field = true
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_MAIN_PATH / "generate_cli_command" / "true_boolean.txt",
        )


def test_generate_cli_command_with_list_option(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test --generate-cli-command with list option."""
    pyproject_toml = """
[tool.datamodel-codegen]
input = "schema.yaml"
strict-types = ["str", "int"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    with chdir(tmp_path):
        run_main_with_args(
            ["--generate-cli-command"],
            capsys=capsys,
            expected_stdout_path=EXPECTED_MAIN_PATH / "generate_cli_command" / "list_option.txt",
        )


@pytest.mark.parametrize(
    ("json_str", "expected"),
    [
        ('{"frozen": true, "slots": true}', {"frozen": True, "slots": True}),
        ("{}", {}),
    ],
)
def test_dataclass_arguments_valid(json_str: str, expected: dict) -> None:
    """Test that valid JSON is parsed correctly."""
    assert _dataclass_arguments(json_str) == expected


@pytest.mark.parametrize(
    ("json_str", "match"),
    [
        ("not-valid-json", "Invalid JSON:"),
        ("[1, 2, 3]", "Expected a JSON dictionary, got list"),
        ('"just a string"', "Expected a JSON dictionary, got str"),
        ("42", "Expected a JSON dictionary, got int"),
        ('{"invalid_key": true}', "Invalid keys:"),
        ('{"frozen": "not_bool"}', "Expected bool for 'frozen', got str"),
    ],
)
def test_dataclass_arguments_invalid(json_str: str, match: str) -> None:
    """Test that invalid input raises ArgumentTypeError."""
    with pytest.raises(ArgumentTypeError, match=match):
        _dataclass_arguments(json_str)


@pytest.mark.cli_doc(
    options=["--type-overrides"],
    input_schema="jsonschema/type_overrides_test.json",
    cli_args=["--type-overrides", '{"CustomType": "my_app.types.CustomType"}'],
    golden_output="main/type_overrides_model_level.py",
    primary=True,
)
@freeze_time(TIMESTAMP)
def test_type_overrides_model_level(output_file: Path) -> None:
    """Replace schema model types with custom Python types via JSON mapping."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_overrides_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--type-overrides",
            '{"CustomType": "my_app.types.CustomType"}',
        ],
    )


@freeze_time(TIMESTAMP)
def test_type_overrides_scoped(output_file: Path) -> None:
    """Test --type-overrides with scoped override replaces specific field only."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_overrides_scoped.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--type-overrides",
            '{"User.address": "my_app.Address"}',
        ],
    )


@freeze_time(TIMESTAMP)
def test_type_overrides_nested_types(output_file: Path) -> None:
    """Test --type-overrides with nested types like List[CustomType]."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "type_overrides_nested.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        extra_args=[
            "--type-overrides",
            '{"Tag": "my_app.Tag"}',
        ],
    )


def test_skip_root_model(tmp_path: Path) -> None:
    """Test --skip-root-model flag functionality using generate()."""
    output_file = tmp_path / "output.py"
    generate(
        DATA_PATH / "jsonschema" / "skip_root_model_test.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
        skip_root_model=True,
    )
    assert_file_content(output_file, "skip_root_model.py")


@pytest.mark.cli_doc(
    options=["--skip-root-model"],
    input_schema="jsonschema/skip_root_model_test.json",
    cli_args=["--output-model-type", "pydantic_v2.BaseModel", "--skip-root-model"],
    golden_output="skip_root_model.py",
)
def test_skip_root_model_command_line(output_file: Path) -> None:
    """Skip generation of root model when schema contains nested definitions.

    The `--skip-root-model` flag prevents generating a model for the root schema object
    when the schema primarily contains reusable definitions. This is useful when the root
    object is just a container for $defs and not a meaningful model itself.
    """
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "skip_root_model_test.json",
        output_path=output_file,
        input_file_type="jsonschema",
        assert_func=assert_file_content,
        expected_file="skip_root_model.py",
        extra_args=["--output-model-type", "pydantic_v2.BaseModel", "--skip-root-model"],
    )


@pytest.mark.cli_doc(
    options=["--check"],
    input_schema="jsonschema/person.json",
    cli_args=["--disable-timestamp", "--check"],
    golden_output="person.py",
)
def test_check_file_matches(output_file: Path) -> None:
    """Verify generated code matches existing output without modifying files.

    The `--check` flag compares the generated output with existing files and exits with
    a non-zero status if they differ. Useful for CI/CD validation to ensure schemas
    and generated code stay in sync. Works with both single files and directory outputs.
    """
    input_path = DATA_PATH / "jsonschema" / "person.json"
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp"],
    )
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.OK,
    )


def test_check_file_does_not_exist(tmp_path: Path) -> None:
    """Test --check returns DIFF when file does not exist."""
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "person.json",
        output_path=tmp_path / "nonexistent.py",
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.DIFF,
    )


def test_check_file_differs(output_file: Path) -> None:
    """Test --check returns DIFF when file content differs."""
    output_file.write_text("# Different content\n", encoding="utf-8")
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "person.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.DIFF,
    )


def test_check_with_stdout_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test --check with stdout output returns error."""
    run_main_and_assert(
        input_path=DATA_PATH / "jsonschema" / "person.json",
        output_path=None,
        input_file_type="jsonschema",
        extra_args=["--check"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="--check cannot be used with stdout",
    )


def test_check_with_nonexistent_input(tmp_path: Path) -> None:
    """Test --check with nonexistent input file returns error."""
    run_main_and_assert(
        input_path=tmp_path / "nonexistent.json",
        output_path=tmp_path / "output.py",
        input_file_type="jsonschema",
        extra_args=["--check"],
        expected_exit=Exit.ERROR,
    )


def test_check_normalizes_line_endings(output_file: Path) -> None:
    """Test --check normalizes line endings (CRLF vs LF)."""
    input_path = DATA_PATH / "jsonschema" / "person.json"
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp"],
    )
    content = output_file.read_text(encoding="utf-8")
    output_file.write_bytes(content.replace("\n", "\r\n").encode("utf-8"))
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.OK,
    )


def test_check_directory_matches(output_dir: Path) -> None:
    """Test --check returns OK when directory matches."""
    input_path = OPEN_API_DATA_PATH / "modular.yaml"
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp"],
    )
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.OK,
    )


def test_check_directory_file_differs(output_dir: Path) -> None:
    """Test --check returns DIFF when a file in directory differs."""
    input_path = OPEN_API_DATA_PATH / "modular.yaml"
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp"],
    )
    py_files = list(output_dir.rglob("*.py"))
    py_files[0].write_text("# Modified content\n", encoding="utf-8")
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.DIFF,
    )


def test_check_directory_missing_file(output_dir: Path) -> None:
    """Test --check returns DIFF when a generated file is missing."""
    input_path = OPEN_API_DATA_PATH / "modular.yaml"
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp"],
    )
    py_files = list(output_dir.rglob("*.py"))
    py_files[0].unlink()
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.DIFF,
    )


def test_check_directory_extra_file(output_dir: Path) -> None:
    """Test --check returns DIFF when an extra file exists."""
    input_path = OPEN_API_DATA_PATH / "modular.yaml"
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp"],
    )
    (output_dir / "extra_model.py").write_text("# Extra file\n", encoding="utf-8")
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.DIFF,
    )


def test_check_directory_does_not_exist(tmp_path: Path) -> None:
    """Test --check returns DIFF when output directory does not exist."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=tmp_path / "nonexistent_model",
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.DIFF,
    )


def test_check_directory_ignores_pycache(output_dir: Path) -> None:
    """Test --check ignores __pycache__ directories in actual output."""
    input_path = OPEN_API_DATA_PATH / "modular.yaml"
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp"],
    )
    pycache_dir = output_dir / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "module.cpython-313.pyc").write_bytes(b"fake bytecode")
    (pycache_dir / "extra.py").write_text("# should be ignored\n", encoding="utf-8")
    run_main_and_assert(
        input_path=input_path,
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--check"],
        expected_exit=Exit.OK,
    )


def test_check_with_invalid_class_name(tmp_path: Path) -> None:
    """Test --check cleans up temp directory when InvalidClassNameError occurs."""
    invalid_schema = tmp_path / "invalid.json"
    invalid_schema.write_text('{"title": "123InvalidName", "type": "object"}', encoding="utf-8")
    output_path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=invalid_schema,
        output_path=output_path,
        input_file_type="jsonschema",
        extra_args=["--check"],
        expected_exit=Exit.ERROR,
        expected_stderr_contains="You have to set `--class-name` option",
    )


def test_check_with_invalid_file_format(tmp_path: Path) -> None:
    """Test --check cleans up temp directory when Error occurs (invalid file format)."""
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("This is not a valid schema format!!!", encoding="utf-8")
    output_path = tmp_path / "output.py"
    run_main_and_assert(
        input_path=invalid_file,
        output_path=output_path,
        extra_args=["--check"],
        expected_exit=Exit.ERROR,
        expected_stderr_contains="Invalid file format",
    )


@pytest.mark.cli_doc(
    options=["--all-exports-scope"],
    input_schema="openapi/modular.yaml",
    cli_args=["--all-exports-scope", "children"],
    golden_output="openapi/modular_all_exports_children",
    related_options=["--all-exports-collision-strategy"],
)
def test_all_exports_scope_children(output_dir: Path) -> None:
    """Generate __all__ exports for child modules in __init__.py files.

    The `--all-exports-scope=children` flag adds __all__ to each __init__.py containing
    exports from direct child modules. This improves IDE autocomplete and explicit exports.
    Use 'recursive' to include all descendant exports with collision handling.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--all-exports-scope", "children"],
        expected_directory=EXPECTED_MAIN_PATH / "openapi" / "modular_all_exports_children",
    )


@pytest.mark.cli_doc(
    options=["--all-exports-collision-strategy"],
    input_schema="openapi/modular.yaml",
    cli_args=["--all-exports-scope", "recursive", "--all-exports-collision-strategy", "minimal-prefix"],
    golden_output="openapi/modular_all_exports_recursive",
    related_options=["--all-exports-scope"],
)
def test_all_exports_scope_recursive_with_collision(output_dir: Path) -> None:
    """Handle name collisions when exporting recursive module hierarchies.

    The `--all-exports-collision-strategy` flag determines how to resolve naming conflicts
    when using `--all-exports-scope=recursive`. The 'minimal-prefix' strategy adds the
    minimum module path prefix needed to disambiguate colliding names, while 'full-prefix'
    uses the complete module path. Requires `--all-exports-scope=recursive`.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--disable-timestamp",
            "--all-exports-scope",
            "recursive",
            "--all-exports-collision-strategy",
            "minimal-prefix",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "openapi" / "modular_all_exports_recursive",
    )


def test_all_exports_scope_children_with_docstring_header(output_dir: Path) -> None:
    """Test --all-exports-scope=children with --custom-file-header containing docstring."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--all-exports-scope",
            "children",
            "--custom-file-header-path",
            str(DATA_PATH / "custom_file_header_docstring.txt"),
        ],
        expected_directory=EXPECTED_MAIN_PATH / "openapi" / "modular_all_exports_children_docstring",
    )


def test_all_exports_scope_recursive_collision_avoided_by_renaming(output_dir: Path) -> None:
    """Test --all-exports-scope=recursive avoids collision through automatic class renaming.

    With circular import resolution, conflicting class names (e.g., foo.Tea and nested.foo.Tea)
    are automatically renamed (e.g., Tea and Tea_1) in _internal.py, so no collision error occurs.
    """
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=["--disable-timestamp", "--all-exports-scope", "recursive"],
    )

    # Verify both Tea and Tea_1 exist in _internal.py (collision avoided through renaming)
    internal_content = (output_dir / "_internal.py").read_text()
    assert "class Tea(BaseModel):" in internal_content, "Tea class should exist in _internal.py"
    assert "class Tea_1(BaseModel):" in internal_content, "Tea_1 class should exist in _internal.py"


def test_all_exports_collision_strategy_requires_recursive(output_dir: Path) -> None:
    """Test --all-exports-collision-strategy requires --all-exports-scope=recursive."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--all-exports-scope",
            "children",
            "--all-exports-collision-strategy",
            "minimal-prefix",
        ],
        expected_exit=Exit.ERROR,
        expected_stderr_contains="--all-exports-collision-strategy",
    )


def test_all_exports_scope_recursive_with_full_prefix(output_dir: Path) -> None:
    """Test --all-exports-scope=recursive with --all-exports-collision-strategy=full-prefix."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "modular.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--disable-timestamp",
            "--all-exports-scope",
            "recursive",
            "--all-exports-collision-strategy",
            "full-prefix",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "openapi" / "modular_all_exports_recursive_full_prefix",
    )


@pytest.mark.parametrize(
    "strategy",
    ["minimal-prefix", "full-prefix"],
    ids=["minimal_prefix", "full_prefix"],
)
def test_all_exports_recursive_prefix_collision_with_local_model(output_dir: Path, strategy: str) -> None:
    """Test that prefix resolution raises error when renamed export collides with local model."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "all_exports_prefix_collision.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--all-exports-scope",
            "recursive",
            "--all-exports-collision-strategy",
            strategy,
        ],
        expected_exit=Exit.ERROR,
        expected_stderr_contains="InputMessage",
    )


def test_all_exports_scope_recursive_jsonschema_multi_file(output_dir: Path) -> None:
    """Test --all-exports-scope=recursive with JSONSchema multi-file input."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_exports_multi_file",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=[
            "--disable-timestamp",
            "--all-exports-scope",
            "recursive",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "jsonschema" / "all_exports_multi_file",
    )


def test_all_exports_recursive_local_model_collision_error(output_dir: Path) -> None:
    """Test --all-exports-scope=recursive raises error when child export collides with local model."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "all_exports_local_collision.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--all-exports-scope",
            "recursive",
        ],
        expected_exit=Exit.ERROR,
        expected_stderr_contains="conflicts with a model in __init__.py",
    )


def test_all_exports_scope_children_no_child_exports(output_dir: Path) -> None:
    """Test --all-exports-scope=children when __init__.py has models but no direct child exports."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "all_exports_no_child.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--disable-timestamp",
            "--all-exports-scope",
            "children",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "openapi" / "all_exports_no_child",
    )


def test_all_exports_scope_children_with_local_models(output_dir: Path) -> None:
    """Test --all-exports-scope=children when __init__.py has both local models and child exports."""
    run_main_and_assert(
        input_path=OPEN_API_DATA_PATH / "all_exports_with_local_models.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--disable-timestamp",
            "--all-exports-scope",
            "children",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "openapi" / "all_exports_with_local_models",
    )


def test_check_respects_pyproject_toml_settings(tmp_path: Path) -> None:
    """Test --check uses pyproject.toml formatter settings from output path.

    This test verifies that both generation and --check mode use the same
    pyproject.toml settings from the output directory. Without the fix,
    generation would use cwd's settings while --check would use output path's
    settings, causing a diff even with identical input.
    """
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("[tool.black]\nline-length = 60\n", encoding="utf-8")

    input_json = tmp_path / "input.json"
    input_json.write_text(
        """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Person",
  "type": "object",
  "properties": {
    "firstName": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "pattern": "^[A-Za-z]+$"
    }
  },
  "required": ["firstName"]
}""",
        encoding="utf-8",
    )

    output_file = tmp_path / "output.py"
    expected_output = """\
# generated by datamodel-codegen:
#   filename:  input.json

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class Person(BaseModel):
    firstName: Annotated[
        str,
        Field(
            max_length=100,
            min_length=1,
            regex='^[A-Za-z]+$',
        ),
    ]
"""
    run_main_and_assert(
        input_path=input_json,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp", "--use-annotated"],
        expected_output=expected_output,
    )

    run_main_and_assert(
        input_path=input_json,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--disable-timestamp", "--use-annotated", "--check"],
        expected_exit=Exit.OK,
    )


def test_use_specialized_enum_requires_python_311(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test --use-specialized-enum requires --target-python-version 3.11+."""
    input_json = tmp_path / "input.json"
    input_json.write_text(
        '{"type": "string", "enum": ["A", "B"]}',
        encoding="utf-8",
    )

    run_main_and_assert(
        input_path=input_json,
        output_path=tmp_path / "output.py",
        input_file_type="jsonschema",
        extra_args=["--use-specialized-enum"],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="--use-specialized-enum requires --target-python-version 3.11 or later",
    )


@pytest.mark.skipif(
    black.__version__.split(".")[0] == "22",
    reason="Installed black doesn't support StrEnum formatting",
)
def test_use_specialized_enum_with_python_311_ok(output_file: Path) -> None:
    """Test --use-specialized-enum works with --target-python-version 3.11."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "string_enum.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--use-specialized-enum", "--target-python-version", "3.11"],
        assert_func=assert_file_content,
        expected_file="use_specialized_enum_py311.py",
    )


def test_use_specialized_enum_pyproject_requires_python_311(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test use_specialized_enum in pyproject.toml requires target_python_version 3.11+."""
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        "[tool.datamodel-codegen]\nuse_specialized_enum = true\n",
        encoding="utf-8",
    )

    input_json = tmp_path / "input.json"
    input_json.write_text(
        '{"type": "string", "enum": ["A", "B"]}',
        encoding="utf-8",
    )

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=input_json,
            output_path=tmp_path / "output.py",
            input_file_type="jsonschema",
            expected_exit=Exit.ERROR,
            capsys=capsys,
            expected_stderr_contains="--use-specialized-enum requires --target-python-version 3.11 or later",
        )


def test_use_specialized_enum_pyproject_override_with_cli(output_file: Path, tmp_path: Path) -> None:
    """Test --no-use-specialized-enum CLI can override pyproject.toml use_specialized_enum=true."""
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        "[tool.datamodel-codegen]\nuse_specialized_enum = true\n",
        encoding="utf-8",
    )

    with chdir(tmp_path):
        run_main_and_assert(
            input_path=JSON_SCHEMA_DATA_PATH / "string_enum.json",
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=["--no-use-specialized-enum"],
            assert_func=assert_file_content,
            expected_file="no_use_specialized_enum.py",
        )


@pytest.mark.cli_doc(
    options=["--module-split-mode"],
    input_schema="jsonschema/module_split_single/input.json",
    cli_args=["--module-split-mode", "single", "--all-exports-scope", "recursive", "--use-exact-imports"],
    golden_output="jsonschema/module_split_single",
    related_options=["--all-exports-scope", "--use-exact-imports"],
)
def test_module_split_mode_single(output_dir: Path) -> None:
    """Split generated models into separate files, one per model class.

    The `--module-split-mode=single` flag generates each model class in its own file,
    named after the class in snake_case. Use with `--all-exports-scope=recursive` to
    create an __init__.py that re-exports all models for convenient imports.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "module_split_single" / "input.json",
        output_path=output_dir,
        input_file_type="jsonschema",
        extra_args=[
            "--disable-timestamp",
            "--module-split-mode",
            "single",
            "--all-exports-scope",
            "recursive",
            "--use-exact-imports",
        ],
        expected_directory=EXPECTED_MAIN_PATH / "jsonschema" / "module_split_single",
    )


@pytest.mark.cli_doc(
    options=["--use-standard-primitive-types"],
    input_schema="jsonschema/use_standard_primitive_types.json",
    cli_args=[
        "--output-model-type",
        "dataclasses.dataclass",
        "--use-standard-primitive-types",
    ],
    golden_output="use_standard_primitive_types.py",
    related_options=["--output-model-type", "--output-datetime-class"],
)
@freeze_time(TIMESTAMP)
def test_use_standard_primitive_types(output_file: Path) -> None:
    """Use Python standard library types for string formats instead of str.

    The `--use-standard-primitive-types` flag configures the code generation to use
    Python standard library types (UUID, IPv4Address, IPv6Address, Path) for corresponding
    string formats instead of plain str. This affects dataclass, msgspec, and TypedDict
    output types. Pydantic already uses these types by default.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "use_standard_primitive_types.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--output-model-type",
            "dataclasses.dataclass",
            "--use-standard-primitive-types",
        ],
        expected_file=EXPECTED_MAIN_PATH / "use_standard_primitive_types.py",
    )


def test_format_code_fallback_on_error(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test that code generation continues with unformatted output when formatting fails."""
    schema = tmp_path / "schema.json"
    schema.write_text('{"type": "object", "properties": {"name": {"type": "string"}}}', encoding="utf-8")
    output = tmp_path / "output.py"

    def mock_format_code(_self: CodeFormatter, _code: str) -> str:
        msg = "mock error"
        raise black.InvalidInput(msg)

    mocker.patch.object(CodeFormatter, "format_code", mock_format_code)

    with pytest.warns(UserWarning, match="Failed to format code.*Emitting unformatted output"):
        generate(
            input_=schema,
            input_file_type=InputFileType.JsonSchema,
            output=output,
        )

    content = output.read_text()
    assert "class Model" in content
    assert "name:" in content


def test_format_code_fallback_on_error_init_exports(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test that __init__.py generation continues with unformatted output when formatting fails."""
    output_dir = tmp_path / "output"

    def mock_format_code(_self: CodeFormatter, _code: str) -> str:
        msg = "mock error"
        raise black.InvalidInput(msg)

    mocker.patch.object(CodeFormatter, "format_code", mock_format_code)

    with pytest.warns(UserWarning, match="Failed to format code.*Emitting unformatted output"):
        generate(
            input_=OPEN_API_DATA_PATH / "modular.yaml",
            input_file_type=InputFileType.OpenAPI,
            output=output_dir,
            all_exports_scope=AllExportsScope.Children,
        )

    init_content = (output_dir / "__init__.py").read_text()
    assert "__all__" in init_content or "from ." in init_content


def test_init_exports_without_formatting(tmp_path: Path) -> None:
    """Test that __init__.py exports work correctly when formatting is disabled."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    parser = OpenAPIParser(source=OPEN_API_DATA_PATH / "modular.yaml")
    results = parser.parse(
        format_=False,
        all_exports_scope=AllExportsScope.Children,
    )

    assert isinstance(results, dict)
    init_key = ("__init__.py",)
    assert init_key in results
    init_content = results[init_key].body
    assert "__all__" in init_content or "from ." in init_content


def test_generate_parent_scoped_naming_backward_compat(tmp_path: Path) -> None:
    """Test generate() with parent_scoped_naming=True triggers ModelResolver backward compat."""
    output_file = tmp_path / "output.py"
    generate(
        input_=JSON_SCHEMA_DATA_PATH / "naming_strategy" / "input.json",
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        output_model_type=DataModelType.PydanticV2BaseModel,
        parent_scoped_naming=True,
    )
    content = output_file.read_text()
    assert "class ModelOrderItem" in content
    assert "class ModelCartItem" in content


def test_ruff_check_and_format_combined(output_file: Path) -> None:
    """Test ruff check and format run together in a pipeline for single file."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "simple_string.json",
        output_path=output_file,
        extra_args=["--formatters", "ruff-check", "ruff-format", "--disable-timestamp"],
        expected_output="""\
# generated by datamodel-codegen:
#   filename:  simple_string.json

from __future__ import annotations
from pydantic import BaseModel


class Model(BaseModel):
    s: str
""",
    )


def test_ruff_check_only(output_file: Path) -> None:
    """Test ruff check formatter alone for single file."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "simple_string.json",
        output_path=output_file,
        extra_args=["--formatters", "ruff-check", "--disable-timestamp"],
        expected_output="""\
# generated by datamodel-codegen:
#   filename:  simple_string.json

from __future__ import annotations
from pydantic import BaseModel


class Model(BaseModel):
    s: str
""",
    )


def test_ruff_format_only(output_file: Path) -> None:
    """Test ruff format formatter alone for single file."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "simple_string.json",
        output_path=output_file,
        extra_args=["--formatters", "ruff-format", "--disable-timestamp"],
        expected_output="""\
# generated by datamodel-codegen:
#   filename:  simple_string.json

from __future__ import annotations
from pydantic import BaseModel


class Model(BaseModel):
    s: str
""",
    )


def test_ruff_batch_formatting_directory(output_dir: Path) -> None:
    """Test ruff batch formatting for directory output (multiple files)."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "all_exports_multi_file",
        output_path=output_dir,
        extra_args=["--formatters", "ruff-check", "ruff-format", "--disable-timestamp"],
        skip_code_validation=True,
    )
    order_file = output_dir / "order.py"
    assert order_file.exists()
    content = order_file.read_text()
    assert "from __future__ import annotations" in content
    assert "class Order" in content


def test_generate_returns_string_when_output_none() -> None:
    """Test that generate() returns str when output=None for single file."""
    json_schema = '{"type": "object", "properties": {"name": {"type": "string"}}}'
    result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        input_filename="test.json",
        disable_timestamp=True,
    )
    assert result == snapshot(
        """\
# generated by datamodel-codegen:
#   filename:  test.json

from __future__ import annotations

from pydantic import BaseModel


class Model(BaseModel):
    name: str | None = None\
"""
    )


def test_generate_returns_string_with_pydantic_v2() -> None:
    """Test that generate() returns str for Pydantic v2 models."""
    json_schema = '{"type": "object", "properties": {"value": {"type": "number"}}}'
    result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        input_filename="schema.json",
        output_model_type=DataModelType.PydanticV2BaseModel,
        disable_timestamp=True,
    )
    assert result == snapshot(
        """\
# generated by datamodel-codegen:
#   filename:  schema.json

from __future__ import annotations

from pydantic import BaseModel


class Model(BaseModel):
    value: float | None = None"""
    )


def test_generate_returns_string_with_dataclass() -> None:
    """Test that generate() returns str for dataclass models."""
    json_schema = '{"type": "object", "properties": {"value": {"type": "string"}}}'
    result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        input_filename="data.json",
        output_model_type=DataModelType.DataclassesDataclass,
        disable_timestamp=True,
    )
    assert result == snapshot(
        """\
# generated by datamodel-codegen:
#   filename:  data.json

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Model:
    value: str | None = None"""
    )


def test_generate_returns_none_when_output_path_provided(tmp_path: Path) -> None:
    """Test that generate() returns None when output path is provided."""
    json_schema = '{"type": "object", "properties": {"name": {"type": "string"}}}'
    output = tmp_path / "model.py"
    result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        output=output,
        disable_timestamp=True,
    )
    assert result is None
    assert output.exists()


def test_generate_file_content_matches_return_value(tmp_path: Path) -> None:
    """Test that file content matches what would be returned with output=None."""
    json_schema = '{"type": "object", "properties": {"id": {"type": "integer"}}}'

    return_result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        input_filename="test.json",
        disable_timestamp=True,
    )

    output = tmp_path / "model.py"
    generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        input_filename="test.json",
        output=output,
        disable_timestamp=True,
    )
    file_content = output.read_text()

    assert isinstance(return_result, str)
    assert return_result.strip() == file_content.strip()


def test_generate_returns_dict_for_multiple_modules(tmp_path: Path) -> None:
    """Test that generate() returns GeneratedModules dict for multiple modules."""
    main_schema = tmp_path / "main.json"
    main_schema.write_text(
        """{
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "address": {"$ref": "address.json#/definitions/Address"}
                }
            }
        }
    }"""
    )

    address_schema = tmp_path / "address.json"
    address_schema.write_text(
        """{
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"}
                }
            }
        }
    }"""
    )

    result = generate(
        tmp_path,
        input_file_type=InputFileType.JsonSchema,
        disable_timestamp=True,
    )

    assert result == snapshot({
        ("__init__.py",): """\
# generated by datamodel-codegen:
#   filename:  test_generate_returns_dict_for0\
""",
        ("address.py",): """\
# generated by datamodel-codegen:
#   filename:  address.json

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Model(BaseModel):
    __root__: Any


class Address(BaseModel):
    street: str | None = None
    city: str | None = None\
""",
        ("main.py",): """\
# generated by datamodel-codegen:
#   filename:  main.json

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from . import address as address_1


class Model(BaseModel):
    __root__: Any


class User(BaseModel):
    id: int | None = None
    address: address_1.Address | None = None\
""",
    })


def test_generated_modules_type_alias_is_exported() -> None:
    """Test that GeneratedModules is exported from the module."""
    assert GeneratedModules is not None


def test_generate_returns_string_with_custom_file_header() -> None:
    """Test generate() with custom_file_header when output=None."""
    json_schema = '{"type": "object", "properties": {"name": {"type": "string"}}}'
    custom_header = "# Custom header\n# More comments"
    result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        custom_file_header=custom_header,
    )
    assert result == snapshot(
        """\
# Custom header
# More comments

from __future__ import annotations

from pydantic import BaseModel


class Model(BaseModel):
    name: str | None = None"""
    )


def test_generate_returns_string_with_custom_file_header_and_code() -> None:
    """Test generate() with custom_file_header containing code after docstring."""
    json_schema = '{"type": "object", "properties": {"id": {"type": "integer"}}}'
    custom_header = '"""Module docstring."""\n\nimport sys'
    result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        custom_file_header=custom_header,
    )
    assert result == snapshot(
        '''\
"""Module docstring."""
from __future__ import annotations

import sys

from pydantic import BaseModel


class Model(BaseModel):
    id: int | None = None\
'''
    )


def test_generate_returns_string_with_custom_file_header_no_future() -> None:
    """Test generate() with custom_file_header when body has no future imports."""
    json_schema = '{"type": "object", "properties": {"id": {"type": "integer"}}}'
    custom_header = "# Custom header for legacy code"
    result = generate(
        json_schema,
        input_file_type=InputFileType.JsonSchema,
        custom_file_header=custom_header,
        disable_future_imports=True,
    )
    assert result == snapshot("""\
# Custom header for legacy code

from pydantic import BaseModel


class Model(BaseModel):
    id: int | None = None\
""")


def test_generate_with_dict_jsonschema() -> None:
    """Test generate() with dict input as JsonSchema."""
    from tests.data.dict_input import jsonschema_dict

    result = generate(
        jsonschema_dict,
        input_file_type=InputFileType.JsonSchema,
        disable_timestamp=True,
    )

    assert_output(result, EXPECTED_MAIN_PATH / "dict_input" / "jsonschema.py")


def test_generate_with_dict_openapi() -> None:
    """Test generate() with dict input as OpenAPI."""
    from tests.data.dict_input import openapi_dict

    result = generate(
        openapi_dict,
        input_file_type=InputFileType.OpenAPI,
        disable_timestamp=True,
    )

    assert_output(result, EXPECTED_MAIN_PATH / "dict_input" / "openapi.py")


def test_generate_with_dict_auto_raises_error() -> None:
    """Test generate() with dict input + Auto raises error."""
    from tests.data.dict_input import auto_error_dict

    with pytest.raises(Error, match="input_file_type=Auto is not supported for dict input"):
        generate(auto_error_dict, input_file_type=InputFileType.Auto)


def test_generate_with_dict_graphql_raises_error() -> None:
    """Test generate() with dict input + GraphQL raises error."""
    from tests.data.dict_input import graphql_error_dict

    with pytest.raises(Error, match="Dict input is not supported for GraphQL"):
        generate(graphql_error_dict, input_file_type=InputFileType.GraphQL)


def test_generate_with_dict_openapi_validation_warns() -> None:
    """Test generate() with dict input + validation skips validation with warning."""
    import warnings

    from tests.data.dict_input import openapi_dict

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = generate(
            openapi_dict,
            input_file_type=InputFileType.OpenAPI,
            validation=True,
            disable_timestamp=True,
        )
        assert_output(result, EXPECTED_MAIN_PATH / "dict_input" / "openapi.py")
        # Check that both deprecated warning and dict input warning were raised
        warning_messages = [str(warning.message) for warning in w]
        assert any("deprecated" in msg.lower() for msg in warning_messages)
        assert any("dict input" in msg.lower() for msg in warning_messages)


@pytest.mark.parametrize(
    "input_file_type",
    [InputFileType.Json, InputFileType.Yaml, InputFileType.CSV],
    ids=["json", "yaml", "csv"],
)
def test_generate_with_dict_raw_data_types_raises_error(input_file_type: InputFileType) -> None:
    """Test generate() with dict input + Json/Yaml/CSV raises error."""
    from tests.data.dict_input import auto_error_dict

    with pytest.raises(Error, match=f"Dict input is not supported for {input_file_type.value}"):
        generate(auto_error_dict, input_file_type=input_file_type)
