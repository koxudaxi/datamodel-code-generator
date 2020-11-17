import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import call

import pytest
from _pytest.capture import CaptureFixture
from _pytest.tmpdir import TempdirFactory
from freezegun import freeze_time

from datamodel_code_generator import chdir
from datamodel_code_generator.__main__ import Exit, main

DATA_PATH: Path = Path(__file__).parent / 'data'
OPEN_API_DATA_PATH: Path = DATA_PATH / 'openapi'
JSON_SCHEMA_DATA_PATH: Path = DATA_PATH / 'jsonschema'
JSON_DATA_PATH: Path = DATA_PATH / 'json'
YAML_DATA_PATH: Path = DATA_PATH / 'yaml'
EXPECTED_MAIN_PATH = DATA_PATH / 'expected' / 'main'

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
            == (EXPECTED_MAIN_PATH / 'main' / 'output.py').read_text()
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
            == (EXPECTED_MAIN_PATH / 'main_base_class' / 'output.py').read_text()
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
            == (EXPECTED_MAIN_PATH / 'target_python_version' / 'output.py').read_text()
        )

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_jsonschema_nested_deep():
    with TemporaryDirectory() as output_dir:
        output_init_file: Path = Path(output_dir) / '__init__.py'
        output_nested_file: Path = Path(output_dir) / 'nested/deep.py'
        output_empty_parent_nested_file: Path = Path(
            output_dir
        ) / 'empty_parent/nested/deep.py'

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
    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_null_and_array():
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
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_null_and_array' / 'output.py').read_text()
        )
    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()


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
        == (EXPECTED_MAIN_PATH / 'main_custom_template_dir' / 'output.py').read_text()
    )
    assert not captured.err


@freeze_time('2019-07-26')
def test_pyproject():
    with TemporaryDirectory() as output_dir:
        output_dir = Path(output_dir)
        with chdir(output_dir):
            output_file: Path = output_dir / 'output.py'
            pyproject_toml_path = Path(DATA_PATH) / "project" / "pyproject.toml"
            pyproject_toml = (
                pyproject_toml_path.read_text()
                .replace('INPUT_PATH', str(OPEN_API_DATA_PATH / 'api.yaml'))
                .replace('OUTPUT_PATH', str(output_file))
                .replace('ALIASES_PATH', str(OPEN_API_DATA_PATH / 'empty_aliases.json'))
                .replace(
                    'EXTRA_TEMPLATE_DATA_PATH',
                    str(OPEN_API_DATA_PATH / 'empty_data.json'),
                )
                .replace('CUSTOM_TEMPLATE_DIR_PATH', str(output_dir))
            )
            (output_dir / 'pyproject.toml').write_text(pyproject_toml)

            return_code: Exit = main([])
            assert return_code == Exit.OK
            assert (
                output_file.read_text()
                == (EXPECTED_MAIN_PATH / 'pyproject' / 'output.py').read_text()
            )
    with pytest.raises(SystemExit):
        main()


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
            ['--output', str(output_file),]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'stdin' / 'output.py').read_text()
        )


@freeze_time('2019-07-26')
def test_validation():
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

    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_validation_failed():
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


@freeze_time('2019-07-26')
def test_main_with_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
                '--field-constraints',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_with_field_constraints' / 'output.py'
            ).read_text()
        )

    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_without_field_constraints():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api_constrained.yaml'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_without_field_constraints' / 'output.py'
            ).read_text()
        )

    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_with_aliases():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--aliases',
                str(OPEN_API_DATA_PATH / 'aliases.json'),
                '--output',
                str(output_file),
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (EXPECTED_MAIN_PATH / 'main_with_aliases' / 'output.py').read_text()
        )

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_allow_population_by_field_name():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            [
                '--input',
                str(OPEN_API_DATA_PATH / 'api.yaml'),
                '--output',
                str(output_file),
                '--allow-population-by-field-name',
            ]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'allow_population_by_field_name' / 'output.py'
            ).read_text()
        )

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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

    with pytest.raises(SystemExit):
        main()


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
            ]
        )
        captured = capsys.readouterr()
        assert return_code == Exit.ERROR
        assert (
            captured.err
            == 'title=\'1 xyz\' is invalid class name. You have to set --class-name option\n'
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
    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_root_id_jsonschema(mocker):
    root_id_response = mocker.Mock()
    root_id_response.text = 'dummy'
    person_response = mocker.Mock()
    person_response.text = (JSON_SCHEMA_DATA_PATH / 'person.json').read_text()
    httpx_get_mock = mocker.patch(
        'httpx.get', side_effect=[root_id_response, person_response]
    )
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
        httpx_get_mock.assert_has_calls(
            [
                call('https://example.com/root_id.json'),
                call('https://example.com/person.json'),
            ]
        )
    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_root_id_jsonschema_root_id_failed(mocker):
    httpx_get_mock = mocker.patch('httpx.get', side_effect=[Exception])
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
        httpx_get_mock.assert_has_calls(
            [call('https://example.com/root_id.json'),]
        )
    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()


@freeze_time('2019-07-26')
def test_main_jsonschema_id_as_stdin(monkeypatch):
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        monkeypatch.setattr('sys.stdin', (JSON_SCHEMA_DATA_PATH / 'id.json').open())
        return_code: Exit = main(
            ['--output', str(output_file), '--input-file-type', 'jsonschema',]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == (
                EXPECTED_MAIN_PATH / 'main_jsonschema_id_stdin' / 'output.py'
            ).read_text()
        )
    with pytest.raises(SystemExit):
        main()


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
    with pytest.raises(SystemExit):
        main()
