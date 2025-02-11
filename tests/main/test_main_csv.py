from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from freezegun import freeze_time

from datamodel_code_generator.__main__ import Exit, main
from tests.main.test_main_general import DATA_PATH, EXPECTED_MAIN_PATH

CSV_DATA_PATH: Path = DATA_PATH / "csv"
EXPECTED_CSV_PATH: Path = EXPECTED_MAIN_PATH / "csv"


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace_)
    monkeypatch.setattr("datamodel_code_generator.arguments.namespace", namespace_)


@freeze_time("2019-07-26")
def test_csv_file() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(CSV_DATA_PATH / "simple.csv"),
            "--output",
            str(output_file),
            "--input-file-type",
            "csv",
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_CSV_PATH / "csv_file_simple.py").read_text()


@freeze_time("2019-07-26")
def test_csv_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        monkeypatch.setattr("sys.stdin", (CSV_DATA_PATH / "simple.csv").open())
        return_code: Exit = main([
            "--output",
            str(output_file),
            "--input-file-type",
            "csv",
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_CSV_PATH / "csv_stdin_simple.py").read_text()
