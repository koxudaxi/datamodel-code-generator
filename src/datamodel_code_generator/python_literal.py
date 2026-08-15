"""Helpers for rendering Python source literals."""

from __future__ import annotations

import keyword
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


_INTERNAL_TYPE_EXPRESSION_TOKEN = object()
_INTERNAL_TYPE_EXPRESSION_ERROR = "internal type expressions must be created by the parser"


class _InternalTypeExpression(str):  # noqa: FURB189 - must remain string-compatible for template contexts.
    """A parser-owned Python type expression.

    Public template data never creates this value.  The private token makes the
    raw-expression path unavailable to ordinary API and JSON template data.
    """

    code: str
    __slots__ = ("code",)

    def __new__(cls, value: str, token: object, code: str | None = None) -> Self:
        if token is not _INTERNAL_TYPE_EXPRESSION_TOKEN:
            raise TypeError(_INTERNAL_TYPE_EXPRESSION_ERROR)
        obj = super().__new__(cls, value)
        obj.code = value if code is None else code
        return obj


def _make_internal_type_expression(value: str, code: str | None = None) -> _InternalTypeExpression:
    """Mark a parser-generated type hint as safe to emit as Python source."""
    return _InternalTypeExpression(value, _INTERNAL_TYPE_EXPRESSION_TOKEN, code)


def _normalize_string(value: str) -> str:
    """Return the underlying built-in string without invoking subclass overrides."""
    return value if type(value) is str else str.__str__(value)  # noqa: PLC2801 - bypass untrusted subclass overrides


def _stringify_untrusted_value(value: object) -> str:
    """Stringify public data once, returning an exact built-in ``str``."""
    return _normalize_string(str(value))


def _normalized_safe_public_type_name(value: object) -> str | None:
    """Return a normalized bare or dotted public type name when safe.

    Built-in scalar and TypedDict template settings accept simple names such as
    ``str`` and ``datetime.date``.  More expressive type syntax belongs to the
    parser-owned boundary above; accepting it here would require parsing source
    at runtime and would make this public extension point an execution sink.
    """
    if not isinstance(value, str):
        return None
    normalized_value = _normalize_string(value)
    if normalized_value and all(
        part.isidentifier() and not keyword.iskeyword(part) for part in normalized_value.split(".")
    ):
        return normalized_value
    return None


def is_safe_public_type_name(value: object) -> bool:
    """Return whether public data is a bare or dotted Python identifier."""
    return _normalized_safe_public_type_name(value) is not None


def represent_untrusted_public_type_name(value: Any) -> str:
    """Render a public type name without admitting executable source syntax."""
    if isinstance(value, str):
        if normalized_value := _normalized_safe_public_type_name(value):
            return normalized_value
        return represent_untrusted_python_value(_normalize_string(value))
    return represent_untrusted_python_value(value)


def represent_python_value(value: Any) -> str:  # noqa: PLR0911
    """Render a value as a Python expression safe for generated source."""
    match value:
        case PythonCode():
            return value.code
        case float() if isnan(value):
            return "float('nan')"
        case float() if not isfinite(value):
            return "float('inf')" if value > 0 else "float('-inf')"
        case dict():
            rendered_items = ", ".join(
                f"{represent_python_value(key)}: {represent_python_value(item)}" for key, item in value.items()
            )
            return f"{{{rendered_items}}}"
        case list():
            return "[" + ", ".join(represent_python_value(item) for item in value) + "]"
        case tuple():
            rendered_items = ", ".join(represent_python_value(item) for item in value)
            trailing_comma = "," if len(value) == 1 else ""
            return f"({rendered_items}{trailing_comma})"
        case set() if not value:
            return "set()"
        case set():
            sorted_items = sorted(value, key=lambda item: (type(item).__name__, repr(item)))
            return "{" + ", ".join(represent_python_value(item) for item in sorted_items) + "}"
    return repr(value)


def represent_untrusted_python_value(value: Any) -> str:  # noqa: PLR0911
    """Render data from a public template context as a non-executing Python literal.

    Unlike :func:`represent_python_value`, this deliberately does not preserve
    ``PythonCode``.  Built-in templates call this at extension-data boundaries;
    parser-owned source fragments remain separate from those boundaries.
    """
    if value is None or type(value) is bool:
        return represent_python_value(value)
    if type(value) is int or type(value) is float:
        return represent_python_value(value)
    if isinstance(value, int):
        return represent_python_value(int.__int__(value))  # noqa: PLC2801 - bypass untrusted subclass overrides
    if isinstance(value, float):
        return represent_python_value(float.__float__(value))  # noqa: PLC2801 - bypass untrusted subclass overrides
    if isinstance(value, str):
        return repr(_normalize_string(value))
    if isinstance(value, dict):
        rendered_items = ", ".join(
            f"{represent_untrusted_python_value(key)}: {represent_untrusted_python_value(item)}"
            for key, item in value.items()
        )
        return f"{{{rendered_items}}}"
    if isinstance(value, list):
        return "[" + ", ".join(represent_untrusted_python_value(item) for item in value) + "]"
    if isinstance(value, tuple):
        rendered_items = ", ".join(represent_untrusted_python_value(item) for item in value)
        trailing_comma = "," if len(value) == 1 else ""
        return f"({rendered_items}{trailing_comma})"
    if isinstance(value, set):
        if not value:
            return "set()"
        rendered_items = [(type(item).__name__, represent_untrusted_python_value(item)) for item in value]
        rendered_items.sort()
        return "{" + ", ".join(item for _, item in rendered_items) + "}"
    return repr(_stringify_untrusted_value(value))
