"""Immutable expressions and a raw-text codec for Python type annotations."""

from __future__ import annotations

import ast
import keyword
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class PythonTypeExpr:
    """Base class for immutable semantic Python type expressions."""

    __slots__ = ()

    def __deepcopy__(self, _memo: dict[int, object]) -> PythonTypeExpr:
        """Share immutable expressions across copied model graphs."""
        return self


def _is_python_identifier(value: str) -> bool:
    return value.isidentifier() and not keyword.iskeyword(value)


@dataclass(frozen=True, slots=True)
class PythonTypeName(PythonTypeExpr):
    """One unqualified Python name."""

    value: str

    def __post_init__(self) -> None:
        if self.value != "None" and not _is_python_identifier(self.value):
            msg = f"Python type name must be one identifier: {self.value!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PythonTypeQualifiedName(PythonTypeExpr):
    """A syntactic dotted name parsed from external annotation text."""

    parts: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.parts or not all(map(_is_python_identifier, self.parts)):
            msg = f"Python qualified type name must contain identifiers: {self.parts!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PythonTypeRuntimeSymbol(PythonTypeExpr):
    """An exact module and qualified-name identity supplied by a runtime producer."""

    module: str
    qualname_parts: tuple[str, ...]

    def __post_init__(self) -> None:
        module_parts = self.module.split(".") if self.module else ()
        if (
            not self.qualname_parts
            or not all(map(_is_python_identifier, self.qualname_parts))
            or not all(map(_is_python_identifier, module_parts))
        ):
            msg = f"Invalid runtime Python type identity: {self.module!r}, {self.qualname_parts!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PythonTypeOpaqueText(PythonTypeExpr):
    """Text retained only for a future runtime or forward-reference boundary."""

    value: str


@dataclass(frozen=True, slots=True)
class PythonTypeSubscript(PythonTypeExpr):
    """A subscripted type expression such as ``list[str]``."""

    base: PythonTypeExpr
    arguments: tuple[PythonTypeExpr, ...]


@dataclass(frozen=True, slots=True)
class PythonTypeUnion(PythonTypeExpr):
    """A union rendered with the ``|`` spelling."""

    items: tuple[PythonTypeExpr, ...]


@dataclass(frozen=True, slots=True)
class PythonTypeParameterList(PythonTypeExpr):
    """The bracketed positional parameter list inside ``Callable``."""

    items: tuple[PythonTypeExpr, ...]


@dataclass(frozen=True, slots=True)
class PythonTypeTuple(PythonTypeExpr):
    """An explicit tuple expression nested inside an annotation argument."""

    items: tuple[PythonTypeExpr, ...]


@dataclass(frozen=True, slots=True)
class PythonTypeStarred(PythonTypeExpr):
    """One unpacked variadic expression such as ``*Ts``."""

    value: PythonTypeExpr


_LITERAL_VALUE_TYPES = (str, bytes, int, float, bool)


@dataclass(frozen=True, slots=True, eq=False)
class PythonTypeLiteralValue(PythonTypeExpr):
    """A supported literal value rendered with its deterministic ``repr``."""

    value: object

    def __post_init__(self) -> None:
        if self.value is not None and type(self.value) not in _LITERAL_VALUE_TYPES:
            msg = f"Unsupported Python type literal value: {self.value!r}"
            raise ValueError(msg)
        if isinstance(self.value, float) and math.isnan(self.value):
            msg = "NaN is not a supported Python type literal value"
            raise ValueError(msg)

    def __eq__(self, other: object) -> bool:
        """Compare both the literal value and its exact Python type."""
        return (
            isinstance(other, PythonTypeLiteralValue)
            and type(self.value) is type(other.value)
            and self.value == other.value
        )

    def __hash__(self) -> int:
        """Hash consistently with type-sensitive literal equality."""
        return hash((type(self.value), self.value))


@dataclass(frozen=True, slots=True)
class PythonTypeEllipsis(PythonTypeExpr):
    """The ellipsis argument used by ``Callable[..., ReturnType]``."""


_COMMON_TYPE_NAMES = {
    value: PythonTypeName(value)
    for value in (
        "None",
        "Any",
        "Annotated",
        "Callable",
        "Dict",
        "FrozenSet",
        "List",
        "Literal",
        "Mapping",
        "Optional",
        "Sequence",
        "Set",
        "Tuple",
        "Type",
        "Union",
        "bool",
        "bytes",
        "dict",
        "float",
        "frozenset",
        "int",
        "list",
        "object",
        "set",
        "str",
        "tuple",
        "type",
    )
}


