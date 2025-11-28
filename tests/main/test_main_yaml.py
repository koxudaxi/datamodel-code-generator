"""Tests for YAML input file code generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator.__main__ import Exit
from tests.conftest import create_assert_file_content
from tests.main.conftest import (
    EXPECTED_MAIN_PATH,
    YAML_DATA_PATH,
    run_main_and_assert,
)

if TYPE_CHECKING:
    from pathlib import Path

assert_file_content = create_assert_file_content(EXPECTED_MAIN_PATH)


@pytest.mark.benchmark
def test_main_yaml(output_file: Path) -> None:
    """Test YAML input file code generation."""
    run_main_and_assert(
        input_path=YAML_DATA_PATH / "pet.yaml",
        output_path=output_file,
        input_file_type="yaml",
        assert_func=assert_file_content,
    )


def test_main_yaml_invalid_root_list(output_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test YAML file with list as root element fails with invalid file format error."""
    run_main_and_assert(
        input_path=YAML_DATA_PATH / "invalid_root_list.yaml",
        output_path=output_file,
        input_file_type="yaml",
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains="Invalid file format",
    )
