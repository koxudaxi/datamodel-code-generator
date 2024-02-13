import platform
import shutil
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import call

import black
import isort
import pydantic
import pytest
from freezegun import freeze_time
from packaging import version

from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    chdir,
    generate,
    inferred_message,
    snooper_to_methods,
)
from datamodel_code_generator.__main__ import Exit, main

try:
    from pytest import TempdirFactory
except ImportError:
    from _pytest.tmpdir import TempdirFactory

CaptureFixture = pytest.CaptureFixture
FixtureRequest = pytest.FixtureRequest
MonkeyPatch = pytest.MonkeyPatch

DATA_PATH: Path = Path(__file__).parent / 'data'
OPEN_API_DATA_PATH: Path = DATA_PATH / 'openapi'
JSON_SCHEMA_DATA_PATH: Path = DATA_PATH / 'jsonschema'
JSON_DATA_PATH: Path = DATA_PATH / 'json'
YAML_DATA_PATH: Path = DATA_PATH / 'yaml'
PYTHON_DATA_PATH: Path = DATA_PATH / 'python'
CSV_DATA_PATH: Path = DATA_PATH / 'csv'
GRAPHQL_DATA_PATH: Path = DATA_PATH / 'graphql'
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


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_inheritance_forward_ref():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        shutil.copy(DATA_PATH / 'pyproject.toml', Path(output_dir) / 'pyproject.toml')
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'inheritance_forward_ref.json'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_inheritance_forward_ref' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_inheritance_forward_ref_keep_model_order():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        shutil.copy(DATA_PATH / 'pyproject.toml', Path(output_dir) / 'pyproject.toml')
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'inheritance_forward_ref.json'),
                '--output',
                str(output_file),
                '--keep-model-order',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_inheritance_forward_ref_keep_model_order'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
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
            == (EXPECTED_MAIN_PATH / 'main' / 'output.py').read_text()
        )


@pytest.mark.skip(reason='pytest-xdist does not support the test')
@freeze_time('2019-07-26')
def test_main_without_arguments():
    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_pydantic_basemodel():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'pydantic.BaseModel',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main' / 'output.py').read_text()
        )


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
            == (EXPECTED_MAIN_PATH / 'main_base_class' / 'output.py').read_text()
        )


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
            == (EXPECTED_MAIN_PATH / 'target_python_version' / 'output.py').read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_autodetect():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'person.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'auto',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_autodetect' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_autodetect_failed():
    with TemporaryDirectory() as input_dir, TemporaryDirectory() as output_dir:
        input_file: Path = Path(input_dir) / 'input.yaml'
        output_file: Path = Path(output_dir) / 'output.py'

        input_file.write_text(':')

        return_code: Exit = main(
            [
                '--input',
                str(input_file),
                '--output',
                str(output_file),
                '--input-file-type',
                'auto',
            ]
        )
        assert return_code == Exit.ERROR


@freeze_time('2019-07-26')
def test_main_jsonschema():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'person.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_jsonschema' / 'output.py').read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_jsonschema_nested_deep():
    with TemporaryDirectory() as output_dir:
        output_init_file: Path = Path(output_dir) / '__init__.py'
        output_nested_file: Path = Path(output_dir) / 'nested/deep.py'
        output_empty_parent_nested_file: Path = (
            Path(output_dir) / 'empty_parent/nested/deep.py'
        )

        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'nested_person.json'),
                '--output',
                str(output_dir),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_init_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_nested_deep' / '__init__.py'
            ).read_text()
        )

        assert (
            output_nested_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_nested_deep'
                / 'nested'
                / 'deep.py'
            ).read_text()
        )
        assert (
            output_empty_parent_nested_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_nested_deep'
                / 'empty_parent'
                / 'nested'
                / 'deep.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_nested_skip():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'nested_skip.json'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        nested_skip_dir = EXPECTED_MAIN_PATH / 'main_jsonschema_nested_skip'
        for path in nested_skip_dir.rglob('*.py'):
            result = output_path.joinpath(path.relative_to(nested_skip_dir)).read_text()
            assert result == path.read_text()


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_jsonschema_external_files():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'external_parent_root.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_external_files' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_jsonschema_multiple_files():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'multiple_files'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        main_modular_dir = EXPECTED_MAIN_PATH / 'multiple_files'
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_json():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_DATA_PATH / 'pet.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'json',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_json' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_space_and_special_characters_json():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_DATA_PATH / 'space_and_special_characters.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'json',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'space_and_special_characters' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_json_failed():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_DATA_PATH / 'broken.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'json',
            ]
        )
        assert return_code == Exit.ERROR


@freeze_time('2019-07-26')
def test_main_json_array_include_null():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_DATA_PATH / 'array_include_null.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'json',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_json_array_include_null' / 'output.py'
            ).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_null_and_array',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_null_and_array_v2',
        ),
    ],
)
@freeze_time('2019-07-26')
def test_main_null_and_array(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'null_and_array.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--output-model',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_yaml():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(YAML_DATA_PATH / 'pet.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'yaml',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_yaml' / 'output.py').read_text()
        )


@pytest.mark.benchmark
def test_main_modular(tmpdir_factory: TempdirFactory) -> None:
    """Test main function on modular file."""

    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(['--input', str(input_filename), '--output', str(output_path)])
    main_modular_dir = EXPECTED_MAIN_PATH / 'main_modular'
    for path in main_modular_dir.rglob('*.py'):
        result = output_path.joinpath(path.relative_to(main_modular_dir)).read_text()
        assert result == path.read_text()


def test_main_modular_reuse_model(tmpdir_factory: TempdirFactory) -> None:
    """Test main function on modular file."""

    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--output',
                str(output_path),
                '--reuse-model',
            ]
        )
    main_modular_dir = EXPECTED_MAIN_PATH / 'main_modular_reuse_model'
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
        captured.out == (EXPECTED_MAIN_PATH / 'main_no_file' / 'output.py').read_text()
    )
    assert captured.err == inferred_message.format('openapi') + '\n'


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_extra_template_data_config',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_extra_template_data_config_pydantic_v2',
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_extra_template_data_config(
    capsys: CaptureFixture, output_model, expected_output
) -> None:
    """Test main function with custom config data in extra template."""

    input_filename = OPEN_API_DATA_PATH / 'api.yaml'
    extra_template_data = OPEN_API_DATA_PATH / 'extra_data.json'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--extra-template-data',
                str(extra_template_data),
                '--output-model',
                output_model,
            ]
        )

    captured = capsys.readouterr()
    assert (
        captured.out == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
    )
    assert captured.err == inferred_message.format('openapi') + '\n'


def test_main_custom_template_dir_old_style(capsys: CaptureFixture) -> None:
    """Test main function with custom template directory."""

    input_filename = OPEN_API_DATA_PATH / 'api.yaml'
    custom_template_dir = DATA_PATH / 'templates_old_style'
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
        == (EXPECTED_MAIN_PATH / 'main_custom_template_dir' / 'output.py').read_text()
    )
    assert captured.err == inferred_message.format('openapi') + '\n'


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
        == (EXPECTED_MAIN_PATH / 'main_custom_template_dir' / 'output.py').read_text()
    )
    assert captured.err == inferred_message.format('openapi') + '\n'


@pytest.mark.skipif(
    black.__version__.split('.')[0] >= '24',
    reason="Installed black doesn't support the old style",
)
@freeze_time('2019-07-26')
def test_pyproject():
    if platform.system() == 'Windows':

        def get_path(path):
            return str(path).replace('\\', '\\\\')

    else:

        def get_path(path):
            return str(path)

    with TemporaryDirectory() as output_dir:
        output_dir = Path(output_dir)

        with chdir(output_dir):
            output_file: Path = output_dir / 'output.py'
            pyproject_toml_path = Path(DATA_PATH) / 'project' / 'pyproject.toml'
            pyproject_toml = (
                pyproject_toml_path.read_text()
                .replace('INPUT_PATH', get_path(OPEN_API_DATA_PATH / 'api.yaml'))
                .replace('OUTPUT_PATH', get_path(output_file))
                .replace(
                    'ALIASES_PATH', get_path(OPEN_API_DATA_PATH / 'empty_aliases.json')
                )
                .replace(
                    'EXTRA_TEMPLATE_DATA_PATH',
                    get_path(OPEN_API_DATA_PATH / 'empty_data.json'),
                )
                .replace('CUSTOM_TEMPLATE_DIR_PATH', get_path(output_dir))
            )
            (output_dir / 'pyproject.toml').write_text(pyproject_toml)

            return_code: Exit = main([])
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (EXPECTED_MAIN_PATH / 'pyproject' / 'output.py').read_text()
            )


