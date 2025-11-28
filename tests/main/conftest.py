"""Shared fixtures and utilities for main integration tests."""

from __future__ import annotations

import inspect
import shutil
from argparse import Namespace
from collections.abc import Callable, Generator, Sequence
from pathlib import Path
from typing import Literal

import pytest
from freezegun import freeze_time

from datamodel_code_generator.__main__ import Exit, main
from tests.conftest import AssertFileContent, assert_directory_content, assert_output

InputFileTypeLiteral = Literal["auto", "openapi", "jsonschema", "json", "yaml", "dict", "csv", "graphql"]
CopyFilesMapping = Sequence[tuple[Path, Path]]

DATA_PATH: Path = Path(__file__).parent.parent / "data"
EXPECTED_MAIN_PATH: Path = DATA_PATH / "expected" / "main"

PYTHON_DATA_PATH: Path = DATA_PATH / "python"
OPEN_API_DATA_PATH: Path = DATA_PATH / "openapi"
JSON_SCHEMA_DATA_PATH: Path = DATA_PATH / "jsonschema"
GRAPHQL_DATA_PATH: Path = DATA_PATH / "graphql"
JSON_DATA_PATH: Path = DATA_PATH / "json"
CSV_DATA_PATH: Path = DATA_PATH / "csv"
YAML_DATA_PATH: Path = DATA_PATH / "yaml"

EXPECTED_OPENAPI_PATH: Path = EXPECTED_MAIN_PATH / "openapi"
EXPECTED_JSON_SCHEMA_PATH: Path = EXPECTED_MAIN_PATH / "jsonschema"
EXPECTED_GRAPHQL_PATH: Path = EXPECTED_MAIN_PATH / "graphql"
EXPECTED_JSON_PATH: Path = EXPECTED_MAIN_PATH / "json"
EXPECTED_CSV_PATH: Path = EXPECTED_MAIN_PATH / "csv"

TIMESTAMP = "1985-10-26T01:21:00-07:00"
DEFAULT_FREEZE_TIME = "2019-07-26"


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset argument namespace before each test."""
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace_)
    monkeypatch.setattr("datamodel_code_generator.arguments.namespace", namespace_)


@pytest.fixture(autouse=True)
def auto_freeze_time() -> Generator[None, None, None]:
    """Auto-freeze time for all tests in main/ directory."""
    with freeze_time(DEFAULT_FREEZE_TIME):
        yield


@pytest.fixture
def output_file(tmp_path: Path) -> Path:
    """Return standard output file path."""
    return tmp_path / "output.py"


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Return standard output directory path."""
    return tmp_path / "model"


def _copy_files(copy_files: CopyFilesMapping | None) -> None:
    """Copy files from source to destination paths."""
    if copy_files is not None:
        for src, dst in copy_files:
            shutil.copy(src, dst)


def run_main_with_args(
    args: Sequence[str],
    *,
    expected_exit: Exit = Exit.OK,
    capsys: pytest.CaptureFixture[str] | None = None,
    expected_stdout_path: Path | None = None,
) -> Exit:
    """Execute main() with custom arguments.

    Args:
        args: Command line arguments to pass to main()
        expected_exit: Expected exit code (default: Exit.OK)
        capsys: pytest capsys fixture for capturing output (required if expected_stdout_path is set)
        expected_stdout_path: Path to file with expected stdout content

    Returns:
        Exit code from main()
    """
    return_code = main(list(args))
    assert return_code == expected_exit
    if expected_stdout_path is not None:
        assert capsys is not None
        captured = capsys.readouterr()
        assert_output(captured.out, expected_stdout_path)
    return return_code


def run_main(
    input_path: Path,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None = None,
    *,
    extra_args: Sequence[str] | None = None,
    copy_files: CopyFilesMapping | None = None,
) -> Exit:
    """Execute main() with standard arguments.

    Args:
        input_path: Path to input schema file
        output_path: Path to output file/directory
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments (e.g., ["--keyword-only", "--target-python-version", "3.10"])
        copy_files: Files to copy before running (list of (source, destination) tuples)

    Returns:
        Exit code from main()
    """
    _copy_files(copy_files)

    args = [
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]

    if input_file_type is not None:
        args.extend(["--input-file-type", input_file_type])

    if extra_args is not None:
        args.extend(extra_args)

    return main(args)


