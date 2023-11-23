import sys
from pathlib import Path

import pytest

from datamodel_code_generator.format import CodeFormatter, PythonVersion

EXAMPLE_LICENSE_FILE = str(
    Path(__file__).parent / 'data/python/custom_formatters/license_example.txt'
)

UN_EXIST_FORMATTER = 'tests.data.python.custom_formatters.un_exist'
WRONG_FORMATTER = 'tests.data.python.custom_formatters.wrong'
NOT_SUBCLASS_FORMATTER = 'tests.data.python.custom_formatters.not_subclass'
ADD_COMMENT_FORMATTER = 'tests.data.python.custom_formatters.add_comment'
ADD_LICENSE_FORMATTER = 'tests.data.python.custom_formatters.add_license'


def test_python_version():
    """Ensure that the python version used for the tests is properly listed"""

    _ = PythonVersion('{}.{}'.format(*sys.version_info[:2]))


@pytest.mark.parametrize(
    ('skip_string_normalization', 'expected_output'),
    [
        (True, "a = 'b'"),
        (False, 'a = "b"'),
    ],
)
def test_format_code_with_skip_string_normalization(
    skip_string_normalization: bool, expected_output: str
) -> None:
    formatter = CodeFormatter(
        PythonVersion.PY_37, skip_string_normalization=skip_string_normalization
    )

    formatted_code = formatter.format_code("a = 'b'")

    assert formatted_code == expected_output + '\n'


def test_format_code_un_exist_custom_formatter():
    with pytest.raises(ModuleNotFoundError):
        _ = CodeFormatter(
            PythonVersion.PY_37,
            custom_formatters=[UN_EXIST_FORMATTER],
        )


def test_format_code_invalid_formatter_name():
    with pytest.raises(NameError):
        _ = CodeFormatter(
            PythonVersion.PY_37,
            custom_formatters=[WRONG_FORMATTER],
        )


def test_format_code_is_not_subclass():
    with pytest.raises(TypeError):
        _ = CodeFormatter(
            PythonVersion.PY_37,
            custom_formatters=[NOT_SUBCLASS_FORMATTER],
        )


def test_format_code_with_custom_formatter_without_kwargs():
    formatter = CodeFormatter(
        PythonVersion.PY_37,
        custom_formatters=[ADD_COMMENT_FORMATTER],
    )

    formatted_code = formatter.format_code('x = 1\ny = 2')

    assert formatted_code == '# a comment\nx = 1\ny = 2' + '\n'


def test_format_code_with_custom_formatter_with_kwargs():
    formatter = CodeFormatter(
        PythonVersion.PY_37,
        custom_formatters=[ADD_LICENSE_FORMATTER],
        custom_formatters_kwargs={'license_file': EXAMPLE_LICENSE_FILE},
    )

    formatted_code = formatter.format_code('x = 1\ny = 2')

    assert (
        formatted_code
        == """# MIT License
# 
# Copyright (c) 2023 Blah-blah
# 
x = 1
y = 2
"""
    )


def test_format_code_with_two_custom_formatters():
    formatter = CodeFormatter(
        PythonVersion.PY_37,
        custom_formatters=[
            ADD_COMMENT_FORMATTER,
            ADD_LICENSE_FORMATTER,
        ],
        custom_formatters_kwargs={'license_file': EXAMPLE_LICENSE_FILE},
    )

    formatted_code = formatter.format_code('x = 1\ny = 2')

    assert (
        formatted_code
        == """# MIT License
# 
# Copyright (c) 2023 Blah-blah
# 
# a comment
x = 1
y = 2
"""
    )
