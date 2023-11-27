from typing import ClassVar

import pytest

from datamodel_code_generator.formatter.base import (
    BaseCodeFormatter,
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
