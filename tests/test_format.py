import sys

import pytest

from datamodel_code_generator.format import CodeFormatter, PythonVersion


def test_python_version():
    """Ensure that the python version used for the tests is properly listed"""

    _ = PythonVersion("{}.{}".format(*sys.version_info[:2]))


@pytest.mark.parametrize(
    ("skip_string_normalization", "expected_output"),
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

    assert formatted_code == expected_output + "\n"