@freeze_time('2019-07-26')
def test_pyproject_not_found():
    with TemporaryDirectory() as output_dir:
        output_dir = Path(output_dir)
        with chdir(output_dir):
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
                == (
                    EXPECTED_MAIN_PATH / 'pyproject_not_found' / 'output.py'
                ).read_text()
            )


@freeze_time('2019-07-26')
def test_stdin(monkeypatch):
    with TemporaryDirectory() as output_dir:
        output_dir = Path(output_dir)
        output_file: Path = output_dir / 'output.py'
        monkeypatch.setattr('sys.stdin', (OPEN_API_DATA_PATH / 'api.yaml').open())
        return_code: Exit = main(
            [
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'stdin' / 'output.py').read_text()
        )


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
def test_validation(mocker):
    mock_prance = mocker.patch('prance.BaseParser')

    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--validation',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'validation' / 'output.py').read_text()
        )
        mock_prance.assert_called_once()


@freeze_time('2019-07-26')
def test_validation_failed(mocker):
    mock_prance = mocker.patch('prance.BaseParser', side_effect=Exception('error'))
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        assert (
            main(
                [
                    '--input',
                    str(OPEN_API_DATA_PATH / 'invalid.yaml'),
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'openapi',
                    '--validation',
                ]
            )
            == Exit.ERROR
        )
        mock_prance.assert_called_once()


@pytest.mark.parametrize(
    'output_model,expected_output, args',
    [
        ('pydantic.BaseModel', 'main_with_field_constraints', []),
        (
            'pydantic.BaseModel',
            'main_with_field_constraints_use_unique_items_as_set',
            ['--use-unique-items-as-set'],
        ),
        ('pydantic_v2.BaseModel', 'main_with_field_constraints_pydantic_v2', []),
        (
            'pydantic_v2.BaseModel',
            'main_with_field_constraints_pydantic_v2_use_generic_container_types',
            ['--use-generic-container-types'],
        ),
        (
            'pydantic_v2.BaseModel',
            'main_with_field_constraints_pydantic_v2_use_generic_container_types_set',
            ['--use-generic-container-types', '--use-unique-items-as-set'],
        ),
        (
            'pydantic_v2.BaseModel',
            'main_with_field_constraints_pydantic_v2_use_standard_collections',
            [
                '--use-standard-collections',
            ],
        ),
        (
            'pydantic_v2.BaseModel',
            'main_with_field_constraints_pydantic_v2_use_standard_collections_set',
            ['--use-standard-collections', '--use-unique-items-as-set'],
        ),
    ],
)
@freeze_time('2019-07-26')
def test_main_with_field_constraints(output_model, expected_output, args):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
                '--field-constraints',
                '--output-model-type',
                output_model,
                *args,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_without_field_constraints',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_without_field_constraints_pydantic_v2',
        ),
    ],
)
@freeze_time('2019-07-26')
def test_main_without_field_constraints(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_with_aliases',
        ),
        (
            'msgspec.Struct',
            'main_with_aliases_msgspec',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_with_aliases(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--aliases',
                str(OPEN_API_DATA_PATH / 'aliases.json'),
                '--target-python',
                '3.9',
                '--output-model',
                output_model,
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


def test_main_with_bad_aliases():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--aliases',
                str(OPEN_API_DATA_PATH / 'not.json'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.ERROR


def test_main_with_more_bad_aliases():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--aliases',
                str(OPEN_API_DATA_PATH / 'list.json'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.ERROR


def test_main_with_bad_extra_data():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--extra-template-data',
                str(OPEN_API_DATA_PATH / 'not.json'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.ERROR


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_with_snake_case_field():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--snake-case-field',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_with_snake_case_field' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_with_strip_default_none():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--strip-default-none',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_with_strip_default_none' / 'output.py'
            ).read_text()
        )


def test_disable_timestamp():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--disable-timestamp',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'disable_timestamp' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_enable_version_header():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--enable-version-header',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'enable_version_header' / 'output.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'allow_population_by_field_name',
        ),
        (
            'pydantic_v2.BaseModel',
            'allow_population_by_field_name_pydantic_v2',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_allow_population_by_field_name(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--allow-population-by-field-name',
                '--output-model-type',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'allow_extra_fields',
        ),
        (
            'pydantic_v2.BaseModel',
            'allow_extra_fields_pydantic_v2',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_allow_extra_fields(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--allow-extra-fields',
                '--output-model-type',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'enable_faux_immutability',
        ),
        (
            'pydantic_v2.BaseModel',
            'enable_faux_immutability_pydantic_v2',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_enable_faux_immutability(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--enable-faux-immutability',
                '--output-model-type',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_use_default():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--use-default',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'use_default' / 'output.py').read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_force_optional():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--force-optional',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'force_optional' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_use_default_pydantic_v2_with_json_schema_const():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'use_default_with_const.json'),
                '--output',
                str(output_file),
                '--output-model-type',
                'pydantic_v2.BaseModel',
                '--use-default',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'use_default_with_const' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_with_exclusive():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'exclusive.yaml'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_with_exclusive' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_subclass_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'subclass_enum.json'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_subclass_enum' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output,option',
    [
        (
            'pydantic.BaseModel',
            'main_complicated_enum_default_member',
            '--set-default-enum-member',
        ),
        (
            'dataclasses.dataclass',
            'main_complicated_enum_default_member_dataclass',
            '--set-default-enum-member',
        ),
        (
            'dataclasses.dataclass',
            'main_complicated_enum_default_member_dataclass',
            None,
        ),
    ],
)
def test_main_complicated_enum_default_member(output_model, expected_output, option):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                a
                for a in [
                    '--input',
                    str(JSON_SCHEMA_DATA_PATH / 'complicated_enum.json'),
                    '--output',
                    str(output_file),
                    option,
                    '--output-model',
                    output_model,
                ]
                if a
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_json_reuse_enum_default_member():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'duplicate_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--reuse-model',
                '--set-default-enum-member',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_json_reuse_enum_default_member' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_invalid_model_name_failed(capsys):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'invalid_model_name.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--class-name',
                'with',
            ]
        )
        captured = capsys.readouterr()
        assert return_code == Exit.ERROR
        assert (
            captured.err
            == "title='with' is invalid class name. You have to set `--class-name` option\n"
        )


@freeze_time('2019-07-26')
def test_main_invalid_model_name_converted(capsys):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'invalid_model_name.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        captured = capsys.readouterr()
        assert return_code == Exit.ERROR
        assert (
            captured.err
            == "title='1Xyz' is invalid class name. You have to set `--class-name` option\n"
        )


@freeze_time('2019-07-26')
def test_main_invalid_model_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'invalid_model_name.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--class-name',
                'ValidModelName',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_invalid_model_name' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_root_id_jsonschema_with_local_file(mocker):
    root_id_response = mocker.Mock()
    root_id_response.text = 'dummy'
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / 'person.json').read_text()
    httpx_get_mock = mocker.patch('httpx.get', side_effect=[person_response])
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'root_id.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_root_id' / 'output.py').read_text()
        )
        httpx_get_mock.assert_not_called()


@freeze_time('2019-07-26')
def test_main_root_id_jsonschema_with_remote_file(mocker):
    root_id_response = mocker.Mock()
    root_id_response.text = 'dummy'
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / 'person.json').read_text()
    httpx_get_mock = mocker.patch('httpx.get', side_effect=[person_response])
    with TemporaryDirectory() as output_dir:
        input_file = Path(output_dir, 'root_id.json')
        shutil.copy(JSON_SCHEMA_DATA_PATH / 'root_id.json', input_file)
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(input_file),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_root_id' / 'output.py').read_text()
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/person.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
            ]
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_root_id_jsonschema_self_refs_with_local_file(mocker):
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / 'person.json').read_text()
    httpx_get_mock = mocker.patch('httpx.get', side_effect=[person_response])
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'root_id_self_ref.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / 'main_root_id' / 'output.py'
        ).read_text().replace(
            'filename:  root_id.json', 'filename:  root_id_self_ref.json'
        )
        httpx_get_mock.assert_not_called()


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_root_id_jsonschema_self_refs_with_remote_file(mocker):
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / 'person.json').read_text()
    httpx_get_mock = mocker.patch('httpx.get', side_effect=[person_response])
    with TemporaryDirectory() as output_dir:
        input_file = Path(output_dir, 'root_id_self_ref.json')
        shutil.copy(JSON_SCHEMA_DATA_PATH / 'root_id_self_ref.json', input_file)
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(input_file),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / 'main_root_id' / 'output.py'
        ).read_text().replace(
            'filename:  root_id.json', 'filename:  root_id_self_ref.json'
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/person.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
            ]
        )


