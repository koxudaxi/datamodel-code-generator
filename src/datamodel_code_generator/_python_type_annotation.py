"""Internal transport codec for structured Python type annotations."""

from __future__ import annotations

import ast
import keyword
import sys
import types
from collections.abc import Callable as ABCCallable
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, Concatenate, Literal, NamedTuple, ParamSpec, Union, get_args, get_origin
from weakref import ReferenceType, ref

from typing_extensions import Self

if TYPE_CHECKING:
    from datamodel_code_generator.imports import Import

PYTHON_LITERAL_ENUM_MEMBER_MARKER = "__datamodel_code_generator_literal_enum_member__"
_MISSING_ATTRIBUTE = object()


class PythonTypeExpr:
    """Base class for immutable semantic Python type expressions."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class PythonTypeName(PythonTypeExpr):
    """One semantic identifier selected from runtime type identity."""

    value: str

    def __post_init__(self) -> None:
        if self.value != "None" and not _is_python_identifier(self.value):
            msg = f"Python type name must be one identifier: {self.value!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PythonTypeQualifiedName(PythonTypeExpr):
    """A dotted runtime identity represented as validated name parts."""

    parts: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.parts or not all(map(_is_python_identifier, self.parts)):
            msg = f"Python qualified type name must contain identifiers: {self.parts!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PythonTypeText(PythonTypeExpr):
    """Opaque text retained only at a runtime string or fallback boundary."""

    value: str


@dataclass(frozen=True, slots=True)
class PythonTypeSubscript(PythonTypeExpr):
    """A subscripted type expression such as ``list[str]``."""

    base: PythonTypeExpr
    arguments: tuple[PythonTypeExpr, ...]


@dataclass(frozen=True, slots=True)
class PythonTypeUnion(PythonTypeExpr):
    """A union rendered with the existing ``|`` spelling."""

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
class PythonTypeLiteralValue(PythonTypeExpr):
    """A literal value rendered with its deterministic ``repr``."""

    value: object


@dataclass(frozen=True, slots=True)
class PythonTypeEllipsis(PythonTypeExpr):
    """The ellipsis argument used by ``Callable[..., ReturnType]``."""


def _is_python_identifier(value: str) -> bool:
    return value.isidentifier() and not keyword.iskeyword(value)


_COMMON_TYPE_NAMES = {
    value: PythonTypeName(value)
    for value in (
        "None",
        "Any",
        "Callable",
        "Literal",
        "Type",
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
    )
}


def _python_type_name(value: str) -> PythonTypeName:
    return _COMMON_TYPE_NAMES.get(value) or PythonTypeName(value)


def _runtime_name_expr(module: str, name: str) -> PythonTypeExpr:
    if module and module not in {"builtins", "typing", "collections.abc"}:
        parts = (*module.split("."), *name.split("."))
        if all(map(_is_python_identifier, parts)):
            return PythonTypeQualifiedName(parts)
        return PythonTypeText(f"{module}.{name}")
    if _is_python_identifier(name) or name == "None":
        return _python_type_name(name)
    return PythonTypeText(name)


def _not_importable_error(module: str, qualname: str, member: str | None) -> ValueError:
    return ValueError(f"Literal enum member is not importable: {module}.{qualname}.{member}")


class LiteralEnumMemberRef(NamedTuple):
    """Importable identity of one enum member transported through JSON Schema."""

    module: str
    qualname_parts: tuple[str, ...]
    member: str

    @classmethod
    def from_enum(cls, value: Enum) -> Self:
        """Build a reference only when the runtime enum is importable by its identity."""
        enum_type = type(value)
        reference = cls._from_parts(enum_type.__module__, enum_type.__qualname__, value.name)
        target: object = sys.modules.get(reference.module, _MISSING_ATTRIBUTE)
        for part in reference.qualname_parts:
            if target is _MISSING_ATTRIBUTE:
                break
            target = getattr(target, "__dict__", {}).get(part, _MISSING_ATTRIBUTE)
        if target is not enum_type:
            raise _not_importable_error(
                reference.module,
                ".".join(reference.qualname_parts),
                reference.member,
            )
        return reference

    @classmethod
    def from_marker_ast(cls, node: ast.Subscript) -> Self | None:
        """Decode the reserved marker, returning None for an ordinary subscript."""
        if not isinstance(node.value, ast.Name) or node.value.id != PYTHON_LITERAL_ENUM_MEMBER_MARKER:
            return None
        match node.slice:
            case ast.Tuple(
                elts=[
                    ast.Constant(value=str() as module),
                    ast.Constant(value=str() as qualname),
                    ast.Constant(value=str() as member),
                ]
            ):
                return cls._from_parts(module, qualname, member)

        msg = "Invalid internal Literal enum member marker"
        raise ValueError(msg)

    @classmethod
    def _from_parts(cls, module: str, qualname: str, member: str | None) -> Self:
        if member is None:
            raise _not_importable_error(module, qualname, member)

        module_parts = module.split(".")
        qualname_parts = qualname.split(".")
        if (
            not module
            or not qualname
            or not all(map(_is_python_identifier, module_parts))
            or not all(map(_is_python_identifier, qualname_parts))
            or not _is_python_identifier(member)
        ):
            raise _not_importable_error(module, qualname, member)
        return cls(module, tuple(qualname_parts), member)

    @property
    def import_path(self) -> str:
        """Return the import path for the outermost enum container."""
        return f"{self.module}.{self.qualname_parts[0]}"

    def to_marker_text(self) -> str:
        """Encode this reference at the existing x-python-type string boundary."""
        qualname = ".".join(self.qualname_parts)
        return f"{PYTHON_LITERAL_ENUM_MEMBER_MARKER}[{self.module!r}, {qualname!r}, {self.member!r}]"


@dataclass(frozen=True, slots=True)
class PythonTypeEnumMember(PythonTypeExpr):
    """An enum member encoded with the existing internal marker spelling."""

    reference: LiteralEnumMemberRef


@dataclass(frozen=True, slots=True)
class PythonTypeEnumMemberAccess(PythonTypeExpr):
    """A decoded enum member access with its importable identity intact."""

    reference: LiteralEnumMemberRef


@dataclass(frozen=True, slots=True)
class BoundPythonTypeAnnotation:
    """A rendered annotation paired with the imports that bind its names."""

    expression: PythonTypeExpr
    rendered: str
    imports: tuple[Import, ...]


def render_python_type_expr(expression: PythonTypeExpr) -> str:
    """Render a Python type expression with stable compatibility formatting."""
    return _render_python_type_expr_uncached(expression)


def _render_python_type_expr_uncached(expression: PythonTypeExpr) -> str:  # noqa: PLR0911
    match expression:
        case PythonTypeName() | PythonTypeText():
            return expression.value
        case PythonTypeQualifiedName():
            return ".".join(expression.parts)
        case PythonTypeSubscript():
            rendered_arguments = ", ".join(
                _render_python_type_expr_uncached(argument) for argument in expression.arguments
            )
            rendered_base = _render_python_type_expr_uncached(expression.base)
            if isinstance(expression.base, PythonTypeUnion):
                rendered_base = f"({rendered_base})"
            return f"{rendered_base}[{rendered_arguments}]"
        case PythonTypeUnion():
            return " | ".join(_render_python_type_expr_uncached(item) for item in expression.items)
        case PythonTypeParameterList():
            return f"[{', '.join(_render_python_type_expr_uncached(item) for item in expression.items)}]"
        case PythonTypeTuple():
            rendered_items = ", ".join(_render_python_type_expr_uncached(item) for item in expression.items)
            return f"({rendered_items}{',' if len(expression.items) == 1 else ''})"
        case PythonTypeLiteralValue():
            return repr(expression.value)
        case PythonTypeEllipsis():
            return "..."
        case PythonTypeEnumMember():
            return expression.reference.to_marker_text()
        case PythonTypeEnumMemberAccess():
            qualname = ".".join(expression.reference.qualname_parts)
            return f"{expression.reference.module}.{qualname}.{expression.reference.member}"
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


def _is_literal_ast_base(node: ast.expr) -> bool:
    parts = _qualified_name_parts(node)
    return parts == ("Literal",) or parts in {("typing", "Literal"), ("typing_extensions", "Literal")}


class _InvalidPythonTypeAnnotationError(ValueError):
    pass


def _python_type_expr_from_ast(  # noqa: PLR0911, PLR0912
    node: ast.expr,
    *,
    allow_literal: bool,
    literal_depth: int = 0,
) -> PythonTypeExpr:
    match node:
        case ast.Name(id=name):
            return _python_type_name(name)
        case ast.Attribute():
            if (parts := _qualified_name_parts(node)) is not None:
                return PythonTypeQualifiedName(parts)
        case ast.Subscript(value=value, slice=slice_node):
            if (enum_member := LiteralEnumMemberRef.from_marker_ast(node)) is not None:
                if not literal_depth:
                    msg = "Internal Literal enum member marker is only valid inside Literal"
                    raise ValueError(msg)
                return PythonTypeEnumMember(enum_member)

            base = _python_type_expr_from_ast(value, allow_literal=False, literal_depth=literal_depth)
            child_literal_depth = literal_depth + int(_is_literal_ast_base(value))
            if isinstance(slice_node, ast.Tuple):
                arguments = tuple(
                    _python_type_expr_from_ast(item, allow_literal=True, literal_depth=child_literal_depth)
                    for item in slice_node.elts
                )
            else:
                arguments = (
                    _python_type_expr_from_ast(
                        slice_node,
                        allow_literal=True,
                        literal_depth=child_literal_depth,
                    ),
                )
            return PythonTypeSubscript(base, arguments)
        case ast.List(elts=items) if allow_literal:
            return PythonTypeParameterList(
                tuple(
                    _python_type_expr_from_ast(item, allow_literal=True, literal_depth=literal_depth) for item in items
                )
            )
        case ast.Tuple(elts=items) if allow_literal:
            return PythonTypeTuple(
                tuple(
                    _python_type_expr_from_ast(item, allow_literal=True, literal_depth=literal_depth) for item in items
                )
            )
        case ast.BinOp(left=left, op=ast.BitOr(), right=right):
            left_expression = _python_type_expr_from_ast(left, allow_literal=False, literal_depth=literal_depth)
            right_expression = _python_type_expr_from_ast(right, allow_literal=False, literal_depth=literal_depth)
            left_items = left_expression.items if isinstance(left_expression, PythonTypeUnion) else (left_expression,)
            right_items = (
                right_expression.items if isinstance(right_expression, PythonTypeUnion) else (right_expression,)
            )
            return PythonTypeUnion((*left_items, *right_items))
        case ast.Constant(value=None):
            return _python_type_name("None")
        case ast.Constant(value=value) if allow_literal and value is Ellipsis:
            return PythonTypeEllipsis()
        case ast.Constant(value=value) if allow_literal and isinstance(value, (str, bytes, int, float, bool)):
            return PythonTypeLiteralValue(value)
        case ast.UnaryOp(op=ast.UAdd() | ast.USub() as operator, operand=ast.Constant(value=value)) if (
            allow_literal and isinstance(value, (int, float))
        ):
            return PythonTypeLiteralValue(+value if isinstance(operator, ast.UAdd) else -value)
    raise _InvalidPythonTypeAnnotationError


@lru_cache(maxsize=1024)
def parse_python_type_annotation(type_str: str) -> PythonTypeExpr | None:
    """Parse the supported annotation grammar once at its raw text boundary."""
    try:
        node = ast.parse(type_str, mode="eval", feature_version=(3, 10)).body
        return _python_type_expr_from_ast(node, allow_literal=False)
    except (SyntaxError, _InvalidPythonTypeAnnotationError):
        return None


def python_type_expr_base_name(expression: PythonTypeExpr) -> str:
    """Return the terminal base name of an annotation expression."""
    if isinstance(expression, PythonTypeSubscript):
        return python_type_expr_base_name(expression.base)
    if isinstance(expression, PythonTypeName):
        return expression.value
    if isinstance(expression, PythonTypeQualifiedName):
        return expression.parts[-1]
    return ""


def python_type_expr_arguments(expression: PythonTypeExpr) -> tuple[PythonTypeExpr, ...]:
    """Return top-level generic or union arguments without reparsing text."""
    if isinstance(expression, (PythonTypeSubscript, PythonTypeUnion)):
        return expression.arguments if isinstance(expression, PythonTypeSubscript) else expression.items
    return ()


def is_union_python_type_expr(expression: PythonTypeExpr) -> bool:
    """Return whether an expression is a union operator, Union, or Optional."""
    return isinstance(expression, PythonTypeUnion) or (
        isinstance(expression, PythonTypeSubscript) and python_type_expr_base_name(expression) in {"Union", "Optional"}
    )


def iter_python_type_expr_names(expression: PythonTypeExpr) -> tuple[str, ...]:
    """Return semantic type names in stable traversal order."""
    names: list[str] = []

    def visit(item: PythonTypeExpr) -> None:
        match item:
            case PythonTypeName():
                names.append(item.value)
                return
            case PythonTypeQualifiedName():
                names.append(item.parts[-1])
                return
            case PythonTypeSubscript():
                visit(item.base)
                for argument in item.arguments:
                    visit(argument)
                return
            case PythonTypeUnion() | PythonTypeParameterList() | PythonTypeTuple():
                for child in item.items:
                    visit(child)

    visit(expression)
    return tuple(names)


def iter_python_type_expr_qualified_names(expression: PythonTypeExpr) -> tuple[str, ...]:
    """Return dotted names in stable traversal order."""
    names: list[str] = []

    def visit(item: PythonTypeExpr) -> None:
        match item:
            case PythonTypeQualifiedName():
                names.append(".".join(item.parts))
                return
            case PythonTypeEnumMemberAccess():
                qualname = ".".join(item.reference.qualname_parts)
                names.append(f"{item.reference.module}.{qualname}.{item.reference.member}")
                return
            case PythonTypeSubscript():
                visit(item.base)
                for argument in item.arguments:
                    visit(argument)
                return
            case PythonTypeUnion() | PythonTypeParameterList() | PythonTypeTuple():
                for child in item.items:
                    visit(child)

    visit(expression)
    return tuple(names)


def map_python_type_expr(
    expression: PythonTypeExpr,
    transform_leaf: ABCCallable[[PythonTypeExpr], PythonTypeExpr],
) -> PythonTypeExpr:
    """Transform semantic leaves while preserving the expression structure."""
    match expression:
        case PythonTypeSubscript():
            return PythonTypeSubscript(
                map_python_type_expr(expression.base, transform_leaf),
                tuple(map_python_type_expr(argument, transform_leaf) for argument in expression.arguments),
            )
        case PythonTypeUnion():
            return PythonTypeUnion(tuple(map_python_type_expr(item, transform_leaf) for item in expression.items))
        case PythonTypeParameterList():
            return PythonTypeParameterList(
                tuple(map_python_type_expr(item, transform_leaf) for item in expression.items)
            )
        case PythonTypeTuple():
            return PythonTypeTuple(tuple(map_python_type_expr(item, transform_leaf) for item in expression.items))
    return transform_leaf(expression)


def _is_union_origin(origin: object) -> bool:
    return origin is Union or origin is getattr(types, "UnionType", None)


def _runtime_leaf_expr(tp: object) -> PythonTypeExpr:
    module = getattr(tp, "__module__", "")
    name = getattr(tp, "__name__", None) or getattr(tp, "__qualname__", None)
    if name is None:
        return PythonTypeText(str(tp).replace("typing.", ""))
    return _runtime_name_expr(module, name)


def _runtime_origin_expr(origin: object) -> PythonTypeExpr:
    name = getattr(origin, "__qualname__", None) or getattr(origin, "__name__", None)
    if name:
        module = getattr(origin, "__module__", "")
        return _runtime_name_expr(module, name)

    origin_text = str(origin)
    rendered = origin_text.replace("typing.", "") if "typing." in origin_text else origin_text
    return _python_type_name(rendered) if _is_python_identifier(rendered) else PythonTypeText(rendered)


def _runtime_simple_expr(tp: object) -> PythonTypeExpr:
    if tp is type(None):
        return _python_type_name("None")
    if get_origin(tp) is not None:
        return PythonTypeText(str(tp).replace("typing.", ""))
    if name := getattr(tp, "__name__", None):
        return _runtime_name_expr("", name)
    return PythonTypeText(str(tp).replace("typing.", ""))


def _python_callable_expr(parameter_expression: PythonTypeExpr, return_type: object) -> PythonTypeExpr:
    return PythonTypeSubscript(
        _python_type_name("Callable"),
        (parameter_expression, _python_type_expr_from_runtime_uncached(return_type)),
    )


def python_callable_expr_from_runtime_args(args: tuple[object, ...]) -> PythonTypeExpr:
    """Build the normalized expression for runtime ``Callable`` arguments."""
    if not args:
        return _python_type_name("Callable")

    if len(args) == 2:  # noqa: PLR2004
        parameters, return_type = args
        if parameters is ...:
            return _python_callable_expr(PythonTypeEllipsis(), return_type)
        match parameters:
            case list() | tuple():
                return _python_callable_expr(
                    PythonTypeParameterList(
                        tuple(_python_type_expr_from_runtime_uncached(parameter) for parameter in parameters)
                    ),
                    return_type,
                )
        if isinstance(parameters, ParamSpec) or get_origin(parameters) is Concatenate:
            return _python_callable_expr(
                _python_type_expr_from_runtime_uncached(parameters),
                return_type,
            )

    *parameters, return_type = args
    return _python_callable_expr(
        PythonTypeParameterList(tuple(_python_type_expr_from_runtime_uncached(parameter) for parameter in parameters)),
        return_type,
    )


def python_type_expr_from_runtime(tp: object) -> PythonTypeExpr:
    """Convert a runtime typing object to the full annotation transport IR."""
    return _python_type_expr_from_runtime_uncached(tp)


def _python_type_expr_from_runtime_uncached(tp: object) -> PythonTypeExpr:  # noqa: PLR0911
    if tp is type(None):
        return _python_type_name("None")
    if tp is ...:
        return PythonTypeEllipsis()

    origin = get_origin(tp)
    args = get_args(tp)
    if origin is None:
        return _runtime_leaf_expr(tp)
    if origin is ABCCallable:
        return python_callable_expr_from_runtime_args(args)
    if _is_union_origin(origin):
        return PythonTypeUnion(tuple(_python_type_expr_from_runtime_uncached(argument) for argument in args))
    if origin is Annotated:
        if args:
            return _python_type_expr_from_runtime_uncached(args[0])
        return PythonTypeText(str(tp).replace("typing.", ""))  # pragma: no cover
    if origin is Literal:
        literal_arguments = tuple(
            PythonTypeEnumMember(LiteralEnumMemberRef.from_enum(argument))
            if isinstance(argument, Enum)
            else PythonTypeLiteralValue(argument)
            for argument in args
        )
        return PythonTypeSubscript(_python_type_name("Literal"), literal_arguments)
    if origin is type:
        if args:
            return PythonTypeSubscript(
                _python_type_name("Type"),
                (_python_type_expr_from_runtime_uncached(args[0]),),
            )
        return _python_type_name("Type")  # pragma: no cover

    origin_expression = _runtime_origin_expr(origin)
    if args:
        return PythonTypeSubscript(
            origin_expression,
            tuple(_python_type_expr_from_runtime_uncached(argument) for argument in args),
        )
    return origin_expression  # pragma: no cover


def python_type_expr_from_runtime_full_name(tp: object) -> PythonTypeExpr:
    """Convert a runtime type using the historical ``_full_type_name`` policy."""
    return _python_type_expr_from_runtime_full_name_uncached(tp)


def _python_type_expr_from_runtime_full_name_uncached(tp: object) -> PythonTypeExpr:  # noqa: PLR0911
    if tp is type(None):
        return _python_type_name("None")
    if isinstance(tp, str):
        return PythonTypeText(tp)

    from typing import ForwardRef  # noqa: PLC0415

    if isinstance(tp, ForwardRef):
        return PythonTypeText(tp.__forward_arg__)

    origin = get_origin(tp)
    if origin is not None:
        args = get_args(tp)
        if _is_union_origin(origin):
            if args:
                return PythonTypeUnion(
                    tuple(_python_type_expr_from_runtime_full_name_uncached(argument) for argument in args)
                )
            return PythonTypeText(str(tp))  # pragma: no cover

        origin_expression = _runtime_simple_expr(origin)
        if args:
            return PythonTypeSubscript(
                origin_expression,
                tuple(_python_type_expr_from_runtime_full_name_uncached(argument) for argument in args),
            )
        return origin_expression

    return _runtime_leaf_expr(tp)


def render_runtime_python_type(tp: object, *, full_name: bool = False) -> str:
    """Render a runtime type through a bounded cache that does not retain the type."""
    name_policy: Literal["qualified", "full_name"] = "full_name" if full_name else "qualified"
    try:
        type_ref = ref(tp)
        hash(type_ref)
    except TypeError:
        return _render_runtime_python_type_uncached(tp, name_policy)
    return _render_runtime_python_type_cached(type_ref, name_policy)


@lru_cache(maxsize=256)
def _render_runtime_python_type_cached(
    type_ref: ReferenceType[object],
    name_policy: Literal["qualified", "full_name"],
) -> str:
    if (tp := type_ref()) is None:  # pragma: no cover
        msg = "Runtime type was released during annotation rendering"
        raise RuntimeError(msg)
    return _render_runtime_python_type_uncached(tp, name_policy)


def _render_runtime_python_type_uncached(
    tp: object,
    name_policy: Literal["qualified", "full_name"],
) -> str:
    expression = (
        _python_type_expr_from_runtime_full_name_uncached(tp)
        if name_policy == "full_name"
        else _python_type_expr_from_runtime_uncached(tp)
    )
    return _render_python_type_expr_uncached(expression)


def encode_literal_enum_member(value: Enum) -> str:
    """Encode a runtime enum member at the existing x-python-type boundary."""
    return LiteralEnumMemberRef.from_enum(value).to_marker_text()
