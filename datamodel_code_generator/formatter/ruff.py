from typing import Any, ClassVar, Dict

from .base import BaseCodeFormatter


class RuffCodeFormatter(BaseCodeFormatter):
    formatter_name: ClassVar[str] = 'ruff'

    def __init__(self, formatter_kwargs: Dict[str, Any]) -> None:
        super().__init__(formatter_kwargs=formatter_kwargs)

    def apply(self, code: str) -> str:
        pass
