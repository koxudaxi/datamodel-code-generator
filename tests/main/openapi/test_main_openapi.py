import platform
import shutil
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
from unittest.mock import call

import black
import isort
import pydantic
import pytest
from freezegun import freeze_time
from packaging import version

try:
    from pytest import TempdirFactory
except ImportError:
    from _pytest.tmpdir import TempdirFactory

from datamodel_code_generator import (
    InputFileType,
    chdir,
    generate,
    inferred_message,
)
from datamodel_code_generator.__main__ import Exit, main
from tests.main.test_main_general import DATA_PATH, EXPECTED_MAIN_PATH, TIMESTAMP

CaptureFixture = pytest.CaptureFixture
MonkeyPatch = pytest.MonkeyPatch

OPEN_API_DATA_PATH: Path = DATA_PATH / 'openapi'
EXPECTED_OPENAPI_PATH: Path = EXPECTED_MAIN_PATH / 'openapi'


@pytest.fixture(autouse=True)
def reset_namespace(monkeypatch: MonkeyPatch):
    namespace_ = Namespace(no_color=False)
    monkeypatch.setattr('datamodel_code_generator.__main__.namespace', namespace_)
    monkeypatch.setattr('datamodel_code_generator.arguments.namespace', namespace_)


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
            == (EXPECTED_OPENAPI_PATH / 'general.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'discriminator' / 'enum.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_discriminator_enum_duplicate():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'discriminator_enum_duplicate.yaml'),
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
                EXPECTED_OPENAPI_PATH / 'discriminator' / 'enum_duplicate.py'
            ).read_text()
        )


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
            == (EXPECTED_OPENAPI_PATH / 'general.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'base_class.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'target_python_version.py').read_text()
        )


@pytest.mark.benchmark
def test_main_modular(tmpdir_factory: TempdirFactory) -> None:
    """Test main function on modular file."""

    output_directory = Path(tmpdir_factory.mktemp('output'))

    input_filename = OPEN_API_DATA_PATH / 'modular.yaml'
    output_path = output_directory / 'model'

    with freeze_time(TIMESTAMP):
        main(['--input', str(input_filename), '--output', str(output_path)])
    main_modular_dir = EXPECTED_OPENAPI_PATH / 'modular'
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
    main_modular_dir = EXPECTED_OPENAPI_PATH / 'modular_reuse_model'
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


def test_main_openapi_no_file(capsys: CaptureFixture) -> None:
    """Test main function on non-modular file with no output name."""

    input_filename = OPEN_API_DATA_PATH / 'api.yaml'

    with freeze_time(TIMESTAMP):
        main(['--input', str(input_filename)])

    captured = capsys.readouterr()
    assert captured.out == (EXPECTED_OPENAPI_PATH / 'no_file.py').read_text()
    assert captured.err == inferred_message.format('openapi') + '\n'


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'extra_template_data_config.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'extra_template_data_config_pydantic_v2.py',
        ),
    ],
)
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_extra_template_data_config(
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
    assert captured.out == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
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
        captured.out == (EXPECTED_OPENAPI_PATH / 'custom_template_dir.py').read_text()
    )
    assert captured.err == inferred_message.format('openapi') + '\n'


def test_main_openapi_custom_template_dir(capsys: CaptureFixture) -> None:
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
        captured.out == (EXPECTED_OPENAPI_PATH / 'custom_template_dir.py').read_text()
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
                == (EXPECTED_OPENAPI_PATH / 'pyproject.py').read_text()
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
                == (EXPECTED_OPENAPI_PATH / 'pyproject_not_found.py').read_text()
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
            output_file.read_text() == (EXPECTED_OPENAPI_PATH / 'stdin.py').read_text()
        )


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
            == (EXPECTED_OPENAPI_PATH / 'validation.py').read_text()
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
        ('pydantic.BaseModel', 'with_field_constraints.py', []),
        (
            'pydantic.BaseModel',
            'with_field_constraints_use_unique_items_as_set.py',
            ['--use-unique-items-as-set'],
        ),
        ('pydantic_v2.BaseModel', 'with_field_constraints_pydantic_v2.py', []),
        (
            'pydantic_v2.BaseModel',
            'with_field_constraints_pydantic_v2_use_generic_container_types.py',
            ['--use-generic-container-types'],
        ),
        (
            'pydantic_v2.BaseModel',
            'with_field_constraints_pydantic_v2_use_generic_container_types_set.py',
            ['--use-generic-container-types', '--use-unique-items-as-set'],
        ),
        (
            'pydantic_v2.BaseModel',
            'with_field_constraints_pydantic_v2_use_standard_collections.py',
            [
                '--use-standard-collections',
            ],
        ),
        (
            'pydantic_v2.BaseModel',
            'with_field_constraints_pydantic_v2_use_standard_collections_set.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'without_field_constraints.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'without_field_constraints_pydantic_v2.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'with_aliases.py',
        ),
        (
            'msgspec.Struct',
            'with_aliases_msgspec.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'with_snake_case_field.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'with_strip_default_none.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'disable_timestamp.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'enable_version_header.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'allow_population_by_field_name.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'allow_population_by_field_name_pydantic_v2.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'allow_extra_fields.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'allow_extra_fields_pydantic_v2.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'enable_faux_immutability.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'enable_faux_immutability_pydantic_v2.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'use_default.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'force_optional.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'with_exclusive.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'subclass_enum.py').read_text()
        )


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
        EXPECTED_OPENAPI_PATH / 'use_standard_collections'
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
        EXPECTED_OPENAPI_PATH / 'use_generic_container_types'
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
        EXPECTED_OPENAPI_PATH / 'use_generic_container_types_standard_collections'
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


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'datetime.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'datetime_pydantic_v2.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'enum_models' / 'one.py').read_text()
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
                EXPECTED_OPENAPI_PATH / 'enum_models' / 'one_literal_as_default.py'
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
            == (EXPECTED_OPENAPI_PATH / 'enum_models' / 'all.py').read_text()
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
                EXPECTED_OPENAPI_PATH / 'enum_models' / 'as_literal_py37.py'
            ).read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'allof_required.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'nullable.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'nullable_strict_nullable.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'general.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'pydantic_v2.py',
        ),
        (
            'msgspec.Struct',
            'msgspec_pattern.py',
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
            EXPECTED_OPENAPI_PATH / 'pattern' / expected_output
        ).read_text().replace('pattern.json', 'pattern.yaml')


