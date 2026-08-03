"""Private transport for input-model schemas and structured type expressions."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datamodel_code_generator._python_type_annotation import PythonTypeExpr

_PYTHON_TYPE_TOKEN_PREFIX = "<datamodel-code-generator-python-type:"  # noqa: S105


@dataclass(frozen=True, slots=True)
class LoadedInputModelSchema(Mapping[str, object]):
    """An internal schema view with parser-owned expression identities."""

    schema: dict[str, object]
    python_type_expressions: Mapping[str, PythonTypeExpr]

    def __getitem__(self, key: str) -> object:
        return self.schema[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.schema)

    def __len__(self) -> int:
        return len(self.schema)

    @property
    def name(self) -> str:
        """Preserve the historical header name of the former JSON text input."""
        return "<stdin>"


class PythonTypeExpressionCollector:
    """Intern expressions behind per-load tokens that survive schema rewrites."""

    __slots__ = ("_expressions", "_nonce", "_tokens")

    def __init__(self) -> None:
        self._nonce: str | None = None
        self._expressions: dict[str, PythonTypeExpr] = {}
        self._tokens: dict[PythonTypeExpr, str] = {}

    def add(self, expression: PythonTypeExpr) -> str:
        """Return one stable token for an equal immutable expression."""
        if token := self._tokens.get(expression):
            return token
        if (nonce := self._nonce) is None:
            from secrets import token_hex  # noqa: PLC0415

            self._nonce = nonce = token_hex(16)
        token = f"{_PYTHON_TYPE_TOKEN_PREFIX}{nonce}:{len(self._expressions)}>"
        self._tokens[expression] = token
        self._expressions[token] = expression
        return token

    def loaded_schema(self, schema: dict[str, object]) -> LoadedInputModelSchema:
        """Freeze the surviving token table and release the build-only reverse map."""
        used_tokens = _collect_python_type_tokens(schema)
        expressions = {token: expression for token, expression in self._expressions.items() if token in used_tokens}
        return LoadedInputModelSchema(schema, MappingProxyType(expressions))


def is_python_type_token(value: object) -> bool:
    """Return whether a value belongs to the private, deliberately invalid syntax."""
    return isinstance(value, str) and value.startswith(_PYTHON_TYPE_TOKEN_PREFIX) and value.endswith(">")


def _collect_python_type_tokens(value: object) -> set[str]:
    """Collect only tokens retained by the final transformed schema."""
    tokens: set[str] = set()
    pending = [value]
    while pending:
        match pending.pop():
            case Mapping() as mapping:
                if is_python_type_token(token := mapping.get("x-python-type")):
                    tokens.add(token)
                pending.extend(mapping.values())
            case list() | tuple() as sequence:
                pending.extend(sequence)
            case _:
                continue
    return tokens


def externalize_python_type_token(value: Any, expressions: Mapping[str, PythonTypeExpr] | None) -> Any:
    """Render a private token only when data crosses into generated output metadata."""
    if expressions is None or not isinstance(value, str) or (expression := expressions.get(value)) is None:
        return value

    from datamodel_code_generator._python_type_annotation import render_python_type_expr  # noqa: PLC0415

    return render_python_type_expr(expression)


__all__ = [
    "LoadedInputModelSchema",
    "PythonTypeExpressionCollector",
    "externalize_python_type_token",
    "is_python_type_token",
]