def _python_type_name(value: str) -> PythonTypeName:
    return _COMMON_TYPE_NAMES.get(value) or PythonTypeName(value)


def render_python_type_expr(expression: PythonTypeExpr) -> str:  # noqa: PLR0911
    """Render an expression with stable formatting and no AST round trip."""
    match expression:
        case PythonTypeName() | PythonTypeOpaqueText():
            return expression.value
        case PythonTypeQualifiedName():
            return ".".join(expression.parts)
        case PythonTypeRuntimeSymbol():
            name = ".".join(expression.qualname_parts)
            return f"{expression.module}.{name}" if expression.module else name
        case PythonTypeSubscript():
            rendered_base = render_python_type_expr(expression.base)
            if isinstance(expression.base, PythonTypeUnion):
                rendered_base = f"({rendered_base})"
            arguments = ", ".join(map(render_python_type_expr, expression.arguments)) or "()"
            return f"{rendered_base}[{arguments}]"
        case PythonTypeUnion():
            return " | ".join(map(render_python_type_expr, expression.items))
        case PythonTypeParameterList():
            return f"[{', '.join(map(render_python_type_expr, expression.items))}]"
        case PythonTypeTuple():
            items = ", ".join(map(render_python_type_expr, expression.items))
            return f"({items}{',' if len(expression.items) == 1 else ''})"
        case PythonTypeStarred():
            value = render_python_type_expr(expression.value)
            return f"*({value})" if isinstance(expression.value, PythonTypeUnion) else f"*{value}"
        case PythonTypeLiteralValue():
            if isinstance(expression.value, float) and math.isinf(expression.value):
                return "1e309" if expression.value > 0 else "-1e309"
            return repr(expression.value)
        case PythonTypeEllipsis():
            return "..."
    msg = f"Unsupported Python type expression: {type(expression).__name__}"
    raise TypeError(msg)


def _qualified_name_parts(node: ast.expr) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return tuple(reversed(parts))


class _InvalidPythonTypeAnnotationError(ValueError):
    pass


_LEGACY_STARRED_SENTINEL_BASE = "__datamodel_code_generator_starred"
_OPENING_DELIMITERS = {"(": ")", "[": "]", "{": "}"}


def _legacy_starred_parse_text(type_str: str) -> tuple[str, str] | None:
    """Rewrite only version-invariant variadic punctuation for Python 3.10.

    ``generate_tokens`` belongs to the running Python, not the requested output
    version.  It must never be extended here to validate or interpret target
    grammar; this compatibility pass recognizes only delimiter depth and a
    prefix ``*`` in the annotation subset shared by supported runtimes.
    """
    import tokenize  # noqa: PLC0415  # Avoid tokenizer cost outside the Python 3.10 variadic fallback.
    from io import StringIO  # noqa: PLC0415

    try:
        tokens = list(tokenize.generate_tokens(StringIO(type_str).readline))
    except tokenize.TokenError as error:
        raise _InvalidPythonTypeAnnotationError from error

    ignored_token_types = frozenset({
        tokenize.COMMENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.INDENT,
        tokenize.NEWLINE,
        tokenize.NL,
    })
    identifiers = {token_info.string for token_info in tokens if token_info.type == tokenize.NAME}
    sentinel = _LEGACY_STARRED_SENTINEL_BASE
    while sentinel in identifiers:
        sentinel += "_"

    result: list[tuple[int, str]] = []
    delimiter_stack: list[str] = []
    starred_depths: list[int] = []
    previous_significant = ""
    replaced = False

    for token_info in tokens:
        token_type, lexeme = token_info.type, token_info.string
        if lexeme in {",", ")", "]", "}"}:
            while starred_depths and starred_depths[-1] == len(delimiter_stack):
                result.append((tokenize.OP, ")"))
                starred_depths.pop()

        # Do not infer target-version expressions from runtime-specific token
        # streams. Only the outer, cross-version variadic marker is rewritten.
        is_variadic_star = lexeme == "*" and "]" in delimiter_stack and previous_significant in {"(", "[", ","}
        if is_variadic_star:
            result.extend(((tokenize.NAME, sentinel), (tokenize.OP, "(")))
            starred_depths.append(len(delimiter_stack))
            replaced = True
        else:
            result.append((token_type, lexeme))

        if lexeme in _OPENING_DELIMITERS:
            delimiter_stack.append(_OPENING_DELIMITERS[lexeme])
        elif lexeme in {")", "]", "}"} and delimiter_stack and lexeme == delimiter_stack[-1]:
            delimiter_stack.pop()

        if token_type not in ignored_token_types and token_type != tokenize.ENDMARKER:
            previous_significant = lexeme

    return (tokenize.untokenize(result), sentinel) if replaced else None