def run_main_and_assert(
    *,
    input_path: Path,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None,
    assert_func: AssertFileContent,
    expected_file: str | Path | None = None,
    expected_exit: Exit = Exit.OK,
    extra_args: Sequence[str] | None = None,
    transform: Callable[[str], str] | None = None,
    copy_files: CopyFilesMapping | None = None,
) -> None:
    """Execute main() and assert success with file content check.

    Args:
        input_path: Path to input schema file
        output_path: Path to output file/directory
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        assert_func: The assert_file_content function to use for verification
        expected_file: Expected output filename (optional, inferred from test name if None)
        expected_exit: Expected exit code (default: Exit.OK)
        extra_args: Additional CLI arguments (e.g., ["--keyword-only"])
        transform: Optional function to transform output before comparison
        copy_files: Files to copy before running (list of (source, destination) tuples)
    """
    return_code = run_main(input_path, output_path, input_file_type, extra_args=extra_args, copy_files=copy_files)
    assert return_code == expected_exit
    if expected_exit == Exit.OK:
        if expected_file is None:
            frame = inspect.currentframe()
            assert frame is not None
            assert frame.f_back is not None
            func_name = frame.f_back.f_code.co_name
            del frame
            for prefix in ("test_main_", "test_"):
                if func_name.startswith(prefix):
                    func_name = func_name[len(prefix) :]
                    break
            expected_file = f"{func_name}.py"
        assert_func(output_path, expected_file, transform=transform)