@freeze_time('2019-07-26')
def test_main_root_id_jsonschema_with_absolute_remote_file(mocker):
    root_id_response = mocker.Mock()
    root_id_response.text = 'dummy'
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / 'person.json').read_text()
    httpx_get_mock = mocker.patch('httpx.get', side_effect=[person_response])
    with TemporaryDirectory() as output_dir:
        input_file = Path(output_dir, 'root_id_absolute_url.json')
        shutil.copy(JSON_SCHEMA_DATA_PATH / 'root_id_absolute_url.json', input_file)
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(input_file),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_root_id_absolute_url' / 'output.py'
            ).read_text()
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/person.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
            ]
        )


@freeze_time('2019-07-26')
def test_main_root_id_jsonschema_with_absolute_local_file(mocker):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'root_id_absolute_url.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_root_id_absolute_url' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_jsonschema_id():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'id.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_jsonschema_id' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_id_as_stdin(monkeypatch):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        monkeypatch.setattr('sys.stdin', (JSON_SCHEMA_DATA_PATH / 'id.json').open())
        return_code: Exit = main(
            [
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_id_stdin' / 'output.py'
            ).read_text()
        )


def test_main_jsonschema_ids(tmpdir_factory: TempdirFactory) -> None:
    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = JSON_SCHEMA_DATA_PATH / 'ids' / 'Organization.schema.json'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
    main_jsonschema_ids_dir = EXPECTED_MAIN_PATH / 'main_jsonschema_ids'
    for path in main_jsonschema_ids_dir.rglob('*.py'):
        result = output_path.joinpath(
            path.relative_to(main_jsonschema_ids_dir)
        ).read_text()
        assert result == path.read_text()


def test_main_use_standard_collections(tmpdir_factory: TempdirFactory) -> None:
    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--output',
                str(output_path),
                '--use-standard-collections',
            ]
        )
    main_use_standard_collections_dir = (
        EXPECTED_MAIN_PATH / 'main_use_standard_collections'
    )
    for path in main_use_standard_collections_dir.rglob('*.py'):
        result = output_path.joinpath(
            path.relative_to(main_use_standard_collections_dir)
        ).read_text()
        assert result == path.read_text()


@pytest.mark.skipif(
    black.__version__.split('.')[0] >= '24',
    reason="Installed black doesn't support the old style",
)
def test_main_use_generic_container_types(tmpdir_factory: TempdirFactory) -> None:
    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--output',
                str(output_path),
                '--use-generic-container-types',
            ]
        )
    main_use_generic_container_types_dir = (
        EXPECTED_MAIN_PATH / 'main_use_generic_container_types'
    )
    for path in main_use_generic_container_types_dir.rglob('*.py'):
        result = output_path.joinpath(
            path.relative_to(main_use_generic_container_types_dir)
        ).read_text()
        assert result == path.read_text()


@pytest.mark.skipif(
    black.__version__.split('.')[0] >= '24',
    reason="Installed black doesn't support the old style",
)
@pytest.mark.benchmark
def test_main_use_generic_container_types_standard_collections(
    tmpdir_factory: TempdirFactory,
) -> None:
    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--output',
                str(output_path),
                '--use-generic-container-types',
                '--use-standard-collections',
            ]
        )
    main_use_generic_container_types_standard_collections_dir = (
        EXPECTED_MAIN_PATH / 'main_use_generic_container_types_standard_collections'
    )
    for path in main_use_generic_container_types_standard_collections_dir.rglob('*.py'):
        result = output_path.joinpath(
            path.relative_to(main_use_generic_container_types_standard_collections_dir)
        ).read_text()
        assert result == path.read_text()


def test_main_use_generic_container_types_py36(capsys) -> None:
    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'

    return_code: Exit = main(
        [
            '--input',
            str(input_filename),
            '--use-generic-container-types',
            '--target-python-version',
            '3.6',
        ]
    )
    captured = capsys.readouterr()
    assert return_code == Exit.ERROR
    assert (
        captured.err == '`--use-generic-container-types` can not be used with '
        '`--target-python_version` 3.6.\n '
        'The version will be not supported in a future version\n'
    )


def test_main_original_field_name_delimiter_without_snake_case_field(capsys) -> None:
    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'

    return_code: Exit = main(
        [
            '--input',
            str(input_filename),
            '--original-field-name-delimiter',
            '-',
        ]
    )
    captured = capsys.readouterr()
    assert return_code == Exit.ERROR
    assert (
        captured.err
        == '`--original-field-name-delimiter` can not be used without `--snake-case-field`.\n'
    )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_external_definitions():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'external_definitions_root.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_external_definitions' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_external_files_in_directory(tmpdir_factory: TempdirFactory) -> None:
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(
                    JSON_SCHEMA_DATA_PATH
                    / 'external_files_in_directory'
                    / 'person.json'
                ),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_external_files_in_directory' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_nested_directory(tmpdir_factory: TempdirFactory) -> None:
    output_directory = Path(tmpdir_factory.mktemp('output'))

    output_path = output_directory / 'model'
    return_code: Exit = main(
        [
            '--input',
            str(JSON_SCHEMA_DATA_PATH / 'external_files_in_directory'),
            '--output',
            str(output_path),
            '--input-file-type',
            'jsonschema',
        ]
    )
    assert return_code == Exit.OK
    main_nested_directory = EXPECTED_MAIN_PATH / 'main_nested_directory'

    for path in main_nested_directory.rglob('*.py'):
        result = output_path.joinpath(
            path.relative_to(main_nested_directory)
        ).read_text()
        assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_circular_reference():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'circular_reference.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_circular_reference' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_invalid_enum_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'invalid_enum_name.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_invalid_enum_name' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_invalid_enum_name_snake_case_field():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'invalid_enum_name.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--snake-case-field',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_invalid_enum_name_snake_case_field'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_json_reuse_model():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_DATA_PATH / 'duplicate_models.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'json',
                '--reuse-model',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_json_reuse_model' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_json_reuse_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'duplicate_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--reuse-model',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_json_reuse_enum' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_json_capitalise_enum_members():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'many_case_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--capitalise-enum-members',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_json_capitalise_enum_members' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_json_capitalise_enum_members_without_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'person.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--capitalise-enum-members',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_autodetect' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_openapi_datetime',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_openapi_datetime_pydantic_v2',
        ),
    ],
)
def test_main_openapi_datetime(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'datetime.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--output-model',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_similar_nested_array():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'similar_nested_array.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_similar_nested_array' / 'output.py'
            ).read_text()
        )


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
            == (
                EXPECTED_MAIN_PATH / 'space_and_special_characters_dict' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_csv_file():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(CSV_DATA_PATH / 'simple.csv'),
                '--output',
                str(output_file),
                '--input-file-type',
                'csv',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'csv_file_simple' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_csv_stdin(monkeypatch):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        monkeypatch.setattr('sys.stdin', (CSV_DATA_PATH / 'simple.csv').open())
        return_code: Exit = main(
            [
                '--output',
                str(output_file),
                '--input-file-type',
                'csv',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'csv_stdin_simple' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_models_not_found(capsys):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'no_components.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        captured = capsys.readouterr()
        assert return_code == Exit.ERROR
        assert captured.err == 'Models not found in the input data\n'


@freeze_time('2019-07-26')
def test_main_json_pointer():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'json_pointer.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_json_pointer' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_nested_json_pointer():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'nested_json_pointer.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_nested_json_pointer' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_multiple_files_json_pointer():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'multiple_files_json_pointer'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        main_modular_dir = EXPECTED_MAIN_PATH / 'multiple_files_json_pointer'
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text()


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse('1.9.0'),
    reason='Require Pydantic version 1.9.0 or later ',
)
@freeze_time('2019-07-26')
def test_main_openapi_enum_models_as_literal_one():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'enum_models.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--enum-field-as-literal',
                'one',
                '--target-python-version',
                '3.8',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_enum_models_one' / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse('1.9.0'),
    reason='Require Pydantic version 1.9.0 or later ',
)
@freeze_time('2019-07-26')
def test_main_openapi_use_one_literal_as_default():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'enum_models.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--enum-field-as-literal',
                'one',
                '--target-python-version',
                '3.8',
                '--use-one-literal-as-default',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_enum_models_one_literal_as_default'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse('1.9.0'),
    reason='Require Pydantic version 1.9.0 or later ',
)
@pytest.mark.skipif(
    black.__version__.split('.')[0] >= '24',
    reason="Installed black doesn't support the old style",
)
@freeze_time('2019-07-26')
def test_main_openapi_enum_models_as_literal_all():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'enum_models.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--enum-field-as-literal',
                'all',
                '--target-python-version',
                '3.8',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_enum_models_all' / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    version.parse(pydantic.VERSION) < version.parse('1.9.0'),
    reason='Require Pydantic version 1.9.0 or later ',
)
@pytest.mark.skipif(
    black.__version__.split('.')[0] >= '24',
    reason="Installed black doesn't support the old style",
)
@freeze_time('2019-07-26')
def test_main_openapi_enum_models_as_literal_py37(capsys):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'enum_models.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--enum-field-as-literal',
                'all',
            ]
        )

        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_enum_models_as_literal_py37'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_root_model_with_additional_properties():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(
                    JSON_SCHEMA_DATA_PATH / 'root_model_with_additional_properties.json'
                ),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_root_model_with_additional_properties'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_root_model_with_additional_properties_use_generic_container_types():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(
                    JSON_SCHEMA_DATA_PATH / 'root_model_with_additional_properties.json'
                ),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--use-generic-container-types',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_root_model_with_additional_properties_use_generic_container_types'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_root_model_with_additional_properties_use_standard_collections():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(
                    JSON_SCHEMA_DATA_PATH / 'root_model_with_additional_properties.json'
                ),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--use-standard-collections',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_root_model_with_additional_properties_use_standard_collections'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_root_model_with_additional_properties_literal():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(
                    JSON_SCHEMA_DATA_PATH / 'root_model_with_additional_properties.json'
                ),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--enum-field-as-literal',
                'all',
                '--target-python-version',
                '3.8',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_root_model_with_additional_properties_literal'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_multiple_files_ref():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'multiple_files_self_ref'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        main_modular_dir = EXPECTED_MAIN_PATH / 'multiple_files_self_ref'
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_jsonschema_multiple_files_ref_test_json():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        with chdir(JSON_SCHEMA_DATA_PATH / 'multiple_files_self_ref'):
            return_code: Exit = main(
                [
                    '--input',
                    'test.json',
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'jsonschema',
                ]
            )
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (
                    EXPECTED_MAIN_PATH / 'multiple_files_self_ref_single' / 'output.py'
                ).read_text()
            )