@pytest.mark.parametrize(
    'expected_output, args',
    [
        ('pattern_with_lookaround_pydantic_v2.py', []),
        (
            'pattern_with_lookaround_pydantic_v2_field_constraints.py',
            ['--field-constraints'],
        ),
    ],
)
@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] < '22',
    reason="Installed black doesn't support Python version 3.10",
)
def test_main_openapi_pattern_with_lookaround_pydantic_v2(
    expected_output: str, args: List[str]
):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'pattern_lookaround.yaml'),
                '--output',
                str(output_file),
                '--input-file-type',
                'openapi',
                '--target-python',
                '3.9',
                '--output-model-type',
                'pydantic_v2.BaseModel',
                *args,
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
        )


@freeze_time('2019-07-26')
def test_main_generate_custom_class_name_generator_modular(
    tmpdir_factory: TempdirFactory,
):
    output_directory = Path(tmpdir_factory.mktemp('output'))

    output_path = output_directory / 'model'
    main_modular_custom_class_name_dir = (
        EXPECTED_OPENAPI_PATH / 'modular_custom_class_name'
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
            == (EXPECTED_OPENAPI_PATH / 'http_refs.py').read_text()
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://example.com/refs.yaml',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                    params=None,
                ),
                call(
                    'https://teamdigitale.github.io/openapi/0.0.6/definitions.yaml',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                    params=None,
                ),
            ]
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
            == (EXPECTED_OPENAPI_PATH / 'disable_appending_item_suffix.py').read_text()
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
                EXPECTED_OPENAPI_PATH / 'body_and_parameters' / 'general.py'
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
                EXPECTED_OPENAPI_PATH / 'body_and_parameters' / 'remote_ref.py'
            ).read_text()
        )
        httpx_get_mock.assert_has_calls(
            [
                call(
                    'https://schema.example',
                    headers=None,
                    verify=True,
                    follow_redirects=True,
                    params=None,
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
                EXPECTED_OPENAPI_PATH / 'body_and_parameters' / 'only_paths.py'
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
                EXPECTED_OPENAPI_PATH / 'body_and_parameters' / 'only_schemas.py'
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
            == (EXPECTED_OPENAPI_PATH / 'content_in_parameters.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'oas_response_reference.py').read_text()
        )


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
            == (EXPECTED_OPENAPI_PATH / 'json_pointer.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        ('pydantic.BaseModel', 'use_annotated_with_field_constraints.py'),
        (
            'pydantic_v2.BaseModel',
            'use_annotated_with_field_constraints_pydantic_v2.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
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
                EXPECTED_OPENAPI_PATH / 'use_annotated_with_field_constraints_py38.py'
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
            == (EXPECTED_OPENAPI_PATH / 'nested_enum.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'special_yaml_keywords.py').read_text()
        )
    mock_prance.assert_called_once()


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
                EXPECTED_OPENAPI_PATH / 'nullable_strict_nullable_use_union_operator.py'
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
        main_modular_dir = EXPECTED_OPENAPI_PATH / 'external_relative_ref'
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
            == (EXPECTED_OPENAPI_PATH / 'collapse_root_models.py').read_text()
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
                EXPECTED_OPENAPI_PATH / 'collapse_root_models_field_constraints.py'
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
                EXPECTED_OPENAPI_PATH
                / 'collapse_root_models_with_references_to_flat_types.py'
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
            == (EXPECTED_OPENAPI_PATH / 'max_items_enum.py').read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'const.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'const_pydantic_v2.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
        )


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'const_field.py',
        ),
        (
            'pydantic_v2.BaseModel',
            'const_field_pydantic_v2.py',
        ),
        (
            'msgspec.Struct',
            'const_field_msgspec.py',
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
            == (EXPECTED_OPENAPI_PATH / expected_output).read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'complex_reference.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'reference_to_object_properties.py').read_text()
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
                EXPECTED_OPENAPI_PATH
                / 'reference_to_object_properties_collapse_root_models.py'
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
            == (EXPECTED_OPENAPI_PATH / 'override_required_all_of.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'use_default_kwarg.py').read_text()
        )


@pytest.mark.parametrize(
    'input,output',
    [
        (
            'discriminator.yaml',
            'general.py',
        ),
        (
            'discriminator_without_mapping.yaml',
            'without_mapping.py',
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
            == (EXPECTED_OPENAPI_PATH / 'discriminator' / output).read_text()
        )


@freeze_time('2023-07-27')
@pytest.mark.parametrize(
    'kind,option, expected',
    [
        (
            'anyOf',
            '--collapse-root-models',
            'in_array_collapse_root_models.py',
        ),
        (
            'oneOf',
            '--collapse-root-models',
            'in_array_collapse_root_models.py',
        ),
        ('anyOf', None, 'in_array.py'),
        ('oneOf', None, 'in_array.py'),
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
            EXPECTED_OPENAPI_PATH / 'discriminator' / expected
        ).read_text().replace('discriminator_in_array.yaml', input_file)


@pytest.mark.parametrize(
    'output_model,expected_output',
    [
        (
            'pydantic.BaseModel',
            'default_object',
        ),
        (
            'pydantic_v2.BaseModel',
            'pydantic_v2_default_object',
        ),
        (
            'msgspec.Struct',
            'msgspec_default_object',
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

        main_modular_dir = EXPECTED_OPENAPI_PATH / expected_output
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
            == (EXPECTED_OPENAPI_PATH / 'dataclass.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'dataclass_base_class.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_reference_same_hierarchy_directory():
    with TemporaryDirectory() as output_dir:
        with chdir(OPEN_API_DATA_PATH / 'reference_same_hierarchy_directory'):
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
                    EXPECTED_OPENAPI_PATH / 'reference_same_hierarchy_directory.py'
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
            == (EXPECTED_OPENAPI_PATH / 'multiple_required_any_of.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_max_min():
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
            == (EXPECTED_OPENAPI_PATH / 'max_min_number.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_use_operation_id_as_name():
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
            == (EXPECTED_OPENAPI_PATH / 'use_operation_id_as_name.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_use_operation_id_as_name_not_found_operation_id(capsys):
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
            == (EXPECTED_OPENAPI_PATH / 'unsorted_optional_fields.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'typed_dict.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'typed_dict_py_38.py').read_text()
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
    main_modular_dir = EXPECTED_OPENAPI_PATH / 'modular_typed_dict'
    for path in main_modular_dir.rglob('*.py'):
        result = output_path.joinpath(path.relative_to(main_modular_dir)).read_text()
        assert result == path.read_text()


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
            == (EXPECTED_OPENAPI_PATH / 'typed_dict_nullable.py').read_text()
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
                EXPECTED_OPENAPI_PATH / 'typed_dict_nullable_strict_nullable.py'
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
            == (EXPECTED_OPENAPI_PATH / 'custom_file_header.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'pydantic_v2.py').read_text()
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
            == (EXPECTED_OPENAPI_PATH / 'custom_id_pydantic_v2.py').read_text()
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
                EXPECTED_OPENAPI_PATH / 'custom_id_pydantic_v2_custom_base.py'
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
            == (EXPECTED_OPENAPI_PATH / 'all_of_with_relative_ref.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_msgspec_struct():
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
            == (EXPECTED_OPENAPI_PATH / 'msgspec_struct.py').read_text()
        )


@freeze_time('2019-07-26')
def test_main_openapi_msgspec_struct_snake_case():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_ordered_required_fields.yaml'),
                '--output',
                str(output_file),
                # min msgspec python version is 3.8
                '--target-python-version',
                '3.8',
                '--snake-case-field',
                '--output-model-type',
                'msgspec.Struct',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_OPENAPI_PATH / 'msgspec_struct_snake_case.py').read_text()
        )


@freeze_time('2019-07-26')
@pytest.mark.skipif(
    black.__version__.split('.')[0] == '19',
    reason="Installed black doesn't support the old style",
)
def test_main_openapi_msgspec_use_annotated_with_field_constraints():
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
                EXPECTED_OPENAPI_PATH
                / 'msgspec_use_annotated_with_field_constraints.py'
            ).read_text()
        )
