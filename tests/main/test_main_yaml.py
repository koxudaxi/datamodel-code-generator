"""Tests for YAML input file code generation."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pytest
from freezegun import freeze_time

from datamodel_code_generator.__main__ import Exit, main
from tests.conftest import create_assert_file_content
from tests.main.test_main_general import DATA_PATH, EXPECTED_MAIN_PATH

if TYPE_CHECKING:
    from pathlib import Path

YAML_DATA_PATH: Path = DATA_PATH / "yaml"

assert_file_content = create_assert_file_content(EXPECTED_MAIN_PATH)


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset argument namespace before each test."""
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace_)
    monkeypatch.setattr("datamodel_code_generator.arguments.namespace", namespace_)


@pytest.mark.benchmark
@freeze_time("2019-07-26")
def test_main_yaml(tmp_path: Path) -> None:
    """Test YAML input file code generation."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = main([
        "--input",
        str(YAML_DATA_PATH / "pet.yaml"),
        "--output",
        str(output_file),
        "--input-file-type",
        "yaml",
    ])
    assert return_code == Exit.OK
    assert_file_content(output_file)


def test_main_yaml_invalid_root_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test YAML file with list as root element fails with invalid file format error."""
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = main([
        "--input",
        str(YAML_DATA_PATH / "invalid_root_list.yaml"),
        "--output",
        str(output_file),
        "--input-file-type",
        "yaml",
    ])
    assert return_code == Exit.ERROR
    captured = capsys.readouterr()
    assert "Invalid file format" in captured.err