@freeze_time('2019-07-26')
def test_simple_json_snake_case_field():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        with chdir(JSON_DATA_PATH / 'simple.json'):
            return_code: Exit = main(
                [
                    '--input',
                    'simple.json',
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'json',
                    '--snake-case-field',
                ]
            )
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (
                    EXPECTED_MAIN_PATH / 'simple_json_snake_case_field' / 'output.py'
                ).read_text()
            )


@freeze_time('2019-07-26')
def test_main_space_field_enum_snake_case_field():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        with chdir(JSON_SCHEMA_DATA_PATH / 'space_field_enum.json'):
            return_code: Exit = main(
                [
                    '--input',
                    'space_field_enum.json',
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'jsonschema',
                    '--snake-case-field',
                    '--original-field-name-delimiter',
                    ' ',
                ]
            )
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (
                    EXPECTED_MAIN_PATH
                    / 'main_space_field_enum_snake_case_field'
                    / 'output.py'
                ).read_text()
            )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_all_of_ref():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        with chdir(JSON_SCHEMA_DATA_PATH / 'all_of_ref'):
            return_code: Exit = main(
                [
                    '--input',
                    'test.json',
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'jsonschema',
                    '--class-name',
                    'Test',
                ]
            )
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (EXPECTED_MAIN_PATH / 'all_of_ref' / 'output.py').read_text()
            )


@freeze_time('2019-07-26')
def test_main_all_of_with_object():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        with chdir(JSON_SCHEMA_DATA_PATH):
            return_code: Exit = main(
                [
                    '--input',
                    'all_of_with_object.json',
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'jsonschema',
                ]
            )
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (EXPECTED_MAIN_PATH / 'all_of_with_object' / 'output.py').read_text()
            )


@pytest.mark.skipif(
    black.__version__.split('.')[0] >= '24',
    reason="Installed black doesn't support the old style",
)
@freeze_time('2019-07-26')
def test_main_combined_array():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        with chdir(JSON_SCHEMA_DATA_PATH):
            return_code: Exit = main(
                [
                    '--input',
                    'combined_array.json',
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'jsonschema',
                ]
            )
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (EXPECTED_MAIN_PATH / 'combined_array' / 'output.py').read_text()
            )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_openapi_all_of_required():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'allof_required.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_allof_required' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_openapi_nullable():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'nullable.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_openapi_nullable' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_nullable_strict_nullable():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'nullable.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--strict-nullable',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_nullable_strict_nullable'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_pattern',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_pattern_pydantic_v2',
        ),
        (
            'msgspec.Struct',
            'main_pattern_msgspec',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_pattern(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'pattern.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--target-python',
                '3.9',
                '--output-model-type',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / expected_output / 'output.py'
        ).read_text().replace('pattern.json', 'pattern.yaml')


@freeze_time('2019-07-26')
def test_main_jsonschema_pattern():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'pattern.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_pattern' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_generate():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        input_ = (JSON_SCHEMA_DATA_PATH / 'person.json').relative_to(Path.cwd())
        assert not input_.is_absolute()
        generate(
            input_=input_,
            input_file_type=InputFileType.JsonSchema,
            output=output_file,
        )

        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_jsonschema' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_generate_non_pydantic_output():
    """
    See https://github.com/koxudaxi/datamodel-code-generator/issues/1452.
    """
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        input_ = (JSON_SCHEMA_DATA_PATH / 'simple_string.json').relative_to(Path.cwd())
        assert not input_.is_absolute()
        generate(
            input_=input_,
            input_file_type=InputFileType.JsonSchema,
            output=output_file,
            output_model_type=DataModelType.DataclassesDataclass,
        )

        file = EXPECTED_MAIN_PATH / 'main_generate_non_pydantic_output' / 'output.py'
        assert output_file.read_text() == file.read_text()


@freeze_time('2019-07-26')
def test_main_generate_from_directory():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        input_ = (JSON_SCHEMA_DATA_PATH / 'external_files_in_directory').relative_to(
            Path.cwd()
        )
        assert not input_.is_absolute()
        assert input_.is_dir()
        generate(
            input_=input_,
            input_file_type=InputFileType.JsonSchema,
            output=output_path,
        )

        main_nested_directory = EXPECTED_MAIN_PATH / 'main_nested_directory'

        for path in main_nested_directory.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_nested_directory)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_generate_custom_class_name_generator():
    def custom_class_name_generator(title):
        return f'Custom{title}'

    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        input_ = (JSON_SCHEMA_DATA_PATH / 'person.json').relative_to(Path.cwd())
        assert not input_.is_absolute()
        generate(
            input_=input_,
            input_file_type=InputFileType.JsonSchema,
            output=output_file,
            custom_class_name_generator=custom_class_name_generator,
        )

        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / 'main_jsonschema' / 'output.py'
        ).read_text().replace('Person', 'CustomPerson')


@freeze_time('2019-07-26')
def test_main_generate_custom_class_name_generator_modular(
    tmpdir_factory: TempdirFactory,
):
    output_directory = Path(tmpdir_factory.mktemp('output'))

    output_path = output_directory / 'model'
    main_modular_custom_class_name_dir = (
        EXPECTED_MAIN_PATH / 'main_modular_custom_class_name'
    )

    def custom_class_name_generator(name):
        return f'Custom{name[0].upper() + name[1:]}'

    with freeze_time(TIMESTAMP):
        input_ = (OPEN_API_DATA_PATH / 'modular.yaml').relative_to(Path.cwd())
        assert not input_.is_absolute()
        generate(
            input_=input_,
            input_file_type=InputFileType.OpenAPI,
            output=output_path,
            custom_class_name_generator=custom_class_name_generator,
        )

        for path in main_modular_custom_class_name_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_custom_class_name_dir)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_generate_custom_class_name_generator_additional_properties(
    tmpdir_factory: TempdirFactory,
):
    output_directory = Path(tmpdir_factory.mktemp('output'))

    output_file = output_directory / 'models.py'

    def custom_class_name_generator(name):
        return f'Custom{name[0].upper() + name[1:]}'

    input_ = (
        JSON_SCHEMA_DATA_PATH / 'root_model_with_additional_properties.json'
    ).relative_to(Path.cwd())
    assert not input_.is_absolute()
    generate(
        input_=input_,
        input_file_type=InputFileType.JsonSchema,
        output=output_file,
        custom_class_name_generator=custom_class_name_generator,
    )

    assert (
        output_file.read_text()
        == (
            EXPECTED_MAIN_PATH
            / 'main_root_model_with_additional_properties_custom_class_name'
            / 'output.py'
        ).read_text()
    )


