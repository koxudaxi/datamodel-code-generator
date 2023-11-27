from pathlib import Path
from typing import Any, ClassVar, Dict

import isort

from .base import BaseCodeFormatter


class IsortCodeFormatter(BaseCodeFormatter):
    formatter_name: ClassVar[str] = 'isort'

    def __init__(self, formatter_kwargs: Dict[str, Any]) -> None:
        super().__init__(formatter_kwargs=formatter_kwargs)

        if 'settings_path' not in self.formatter_kwargs:
            settings_path = Path().resolve()
        else:
            settings_path = Path(self.formatter_kwargs['settings_path'])

        self.settings_path: str = str(settings_path)
        self.isort_config_kwargs: Dict[str, Any] = {}

        if 'known_third_party' in self.formatter_kwargs:
            self.isort_config_kwargs['known_third_party'] = self.formatter_kwargs[
                'known_third_party'
            ]

        if isort.__version__.startswith('4.'):
            self.isort_config = None
        else:
            self.isort_config = isort.Config(
                settings_path=self.settings_path, **self.isort_config_kwargs
            )

    if isort.__version__.startswith('4.'):

        def apply(self, code: str) -> str:
            return isort.SortImports(
                file_contents=code,
                settings_path=self.settings_path,
                **self.isort_config_kwargs,
            ).output

    else:

        def apply(self, code: str) -> str:
            return isort.code(code, config=self.isort_config)
