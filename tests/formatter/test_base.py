from typing import ClassVar

import pytest

from datamodel_code_generator.formatter.base import (
    BaseCodeFormatter,
    CodeFormattersRunner,
    load_code_formatter,
)

UN_EXIST_FORMATTER = 'tests.data.python.custom_formatters.un_exist.CustomFormatter'
WRONG_FORMATTER = 'tests.data.python.custom_formatters.wrong.WrongFormatterName_'
NOT_SUBCLASS_FORMATTER = (
    'tests.data.python.custom_formatters.not_subclass.CodeFormatter'
)
ADD_LICENSE_FORMATTER = (
    'tests.data.python.custom_formatters.add_license_formatter.LicenseFormatter'
)


def test_incorrect_from_base_not_implemented_apply():
    class CustomFormatter(BaseCodeFormatter):
        formatter_name: ClassVar[str] = 'formatter'

    with pytest.raises(NotImplementedError):
        formatter = CustomFormatter({})
        formatter.apply('')


def test_incorrect_from_base():
    class CustomFormatter(BaseCodeFormatter):
        def apply(self, code: str) -> str:
            return code

    with pytest.raises(ValueError):
        _ = CustomFormatter({})


def test_load_code_formatter_un_exist_custom_formatter():
    with pytest.raises(ModuleNotFoundError):
        load_code_formatter(UN_EXIST_FORMATTER, {})


def test_load_code_formatter_invalid_formatter_name():
    with pytest.raises(NameError):
        load_code_formatter(WRONG_FORMATTER, {})


def test_load_code_formatter_is_not_subclass():
    with pytest.raises(TypeError):
        load_code_formatter(NOT_SUBCLASS_FORMATTER, {})


def test_add_license_formatter_without_kwargs():
    formatter = load_code_formatter(ADD_LICENSE_FORMATTER, {})
    formatted_code = formatter.apply('x = 1\ny = 2')

    assert (
        formatted_code
        == """# a license
x = 1
y = 2"""
    )


def test_add_license_formatter_with_kwargs():
    formatter = load_code_formatter(
        ADD_LICENSE_FORMATTER,
        {
            'license_formatter': {
                'license_txt': 'MIT License\n\nCopyright (c) 2023 Blah-blah\n'
            }
        },
    )
    formatted_code = formatter.apply('x = 1\ny = 2')

    assert (
        formatted_code
        == """# MIT License
# 
# Copyright (c) 2023 Blah-blah
# 
x = 1
y = 2"""
    )


def test_runner_quick_init():
    runner = CodeFormattersRunner()

    assert runner.disable_default_formatter is False
    assert runner.custom_formatters_kwargs == {
        'black': {
            'settings_path': None,
            'wrap_string_literal': None,
            'skip_string_normalization': True,
        },
        'isort': {
            'settings_path': None,
            'known_third_party': None,
        },
    }

    assert len(runner.default_formatters) == 1
    assert runner.default_formatters[0].formatter_name == 'ruff'

    assert runner.custom_formatters == []


def test_runner_set_default_formatters():
    runner = CodeFormattersRunner(
        default_formatter=['black', 'isort'],
    )

    assert runner.disable_default_formatter is False

    assert len(runner.default_formatters) == 2
    assert runner.default_formatters[0].formatter_name == 'black'
    assert runner.default_formatters[1].formatter_name == 'isort'

    assert runner.custom_formatters == []


def test_runner_set_default_formatters_disable():
    runner = CodeFormattersRunner(
        default_formatter=['black', 'isort'],
        disable_default_formatter=True,
    )

    assert runner.disable_default_formatter is True

    assert len(runner.default_formatters) == 0
    assert runner.custom_formatters == []


def test_runner_custom_formatters():
    runner = CodeFormattersRunner(custom_formatters=[ADD_LICENSE_FORMATTER])

    assert len(runner.custom_formatters) == 1
    assert runner.custom_formatters[0].formatter_name == 'license_formatter'


def test_runner_custom_formatters_kwargs():
    runner = CodeFormattersRunner(
        custom_formatters=[ADD_LICENSE_FORMATTER],
        custom_formatters_kwargs={
            'license_formatter': {
                'license_txt': 'MIT License\n\nCopyright (c) 2023 Blah-blah\n'
            }
        },
    )

    assert len(runner.custom_formatters) == 1
    assert runner.custom_formatters[0].formatter_name == 'license_formatter'

    assert runner.custom_formatters_kwargs == {
        'black': {
            'settings_path': None,
            'wrap_string_literal': None,
            'skip_string_normalization': True,
        },
        'isort': {
            'settings_path': None,
            'known_third_party': None,
        },
        'license_formatter': {
            'license_txt': 'MIT License\n\nCopyright (c) 2023 Blah-blah\n'
        },
    }
