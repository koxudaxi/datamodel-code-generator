from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import black
import isort
import toml


class PythonVersion(Enum):
    PY_36 = '3.6'
    PY_37 = '3.7'
    PY_38 = '3.8'
    PY_39 = '3.9'


BLACK_PYTHON_VERSION: Dict[PythonVersion, black.TargetVersion] = {
    v: getattr(black.TargetVersion, f'PY{v.name.split("_")[-1]}')
    for v in PythonVersion
    if hasattr(black.TargetVersion, f'PY{v.name.split("_")[-1]}')
}


def is_supported_in_black(python_version: PythonVersion) -> bool:  # pragma: no cover
    return python_version in BLACK_PYTHON_VERSION


def format_code(
    code: str, python_version: PythonVersion, settings_path: Optional[Path] = None
) -> str:
    if not settings_path:
        settings_path = Path().resolve()
    code = apply_isort(code, settings_path)
    code = apply_black(code, python_version, settings_path)
    return code


def apply_black(code: str, python_version: PythonVersion, settings_path: Path) -> str:
    root = black.find_project_root((settings_path,))
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


def apply_isort(code: str, settings_path: Path) -> str:
    if isort.__version__.startswith('4.'):
        return isort.SortImports(
            file_contents=code, settings_path=str(settings_path)
        ).output
    else:
        return isort.code(code, config=isort.Config(settings_path=str(settings_path)))
