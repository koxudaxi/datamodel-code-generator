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

    @property
    def has_literal_type(self) -> bool:
        return self.value >= self.PY_38.value  # type: ignore


BLACK_PYTHON_VERSION: Dict[PythonVersion, black.TargetVersion] = {
    v: getattr(black.TargetVersion, f'PY{v.name.split("_")[-1]}')
    for v in PythonVersion
    if hasattr(black.TargetVersion, f'PY{v.name.split("_")[-1]}')
}


def is_supported_in_black(python_version: PythonVersion) -> bool:  # pragma: no cover
    return python_version in BLACK_PYTHON_VERSION


class CodeFormatter:
    def __init__(
        self, python_version: PythonVersion, settings_path: Optional[Path] = None
    ):
        if not settings_path:
            settings_path = Path().resolve()

        root = black.find_project_root((settings_path,))
        path = root / "pyproject.toml"
        if path.is_file():
            value = str(path)
            pyproject_toml = toml.load(value)
            config = pyproject_toml.get("tool", {}).get("black", {})
        else:
            config = {}
        self.back_mode = black.FileMode(
            target_versions={BLACK_PYTHON_VERSION[python_version]},
            line_length=config.get("line-length", black.DEFAULT_LINE_LENGTH),
            string_normalization=not config.get("skip-string-normalization", True),
        )

        self.settings_path: str = str(settings_path)
        if isort.__version__.startswith('4.'):
            self.isort_config = None
        else:
            self.isort_config = isort.Config(settings_path=self.settings_path)

    def format_code(self, code: str,) -> str:
        code = self.apply_isort(code)
        code = self.apply_black(code)
        return code

    def apply_black(self, code: str) -> str:
        return black.format_str(code, mode=self.back_mode,)

    if isort.__version__.startswith('4.'):

        def apply_isort(self, code: str) -> str:
            return isort.SortImports(
                file_contents=code, settings_path=self.settings_path
            ).output

    else:

        def apply_isort(self, code: str) -> str:
            return isort.code(code, config=self.isort_config)
