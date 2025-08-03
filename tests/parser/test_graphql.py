from __future__ import annotations

from typing import TYPE_CHECKING

from freezegun import freeze_time

from datamodel_code_generator.__main__ import Exit, main
from tests.main.test_main_general import DATA_PATH

if TYPE_CHECKING:
    from pathlib import Path

GRAPHQL_DATA_PATH: Path = DATA_PATH / "graphql"
EXPECTED_GRAPHQL_PATH: Path = DATA_PATH / "expected" / "parser" / "graphql"


@freeze_time("2019-07-26")
def test_graphql_field_enum(tmp_path: Path) -> None:
    output_file: Path = tmp_path / "output.py"
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
def test_graphql_union_aliased_bug(tmp_path: Path) -> None:
    output_file: Path = tmp_path / "output.py"
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


@freeze_time("2019-07-26")
def test_graphql_union_commented(tmp_path: Path) -> None:
    output_file: Path = tmp_path / "output.py"
    return_code: Exit = main([
        "--input",
        str(GRAPHQL_DATA_PATH / "union-commented.graphql"),
        "--output",
        str(output_file),
        "--input-file-type",
        "graphql",
    ])
    assert return_code == Exit.OK
    actual = output_file.read_text().rstrip()
    expected = (EXPECTED_GRAPHQL_PATH / "union-commented.py").read_text().rstrip()
    if actual != expected:
        pass
    assert actual == expected
