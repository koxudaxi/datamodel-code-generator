from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import pytest
from freezegun import freeze_time

from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    generate,
    snooper_to_methods,
)
from datamodel_code_generator.__main__ import Config, Exit, main

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

DATA_PATH: Path = Path(__file__).parent.parent / "data"
PYTHON_DATA_PATH: Path = DATA_PATH / "python"
EXPECTED_MAIN_PATH = DATA_PATH / "expected" / "main"

TIMESTAMP = "1985-10-26T01:21:00-07:00"


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace_)
    monkeypatch.setattr("datamodel_code_generator.arguments.namespace", namespace_)


def test_debug(mocker: MockerFixture) -> None:
    with pytest.raises(expected_exception=SystemExit):
        main(["--debug", "--help"])

    mocker.patch("datamodel_code_generator.pysnooper", None)
    with pytest.raises(expected_exception=SystemExit):
        main(["--debug", "--help"])


@freeze_time("2019-07-26")
def test_snooper_to_methods_without_pysnooper(mocker: MockerFixture) -> None:
    mocker.patch("datamodel_code_generator.pysnooper", None)
    mock = mocker.Mock()
    assert snooper_to_methods()(mock) == mock


@pytest.mark.parametrize(argnames="no_color", argvalues=[False, True])
def test_show_help(no_color: bool, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["--no-color"] if no_color else []
    args += ["--help"]

    with pytest.raises(expected_exception=SystemExit) as context:
        main(args)
    assert context.value.code == Exit.OK

    output = capsys.readouterr().out
    assert ("\x1b" not in output) == no_color


def test_show_help_when_no_input(mocker: MockerFixture) -> None:
    print_help_mock = mocker.patch("datamodel_code_generator.__main__.arg_parser.print_help")
    isatty_mock = mocker.patch("sys.stdin.isatty", return_value=True)
    return_code: Exit = main([])
    assert return_code == Exit.ERROR
    assert isatty_mock.called
    assert print_help_mock.called


def test_no_args_has_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    No argument should have a default value set because it would override pyproject.toml values.

    Default values are set in __main__.Config class.
    """
    namespace = Namespace()
    monkeypatch.setattr("datamodel_code_generator.__main__.namespace", namespace)
    main([])
    for field in Config.get_fields():
        assert getattr(namespace, field, None) is None


@freeze_time("2019-07-26")
def test_space_and_special_characters_dict() -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / "output.py"
        return_code: Exit = main([
            "--input",
            str(PYTHON_DATA_PATH / "space_and_special_characters_dict.py"),
            "--output",
            str(output_file),
            "--input-file-type",
            "dict",
        ])
        assert return_code == Exit.OK
        assert output_file.read_text() == (EXPECTED_MAIN_PATH / "space_and_special_characters_dict.py").read_text()


@freeze_time("2024-12-14")
def test_direct_input_dict() -> None:
    with TemporaryDirectory() as output_dir:
        output_file = Path(output_dir) / "output.py"
        generate(
            {"foo": 1, "bar": {"baz": 2}},
            input_file_type=InputFileType.Dict,
            output=output_file,
            output_model_type=DataModelType.PydanticV2BaseModel,
            snake_case_field=True,
        )
        assert output_file.read_text() == (EXPECTED_MAIN_PATH / "direct_input_dict.py").read_text()
