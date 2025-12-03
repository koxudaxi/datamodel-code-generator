"""Test configuration and shared fixtures."""

from __future__ import annotations

import difflib
import inspect
import sys
from typing import TYPE_CHECKING, Any, Protocol

import pytest
from inline_snapshot import external_file, register_format_alias

from datamodel_code_generator import MIN_VERSION

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

if sys.version_info >= (3, 10):
    from datetime import datetime, timezone

    import time_machine

    def _parse_time_string(time_str: str) -> datetime:
        """Parse time string to datetime with UTC timezone."""
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(time_str, fmt)  # noqa: DTZ007
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt  # noqa: TRY300
            except ValueError:  # noqa: PERF203
                continue
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))  # pragma: no cover

    def freeze_time(time_to_freeze: str, **kwargs: Any) -> time_machine.travel:  # noqa: ARG001
        """Freeze time using time-machine (100-200x faster than freezegun)."""
        dt = _parse_time_string(time_to_freeze)
        return time_machine.travel(dt, tick=False)

else:
    from freezegun import freeze_time as freeze_time  # noqa: PLC0414


def _normalize_line_endings(text: str) -> str:
    """Normalize line endings to LF for cross-platform comparison."""
    return text.replace("\r\n", "\n")


def _get_tox_env() -> str:  # pragma: no cover
    """Get the current tox environment name from TOX_ENV_NAME or fallback.

    Strips '-parallel' suffix since inline-snapshot requires -n0 (single process).
    """
    import os  # noqa: PLC0415

    env = os.environ.get("TOX_ENV_NAME", "<version>")
    # Remove -parallel suffix since inline-snapshot needs single process mode
    return env.removesuffix("-parallel")


def _format_snapshot_hint(action: str) -> str:  # pragma: no cover
    """Format a hint message for inline-snapshot commands with rich formatting."""
    from io import StringIO  # noqa: PLC0415

    from rich.console import Console  # noqa: PLC0415
    from rich.text import Text  # noqa: PLC0415

    tox_env = _get_tox_env()
    command = f"  tox run -e {tox_env} -- --inline-snapshot={action}"

    description = "To update the expected file, run:" if action == "fix" else "To create the expected file, run:"

    output = StringIO()
    console = Console(file=output, force_terminal=True, width=200, soft_wrap=False)

    console.print(Text(description, style="default"))
    console.print(Text(command, style="bold cyan"))

    return output.getvalue()


def _format_new_content(content: str) -> str:  # pragma: no cover
    """Format new content (for create mode) with green color."""
    from io import StringIO  # noqa: PLC0415

    from rich.console import Console  # noqa: PLC0415
    from rich.text import Text  # noqa: PLC0415

    output = StringIO()
    console = Console(file=output, force_terminal=True, width=200, soft_wrap=False)

    for line in content.splitlines():
        console.print(Text(f"+{line}", style="green"))

    return output.getvalue()


def _format_diff(expected: str, actual: str, expected_path: Path) -> str:  # pragma: no cover
    """Format a unified diff between expected and actual content with colors."""
    from io import StringIO  # noqa: PLC0415

    from rich.console import Console  # noqa: PLC0415
    from rich.text import Text  # noqa: PLC0415

    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile=str(expected_path),
            tofile="actual",
        )
    )

    if not diff_lines:
        return ""

    output = StringIO()
    console = Console(file=output, force_terminal=True, width=200, soft_wrap=False)

    for line in diff_lines:
        line_stripped = line.rstrip("\n")
        # Skip header lines since file path is already in the error message
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("@@"):
            console.print(Text(line_stripped, style="cyan"))
        elif line.startswith("-"):
            console.print(Text(line_stripped, style="red"))
        elif line.startswith("+"):
            console.print(Text(line_stripped, style="green"))
        else:
            # Use default to override pytest's red color for E lines
            console.print(Text(line_stripped, style="default"))

    return output.getvalue()


def _assert_with_external_file(content: str, expected_path: Path) -> None:
    """Assert content matches external file, handling line endings."""
    __tracebackhide__ = True
    try:
        expected = external_file(expected_path)
    except FileNotFoundError:  # pragma: no cover
        hint = _format_snapshot_hint("create")
        formatted_content = _format_new_content(content)
        msg = f"Expected file not found: {expected_path}\n{hint}\n{formatted_content}"
        raise AssertionError(msg) from None  # pragma: no cover
    normalized_content = _normalize_line_endings(content)
    if isinstance(expected, str):  # pragma: no branch
        normalized_expected = _normalize_line_endings(expected)
        if normalized_content != normalized_expected:  # pragma: no cover
            hint = _format_snapshot_hint("fix")
            diff = _format_diff(normalized_expected, normalized_content, expected_path)
            msg = f"Content mismatch for {expected_path}\n{hint}\n{diff}"
            raise AssertionError(msg) from None
    else:
        assert expected == normalized_content  # pragma: no cover


class AssertFileContent(Protocol):
    """Protocol for file content assertion callable."""

    def __call__(
        self,
        output_file: Path,
        expected_name: str | Path | None = None,
        encoding: str = "utf-8",
        transform: Callable[[str], str] | None = None,
    ) -> None:
        """Assert file content matches expected output."""
        ...


