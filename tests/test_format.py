import sys

from datamodel_code_generator.format import PythonVersion


def test_python_version():
    """Ensure that the python version used for the tests is properly listed"""

    _ = PythonVersion("{}.{}".format(*sys.version_info[:2]))
