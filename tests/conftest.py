from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from inline_snapshot import external_file, register_format_alias

from datamodel_code_generator import MIN_VERSION


def _get_caller_info() -> tuple[Path | None, str]:
    """Get expected base path and function name from caller's caller."""
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back.f_back
        func_name = caller_frame.f_code.co_name

        caller_globals = caller_frame.f_globals
        expected_base = None
        for name, value in caller_globals.items():
            if name.startswith("EXPECTED_") and name.endswith("_PATH") and isinstance(value, Path):
                expected_base = value
                break

        return expected_base, func_name
    finally:
        del frame


def assert_file_content(
    output_file: Path,
    expected_path: Path | None = None,
    *,
    expected_name: str | None = None,
    encoding: str = "utf-8",
) -> None:
    """Assert that file content matches expected external file.

    Args:
        output_file: The generated output file to check.
        expected_path: Full path to expected file. If None, inferred from caller.
        expected_name: Filename only (e.g., "general.py"). Used with auto-detected base path.
        encoding: File encoding.

    Usage:
        # Full path
        assert_file_content(output_file, EXPECTED_PATH / "output.py")

        # Auto-infer from function name (test_main_foo -> foo.py)
        assert_file_content(output_file)

        # Custom filename with auto-detected base path
        assert_file_content(output_file, expected_name="general.py")
    """
    if expected_path is None:
        expected_base, func_name = _get_caller_info()

        if expected_base is None:
            raise ValueError(
                "Could not find EXPECTED_*_PATH in calling module. "
                "Please specify expected_path explicitly."
            )

        if expected_name is None:
            name = func_name
            for prefix in ["test_main_", "test_"]:
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    break
            expected_name = f"{name}.py"

        expected_path = expected_base / expected_name

    assert output_file.read_text(encoding=encoding) == external_file(expected_path)


register_format_alias(".py", ".txt")
register_format_alias(".pyi", ".txt")


@pytest.fixture(autouse=True)
def _inline_snapshot_file_formats() -> None:
    register_format_alias(".py", ".txt")
    register_format_alias(".pyi", ".txt")


@pytest.fixture(scope="session")
def min_version() -> str:
    return f"3.{MIN_VERSION}"
