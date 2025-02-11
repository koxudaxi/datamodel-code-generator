from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from freezegun import freeze_time

from datamodel_code_generator.__main__ import Exit, main
from tests.main.test_main_general import DATA_PATH, EXPECTED_MAIN_PATH

GRAPHQL_DATA_PATH: Path = DATA_PATH / "graphql"
EXPECTED_GRAPHQL_PATH: Path = EXPECTED_MAIN_PATH / "graphql"


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace_)
    monkeypatch.setattr("datamodel_code_generator.arguments.namespace", namespace_)


@freeze_time("2019-07-26")
def test_annotated() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(GRAPHQL_DATA_PATH / "annotated.graphql"),
            "--output",
            str(output_file),
            "--input-file-type",
            "graphql",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_GRAPHQL_PATH / "annotated.py").read_text()


@freeze_time("2019-07-26")
def test_annotated_use_standard_collections() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(GRAPHQL_DATA_PATH / "annotated.graphql"),
            "--output",
            str(output_file),
            "--input-file-type",
            "graphql",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--use-standard-collections",
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_GRAPHQL_PATH / "annotated_use_standard_collections.py").read_text()


@freeze_time("2019-07-26")
def test_annotated_use_standard_collections_use_union_operator() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(GRAPHQL_DATA_PATH / "annotated.graphql"),
            "--output",
            str(output_file),
            "--input-file-type",
            "graphql",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--use-standard-collections",
            "--use-union-operator",
        ])
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_GRAPHQL_PATH / "annotated_use_standard_collections_use_union_operator.py").read_text()
        )


@freeze_time("2019-07-26")
def test_annotated_use_union_operator() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(GRAPHQL_DATA_PATH / "annotated.graphql"),
            "--output",
            str(output_file),
            "--input-file-type",
            "graphql",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--use-union-operator",
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_GRAPHQL_PATH / "annotated_use_union_operator.py").read_text()


@freeze_time("2019-07-26")
def test_annotated_field_aliases() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(GRAPHQL_DATA_PATH / "field-aliases.graphql"),
            "--output",
            str(output_file),
            "--input-file-type",
            "graphql",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--aliases",
            str(GRAPHQL_DATA_PATH / "field-aliases.json"),
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_GRAPHQL_PATH / "annotated_field_aliases.py").read_text()
