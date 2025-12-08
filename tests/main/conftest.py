"""Shared fixtures and utilities for main integration tests."""

from __future__ import annotations

import inspect
import shutil
import sys
from argparse import Namespace
from collections.abc import Callable, Generator, Sequence
from pathlib import Path
from typing import Literal

import black
import pytest
from packaging import version

from datamodel_code_generator.__main__ import Exit, main
from tests.conftest import AssertFileContent, assert_directory_content, assert_output, freeze_time

InputFileTypeLiteral = Literal["auto", "openapi", "jsonschema", "json", "yaml", "dict", "csv", "graphql"]
CopyFilesMapping = Sequence[tuple[Path, Path]]

MSGSPEC_LEGACY_BLACK_SKIP = pytest.mark.skipif(
    sys.version_info[:2] == (3, 12) and version.parse(black.__version__) < version.parse("24.0.0"),
    reason="msgspec.Struct formatting differs with python3.12 + black < 24",
)

LEGACY_BLACK_SKIP = pytest.mark.skipif(
    version.parse(black.__version__) < version.parse("24.0.0"),
    reason="Type annotation formatting differs with black < 24",
)

DATA_PATH: Path = Path(__file__).parent.parent / "data"
EXPECTED_MAIN_PATH: Path = DATA_PATH / "expected" / "main"

PYTHON_DATA_PATH: Path = DATA_PATH / "python"
OPEN_API_DATA_PATH: Path = DATA_PATH / "openapi"
JSON_SCHEMA_DATA_PATH: Path = DATA_PATH / "jsonschema"
GRAPHQL_DATA_PATH: Path = DATA_PATH / "graphql"
JSON_DATA_PATH: Path = DATA_PATH / "json"
CSV_DATA_PATH: Path = DATA_PATH / "csv"
YAML_DATA_PATH: Path = DATA_PATH / "yaml"
ALIASES_DATA_PATH: Path = DATA_PATH / "aliases"

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


def _assert_exit_code(return_code: Exit, expected_exit: Exit, context: str) -> None:
    """Assert exit code matches expected value."""
    if return_code != expected_exit:  # pragma: no cover
        pytest.fail(f"Expected exit code {expected_exit!r}, got {return_code!r}\n{context}")


def _extend_args(
    args: list[str],
    *,
    input_path: Path | None = None,
    output_path: Path | None = None,
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
) -> None:
    """Extend args with optional input_path, output_path, input_file_type and extra_args."""
    if input_path is not None:
        args.extend(["--input", str(input_path)])
    if output_path is not None:
        args.extend(["--output", str(output_path)])
    if input_file_type is not None:
        args.extend(["--input-file-type", input_file_type])
    if extra_args is not None:
        args.extend(extra_args)


def _run_main(
    input_path: Path,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None = None,
    *,
    extra_args: Sequence[str] | None = None,
    copy_files: CopyFilesMapping | None = None,
) -> Exit:
    """Execute main() with standard arguments (internal use)."""
    _copy_files(copy_files)
    args: list[str] = []
    _extend_args(
        args, input_path=input_path, output_path=output_path, input_file_type=input_file_type, extra_args=extra_args
    )
    return main(args)


def _run_main_url(
    url: str,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None = None,
    *,
    extra_args: Sequence[str] | None = None,
) -> Exit:
    """Execute main() with URL input (internal use)."""
    args = ["--url", url]
    _extend_args(args, output_path=output_path, input_file_type=input_file_type, extra_args=extra_args)
    return main(args)


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
    __tracebackhide__ = True
    return_code = main(list(args))
    _assert_exit_code(return_code, expected_exit, f"Args: {args}")
    if expected_stdout_path is not None:  # pragma: no branch
        if capsys is None:  # pragma: no cover
            pytest.fail("capsys is required when expected_stdout_path is set")
        captured = capsys.readouterr()
        assert_output(captured.out, expected_stdout_path)
    return return_code