@freeze_time('2019-07-26')
def test_main_http_jsonschema(mocker):
    external_directory = JSON_SCHEMA_DATA_PATH / 'external_files_in_directory'

    def get_mock_response(path: str) -> mocker.Mock:
        mock = mocker.Mock()
        mock.text = (external_directory / path).read_text()
        return mock

    httpx_get_mock = mocker.patch(
        'httpx.get',
        side_effect=[
            get_mock_response('person.json'),
            get_mock_response('definitions/pet.json'),
            get_mock_response('definitions/fur.json'),
            get_mock_response('definitions/friends.json'),
            get_mock_response('definitions/food.json'),
            get_mock_response('definitions/machine/robot.json'),
            get_mock_response('definitions/drink/coffee.json'),
            get_mock_response('definitions/drink/tea.json'),
        ],
    )
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--url',
                'https://example.com/external_files_in_directory/person.json',
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / 'main_external_files_in_directory' / 'output.py'
        ).read_text().replace(
            '#   filename:  person.json',
            '#   filename:  https://example.com/external_files_in_directory/person.json',
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/external_files_in_directory/person.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/pet.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/fur.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/friends.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/food.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/machine/robot.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/drink/coffee.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/drink/tea.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
            ]
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'headers_arguments,headers_requests,http_ignore_tls',
    [
        (
            ('Authorization: Basic dXNlcjpwYXNz',),
            [('Authorization', 'Basic dXNlcjpwYXNz')],
            False,
        ),
        (
            ('Authorization: Basic dXNlcjpwYXNz', 'X-API-key: abcefg'),
            [('Authorization', 'Basic dXNlcjpwYXNz'), ('X-API-key', 'abcefg')],
            True,
        ),
    ],
)
def test_main_http_jsonschema_with_http_headers_and_ignore_tls(
    mocker, headers_arguments, headers_requests, http_ignore_tls
):
    external_directory = JSON_SCHEMA_DATA_PATH / 'external_files_in_directory'

    def get_mock_response(path: str) -> mocker.Mock:
        mock = mocker.Mock()
        mock.text = (external_directory / path).read_text()
        return mock

    httpx_get_mock = mocker.patch(
        'httpx.get',
        side_effect=[
            get_mock_response('person.json'),
            get_mock_response('definitions/pet.json'),
            get_mock_response('definitions/fur.json'),
            get_mock_response('definitions/friends.json'),
            get_mock_response('definitions/food.json'),
            get_mock_response('definitions/machine/robot.json'),
            get_mock_response('definitions/drink/coffee.json'),
            get_mock_response('definitions/drink/tea.json'),
        ],
    )
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        args = [
            '--url',
            'https://example.com/external_files_in_directory/person.json',
            '--http-headers',
            *headers_arguments,
            '--output',
            str(output_file),
            '--input-file-type',
            'jsonschema',
        ]
        if http_ignore_tls:
            args.append('--http-ignore-tls')

        return_code: Exit = main(args)
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / 'main_external_files_in_directory' / 'output.py'
        ).read_text().replace(
            '#   filename:  person.json',
            '#   filename:  https://example.com/external_files_in_directory/person.json',
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/external_files_in_directory/person.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/pet.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/fur.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/friends.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/food.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/machine/robot.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/drink/coffee.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
                call(
                    'https://example.com/external_files_in_directory/definitions/drink/tea.json',
                    headers=headers_requests,
                    verify=True if not http_ignore_tls else False,
                    follow_redirects=True,
                ),
            ]
        )


@freeze_time('2019-07-26')
def test_main_http_openapi(mocker):
    def get_mock_response(path: str) -> mocker.Mock:
        mock = mocker.Mock()
        mock.text = (OPEN_API_DATA_PATH / path).read_text()
        return mock

    httpx_get_mock = mocker.patch(
        'httpx.get',
        side_effect=[
            get_mock_response('refs.yaml'),
            get_mock_response('definitions.yaml'),
        ],
    )
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--url',
                'https://example.com/refs.yaml',
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_openapi_http_refs' / 'output.py').read_text()
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/refs.yaml',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
                call(
                    'https://teamdigitale.github.io/openapi/0.0.6/definitions.yaml',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
            ]
        )


@freeze_time('2019-07-26')
def test_main_http_json(mocker):
    def get_mock_response(path: str) -> mocker.Mock:
        mock = mocker.Mock()
        mock.text = (JSON_DATA_PATH / path).read_text()
        return mock

    httpx_get_mock = mocker.patch(
        'httpx.get',
        side_effect=[
            get_mock_response('pet.json'),
        ],
    )
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--url',
                'https://example.com/pet.json',
                '--output',
                str(output_file),
                '--input-file-type',
                'json',
            ]
        )
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / 'main_json' / 'output.py'
        ).read_text().replace(
            '#   filename:  pet.json',
            '#   filename:  https://example.com/pet.json',
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/pet.json',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
            ]
        )


@freeze_time('2019-07-26')
def test_main_self_reference():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'self_reference.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_self_reference' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_disable_appending_item_suffix():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
                '--field-constraints',
                '--disable-appending-item-suffix',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_disable_appending_item_suffix' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_strict_types():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'strict_types.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_strict_types' / 'output.py').read_text()
        )


@pytest.mark.skipif(
    black.__version__.split('.')[0] >= '24',
    reason="Installed black doesn't support the old style",
)
@freeze_time('2019-07-26')
def test_main_strict_types_all():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'strict_types.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--strict-types',
                'str',
                'bytes',
                'int',
                'float',
                'bool',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_strict_types_all' / 'output.py').read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_strict_types_all_with_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'strict_types.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--strict-types',
                'str',
                'bytes',
                'int',
                'float',
                'bool',
                '--field-constraints',
            ]
        )

        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_strict_types_all_field_constraints'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_special_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'special_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_special_enum' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_special_enum_special_field_name_prefix():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'special_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--special-field-name-prefix',
                'special',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_special_enum_special_field_name_prefix'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_special_enum_special_field_name_prefix_keep_private():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'special_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--special-field-name-prefix',
                '',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_special_enum_special_field_name_prefix_keep_private'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_special_model_remove_special_field_name_prefix():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'special_prefix_model.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--remove-special-field-name-prefix',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_special_model_remove_special_field_name_prefix'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_subclass_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'subclass_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--use-subclass-enum',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_subclass_enum' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_special_enum_empty_enum_field_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'special_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--empty-enum-field-name',
                'empty',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_special_enum_empty_enum_field_name'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_jsonschema_special_field_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'special_field_name.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_special_field_name' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_complex_one_of():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'complex_one_of.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_complex_one_of' / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_jsonschema_complex_any_of():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'complex_any_of.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_complex_any_of' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_combine_one_of_object():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'combine_one_of_object.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_combine_one_of_object'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_combine_any_of_object():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'combine_any_of_object.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_combine_any_of_object'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_jsonschema_field_include_all_keys():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'person.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--field-include-all-keys',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_jsonschema' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_jsonschema_field_extras_field_include_all_keys',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_jsonschema_field_extras_field_include_all_keys_v2',
        ),
    ],
)
def test_main_jsonschema_field_extras_field_include_all_keys(
    output_model, expected_output
):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'extras.json'),
                '--output',
                str(output_file),
                '--output-model',
                output_model,
                '--input-file-type',
                'jsonschema',
                '--field-include-all-keys',
                '--field-extra-keys-without-x-prefix',
                'x-repr',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_jsonschema_field_extras_field_extra_keys',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_jsonschema_field_extras_field_extra_keys_v2',
        ),
    ],
)
def test_main_jsonschema_field_extras_field_extra_keys(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'extras.json'),
                '--output',
                str(output_file),
                '--output-model',
                output_model,
                '--input-file-type',
                'jsonschema',
                '--field-extra-keys',
                'key2',
                'invalid-key-1',
                '--field-extra-keys-without-x-prefix',
                'x-repr',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_jsonschema_field_extras',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_jsonschema_field_extras_v2',
        ),
    ],
)
def test_main_jsonschema_field_extras(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'extras.json'),
                '--output',
                str(output_file),
                '--output-model',
                output_model,
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.skipif(
    not isort.__version__.startswith('4.'),
    reason="isort 5.x don't sort pydantic modules",
)
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_jsonschema_custom_type_path',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_jsonschema_custom_type_path_pydantic_v2',
        ),
    ],
)
@freeze_time('2019-07-26')
def test_main_jsonschema_custom_type_path(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'custom_type_path.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--output-model',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_custom_base_path():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'custom_base_path.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_custom_base_path' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_body_and_parameters():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'body_and_parameters.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--openapi-scopes',
                'paths',
                'schemas',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_body_and_parameters' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_body_and_parameters_remote_ref(mocker):
    input_path = OPEN_API_DATA_PATH / 'body_and_parameters_remote_ref.yaml'
    person_response = mocker.Mock()
    person_response.text = input_path.read_text()
    httpx_get_mock = mocker.patch('httpx.get', side_effect=[person_response])

    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(input_path),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--openapi-scopes',
                'paths',
                'schemas',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_body_and_parameters_remote_ref'
                / 'output.py'
            ).read_text()
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://schema.example',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                ),
            ]
        )


