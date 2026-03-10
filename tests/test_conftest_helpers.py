"""Tests for shared assertion helpers in tests.conftest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.conftest import assert_exact_directory_content

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
