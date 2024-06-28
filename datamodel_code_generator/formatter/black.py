from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Dict
from warnings import warn

import black

from datamodel_code_generator.format import (
    BLACK_PYTHON_VERSION,
    PythonVersion,
    black_find_project_root,
)
from datamodel_code_generator.util import load_toml

from .base import BaseCodeFormatter


class BlackCodeFormatter(BaseCodeFormatter):
    formatter_name: ClassVar[str] = 'black'

    def __init__(self, formatter_kwargs: Dict[str, Any]) -> None:
        super().__init__(formatter_kwargs=formatter_kwargs)

        if 'settings_path' not in self.formatter_kwargs:
            settings_path = Path().resolve()
        else:
            settings_path = Path(self.formatter_kwargs['settings_path'])

        wrap_string_literal = self.formatter_kwargs.get('wrap_string_literal', None)
        skip_string_normalization = self.formatter_kwargs.get(
            'skip_string_normalization', True
        )

        config = self._load_config(settings_path)

        black_kwargs: Dict[str, Any] = {}
        if wrap_string_literal is not None:
            experimental_string_processing = wrap_string_literal
        else:
            experimental_string_processing = config.get(
                'experimental-string-processing'
            )

        if experimental_string_processing is not None:  # pragma: no cover
            if black.__version__.startswith('19.'):  # type: ignore
                warn(
                    f"black doesn't support `experimental-string-processing` option"  # type: ignore
                    f' for wrapping string literal in {black.__version__}'
                )
            else:
                black_kwargs[
                    'experimental_string_processing'
                ] = experimental_string_processing

        if TYPE_CHECKING:
            self.black_mode: black.FileMode
        else:
            self.black_mode = black.FileMode(
                target_versions={
                    BLACK_PYTHON_VERSION[
                        formatter_kwargs.get('target-version', PythonVersion.PY_37)
                    ]
                },
                line_length=config.get('line-length', black.DEFAULT_LINE_LENGTH),
                string_normalization=not skip_string_normalization
                or not config.get('skip-string-normalization', True),
                **formatter_kwargs,
            )

    @staticmethod
    def _load_config(settings_path: Path) -> Dict[str, Any]:
        root = black_find_project_root((settings_path,))
        path = root / 'pyproject.toml'

        if path.is_file():
            pyproject_toml = load_toml(path)
            config = pyproject_toml.get('tool', {}).get('black', {})
        else:
            config = {}

        return config

    def apply(self, code: str) -> str:
        return black.format_str(
            code,
            mode=self.black_mode,
        )
