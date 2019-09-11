from typing import Dict

import black
from datamodel_code_generator import PythonVersion
from isort import SortImports

BLACK_PYTHON_VERSION: Dict[PythonVersion, black.TargetVersion] = {
    PythonVersion.PY_36: black.TargetVersion.PY36,
    PythonVersion.PY_37: black.TargetVersion.PY37,
    PythonVersion.PY_38: black.TargetVersion.PY38,
}


def format_code(code: str, python_version: PythonVersion) -> str:
    code = apply_black(code, python_version)
    return apply_isort(code)


def apply_black(code: str, python_version: PythonVersion) -> str:

    return black.format_str(
        code,
        mode=black.FileMode(
            target_versions={BLACK_PYTHON_VERSION[python_version]},
            string_normalization=False,
        ),
    )


def apply_isort(code: str) -> str:
    return SortImports(file_contents=code).output
