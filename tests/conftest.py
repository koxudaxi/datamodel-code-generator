from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Protocol

import pytest
from inline_snapshot import external_file, register_format_alias

from datamodel_code_generator import MIN_VERSION

if TYPE_CHECKING:
    from pathlib import Path


class AssertFileContent(Protocol):
    def __call__(
        self,
        output_file: Path,
        expected_name: str | Path | None = None,
        encoding: str = "utf-8",
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
        assert output_file.read_text(encoding=encoding) == external_file(expected_path)

    return _assert_file_content


register_format_alias(".py", ".txt")
register_format_alias(".pyi", ".txt")


@pytest.fixture(autouse=True)
def _inline_snapshot_file_formats() -> None:
    register_format_alias(".py", ".txt")
    register_format_alias(".pyi", ".txt")


@pytest.fixture(scope="session")
def min_version() -> str:
    return f"3.{MIN_VERSION}"
