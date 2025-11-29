"""Tests for CSV input file code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.conftest import create_assert_file_content
from tests.main.conftest import (
    CSV_DATA_PATH,
    EXPECTED_CSV_PATH,
    run_main_and_assert,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


assert_file_content = create_assert_file_content(EXPECTED_CSV_PATH)


def test_csv_file(output_file: Path) -> None:
    """Test CSV file input code generation."""
    run_main_and_assert(
        input_path=CSV_DATA_PATH / "simple.csv",
        output_path=output_file,
        input_file_type="csv",
        assert_func=assert_file_content,
        expected_file="csv_file_simple.py",
    )


def test_csv_stdin(monkeypatch: pytest.MonkeyPatch, output_file: Path) -> None:
    """Test CSV stdin input code generation."""
    run_main_and_assert(
        stdin_path=CSV_DATA_PATH / "simple.csv",
        output_path=output_file,
        monkeypatch=monkeypatch,
        input_file_type="csv",
        assert_func=assert_file_content,
        expected_file="csv_stdin_simple.py",
    )