class _LegacyStarredRestorer(ast.NodeTransformer):
    """Restore compatibility-parser sentinel calls to native ``ast.Starred`` nodes."""

    def __init__(self, sentinel: str) -> None:
        self.sentinel = sentinel

    def visit_Call(self, node: ast.Call) -> ast.AST:
        """Restore only the exact sentinel call shape emitted by the tokenizer."""
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == self.sentinel
            and len(node.args) == 1
            and not node.keywords
        ):
            return ast.copy_location(ast.Starred(value=self.visit(node.args[0]), ctx=ast.Load()), node)
        return self.generic_visit(node)


def _parse_python_type_annotation_ast(type_str: str) -> ast.expr:
    try:
        # feature_version is a best-effort grammar switch in the running AST
        # implementation. The strict node codec below, not this call alone,
        # defines the version-independent annotation subset we accept.
        return ast.parse(type_str, mode="eval", feature_version=(3, 10)).body
    except SyntaxError:
        if (legacy_parse := _legacy_starred_parse_text(type_str)) is None:
            raise
        rewritten, sentinel = legacy_parse
        expression = ast.parse(rewritten, mode="eval", feature_version=(3, 10)).body
        restored = _LegacyStarredRestorer(sentinel).visit(expression)
        if not isinstance(restored, ast.expr):  # pragma: no cover
            raise _InvalidPythonTypeAnnotationError from None
        return restored


def _python_type_union_from_ast(node: ast.BinOp) -> PythonTypeUnion:
    """Convert and flatten a bit-or tree iteratively in source order."""
    pending: list[ast.expr] = [node]
    items: list[PythonTypeExpr] = []
    while pending:
        current = pending.pop()
        if isinstance(current, ast.BinOp) and isinstance(current.op, ast.BitOr):
            pending.extend((current.right, current.left))
        else:
            items.append(_python_type_expr_from_ast(current, allow_literal=False))
    return PythonTypeUnion(tuple(items))


def _python_type_expr_from_ast(  # noqa: PLR0911, PLR0912
    node: ast.expr,
    *,
    allow_literal: bool,
) -> PythonTypeExpr:
    match node:
        case ast.Name(id=name):
            return _python_type_name(name)
        case ast.Attribute():
            if (parts := _qualified_name_parts(node)) is not None:
                return PythonTypeQualifiedName(parts)
        case ast.Subscript(value=value, slice=slice_node):
            base = _python_type_expr_from_ast(value, allow_literal=False)
            if isinstance(slice_node, ast.Tuple):
                arguments = tuple(_python_type_expr_from_ast(item, allow_literal=True) for item in slice_node.elts)
            else:
                arguments = (_python_type_expr_from_ast(slice_node, allow_literal=True),)
            return PythonTypeSubscript(base, arguments)
        case ast.List(elts=items) if allow_literal:
            return PythonTypeParameterList(
                tuple(_python_type_expr_from_ast(item, allow_literal=True) for item in items)
            )
        case ast.Tuple(elts=items) if allow_literal:
            return PythonTypeTuple(tuple(_python_type_expr_from_ast(item, allow_literal=True) for item in items))
        case ast.Starred(value=value) if allow_literal:
            return PythonTypeStarred(_python_type_expr_from_ast(value, allow_literal=False))
        case ast.BinOp(op=ast.BitOr()):
            return _python_type_union_from_ast(node)
        case ast.Constant(value=None):
            return _python_type_name("None")
        case ast.Constant(value=value) if allow_literal and value is Ellipsis:
            return PythonTypeEllipsis()
        case ast.Constant(value=value) if allow_literal and isinstance(value, _LITERAL_VALUE_TYPES):
            return PythonTypeLiteralValue(value)
        case ast.UnaryOp(op=ast.UAdd() | ast.USub() as operator, operand=ast.Constant(value=value)) if (
            allow_literal and type(value) in {int, float}
        ):
            return PythonTypeLiteralValue(+value if isinstance(operator, ast.UAdd) else -value)
    raise _InvalidPythonTypeAnnotationError


