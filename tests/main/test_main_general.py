from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from freezegun import freeze_time

from datamodel_code_generator import (
    snooper_to_methods,
)
from datamodel_code_generator.__main__ import Exit, main

CaptureFixture = pytest.CaptureFixture
MonkeyPatch = pytest.MonkeyPatch

DATA_PATH: Path = Path(__file__).parent.parent / 'data'
PYTHON_DATA_PATH: Path = DATA_PATH / 'python'
EXPECTED_MAIN_PATH = DATA_PATH / 'expected' / 'main'

TIMESTAMP = '1985-10-26T01:21:00-07:00'


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: MonkeyPatch):
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr('datamodel_code_generator.__main__.namespace', namespace_)
    monkeypatch.setattr('datamodel_code_generator.arguments.namespace', namespace_)


def test_debug(mocker) -> None:
    with pytest.raises(expected_exception=SystemExit):
        main(['--debug', '--help'])

    mocker.patch('datamodel_code_generator.pysnooper', None)
    with pytest.raises(expected_exception=SystemExit):
        main(['--debug', '--help'])


@freeze_time('2019-07-26')
def test_snooper_to_methods_without_pysnooper(mocker) -> None:
    mocker.patch('datamodel_code_generator.pysnooper', None)
    mock = mocker.Mock()
    assert snooper_to_methods()(mock) == mock


@pytest.mark.parametrize(argnames='no_color', argvalues=[False, True])
def test_show_help(no_color: bool, capsys: CaptureFixture[str]):
    args = ['--no-color'] if no_color else []
    args += ['--help']

    with pytest.raises(expected_exception=SystemExit):
        return_code: Exit = main(args)
        assert return_code == Exit.OK

    output = capsys.readouterr().out
    assert ('\x1b' not in output) == no_color


def test_show_help_when_no_input(mocker):
    print_help_mock = mocker.patch(
        'datamodel_code_generator.__main__.arg_parser.print_help'
    )
    isatty_mock = mocker.patch('sys.stdin.isatty', return_value=True)
    return_code: Exit = main([])
    assert return_code == Exit.ERROR
    assert isatty_mock.called
    assert print_help_mock.called


@freeze_time('2019-07-26')
def test_space_and_special_characters_dict():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(PYTHON_DATA_PATH / 'space_and_special_characters_dict.py'),
                '--output',
                str(output_file),
                '--input-file-type',
                'dict',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'space_and_special_characters_dict.py').read_text()
        )