@freeze_time('2019-07-26')
def test_main_openapi_body_and_parameters_only_paths():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'body_and_parameters.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--openapi-scopes',
                'paths',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_body_and_parameters_only_paths'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_body_and_parameters_only_schemas():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'body_and_parameters.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--openapi-scopes',
                'schemas',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_body_and_parameters_only_schemas'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_content_in_parameters():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'content_in_parameters.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_content_in_parameters' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_oas_response_reference():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'oas_response_reference.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--openapi-scopes',
                'paths',
                'schemas',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_oas_response_reference' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_long_description():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'long_description.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_long_description' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_long_description_wrap_string_literal():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'long_description.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--wrap-string-literal',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_long_description_wrap_string_literal'
                / 'output.py'
            ).read_text()
        )


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(['--version'])
    assert e.value.code == Exit.OK
    captured = capsys.readouterr()
    assert captured.out == '0.0.0\n'
    assert captured.err == ''


@freeze_time('2019-07-26')
def test_main_openapi_json_pointer():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'json_pointer.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_json_pointer' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_jsonschema_pattern_properties():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'pattern_properties.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_pattern_properties' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_jsonschema_pattern_properties_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'pattern_properties.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--field-constraints',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_pattern_properties_field_constraints'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_jsonschema_titles():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'titles.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_jsonschema_titles' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_jsonschema_titles_use_title_as_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'titles.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--use-title-as-name',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_titles_use_title_as_name'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_jsonschema_without_titles_use_title_as_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'without_titles.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--use-title-as-name',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_without_titles_use_title_as_name'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        ('pydantic.BaseModel', 'main_use_annotated_with_field_constraints'),
        (
            'pydantic_v2.BaseModel',
            'main_use_annotated_with_field_constraints_pydantic_v2',
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_use_annotated_with_field_constraints(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
                '--field-constraints',
                '--use-annotated',
                '--target-python-version',
                '3.9',
                '--output-model',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_use_annotated_with_field_constraints_py38():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
                '--use-annotated',
                '--target-python-version',
                '3.8',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_use_annotated_with_field_constraints_py38'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_nested_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'nested_enum.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_nested_enum' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_has_default_value():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'has_default_value.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'has_default_value' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_openapi_special_yaml_keywords(mocker):
    mock_prance = mocker.patch('prance.BaseParser')

    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'special_yaml_keywords.yaml'),
                '--output',
                str(output_file),
                '--validation',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_special_yaml_keywords' / 'output.py'
            ).read_text()
        )
    mock_prance.assert_called_once()


@freeze_time('2019-07-26')
def test_main_jsonschema_boolean_property():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'boolean_property.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_boolean_property' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_modular_default_enum_member(
    tmpdir_factory: TempdirFactory,
) -> None:
    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = JSON_SCHEMA_DATA_PATH / 'modular_default_enum_member'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--output',
                str(output_path),
                '--set-default-enum-member',
            ]
        )
    main_modular_dir = (
        EXPECTED_MAIN_PATH / 'main_jsonschema_modular_default_enum_member'
    )
    for path in main_modular_dir.rglob('*.py'):
        result = output_path.joinpath(path.relative_to(main_modular_dir)).read_text()
        assert result == path.read_text()


@pytest.mark.skipif(
    black.__version__.split('.')[0] < '22',
    reason="Installed black doesn't support Python version 3.10",
)
@freeze_time('2019-07-26')
def test_main_use_union_operator(tmpdir_factory: TempdirFactory) -> None:
    output_directory = Path(tmpdir_factory.mktemp('output'))

    output_path = output_directory / 'model'
    return_code: Exit = main(
        [
            '--input',
            str(JSON_SCHEMA_DATA_PATH / 'external_files_in_directory'),
            '--output',
            str(output_path),
            '--input-file-type',
            'jsonschema',
            '--use-union-operator',
        ]
    )
    assert return_code == Exit.OK
    main_nested_directory = EXPECTED_MAIN_PATH / 'main_use_union_operator'

    for path in main_nested_directory.rglob('*.py'):
        result = output_path.joinpath(
            path.relative_to(main_nested_directory)
        ).read_text()
        assert result == path.read_text()


@pytest.mark.skipif(
    black.__version__.split('.')[0] < '22',
    reason="Installed black doesn't support Python version 3.10",
)
@freeze_time('2019-07-26')
def test_main_openapi_nullable_use_union_operator():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'nullable.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--use-union-operator',
                '--strict-nullable',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_nullable_strict_nullable_use_union_operator'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_external_relative_ref():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'external_relative_ref' / 'model_b'),
                '--output',
                str(output_path),
            ]
        )
        assert return_code == Exit.OK
        main_modular_dir = EXPECTED_MAIN_PATH / 'external_relative_ref'
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text()


@pytest.mark.benchmark
@freeze_time('2019-07-26')
def test_main_collapse_root_models():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'not_real_string.json'),
                '--output',
                str(output_file),
                '--collapse-root-models',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_collapse_root_models' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_collapse_root_models_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'not_real_string.json'),
                '--output',
                str(output_file),
                '--collapse-root-models',
                '--field-constraints',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_collapse_root_models_field_constraints'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_collapse_root_models_with_references_to_flat_types():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'flat_type.jsonschema'),
                '--output',
                str(output_file),
                '--collapse-root-models',
            ]
        )

        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_collapse_root_models_with_references_to_flat_types'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_max_items_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'max_items_enum.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_max_items_enum' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_duplicate_name():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'duplicate_name'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        main_modular_dir = EXPECTED_MAIN_PATH / 'main_jsonschema_duplicate_name'
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_jsonschema_items_boolean():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'items_boolean.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_items_boolean' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_array_in_additional_properites():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'array_in_additional_properties.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_array_in_additional_properties'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_nullable_object():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'nullable_object.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_nullable_object' / 'output.py'
            ).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_openapi_const',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_openapi_const_pydantic_v2',
        ),
    ],
)
@freeze_time('2019-07-26')
def test_main_openapi_const(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'const.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--output-model',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_openapi_const_field',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_openapi_const_field_pydantic_v2',
        ),
        (
            'msgspec.Struct',
            'main_openapi_const_field_msgspec',
        ),
    ],
)
@freeze_time('2019-07-26')
def test_main_openapi_const_field(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'const.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--output-model',
                output_model,
                '--collapse-root-models',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_complex_reference():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'complex_reference.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_complex_reference' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_reference_to_object_properties():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'reference_to_object_properties.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_reference_to_object_properties'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_reference_to_object_properties_collapse_root_models():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'reference_to_object_properties.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--collapse-root-models',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_reference_to_object_properties_collapse_root_models'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_override_required_all_of_field():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'override_required_all_of.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--collapse-root-models',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_override_required_all_of'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_object_has_one_of():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'object_has_one_of.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_object_has_one_of' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_json_pointer_array():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'json_pointer_array.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_json_pointer_array' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_use_default_kwarg():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'nullable.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--use-default-kwarg',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_use_default_kwarg' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_json_snake_case_field():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_DATA_PATH / 'snake_case.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'json',
                '--snake-case-field',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_json_snake_case_field' / 'output.py'
            ).read_text()
        )


