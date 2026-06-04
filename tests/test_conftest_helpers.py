"""Tests for shared assertion helpers in tests.conftest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import black
import pytest

from tests.conftest import assert_exact_directory_content
from tests.main.conftest import (
    _black_line_length_for_settings,
    _builtin_formatter_extra_args,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_assert_exact_directory_content_reports_diff(tmp_path: Path) -> None:
    """Test exact directory comparison reports the mismatched file path."""
    output_dir = tmp_path / "output"
    expected_dir = tmp_path / "expected"
    output_dir.mkdir()
    expected_dir.mkdir()

    (output_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")
    (expected_dir / "sample.py").write_text("value = 2\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="Content mismatch") as exc_info:
        assert_exact_directory_content(output_dir, expected_dir)

    assert "sample.py" in str(exc_info.value)


def test_black_line_length_for_settings_ignores_bool_line_length(tmp_path: Path) -> None:
    """Test invalid pyproject Black line length falls back to Black's default."""
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text("[tool.black]\nline-length = false\n", encoding="utf-8")

    assert _black_line_length_for_settings(tmp_path) == black.DEFAULT_LINE_LENGTH


@pytest.mark.parametrize(
    ("line_length_args", "expected_line_length_args"),
    [
        (["--builtin-format-line-length", "96"], ["--builtin-format-line-length", "96"]),
        (["--builtin-format-line-length=96"], ["--builtin-format-line-length=96"]),
    ],
)
def test_builtin_formatter_extra_args_preserves_explicit_line_length(
    line_length_args: list[str], expected_line_length_args: list[str], tmp_path: Path
) -> None:
    """Test builtin formatter parity does not duplicate an explicit builtin line length."""
    extra_args = [*line_length_args, "--reuse-model"]

    assert _builtin_formatter_extra_args(extra_args, tmp_path) == [
        *expected_line_length_args,
        "--reuse-model",
        "--formatters",
        "builtin",
    ]


def test_builtin_formatter_extra_args_adds_missing_line_length(tmp_path: Path) -> None:
    """Test builtin formatter parity adds builtin line length when it is absent."""
    assert _builtin_formatter_extra_args(["--reuse-model"], tmp_path) == [
        "--reuse-model",
        "--builtin-format-line-length",
        str(black.DEFAULT_LINE_LENGTH),
        "--formatters",
        "builtin",
    ]
