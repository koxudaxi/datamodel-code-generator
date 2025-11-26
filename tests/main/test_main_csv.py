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

CSV_DATA_PATH: Path = DATA_PATH / "csv"
EXPECTED_CSV_PATH: Path = EXPECTED_MAIN_PATH / "csv"

assert_file_content = create_assert_file_content(EXPECTED_CSV_PATH)


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace_)
    monkeypatch.setattr("datamodel_code_generator.arguments.namespace", namespace_)


@freeze_time("2019-07-26")
def test_csv_file(tmp_path: Path) -> None:
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = main([
        "--input",
        str(CSV_DATA_PATH / "simple.csv"),
        "--output",
        str(output_file),
        "--input-file-type",
        "csv",
    ])
    assert return_code == Exit.OK
    assert_file_content(output_file, "csv_file_simple.py")


@freeze_time("2019-07-26")
def test_csv_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_file: Path = tmp_path / "output.py"
    monkeypatch.setattr("sys.stdin", (CSV_DATA_PATH / "simple.csv").open())
    return_code: Exit = main([
        "--output",
        str(output_file),
        "--input-file-type",
        "csv",
    ])
    assert return_code == Exit.OK
    assert_file_content(output_file, "csv_stdin_simple.py")