@pytest.mark.filterwarnings('error')
def test_main_disable_warnings_config(capsys: CaptureFixture):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'person.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--use-union-operator',
                '--target-python-version',
                '3.6',
                '--disable-warnings',
            ]
        )
        captured = capsys.readouterr()
        assert return_code == Exit.OK
        assert captured.err == ''


@pytest.mark.filterwarnings('error')
def test_main_disable_warnings(capsys: CaptureFixture):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'all_of_with_object.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--disable-warnings',
            ]
        )
        captured = capsys.readouterr()
        assert return_code == Exit.OK
        assert captured.err == ''


@pytest.mark.parametrize(
    'input,output',
    [
        (
            'discriminator.yaml',
            'main_openapi_discriminator',
        ),
        (
            'discriminator_without_mapping.yaml',
            'main_openapi_discriminator_without_mapping',
        ),
    ],
)
@freeze_time('2019-07-26')
def test_main_openapi_discriminator(input, output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / input),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / output / 'output.py').read_text()
        )


@freeze_time('2023-07-27')
@pytest.mark.parametrize(
    'kind,option, expected',
    [
        (
            'anyOf',
            '--collapse-root-models',
            'main_openapi_discriminator_in_array_collapse_root_models',
        ),
        (
            'oneOf',
            '--collapse-root-models',
            'main_openapi_discriminator_in_array_collapse_root_models',
        ),
        ('anyOf', None, 'main_openapi_discriminator_in_array'),
        ('oneOf', None, 'main_openapi_discriminator_in_array'),
    ],
)
def test_main_openapi_discriminator_in_array(kind, option, expected):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        input_file = f'discriminator_in_array_{kind.lower()}.yaml'
        return_code: Exit = main(
            [
                a
                for a in [
                    '--input',
                    str(OPEN_API_DATA_PATH / input_file),
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'openapi',
                    option,
                ]
                if a
            ]
        )
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / expected / 'output.py'
        ).read_text().replace('discriminator_in_array.yaml', input_file)


@freeze_time('2019-07-26')
def test_main_jsonschema_pattern_properties_by_reference():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'pattern_properties_by_reference.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_pattern_properties_by_reference'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_openapi_default_object',
        ),
        (
            'pydantic_v2.BaseModel',
            'main_openapi_pydantic_v2_default_object',
        ),
        (
            'msgspec.Struct',
            'main_openapi_msgspec_default_object',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_default_object(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'default_object.yaml'),
                '--output',
                str(output_dir),
                '--output-model',
                output_model,
                '--input-file-type',
                'openapi',
                '--target-python-version',
                '3.9',
            ]
        )
        assert return_code == Exit.OK

        main_modular_dir = EXPECTED_MAIN_PATH / expected_output
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text(), path


@freeze_time('2019-07-26')
def test_main_dataclass():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'dataclasses.dataclass',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_dataclass' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_dataclass_base_class():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'dataclasses.dataclass',
                '--base-class',
                'custom_base.Base',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_dataclass_base_class' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_dataclass_field():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'user.json'),
                '--output',
                str(output_file),
                '--output-model-type',
                'dataclasses.dataclass',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_dataclass_field' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_jsonschema_enum_root_literal():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'enum_in_root' / 'enum_in_root.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--use-schema-description',
                '--use-title-as-name',
                '--field-constraints',
                '--target-python-version',
                '3.9',
                '--allow-population-by-field-name',
                '--strip-default-none',
                '--use-default',
                '--enum-field-as-literal',
                'all',
                '--snake-case-field',
                '--collapse-root-models',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_root_in_enum' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_reference_same_hierarchy_directory():
    with TemporaryDirectory() as output_dir:
        with chdir(JSON_SCHEMA_DATA_PATH / 'reference_same_hierarchy_directory'):
            output_file: Path = Path(output_dir) / 'output.py'
            return_code: Exit = main(
                [
                    '--input',
                    './public/entities.yaml',
                    '--output',
                    str(output_file),
                    '--input-file-type',
                    'openapi',
                ]
            )
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (
                    EXPECTED_MAIN_PATH
                    / 'main_jsonschema_reference_same_hierarchy_directory'
                    / 'output.py'
                ).read_text()
            )


@freeze_time('2019-07-26')
def test_main_multiple_required_any_of():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'multiple_required_any_of.yaml'),
                '--output',
                str(output_file),
                '--collapse-root-models',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_multiple_required_any_of' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_nullable_any_of():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'nullable_any_of.json'),
                '--output',
                str(output_file),
                '--field-constraints',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_nullable_any_of' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_nullable_any_of_use_union_operator():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'nullable_any_of.json'),
                '--output',
                str(output_file),
                '--field-constraints',
                '--use-union-operator',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_nullable_any_of_use_union_operator'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_nested_all_of():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'nested_all_of.json'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_nested_all_of' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_max_min_openapi():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'max_min_number.yaml'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'max_min_number' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_use_operation_id_as_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--use-operation-id-as-name',
                '--openapi-scopes',
                'paths',
                'schemas',
                'parameters',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_use_operation_id_as_name' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_use_operation_id_as_name_not_found_operation_id(capsys):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'body_and_parameters.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--use-operation-id-as-name',
                '--openapi-scopes',
                'paths',
                'schemas',
                'parameters',
            ]
        )
        captured = capsys.readouterr()
        assert return_code == Exit.ERROR
        assert (
            captured.err
            == 'All operations must have an operationId when --use_operation_id_as_name is set.'
            'The following path was missing an operationId: pets\n'
        )


@freeze_time('2019-07-26')
def test_main_unsorted_optional_fields():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'unsorted_optional_fields.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'dataclasses.dataclass',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'unsorted_optional_fields' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_all_of_any_of():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'all_of_any_of'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        all_of_any_of_dir = EXPECTED_MAIN_PATH / 'main_all_of_any_of'
        for path in all_of_any_of_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(all_of_any_of_dir)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_all_of_one_of():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'all_of_one_of'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        all_of_any_of_dir = EXPECTED_MAIN_PATH / 'main_all_of_one_of'
        for path in all_of_any_of_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(all_of_any_of_dir)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_null():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'null.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_null' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_typed_dict():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'typing.TypedDict',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_typed_dict' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_typed_dict_py_38():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'typing.TypedDict',
                '--target-python-version',
                '3.8',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_typed_dict_py_38' / 'output.py').read_text()
        )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse('23.3.0'),
    reason='Require Black version 23.3.0 or later ',
)
@freeze_time('2019-07-26')
def test_main_typed_dict_space_and_special_characters():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_DATA_PATH / 'space_and_special_characters.json'),
                '--output',
                str(output_file),
                '--output-model-type',
                'typing.TypedDict',
                '--target-python-version',
                '3.11',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_typed_dict_space_and_special_characters'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse('23.3.0'),
    reason='Require Black version 23.3.0 or later ',
)
def test_main_modular_typed_dict(tmpdir_factory: TempdirFactory) -> None:
    """Test main function on modular file."""

    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(
            [
                '--input',
                str(input_filename),
                '--output',
                str(output_path),
                '--output-model-type',
                'typing.TypedDict',
                '--target-python-version',
                '3.11',
            ]
        )
    main_modular_dir = EXPECTED_MAIN_PATH / 'main_modular_typed_dict'
    for path in main_modular_dir.rglob('*.py'):
        result = output_path.joinpath(path.relative_to(main_modular_dir)).read_text()
        assert result == path.read_text()


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse('23.3.0'),
    reason='Require Black version 23.3.0 or later ',
)
@freeze_time('2019-07-26')
def test_main_typed_dict_special_field_name_with_inheritance_model():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(
                    JSON_SCHEMA_DATA_PATH
                    / 'special_field_name_with_inheritance_model.json'
                ),
                '--output',
                str(output_file),
                '--output-model-type',
                'typing.TypedDict',
                '--target-python-version',
                '3.11',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_typed_dict_special_field_name_with_inheritance_model'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse('23.3.0'),
    reason='Require Black version 23.3.0 or later ',
)
@freeze_time('2019-07-26')
def test_main_typed_dict_not_required_nullable():
    """Test main function writing to TypedDict, with combos of Optional/NotRequired."""
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'not_required_nullable.json'),
                '--output',
                str(output_file),
                '--output-model-type',
                'typing.TypedDict',
                '--target-python-version',
                '3.11',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_typed_dict_not_required_nullable'
                / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse('23.3.0'),
    reason='Require Black version 23.3.0 or later ',
)
@freeze_time('2019-07-26')
def test_main_typed_dict_nullable():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'nullable.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'typing.TypedDict',
                '--target-python-version',
                '3.11',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_typed_dict_nullable' / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    version.parse(black.__version__) < version.parse('23.3.0'),
    reason='Require Black version 23.3.0 or later ',
)
@freeze_time('2019-07-26')
def test_main_typed_dict_nullable_strict_nullable():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'nullable.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'typing.TypedDict',
                '--target-python-version',
                '3.11',
                '--strict-nullable',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_typed_dict_nullable_strict_nullable'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_custom_file_header_path():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--custom-file-header-path',
                str(DATA_PATH / 'custom_file_header.txt'),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_custom_file_header' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_custom_file_header_duplicate_options(capsys):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--custom-file-header-path',
                str(DATA_PATH / 'custom_file_header.txt'),
                '--custom-file-header',
                'abc',
            ]
        )

        captured = capsys.readouterr()
        assert return_code == Exit.ERROR
        assert (
            captured.err
            == '`--custom_file_header_path` can not be used with `--custom_file_header`.\n'
        )


