"""Helpers for rendering Python source literals."""

from __future__ import annotations

from math import isfinite, isnan
from typing import Any

from typing_extensions import Self


class PythonCode(str):  # noqa: FURB189 - must behave as str for regex consumers.
    """Python expression rendered without extra quoting."""

    code: str
    __slots__ = ("code",)

    def __new__(cls, code: str, value: str | None = None) -> Self:
        """Initialize with a raw Python expression and optional string value."""
        obj = super().__new__(cls, code if value is None else value)
        obj.code = code
        return obj

    def __repr__(self) -> str:
        """Render the wrapped expression."""
        return self.code


def represent_python_value(value: Any) -> str:  # noqa: PLR0911
    """Render a value as a Python expression safe for generated source."""
    if isinstance(value, PythonCode):
        return value.code
    if isinstance(value, float):
        if isnan(value):
            return "float('nan')"
        if not isfinite(value):
            return "float('inf')" if value > 0 else "float('-inf')"
    if isinstance(value, dict):
        rendered_items = ", ".join(
            f"{represent_python_value(key)}: {represent_python_value(item)}" for key, item in value.items()
        )
        return f"{{{rendered_items}}}"
    if isinstance(value, list):
        return "[" + ", ".join(represent_python_value(item) for item in value) + "]"
    if isinstance(value, tuple):
        rendered_items = ", ".join(represent_python_value(item) for item in value)
        trailing_comma = "," if len(value) == 1 else ""
        return f"({rendered_items}{trailing_comma})"
    if isinstance(value, set):
        if not value:
            return "set()"
        sorted_items = sorted(value, key=lambda item: (type(item).__name__, repr(item)))
        return "{" + ", ".join(represent_python_value(item) for item in sorted_items) + "}"
    return repr(value)