@lru_cache(maxsize=1024)
def parse_python_type_annotation(type_str: str) -> PythonTypeExpr | None:
    """Parse the supported Python annotation grammar at a raw-text boundary."""
    try:
        node = _parse_python_type_annotation_ast(type_str)
        return _python_type_expr_from_ast(node, allow_literal=False)
    except (SyntaxError, UnicodeError, ValueError, RecursionError, _InvalidPythonTypeAnnotationError):
        return None


def python_type_expr_base_name(expression: PythonTypeExpr) -> str:
    """Return the terminal base name of an annotation expression."""
    if isinstance(expression, PythonTypeSubscript):
        return python_type_expr_base_name(expression.base)
    if isinstance(expression, PythonTypeName):
        return expression.value
    if isinstance(expression, PythonTypeQualifiedName):
        return expression.parts[-1]
    if isinstance(expression, PythonTypeRuntimeSymbol):
        return expression.qualname_parts[-1]
    return ""


def python_type_expr_arguments(expression: PythonTypeExpr) -> tuple[PythonTypeExpr, ...]:
    """Return top-level generic or union arguments."""
    if isinstance(expression, PythonTypeSubscript):
        return expression.arguments
    if isinstance(expression, PythonTypeUnion):
        return expression.items
    return ()


def iter_python_type_expr_qualified_names(expression: PythonTypeExpr) -> Iterator[str]:
    """Yield dotted syntactic and runtime names in stable traversal order."""
    match expression:
        case PythonTypeQualifiedName():
            yield ".".join(expression.parts)
        case PythonTypeRuntimeSymbol():
            name = ".".join(expression.qualname_parts)
            yield f"{expression.module}.{name}" if expression.module else name
        case PythonTypeSubscript():
            yield from iter_python_type_expr_qualified_names(expression.base)
            for argument in expression.arguments:
                yield from iter_python_type_expr_qualified_names(argument)
        case PythonTypeStarred():
            yield from iter_python_type_expr_qualified_names(expression.value)
        case PythonTypeUnion() | PythonTypeParameterList() | PythonTypeTuple():
            for item in expression.items:
                yield from iter_python_type_expr_qualified_names(item)


def rewrite_python_type_expr(  # noqa: PLR0911
    expression: PythonTypeExpr,
    transform_leaf: Callable[[PythonTypeExpr], PythonTypeExpr],
) -> PythonTypeExpr:
    """Rewrite leaves while sharing every unchanged immutable subtree."""
    match expression:
        case PythonTypeSubscript():
            base = rewrite_python_type_expr(expression.base, transform_leaf)
            arguments = tuple(rewrite_python_type_expr(item, transform_leaf) for item in expression.arguments)
            if base is expression.base and all(
                rewritten is original for rewritten, original in zip(arguments, expression.arguments, strict=True)
            ):
                return expression
            return PythonTypeSubscript(base, arguments)
        case PythonTypeUnion():
            items = tuple(rewrite_python_type_expr(item, transform_leaf) for item in expression.items)
            if all(rewritten is original for rewritten, original in zip(items, expression.items, strict=True)):
                return expression
            return PythonTypeUnion(items)
        case PythonTypeParameterList():
            items = tuple(rewrite_python_type_expr(item, transform_leaf) for item in expression.items)
            if all(rewritten is original for rewritten, original in zip(items, expression.items, strict=True)):
                return expression
            return PythonTypeParameterList(items)
        case PythonTypeTuple():
            items = tuple(rewrite_python_type_expr(item, transform_leaf) for item in expression.items)
            if all(rewritten is original for rewritten, original in zip(items, expression.items, strict=True)):
                return expression
            return PythonTypeTuple(items)
        case PythonTypeStarred():
            value = rewrite_python_type_expr(expression.value, transform_leaf)
            return expression if value is expression.value else PythonTypeStarred(value)
    return transform_leaf(expression)


__all__ = [
    "PythonTypeEllipsis",
    "PythonTypeExpr",
    "PythonTypeLiteralValue",
    "PythonTypeName",
    "PythonTypeOpaqueText",
    "PythonTypeParameterList",
    "PythonTypeQualifiedName",
    "PythonTypeRuntimeSymbol",
    "PythonTypeStarred",
    "PythonTypeSubscript",
    "PythonTypeTuple",
    "PythonTypeUnion",
    "iter_python_type_expr_qualified_names",
    "parse_python_type_annotation",
    "python_type_expr_arguments",
    "python_type_expr_base_name",
    "render_python_type_expr",
    "rewrite_python_type_expr",
]