def create_assert_file_content(
    base_path: Path,
) -> AssertFileContent:
    """Create an assert function bound to a specific expected path.

    Args:
        base_path: The base path for expected files (e.g., EXPECTED_JSON_SCHEMA_PATH).

    Returns:
        A function that asserts file content matches expected.

    Usage:
        # In test module
        assert_file_content = create_assert_file_content(EXPECTED_JSON_SCHEMA_PATH)

        # In tests - infer from function name
        assert_file_content(output_file)  # test_main_foo -> foo.py

        # Explicit filename
        assert_file_content(output_file, "custom.py")
        assert_file_content(output_file, "subdir/bar.py")
        assert_file_content(output_file, f"{expected_output}/file.py")
    """

    def _assert_file_content(
        output_file: Path,
        expected_name: str | Path | None = None,
        encoding: str = "utf-8",
        transform: Callable[[str], str] | None = None,
    ) -> None:
        """Assert that file content matches expected external file."""
        __tracebackhide__ = True
        if expected_name is None:
            frame = inspect.currentframe()
            assert frame is not None
            assert frame.f_back is not None
            func_name = frame.f_back.f_code.co_name
            del frame
            name = func_name
            for prefix in ("test_main_", "test_"):
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    break
            expected_name = f"{name}.py"

        expected_path = base_path / expected_name
        content = output_file.read_text(encoding=encoding)
        if transform is not None:
            content = transform(content)
        _assert_with_external_file(content, expected_path)

    return _assert_file_content


def assert_output(
    output: str,
    expected_path: Path,
) -> None:
    """Assert that output string matches expected external file.

    Args:
        output: The output string to compare (e.g., captured.out, parser.parse()).
        expected_path: Path to the expected file.

    Usage:
        assert_output(captured.out, EXPECTED_PATH / "output.py")
        assert_output(parser.parse(), EXPECTED_PATH / "output.py")
    """
    __tracebackhide__ = True
    _assert_with_external_file(output, expected_path)


def assert_directory_content(
    output_dir: Path,
    expected_dir: Path,
    pattern: str = "*.py",
    encoding: str = "utf-8",
) -> None:
    """Assert all files in output_dir match expected files in expected_dir.

    Args:
        output_dir: Directory containing generated output files.
        expected_dir: Directory containing expected files.
        pattern: Glob pattern for files to compare (default: "*.py").
        encoding: File encoding (default: "utf-8").

    Usage:
        assert_directory_content(tmp_path / "model", EXPECTED_PATH / "main_modular")
    """
    __tracebackhide__ = True
    output_files = {p.relative_to(output_dir) for p in output_dir.rglob(pattern)}
    expected_files = {p.relative_to(expected_dir) for p in expected_dir.rglob(pattern)}

    # Check for extra expected files (output missing files that are expected)
    extra = expected_files - output_files
    assert not extra, f"Expected files not in output: {extra}"

    # Compare all output files (including new ones not yet in expected)
    for output_path in output_dir.rglob(pattern):
        relative_path = output_path.relative_to(output_dir)
        expected_path = expected_dir / relative_path
        result = output_path.read_text(encoding=encoding)
        _assert_with_external_file(result, expected_path)


def _get_full_body(result: object) -> str:
    """Get full body from Result."""
    return getattr(result, "body", "")


def assert_parser_results(
    results: dict,
    expected_dir: Path,
    pattern: str = "*.py",
) -> None:
    """Assert parser results match expected files.

    Args:
        results: Dictionary with string keys mapping to objects with .body attribute.
        expected_dir: Directory containing expected files.
        pattern: Glob pattern for files to compare (default: "*.py").

    Usage:
        results = {delimiter.join(p): r for p, r in parser.parse().items()}
        assert_parser_results(results, EXPECTED_PATH / "parser_output")
    """
    __tracebackhide__ = True
    for expected_path in expected_dir.rglob(pattern):
        key = str(expected_path.relative_to(expected_dir))
        result_obj = results.pop(key)
        _assert_with_external_file(_get_full_body(result_obj), expected_path)


def assert_parser_modules(
    modules: dict,
    expected_dir: Path,
) -> None:
    """Assert parser modules match expected files.

    Args:
        modules: Dictionary with tuple keys mapping to objects with .body attribute.
        expected_dir: Directory containing expected files.

    Usage:
        modules = parser.parse()
        assert_parser_modules(modules, EXPECTED_PATH / "parser_modular")
    """
    __tracebackhide__ = True
    for paths, result in modules.items():
        expected_path = expected_dir.joinpath(*paths)
        _assert_with_external_file(_get_full_body(result), expected_path)


@pytest.fixture(autouse=True)
def _inline_snapshot_file_formats() -> None:
    register_format_alias(".py", ".txt")
    register_format_alias(".pyi", ".txt")
    register_format_alias(".snapshot", ".txt")


@pytest.fixture(scope="session")
def min_version() -> str:
    """Return minimum Python version as string."""
    return f"3.{MIN_VERSION}"


@pytest.fixture(scope="session", autouse=True)
def _preload_heavy_modules() -> None:
    """Pre-import heavy modules once per session to warm up the import cache.

    This reduces per-test overhead when running with pytest-xdist,
    as each worker only pays the import cost once at session start.
    """
    import black  # noqa: PLC0415, F401
    import inflect  # noqa: PLC0415, F401
    import isort  # noqa: PLC0415, F401

    import datamodel_code_generator  # noqa: PLC0415, F401
