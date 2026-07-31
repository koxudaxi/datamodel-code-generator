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
from typing import Annotated, Concatenate, Literal, NamedTuple, ParamSpec, Union, get_args, get_origin
from weakref import ReferenceType, ref

from typing_extensions import Self

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

    def to_member_expression(self) -> ast.expr:
        """Build the exact nested enum member access expression."""
        module_root, *module_attrs = self.module.split(".")
        expression: ast.expr = ast.Name(id=module_root, ctx=ast.Load())
        for attr in (*module_attrs, *self.qualname_parts, self.member):
            expression = ast.Attribute(value=expression, attr=attr, ctx=ast.Load())
        return expression


@dataclass(frozen=True, slots=True)
class PythonTypeEnumMember(PythonTypeExpr):
    """An enum member encoded with the existing internal marker spelling."""

    reference: LiteralEnumMemberRef


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
            return f"{_render_python_type_expr_uncached(expression.base)}[{rendered_arguments}]"
        case PythonTypeUnion():
            return " | ".join(_render_python_type_expr_uncached(item) for item in expression.items)
        case PythonTypeParameterList():
            return f"[{', '.join(_render_python_type_expr_uncached(item) for item in expression.items)}]"
        case PythonTypeLiteralValue():
            return repr(expression.value)
        case PythonTypeEllipsis():
            return "..."
        case PythonTypeEnumMember():
            return expression.reference.to_marker_text()
    msg = f"Unsupported Python type expression: {type(expression).__name__}"
    raise TypeError(msg)


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