@freeze_time('2019-07-26')
def test_main_pydantic_v2():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'pydantic_v2.BaseModel',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_pydantic_v2' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_custom_id_pydantic_v2():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'custom_id.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'pydantic_v2.BaseModel',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_custom_id_pydantic_v2' / 'output.py'
            ).read_text()
        )


@pytest.mark.skipif(
    not isort.__version__.startswith('4.'),
    reason="isort 5.x don't sort pydantic modules",
)
@freeze_time('2019-07-26')
def test_main_openapi_custom_id_pydantic_v2_custom_base():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'custom_id.yaml'),
                '--output',
                str(output_file),
                '--output-model-type',
                'pydantic_v2.BaseModel',
                '--base-class',
                'custom_base.Base',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_openapi_custom_id_pydantic_v2_custom_base'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_jsonschema_discriminator_literals():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'discriminator_literals.json'),
                '--output',
                str(output_file),
                '--output-model-type',
                'pydantic_v2.BaseModel',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_jsonschema_discriminator_literals'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_all_of_with_relative_ref():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'all_of_with_relative_ref' / 'openapi.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--output-model-type',
                'pydantic_v2.BaseModel',
                '--keep-model-order',
                '--collapse-root-models',
                '--field-constraints',
                '--use-title-as-name',
                '--field-include-all-keys',
                '--use-field-description',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_all_of_with_relative_ref' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_msgspec_struct():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                # min msgspec python version is 3.8
                '--target-python-version',
                '3.8',
                '--output-model-type',
                'msgspec.Struct',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_msgspec_struct' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_msgspec_use_annotated_with_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
                '--field-constraints',
                '--target-python-version',
                '3.9',
                '--output-model-type',
                'msgspec.Struct',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_use_annotated_with_msgspec_meta_constraints'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_duplicate_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'duplicate_field_constraints'),
                '--output',
                str(output_path),
                '--input-file-type',
                'jsonschema',
                '--collapse-root-models',
                '--output-model-type',
                'pydantic_v2.BaseModel',
            ]
        )
        assert return_code == Exit.OK
        main_modular_dir = EXPECTED_MAIN_PATH / 'duplicate_field_constraints'
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text()


@pytest.mark.parametrize(
    'collapse_root_models,python_version,expected_output',
    [
        (
            '--collapse-root-models',
            '3.8',
            'duplicate_field_constraints_msgspec_py38_collapse_root_models',
        ),
        (
            None,
            '3.9',
            'duplicate_field_constraints_msgspec',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_duplicate_field_constraints_msgspec(
    collapse_root_models, python_version, expected_output
):
    with TemporaryDirectory() as output_dir:
        output_path: Path = Path(output_dir)
        return_code: Exit = main(
            [
                a
                for a in [
                    '--input',
                    str(JSON_SCHEMA_DATA_PATH / 'duplicate_field_constraints'),
                    '--output',
                    str(output_path),
                    '--input-file-type',
                    'jsonschema',
                    '--output-model-type',
                    'msgspec.Struct',
                    '--target-python-version',
                    python_version,
                    collapse_root_models,
                ]
                if a
            ]
        )
        assert return_code == Exit.OK
        main_modular_dir = EXPECTED_MAIN_PATH / expected_output
        for path in main_modular_dir.rglob('*.py'):
            result = output_path.joinpath(
                path.relative_to(main_modular_dir)
            ).read_text()
            assert result == path.read_text()


@freeze_time('2019-07-26')
def test_main_dataclass_field_defs():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'user_defs.json'),
                '--output',
                str(output_file),
                '--output-model-type',
                'dataclasses.dataclass',
            ]
        )
        assert return_code == Exit.OK
        assert output_file.read_text() == (
            EXPECTED_MAIN_PATH / 'main_dataclass_field' / 'output.py'
        ).read_text().replace('filename:  user.json', 'filename:  user_defs.json')


@freeze_time('2019-07-26')
def test_main_dataclass_default():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'user_default.json'),
                '--output',
                str(output_file),
                '--output-model-type',
                'dataclasses.dataclass',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_dataclass_field_default' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_main_all_of_ref_self():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'all_of_ref_self.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_all_of_ref_self' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_array_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'array_field_constraints.json'),
                '--output',
                str(output_file),
                '--input-file-type',
                'jsonschema',
                '--target-python-version',
                '3.9',
                '--field-constraints',
                '--collapse-root-models',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_array_field_constraints' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
def test_all_of_use_default():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(JSON_SCHEMA_DATA_PATH / 'all_of_default.json'),
                '--output',
                str(output_file),
                '--use-default',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_all_of_use_default' / 'output.py'
            ).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'main_graphql_simple_star_wars',
        ),
        (
            'dataclasses.dataclass',
            'main_graphql_simple_star_wars_dataclass',
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_simple_star_wars(output_model, expected_output):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'simple-star-wars.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
                '--output-model',
                output_model,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / expected_output / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_different_types_of_fields():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'different-types-of-fields.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_graphql_different_types_of_fields'
                / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_custom_scalar_types():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'custom-scalar-types.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
                '--extra-template-data',
                str(GRAPHQL_DATA_PATH / 'custom-scalar-types.json'),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_graphql_custom_scalar_types' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_field_aliases():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'field-aliases.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
                '--aliases',
                str(GRAPHQL_DATA_PATH / 'field-aliases.json'),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_graphql_field_aliases' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_enums():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'enums.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_graphql_enums' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_union():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'union.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_graphql_union' / 'output.py').read_text()
        )


@pytest.mark.skipif(
    not isort.__version__.startswith('4.'),
    reason='See https://github.com/PyCQA/isort/issues/1600 for example',
)
@freeze_time('2019-07-26')
def test_main_graphql_additional_imports_isort_4():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'additional-imports.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
                '--extra-template-data',
                str(GRAPHQL_DATA_PATH / 'additional-imports-types.json'),
                '--additional-imports',
                'datetime.datetime,datetime.date,mymodule.myclass.MyCustomPythonClass',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_graphql_additional_imports'
                / 'output_isort4.py'
            ).read_text()
        )


@pytest.mark.skipif(
    not isort.__version__.startswith('5.'),
    reason='See https://github.com/PyCQA/isort/issues/1600 for example',
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_additional_imports_isort_5():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'additional-imports.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
                '--extra-template-data',
                str(GRAPHQL_DATA_PATH / 'additional-imports-types.json'),
                '--additional-imports',
                'datetime.datetime,datetime.date,mymodule.myclass.MyCustomPythonClass',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH
                / 'main_graphql_additional_imports'
                / 'output_isort5.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_graphql_custom_formatters():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(GRAPHQL_DATA_PATH / 'custom-scalar-types.graphql'),
                '--output',
                str(output_file),
                '--input-file-type',
                'graphql',
                '--custom-formatters',
                'tests.data.python.custom_formatters.add_comment',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_graphql_custom_formatters' / 'output.py'
            ).read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'discriminator_enum.yaml'),
                '--output',
                str(output_file),
                '--target-python-version',
                '3.10',
                '--output-model-type',
                'pydantic_v2.BaseModel',
                '--input-file-type',
                'openapi',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_openapi_discriminator_enum' / 'output.py'
            ).read_text()
        )
