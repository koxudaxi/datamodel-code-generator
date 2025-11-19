from __future__ import annotations

import inspect
import sys
from typing import TYPE_CHECKING, Protocol

import pytest
from inline_snapshot import external_file, register_format_alias

from datamodel_code_generator import MIN_VERSION

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

IS_WINDOWS = sys.platform == "win32"


def _normalize_line_endings(text: str) -> str:
    """Normalize line endings to LF on Windows."""
    if IS_WINDOWS:
        return text.replace("\r\n", "\n")
    return text


class AssertFileContent(Protocol):
    def __call__(
        self,
        output_file: Path,
        expected_name: str | Path | None = None,
        encoding: str = "utf-8",
        transform: Callable[[str], str] | None = None,
    ) -> None: ...


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
        if expected_name is None:
            frame = inspect.currentframe()
            if frame is None or frame.f_back is None:
                msg = "Cannot determine caller frame"
                raise RuntimeError(msg)
            try:
                func_name = frame.f_back.f_code.co_name
                name = func_name
                for prefix in ("test_main_", "test_"):
                    if name.startswith(prefix):
                        name = name[len(prefix) :]
                        break
                expected_name = f"{name}.py"
            finally:
                del frame

        expected_path = base_path / expected_name
        content = output_file.read_text(encoding=encoding)
        if transform is not None:
            content = transform(content)
        assert _normalize_line_endings(content) == external_file(expected_path)

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
    assert _normalize_line_endings(output) == external_file(expected_path)


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
    for expected_path in expected_dir.rglob(pattern):
        relative_path = expected_path.relative_to(expected_dir)
        output_path = output_dir / relative_path
        result = output_path.read_text(encoding=encoding)
        assert _normalize_line_endings(result) == external_file(expected_path)


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
    for expected_path in expected_dir.rglob(pattern):
        key = str(expected_path.relative_to(expected_dir))
        result_obj = results.pop(key)
        assert _normalize_line_endings(result_obj.body) == external_file(expected_path)


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
    for paths, result in modules.items():
        expected_path = expected_dir.joinpath(*paths)
        assert _normalize_line_endings(result.body) == external_file(expected_path)


register_format_alias(".py", ".txt")
register_format_alias(".pyi", ".txt")
register_format_alias(".snapshot", ".txt")


@pytest.fixture(autouse=True)
def _inline_snapshot_file_formats() -> None:
    register_format_alias(".py", ".txt")
    register_format_alias(".pyi", ".txt")
    register_format_alias(".snapshot", ".txt")


@pytest.fixture(scope="session")
def min_version() -> str:
    return f"3.{MIN_VERSION}"
