from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from freezegun import freeze_time

from datamodel_code_generator.__main__ import Exit, main
from tests.main.test_main_general import DATA_PATH

GRAPHQL_DATA_PATH: Path = DATA_PATH / "graphql"
EXPECTED_GRAPHQL_PATH: Path = DATA_PATH / "expected" / "parser" / "graphql"


@freeze_time("2019-07-26")
def test_graphql_field_enum() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(GRAPHQL_DATA_PATH / "field-default-enum.graphql"),
            "--output",
            str(output_file),
            "--input-file-type",
            "graphql",
            "--set-default-enum-member",
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_GRAPHQL_PATH / "field-default-enum.py").read_text()


@freeze_time("2019-07-26")
def test_graphql_union_aliased_bug() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(GRAPHQL_DATA_PATH / "union-aliased-bug.graphql"),
            "--output",
            str(output_file),
            "--input-file-type",
            "graphql",
        ])
        assert return_code == Exit.OK
        actual = output_file.read_text().rstrip()
        expected = (EXPECTED_GRAPHQL_PATH / "union-aliased-bug.py").read_text().rstrip()
        if actual != expected:
            pass
        assert actual == expected
