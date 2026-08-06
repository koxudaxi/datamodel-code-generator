"""End-to-end tests for comparing generated output from two local inputs."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import jsonschema
import pytest

from datamodel_code_generator.__main__ import Exit
from tests.main.conftest import DATA_PATH, InputFileTypeLiteral, run_main_and_assert, run_main_with_args

if TYPE_CHECKING:
    from pathlib import Path


INPUT_DIFF_EXPECTED_PATH = DATA_PATH / "expected" / "main" / "input_diff"
JSON_SCHEMA_INPUT_DIFF_PATH = DATA_PATH / "jsonschema" / "input_diff"
OPENAPI_INPUT_DIFF_PATH = DATA_PATH / "openapi" / "input_diff"
LOCAL_INPUT_TYPE_CASES: tuple[tuple[InputFileTypeLiteral, Path, bool], ...] = (
    ("jsonschema", JSON_SCHEMA_INPUT_DIFF_PATH / "same_old.json", False),
    ("openapi", OPENAPI_INPUT_DIFF_PATH / "new.yaml", True),
    ("asyncapi", DATA_PATH / "asyncapi" / "user-events.yaml", False),
    ("mcp-tools", DATA_PATH / "mcp_tools" / "direct_tool.json", False),
    ("xmlschema", DATA_PATH / "xmlschema" / "inline_root.xsd", False),
    ("protobuf", DATA_PATH / "protobuf" / "common.proto", False),
    ("avro", DATA_PATH / "avro" / "root_type_object.avsc", False),
    ("json", DATA_PATH / "json" / "simple.json", False),
    ("yaml", DATA_PATH / "yaml" / "pet.yaml", False),
    ("dict", DATA_PATH / "python" / "space_and_special_characters_dict.py", False),
    ("csv", DATA_PATH / "csv" / "simple.csv", False),
    ("graphql", DATA_PATH / "graphql" / "simple-star-wars.graphql", False),
)


def test_diff_against_identical_single_file_does_not_write_virtual_output(
    output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Equivalent files with different names do not make generated headers differ."""
    new_input = JSON_SCHEMA_INPUT_DIFF_PATH / "same_new.json"
    run_main_and_assert(
        input_path=new_input,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--diff-against", str(JSON_SCHEMA_INPUT_DIFF_PATH / "same_old.json"), "--disable-timestamp"],
        expected_exit=Exit.OK,
        output_should_not_exist=True,
        capsys=capsys,
        expected_stdout_path=INPUT_DIFF_EXPECTED_PATH / "identical.txt",
        assert_no_stderr=True,
    )


def test_diff_against_infers_each_input_type_independently(
    output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Automatic input-type inference runs for both the old and new local paths."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_INPUT_DIFF_PATH / "same_new.yaml",
        output_path=output_file,
        extra_args=["--diff-against", str(JSON_SCHEMA_INPUT_DIFF_PATH / "same_old.json"), "--disable-timestamp"],
        expected_exit=Exit.OK,
        output_should_not_exist=True,
        capsys=capsys,
        expected_stdout_path=INPUT_DIFF_EXPECTED_PATH / "identical.txt",
        expected_stderr=(
            "The input file type was determined to be: jsonschema\n"
            "This can be specified explicitly with the `--input-file-type` option.\n"
        )
        * 2,
    )


