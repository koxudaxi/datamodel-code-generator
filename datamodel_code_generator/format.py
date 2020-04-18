from enum import Enum
from pathlib import Path
from typing import Dict

import black
import toml
from isort import SortImports


class PythonVersion(Enum):
    PY_36 = '3.6'
    PY_37 = '3.7'
    PY_38 = '3.8'


BLACK_PYTHON_VERSION: Dict[PythonVersion, black.TargetVersion] = {
    PythonVersion.PY_36: black.TargetVersion.PY36,
    PythonVersion.PY_37: black.TargetVersion.PY37,
    PythonVersion.PY_38: black.TargetVersion.PY38,
}


def format_code(code: str, python_version: PythonVersion) -> str:

    code = apply_isort(code)
    code = apply_black(code, python_version)
    return code


def apply_black(code: str, python_version: PythonVersion) -> str:

    root = black.find_project_root((Path().resolve(),))
    path = root / "pyproject.toml"
    if path.is_file():
        value = str(path)
        pyproject_toml = toml.load(value)
        config = pyproject_toml.get("tool", {}).get("black", {})
    else:
        config = {}

    return black.format_str(
        code,
        mode=black.FileMode(
            target_versions={BLACK_PYTHON_VERSION[python_version]},
            line_length=config.get("line-length", black.DEFAULT_LINE_LENGTH),
            string_normalization=not config.get("skip-string-normalization", True),
        ),
    )


def apply_isort(code: str) -> str:
    return SortImports(file_contents=code).output
