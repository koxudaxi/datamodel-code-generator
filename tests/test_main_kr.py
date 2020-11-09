import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from _pytest.capture import CaptureFixture
from _pytest.tmpdir import TempdirFactory
from freezegun import freeze_time

from datamodel_code_generator.__main__ import Exit, main

DATA_PATH: Path = Path(__file__).parent / 'data'
OPEN_API_DATA_PATH: Path = DATA_PATH / 'openapi'
EXPECTED_MAIN_KR_PATH = DATA_PATH / 'expected' / 'main_kr'


TIMESTAMP = '1985-10-26T01:21:00-07:00'


@freeze_time('2019-07-26')
def test_main():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_KR_PATH / 'main' / 'output.py').read_text()
        )

    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_base_class():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        shutil.copy(DATA_PATH / 'pyproject.toml', Path(output_dir) / 'pyproject.toml')
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--base-class',
                'custom_module.Base',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_KR_PATH / 'main_base_class' / 'output.py').read_text()
        )

    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_target_python_version():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--target-python-version',
                '3.6',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_KR_PATH / 'target_python_version' / 'output.py'
            ).read_text()
        )

    with pytest.raises(SystemExit):
        main()


def test_main_modular(tmpdir_factory: TempdirFactory) -> None:
    """Test main function on modular file."""

    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(['--input', str(input_filename), '--output', str(output_path)])
    main_modular_dir = EXPECTED_MAIN_KR_PATH / 'main_modular'
    for path in main_modular_dir.rglob('*.py'):
        result = output_path.joinpath(path.relative_to(main_modular_dir)).read_text()
        assert result == path.read_text()


def test_main_modular_no_file() -> None:
    """Test main function on modular file with no output name."""

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'

    assert main(['--input', str(input_filename)]) == Exit.ERROR


def test_main_modular_filename(tmpdir_factory: TempdirFactory) -> None:
    """Test main function on modular file with filename."""

    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_filename = output_directory / 'model.py'

    assert (
        main(['--input', str(input_filename), '--output', str(output_filename)])
        == Exit.ERROR
    )


def test_main_no_file(capsys: CaptureFixture) -> None:
    """Test main function on non-modular file with no output name."""

    input_filename = OPEN_API_DATA_PATH / 'api.yaml'

    with freeze_time(TIMESTAMP):
        main(['--input', str(input_filename)])

    captured = capsys.readouterr()
    assert (
        captured.out
        == (EXPECTED_MAIN_KR_PATH / 'main_no_file' / 'output.py').read_text()
    )

    assert not captured.err


def test_main_custom_template_dir(capsys: CaptureFixture) -> None:
    """Test main function with custom template directory."""

    input_filename = OPEN_API_DATA_PATH / 'api.yaml'
    custom_template_dir = DATA_PATH / 'templates'
    extra_template_data = OPEN_API_DATA_PATH / 'extra_data.json'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--custom-template-dir',
                str(custom_template_dir),
                '--extra-template-data',
                str(extra_template_data),
            ]
        )

    captured = capsys.readouterr()
    assert (
        captured.out
        == (
            EXPECTED_MAIN_KR_PATH / 'main_custom_template_dir' / 'output.py'
        ).read_text()
    )
    assert not captured.err


@freeze_time('2019-07-26')
def test_pyproject():
    with TemporaryDirectory() as output_dir:
        output_dir = Path(output_dir)
        pyproject_toml = Path(DATA_PATH) / "project" / "pyproject.toml"
        shutil.copy(pyproject_toml, output_dir)
        output_file: Path = output_dir / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_KR_PATH / 'pyproject' / 'output.py').read_text()
        )

    with pytest.raises(SystemExit):
        main()
