from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Dict

import black

from datamodel_code_generator.util import cached_property

from .base import BaseCodeFormatter


class PythonVersion(Enum):
    PY_36 = '3.6'
    PY_37 = '3.7'
    PY_38 = '3.8'
    PY_39 = '3.9'
    PY_310 = '3.10'
    PY_311 = '3.11'
    PY_312 = '3.12'

    @cached_property
    def _is_py_38_or_later(self) -> bool:  # pragma: no cover
        return self.value not in {self.PY_36.value, self.PY_37.value}  # type: ignore

    @cached_property
    def _is_py_39_or_later(self) -> bool:  # pragma: no cover
        return self.value not in {self.PY_36.value, self.PY_37.value, self.PY_38.value}  # type: ignore

    @cached_property
    def _is_py_310_or_later(self) -> bool:  # pragma: no cover
        return self.value not in {
            self.PY_36.value,
            self.PY_37.value,
            self.PY_38.value,
            self.PY_39.value,
        }  # type: ignore

    @cached_property
    def _is_py_311_or_later(self) -> bool:  # pragma: no cover
        return self.value not in {
            self.PY_36.value,
            self.PY_37.value,
            self.PY_38.value,
            self.PY_39.value,
            self.PY_310.value,
        }  # type: ignore

    @property
    def has_literal_type(self) -> bool:
        return self._is_py_38_or_later

    @property
    def has_union_operator(self) -> bool:  # pragma: no cover
        return self._is_py_310_or_later

    @property
    def has_annotated_type(self) -> bool:
        return self._is_py_39_or_later

    @property
    def has_typed_dict(self) -> bool:
        return self._is_py_38_or_later

    @property
    def has_typed_dict_non_required(self) -> bool:
        return self._is_py_311_or_later


if TYPE_CHECKING:

    class _TargetVersion(Enum):
        ...

    BLACK_PYTHON_VERSION: Dict[PythonVersion, _TargetVersion]
else:
    BLACK_PYTHON_VERSION: Dict[PythonVersion, black.TargetVersion] = {
        v: getattr(black.TargetVersion, f'PY{v.name.split("_")[-1]}')
        for v in PythonVersion
        if hasattr(black.TargetVersion, f'PY{v.name.split("_")[-1]}')
    }


class BlackCodeFormatter(BaseCodeFormatter):
    formatter_name: ClassVar[str] = 'black'

    def __init__(self, formatter_kwargs: Dict[str, Any]) -> None:
        super().__init__(formatter_kwargs=formatter_kwargs)

        if TYPE_CHECKING:
            self.black_mode: black.FileMode
        else:
            self.black_mode = black.FileMode(
                target_versions={
                    BLACK_PYTHON_VERSION[
                        formatter_kwargs.get('target-version', PythonVersion.PY_37)
                    ]
                },
                line_length=formatter_kwargs.get(
                    'line-length', black.DEFAULT_LINE_LENGTH
                ),
                string_normalization=not formatter_kwargs.get(
                    'skip-string-normalization', True
                ),
                **formatter_kwargs,
            )

    def apply(self, code: str) -> str:
        return black.format_str(
            code,
            mode=self.black_mode,
        )
