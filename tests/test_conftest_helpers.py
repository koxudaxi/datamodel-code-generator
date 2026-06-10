"""Tests for shared assertion helpers in tests.conftest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.conftest import assert_exact_directory_content, assert_parser_modules, assert_parser_results

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


def test_assert_parser_results_rejects_unexpected_result(tmp_path: Path) -> None:
    """Parser result assertions fail when generated output has no expected file."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()
    (expected_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(AssertionError, match=r"extra\.py"):
        assert_parser_results({"sample.py": "value = 1\n", "extra.py": "value = 2\n"}, expected_dir)


def test_assert_parser_results_rejects_missing_result(tmp_path: Path) -> None:
    """Parser result assertions fail when an expected file is not generated."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()
    (expected_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")
    (expected_dir / "missing.py").write_text("value = 2\n", encoding="utf-8")

    with pytest.raises(AssertionError, match=r"missing\.py"):
        assert_parser_results({"sample.py": "value = 1\n"}, expected_dir)


def test_assert_parser_modules_rejects_missing_expected_module(tmp_path: Path) -> None:
    """Parser module assertions fail when an expected module is not generated."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()
    (expected_dir / "sample.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="Expected files not in parser modules"):
        assert_parser_modules({}, expected_dir)


def test_assert_parser_modules_rejects_unexpected_module(tmp_path: Path) -> None:
    """Parser module assertions fail when generated output has no expected file."""
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()

    with pytest.raises(AssertionError, match="Parser modules not in expected files"):
        assert_parser_modules({("sample.py",): "value = 1\n"}, expected_dir)