def run_main_and_assert_directory(
    *,
    input_path: Path,
    output_path: Path,
    expected_directory: Path,
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Execute main() and assert directory output matches expected.

    Args:
        input_path: Path to input schema file
        output_path: Path to output directory
        expected_directory: Path to directory with expected files
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
    """
    return_code = run_main(input_path, output_path, input_file_type, extra_args=extra_args)
    assert return_code == Exit.OK
    assert_directory_content(output_path, expected_directory)


OutputToExpectedMapping = Sequence[tuple[str, str | Path]]


def run_main_and_assert_files(
    *,
    input_path: Path,
    output_path: Path,
    output_to_expected: OutputToExpectedMapping,
    assert_func: AssertFileContent,
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Execute main() and assert specific output files match expected files.

    Args:
        input_path: Path to input schema file
        output_path: Path to output directory
        output_to_expected: List of (output_relative_path, expected_file_path) tuples
        assert_func: The assert_file_content function to use for verification
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
    """
    return_code = run_main(input_path, output_path, input_file_type, extra_args=extra_args)
    assert return_code == Exit.OK
    for output_relative, expected_file in output_to_expected:
        assert_func(output_path / output_relative, expected_file)


def run_main_and_assert_stdout(
    *,
    input_path: Path,
    expected_output_path: Path,
    capsys: pytest.CaptureFixture[str],
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
    expected_stderr: str | None = None,
) -> None:
    """Execute main() without output file and assert stdout matches expected.

    Args:
        input_path: Path to input schema file
        expected_output_path: Path to file with expected stdout content
        capsys: pytest capsys fixture for capturing output
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
        expected_stderr: Expected stderr content (if any)
    """
    args = ["--input", str(input_path)]
    if input_file_type is not None:
        args.extend(["--input-file-type", input_file_type])
    if extra_args is not None:
        args.extend(extra_args)

    main(args)
    captured = capsys.readouterr()
    assert_output(captured.out, expected_output_path)
    if expected_stderr is not None:
        assert captured.err == expected_stderr


def run_main_and_assert_stdin(
    *,
    stdin_path: Path,
    output_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    input_file_type: InputFileTypeLiteral | None = None,
    assert_func: AssertFileContent,
    expected_file: str | Path | None = None,
    extra_args: Sequence[str] | None = None,
    transform: Callable[[str], str] | None = None,
) -> None:
    """Execute main() with stdin input and assert output.

    Args:
        stdin_path: Path to file that will be used as stdin
        output_path: Path to output file
        monkeypatch: pytest monkeypatch fixture for mocking stdin
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        assert_func: The assert_file_content function to use for verification
        expected_file: Expected output filename (optional, inferred from test name if None)
        extra_args: Additional CLI arguments
        transform: Optional function to transform output before comparison
    """
    monkeypatch.setattr("sys.stdin", stdin_path.open(encoding="utf-8"))
    args = ["--output", str(output_path)]
    if input_file_type is not None:
        args.extend(["--input-file-type", input_file_type])
    if extra_args is not None:
        args.extend(extra_args)

    return_code = main(args)
    assert return_code == Exit.OK

    if expected_file is None:
        frame = inspect.currentframe()
        assert frame is not None
        assert frame.f_back is not None
        func_name = frame.f_back.f_code.co_name
        del frame
        for prefix in ("test_main_", "test_"):
            if func_name.startswith(prefix):
                func_name = func_name[len(prefix) :]
                break
        expected_file = f"{func_name}.py"
    assert_func(output_path, expected_file, transform=transform)


def run_main_url(
    url: str,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None = None,
    *,
    extra_args: Sequence[str] | None = None,
) -> Exit:
    """Execute main() with URL input.

    Args:
        url: URL to fetch schema from
        output_path: Path to output file/directory
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments

    Returns:
        Exit code from main()
    """
    args = ["--url", url, "--output", str(output_path)]
    if input_file_type is not None:
        args.extend(["--input-file-type", input_file_type])
    if extra_args is not None:
        args.extend(extra_args)
    return main(args)


def run_main_url_and_assert(
    *,
    url: str,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None,
    assert_func: AssertFileContent,
    expected_file: str | Path | None = None,
    extra_args: Sequence[str] | None = None,
    transform: Callable[[str], str] | None = None,
) -> None:
    """Execute main() with URL input and assert output.

    Args:
        url: URL to fetch schema from
        output_path: Path to output file
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        assert_func: The assert_file_content function to use for verification
        expected_file: Expected output filename (optional, inferred from test name if None)
        extra_args: Additional CLI arguments
        transform: Optional function to transform output before comparison
    """
    return_code = run_main_url(url, output_path, input_file_type, extra_args=extra_args)
    assert return_code == Exit.OK

    if expected_file is None:
        frame = inspect.currentframe()
        assert frame is not None
        assert frame.f_back is not None
        func_name = frame.f_back.f_code.co_name
        del frame
        for prefix in ("test_main_", "test_"):
            if func_name.startswith(prefix):
                func_name = func_name[len(prefix) :]
                break
        expected_file = f"{func_name}.py"
    assert_func(output_path, expected_file, transform=transform)


def run_main_and_assert_error(
    input_path: Path,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None = None,
    *,
    extra_args: Sequence[str] | None = None,
    capsys: pytest.CaptureFixture[str] | None = None,
    expected_stderr_contains: str | None = None,
) -> None:
    """Execute main() and assert it returns an error.

    Args:
        input_path: Path to input schema file
        output_path: Path to output file/directory
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
        capsys: pytest capsys fixture for capturing output (required if expected_stderr_contains is set)
        expected_stderr_contains: String that should be contained in stderr
    """
    return_code = run_main(input_path, output_path, input_file_type, extra_args=extra_args)
    assert return_code == Exit.ERROR
    if expected_stderr_contains is not None:
        assert capsys is not None
        captured = capsys.readouterr()
        assert expected_stderr_contains in captured.err


def run_main_and_assert_output(
    *,
    input_path: Path,
    output_path: Path,
    expected_output: str,
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
    ignore_whitespace: bool = False,
) -> None:
    """Execute main() and assert output matches expected string.

    Args:
        input_path: Path to input schema file
        output_path: Path to output file
        expected_output: Expected output content as string
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
        ignore_whitespace: If True, compare outputs ignoring all whitespace
    """
    return_code = run_main(input_path, output_path, input_file_type, extra_args=extra_args)
    assert return_code == Exit.OK
    actual_output = output_path.read_text(encoding="utf-8")
    if ignore_whitespace:
        assert "".join(actual_output.split()) == "".join(expected_output.split()), (
            f"\nExpected output:\n{expected_output}\n\nGenerated output:\n{actual_output}"
        )
    else:
        assert actual_output == expected_output, (
            f"\nExpected output:\n{expected_output}\n\nGenerated output:\n{actual_output}"
        )


def run_main_and_assert_no_stderr(
    *,
    input_path: Path,
    output_path: Path,
    capsys: pytest.CaptureFixture[str],
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Execute main() and assert no stderr output.

    Args:
        input_path: Path to input schema file
        output_path: Path to output file
        capsys: pytest capsys fixture for capturing output
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
    """
    return_code = run_main(input_path, output_path, input_file_type, extra_args=extra_args)
    captured = capsys.readouterr()
    assert return_code == Exit.OK
    assert not captured.err


def run_main_and_assert_file_not_exists(
    *,
    input_path: Path,
    output_path: Path,
    file_should_not_exist: Path,
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Execute main() and assert a specific file does not exist.

    Args:
        input_path: Path to input schema file
        output_path: Path to output directory
        file_should_not_exist: Path to file that should NOT exist after generation
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
    """
    return_code = run_main(input_path, output_path, input_file_type, extra_args=extra_args)
    assert return_code == Exit.OK
    assert not file_should_not_exist.exists()