def run_main_and_assert(  # noqa: PLR0912
    *,
    input_path: Path | None = None,
    output_path: Path | None = None,
    input_file_type: InputFileTypeLiteral | None = None,
    extra_args: Sequence[str] | None = None,
    expected_exit: Exit = Exit.OK,
    # Output verification options (use one)
    assert_func: AssertFileContent | None = None,
    expected_file: str | Path | None = None,
    expected_output: str | None = None,
    expected_directory: Path | None = None,
    output_to_expected: Sequence[tuple[str, str | Path]] | None = None,
    file_should_not_exist: Path | None = None,
    # Verification options
    ignore_whitespace: bool = False,
    transform: Callable[[str], str] | None = None,
    # Capture options
    capsys: pytest.CaptureFixture[str] | None = None,
    expected_stdout_path: Path | None = None,
    expected_stderr: str | None = None,
    expected_stderr_contains: str | None = None,
    assert_no_stderr: bool = False,
    # Other options
    copy_files: CopyFilesMapping | None = None,
    # stdin options
    stdin_path: Path | None = None,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> None:
    """Execute main() and assert output.

    This is the unified helper function for testing file-based input.

    Input options:
        input_path: Path to input schema file
        stdin_path: Path to file that will be used as stdin (requires monkeypatch)
        monkeypatch: pytest monkeypatch fixture for mocking stdin

    Output options:
        output_path: Path to output file/directory (None for stdout-only tests)

    Common options:
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        extra_args: Additional CLI arguments
        expected_exit: Expected exit code (default: Exit.OK)
        copy_files: Files to copy before running

    Output verification (use one):
        assert_func + expected_file: Compare with expected file using assert function
        expected_output: Compare with string directly
        expected_directory: Compare entire directory
        output_to_expected: Compare multiple files
        file_should_not_exist: Assert a file does NOT exist

    Verification modifiers:
        ignore_whitespace: Ignore whitespace when comparing (for expected_output)
        transform: Transform output before comparison

    Capture verification:
        capsys: pytest capsys fixture
        expected_stdout_path: Compare stdout with file
        expected_stderr: Assert exact stderr match
        expected_stderr_contains: Assert stderr contains string
        assert_no_stderr: Assert stderr is empty
    """
    __tracebackhide__ = True

    # Handle stdin input
    if stdin_path is not None:
        if monkeypatch is None:  # pragma: no cover
            pytest.fail("monkeypatch is required when using stdin_path")
        monkeypatch.setattr("sys.stdin", stdin_path.open(encoding="utf-8"))
        args: list[str] = []
        _extend_args(args, output_path=output_path, input_file_type=input_file_type, extra_args=extra_args)
        return_code = main(args)
    # Handle stdout-only output (no output_path)
    elif output_path is None:
        if input_path is None:  # pragma: no cover
            pytest.fail("input_path is required when output_path is None")
        args = []
        _extend_args(args, input_path=input_path, input_file_type=input_file_type, extra_args=extra_args)
        return_code = main(args)
    # Standard file input
    else:
        if input_path is None:  # pragma: no cover
            pytest.fail("input_path is required")
        return_code = _run_main(input_path, output_path, input_file_type, extra_args=extra_args, copy_files=copy_files)

    _assert_exit_code(return_code, expected_exit, f"Input: {input_path}")

    # Handle capture assertions
    if capsys is not None and (
        expected_stdout_path is not None
        or expected_stderr is not None
        or expected_stderr_contains is not None
        or assert_no_stderr
    ):
        captured = capsys.readouterr()
        if expected_stdout_path is not None:
            assert_output(captured.out, expected_stdout_path)
        if expected_stderr is not None and captured.err != expected_stderr:  # pragma: no cover
            pytest.fail(f"Expected stderr:\n{expected_stderr}\n\nActual stderr:\n{captured.err}")
        if expected_stderr_contains is not None and expected_stderr_contains not in captured.err:  # pragma: no cover
            pytest.fail(f"Expected stderr to contain: {expected_stderr_contains!r}\n\nActual stderr:\n{captured.err}")
        if assert_no_stderr and captured.err:  # pragma: no cover
            pytest.fail(f"Expected no stderr, but got:\n{captured.err}")

    # Skip output verification if expected_exit is not OK
    if expected_exit != Exit.OK:
        return

    # Output verification
    if expected_directory is not None:
        if output_path is None:  # pragma: no cover
            pytest.fail("output_path is required when using expected_directory")
        assert_directory_content(output_path, expected_directory)
    elif output_to_expected is not None:
        if output_path is None:  # pragma: no cover
            pytest.fail("output_path is required when using output_to_expected")
        if assert_func is None:  # pragma: no cover
            pytest.fail("assert_func is required when using output_to_expected")
        for output_relative, exp_file in output_to_expected:
            assert_func(output_path / output_relative, exp_file)
    elif expected_output is not None:
        if output_path is None:  # pragma: no cover
            pytest.fail("output_path is required when using expected_output")
        actual_output = output_path.read_text(encoding="utf-8")
        if ignore_whitespace:
            if "".join(actual_output.split()) != "".join(expected_output.split()):  # pragma: no cover
                pytest.fail(
                    f"Output mismatch (ignoring whitespace)\nExpected:\n{expected_output}\n\nActual:\n{actual_output}"
                )
        elif actual_output != expected_output:  # pragma: no cover
            pytest.fail(f"Output mismatch\nExpected:\n{expected_output}\n\nActual:\n{actual_output}")
    elif file_should_not_exist is not None:
        if file_should_not_exist.exists():  # pragma: no cover
            pytest.fail(f"File should not exist: {file_should_not_exist}")
    elif assert_func is not None:
        if output_path is None:  # pragma: no cover
            pytest.fail("output_path is required when using assert_func")
        if expected_file is None:  # pragma: no branch
            frame = inspect.currentframe()
            assert frame is not None
            assert frame.f_back is not None
            func_name = frame.f_back.f_code.co_name
            del frame
            for prefix in ("test_main_", "test_"):  # pragma: no branch
                if func_name.startswith(prefix):
                    func_name = func_name[len(prefix) :]
                    break
            expected_file = f"{func_name}.py"
        assert_func(output_path, expected_file, transform=transform)


def run_main_url_and_assert(
    *,
    url: str,
    output_path: Path,
    input_file_type: InputFileTypeLiteral | None,
    assert_func: AssertFileContent,
    expected_file: str | Path,
    extra_args: Sequence[str] | None = None,
    transform: Callable[[str], str] | None = None,
) -> None:
    """Execute main() with URL input and assert output.

    Args:
        url: URL to fetch schema from
        output_path: Path to output file
        input_file_type: Type of input file (openapi, jsonschema, graphql, etc.)
        assert_func: The assert_file_content function to use for verification
        expected_file: Expected output filename
        extra_args: Additional CLI arguments
        transform: Optional function to transform output before comparison
    """
    __tracebackhide__ = True
    return_code = _run_main_url(url, output_path, input_file_type, extra_args=extra_args)
    _assert_exit_code(return_code, Exit.OK, f"URL: {url}")
    assert_func(output_path, expected_file, transform=transform)