@pytest.mark.parametrize(("input_file_type", "source_input", "is_directory"), LOCAL_INPUT_TYPE_CASES)
def test_diff_against_supports_every_local_input_type(
    input_file_type: InputFileTypeLiteral,
    source_input: Path,
    is_directory: bool,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each local parser can compare two equivalent inputs through the CLI."""
    copied_input = tmp_path / f"candidate-{source_input.name}"
    virtual_output = tmp_path / ("models" if is_directory else "models.py")
    run_main_and_assert(
        input_path=copied_input,
        output_path=virtual_output,
        input_file_type=input_file_type,
        extra_args=["--diff-against", str(source_input), "--disable-timestamp"],
        expected_exit=Exit.OK,
        output_should_not_exist=True,
        capsys=capsys,
        expected_stdout_path=INPUT_DIFF_EXPECTED_PATH / "identical.txt",
        assert_no_stderr=True,
        copy_files=[(source_input, copied_input)],
    )


def test_diff_against_reports_changed_single_file_without_writing_virtual_output(
    output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Compare two local JSON Schema revisions through the normal generation pipeline."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_INPUT_DIFF_PATH / "new.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--diff-against",
            str(JSON_SCHEMA_INPUT_DIFF_PATH / "old.json"),
            "--disable-timestamp",
        ],
        expected_exit=Exit.DIFF,
        output_should_not_exist=True,
        capsys=capsys,
        assert_no_stderr=True,
    )


@pytest.mark.cli_doc(
    options=["--diff-against"],
    option_description="""Compare generated code from two local schema revisions without writing generated files.

Pass the newer revision with `--input` and the older one with `--diff-against`.
The required `--output` value is a virtual destination: it selects single-file or
directory layout and formatter settings, but datamodel-code-generator never writes it.
The command exits non-zero when the formatted generated outputs differ, making it useful
for reviewing schema migrations in CI.""",
    input_schema="openapi/input_diff/new.yaml",
    cli_args=[
        "--diff-against",
        "tests/data/openapi/input_diff/old.yaml",
        "--output",
        "models",
        "--input-file-type",
        "openapi",
        "--disable-timestamp",
    ],
    expected_stdout="main/input_diff/different_directory.txt",
    related_options=["--input", "--output", "--check", "--output-format"],
)
def test_diff_against_reports_added_and_removed_directory_files_without_writing_virtual_output(
    output_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Directory comparison uses the existing generated-file manifest comparison."""
    run_main_and_assert(
        input_path=OPENAPI_INPUT_DIFF_PATH / "new.yaml",
        output_path=output_dir,
        input_file_type="openapi",
        extra_args=[
            "--diff-against",
            str(OPENAPI_INPUT_DIFF_PATH / "old.yaml"),
            "--disable-timestamp",
        ],
        expected_exit=Exit.DIFF,
        output_should_not_exist=True,
        capsys=capsys,
        expected_stdout_path=INPUT_DIFF_EXPECTED_PATH / "different_directory.txt",
        assert_no_stderr=True,
    )


def test_diff_against_json_reports_structured_differences_without_writing_virtual_output(
    output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON output reuses the generated-output difference payload."""
    run_main_and_assert(
        input_path=JSON_SCHEMA_INPUT_DIFF_PATH / "new.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--diff-against",
            str(JSON_SCHEMA_INPUT_DIFF_PATH / "old.json"),
            "--disable-timestamp",
            "--output-format",
            "json",
        ],
        expected_exit=Exit.DIFF,
        output_should_not_exist=True,
        capsys=capsys,
        expected_stdout_path=INPUT_DIFF_EXPECTED_PATH / "different_file_json.txt",
        assert_no_stderr=True,
    )


def test_diff_against_json_fixture_matches_structured_output_schema() -> None:
    """The input-diff payload remains part of the public structured-output schema."""
    schema_path = DATA_PATH / "expected" / "main_kr" / "output_format_json" / "structured_output_schema.txt"
    jsonschema.validate(
        instance=json.loads((INPUT_DIFF_EXPECTED_PATH / "different_file_json.txt").read_text(encoding="utf-8")),
        schema=json.loads(schema_path.read_text(encoding="utf-8")),
    )


@pytest.mark.parametrize(
    ("args", "expected_stderr"),
    [
        (
            ["--diff-against", str(JSON_SCHEMA_INPUT_DIFF_PATH / "old.json"), "--output", "output.py"],
            "--diff-against requires --input",
        ),
        (
            ["--input", str(JSON_SCHEMA_INPUT_DIFF_PATH / "new.json"), "--diff-against", "old.json"],
            "--diff-against requires --output",
        ),
        (
            [
                "--input",
                str(JSON_SCHEMA_INPUT_DIFF_PATH / "new.json"),
                "--diff-against",
                "old.json",
                "--output",
                "output.py",
                "--check",
            ],
            "--diff-against and --check",
        ),
        (
            [
                "--input",
                str(JSON_SCHEMA_INPUT_DIFF_PATH / "new.json"),
                "--diff-against",
                "old.json",
                "--output",
                "output.py",
                "--watch",
            ],
            "--diff-against and --watch",
        ),
        (
            [
                "--input",
                str(JSON_SCHEMA_INPUT_DIFF_PATH / "new.json"),
                "--diff-against",
                "old.json",
                "--output",
                "output.py",
                "--emit-model-metadata",
                "metadata.json",
            ],
            "--diff-against cannot be used with --emit-model-metadata",
        ),
        (
            [
                "--input",
                str(JSON_SCHEMA_INPUT_DIFF_PATH / "new.json"),
                "--diff-against",
                "old.json",
                "--output",
                "output.py",
                "--input-model",
                "tests.data.python.input_model.pydantic_models:User",
            ],
            "--diff-against cannot be used with --input-model",
        ),
        (
            [
                "--input",
                str(JSON_SCHEMA_INPUT_DIFF_PATH / "new.json"),
                "--url",
                "https://example.com/schema.json",
                "--diff-against",
                "old.json",
                "--output",
                "output.py",
            ],
            "--diff-against cannot be used with --url",
        ),
        (
            [
                "--input",
                str(JSON_SCHEMA_INPUT_DIFF_PATH / "new.json"),
                "--diff-against",
                "old.json",
                "--output",
                "output.py",
                "--fail-on-multi-module-stdout",
            ],
            "--diff-against cannot be used with --fail-on-multi-module-stdout",
        ),
    ],
)
def test_diff_against_rejects_incompatible_inputs_and_outputs(
    args: list[str], expected_stderr: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Diff mode rejects commands that cannot preserve its two-local-input contract."""
    run_main_with_args(
        args,
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=expected_stderr,
    )
