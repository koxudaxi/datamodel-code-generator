"""Tests for the internal Python type-expression representation."""

from __future__ import annotations

import gc
from dataclasses import FrozenInstanceError
from enum import Enum
from types import SimpleNamespace
from typing import Annotated, ForwardRef, Generic, Literal, TypeVar, Union
from weakref import ref

import pytest

from datamodel_code_generator._python_type_annotation import (
    PYTHON_LITERAL_ENUM_MEMBER_MARKER,
    LiteralEnumMemberRef,
    PythonTypeEllipsis,
    PythonTypeEnumMemberAccess,
    PythonTypeExpr,
    PythonTypeLiteralValue,
    PythonTypeName,
    PythonTypeParameterList,
    PythonTypeQualifiedName,
    PythonTypeSubscript,
    PythonTypeText,
    PythonTypeUnion,
    _runtime_origin_expr,
    _runtime_simple_expr,
    encode_literal_enum_member,
    is_union_python_type_expr,
    iter_python_type_expr_names,
    iter_python_type_expr_qualified_names,
    map_python_type_expr,
    parse_python_type_annotation,
    python_callable_expr_from_runtime_args,
    python_type_expr_arguments,
    python_type_expr_base_name,
    python_type_expr_from_runtime,
    python_type_expr_from_runtime_full_name,
    render_python_type_expr,
    render_runtime_python_type,
)

T = TypeVar("T")


class Box(Generic[T]):
    """Generic used to distinguish qualified and argument-name policies."""


class Status(Enum):
    """Importable enum used by the Literal marker adapter."""

    ACTIVE = "active"


@pytest.mark.allow_direct_assert
def test_python_type_expr_is_frozen_and_slotted() -> None:
    """Expression nodes are safe to share without mutable per-instance dictionaries."""
    expression = PythonTypeName("int")

    assert not hasattr(expression, "__dict__")
    with pytest.raises(FrozenInstanceError):
        expression.value = "str"  # ty: ignore[invalid-assignment]


def test_python_type_name_rejects_text_and_qualified_names() -> None:
    """Semantic names cannot silently become raw or dotted annotation text."""
    with pytest.raises(ValueError, match="must be one identifier"):
        PythonTypeName("module.Model")
    with pytest.raises(ValueError, match="must be one identifier"):
        PythonTypeName("list[int]")
    with pytest.raises(ValueError, match="must contain identifiers"):
        PythonTypeQualifiedName(())
    with pytest.raises(ValueError, match="must contain identifiers"):
        PythonTypeQualifiedName(("invalid-name",))


@pytest.mark.allow_direct_assert
def test_runtime_name_fallbacks_remain_opaque_text() -> None:
    """Invalid runtime identities stay at the explicit text boundary."""
    invalid_module = SimpleNamespace(__module__="invalid-module", __name__="Model")
    invalid_name = SimpleNamespace(__module__="", __name__="invalid-name")

    assert python_type_expr_from_runtime(invalid_module) == PythonTypeText("invalid-module.Model")
    assert python_type_expr_from_runtime(invalid_name) == PythonTypeText("invalid-name")


@pytest.mark.allow_direct_assert
def test_nameless_runtime_origin_and_simple_fallbacks() -> None:
    """Defensive runtime fallbacks preserve normalized text without inventing names."""

    class NamelessRuntimeType:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:
            return self.value

    assert _runtime_origin_expr(NamelessRuntimeType("typing.Invalid[Name]")) == PythonTypeText("Invalid[Name]")
    assert _runtime_origin_expr(NamelessRuntimeType("Fallback")) == PythonTypeName("Fallback")
    assert _runtime_simple_expr(type(None)) == PythonTypeName("None")
    assert _runtime_simple_expr(list[int]) == PythonTypeText("list[int]")
    assert _runtime_simple_expr(NamelessRuntimeType("typing.Opaque")) == PythonTypeText("Opaque")


@pytest.mark.allow_direct_assert
def test_runtime_qualified_name_is_structured() -> None:
    """Runtime-qualified identity is transported as validated dotted parts."""
    expression = python_type_expr_from_runtime(Box)

    assert expression == PythonTypeQualifiedName(("tests", "test_python_type_annotation", "Box"))
    assert render_python_type_expr(expression) == "tests.test_python_type_annotation.Box"


@pytest.mark.allow_direct_assert
def test_render_python_type_expr_is_deterministic() -> None:
    """Render nested nodes with the compatibility separators used by x-python-type."""
    expression = PythonTypeSubscript(
        PythonTypeName("Callable"),
        (
            PythonTypeParameterList((PythonTypeName("int"), PythonTypeName("str"))),
            PythonTypeUnion((PythonTypeName("bool"), PythonTypeName("None"))),
        ),
    )

    assert render_python_type_expr(expression) == "Callable[[int, str], bool | None]"


@pytest.mark.allow_direct_assert
def test_runtime_type_expr_preserves_full_and_argument_name_policies() -> None:
    """The two historical serializers share IR while retaining different outer-name policies."""
    qualified = render_python_type_expr(python_type_expr_from_runtime(Box[list[int]]))
    argument_name = render_python_type_expr(python_type_expr_from_runtime_full_name(Box[list[int]]))

    assert qualified == "tests.test_python_type_annotation.Box[list[int]]"
    assert argument_name == "Box[list[int]]"


@pytest.mark.allow_direct_assert
def test_runtime_type_expr_preserves_forward_ref_text() -> None:
    """Forward references remain an atomic text boundary in full-name mode."""
    expression = python_type_expr_from_runtime_full_name(ForwardRef("module.Model"))

    assert isinstance(expression, PythonTypeText)
    assert render_python_type_expr(expression) == "module.Model"


@pytest.mark.allow_direct_assert
def test_runtime_type_renderer_does_not_retain_user_owned_types() -> None:
    """The process cache must not retain temporary input-model classes."""
    from datamodel_code_generator._python_type_annotation import _render_runtime_python_type_cached

    _render_runtime_python_type_cached.cache_clear()
    annotation = list[ForwardRef("TemporaryModel")]
    annotation_ref = ref(annotation)
    assert render_runtime_python_type(annotation) == "list[ForwardRef('TemporaryModel')]"

    del annotation
    gc.collect()
    assert annotation_ref() is None


@pytest.mark.allow_direct_assert
def test_runtime_type_expr_preserves_nested_union_and_forward_ref_precedence() -> None:
    """A forward-reference union remains nested inside its generic argument brackets."""
    expression = python_type_expr_from_runtime_full_name(
        list[Union[ForwardRef("Model"), None]]  # noqa: UP007  # ty: ignore[invalid-type-form]
    )

    assert render_python_type_expr(expression) == "list[Model | None]"


@pytest.mark.allow_direct_assert
def test_runtime_type_expr_accepts_unhashable_typing_metadata() -> None:
    """The bounded expression cache falls back safely for unhashable typing objects."""
    expression = python_type_expr_from_runtime(Annotated[int, []])

    assert render_python_type_expr(expression) == "int"


@pytest.mark.allow_direct_assert
def test_runtime_type_expr_preserves_literal_marker_and_values() -> None:
    """Enum markers and scalar repr output remain byte-for-byte compatible."""
    expression = python_type_expr_from_runtime(Literal[Status.ACTIVE, b"bytes", True, None])  # noqa: PYI061

    assert render_python_type_expr(expression) == (
        "Literal["
        f"{PYTHON_LITERAL_ENUM_MEMBER_MARKER}['tests.test_python_type_annotation', 'Status', 'ACTIVE'], "
        "b'bytes', True, None]"
    )
    assert encode_literal_enum_member(Status.ACTIVE) == (
        f"{PYTHON_LITERAL_ENUM_MEMBER_MARKER}['tests.test_python_type_annotation', 'Status', 'ACTIVE']"
    )


@pytest.mark.allow_direct_assert
def test_runtime_type_expr_handles_callable_base_and_ellipsis() -> None:
    """Standalone Callable and ellipsis use dedicated structured nodes."""
    assert python_callable_expr_from_runtime_args(()) == PythonTypeName("Callable")
    assert python_type_expr_from_runtime(type(None)) == PythonTypeName("None")
    assert python_type_expr_from_runtime(...) == PythonTypeEllipsis()


@pytest.mark.allow_direct_assert
def test_enum_member_access_exposes_its_bound_qualified_name() -> None:
    """Import pruning can retain the root module bound by an enum access."""
    expression = PythonTypeEnumMemberAccess(LiteralEnumMemberRef.from_enum(Status.ACTIVE))

    assert iter_python_type_expr_qualified_names(expression) == ("tests.test_python_type_annotation.Status.ACTIVE",)


def test_render_python_type_expr_rejects_unknown_node() -> None:
    """The renderer fails closed when a new node has no explicit spelling policy."""

    class UnsupportedExpr(PythonTypeExpr):
        pass

    with pytest.raises(TypeError, match="Unsupported Python type expression: UnsupportedExpr"):
        render_python_type_expr(UnsupportedExpr())


@pytest.mark.allow_direct_assert
def test_parse_python_type_annotation_builds_semantic_structure() -> None:
    """The raw text boundary produces reusable semantic nodes, not source fragments."""
    expression = parse_python_type_annotation("Callable[[foo.Bar, ...], Literal['value', -1]] | None")

    assert expression == PythonTypeUnion((
        PythonTypeSubscript(
            PythonTypeName("Callable"),
            (
                PythonTypeParameterList((PythonTypeQualifiedName(("foo", "Bar")), PythonTypeEllipsis())),
                PythonTypeSubscript(
                    PythonTypeName("Literal"),
                    (PythonTypeLiteralValue("value"), PythonTypeLiteralValue(-1)),
                ),
            ),
        ),
        PythonTypeName("None"),
    ))
    assert render_python_type_expr(expression) == "Callable[[foo.Bar, ...], Literal['value', -1]] | None"
    assert not python_type_expr_base_name(expression)
    assert tuple(map(python_type_expr_base_name, python_type_expr_arguments(expression))) == ("Callable", "None")
    assert is_union_python_type_expr(expression)
    assert iter_python_type_expr_names(expression) == ("Callable", "Bar", "Literal", "None")
    assert iter_python_type_expr_qualified_names(expression) == ("foo.Bar",)


@pytest.mark.parametrize(
    "annotation",
    [
        "[",
        "factory()",
        "list[{1: 2}]",
        "Literal[object()]",
        "lambda: str",
    ],
)
@pytest.mark.allow_direct_assert
def test_parse_python_type_annotation_rejects_unsupported_syntax(annotation: str) -> None:
    """The boundary parser fails closed for executable or unsupported expressions."""
    assert parse_python_type_annotation(annotation) is None


@pytest.mark.allow_direct_assert
def test_map_python_type_expr_transforms_all_structural_leaves() -> None:
    """One traversal primitive keeps binding and compatibility helpers DRY."""
    expression = parse_python_type_annotation("Callable[[(int, str)], str]")
    assert expression is not None

    transformed = map_python_type_expr(
        expression,
        lambda item: PythonTypeName(item.value.upper()) if isinstance(item, PythonTypeName) else item,
    )

    assert render_python_type_expr(transformed) == "CALLABLE[[(INT, STR)], STR]"


@pytest.mark.allow_direct_assert
def test_render_python_type_expr_parenthesizes_union_subscript_base() -> None:
    """Nested union bases retain the precedence expressed by the IR tree."""
    expression = PythonTypeSubscript(
        PythonTypeUnion((PythonTypeName("First"), PythonTypeName("Second"))),
        (PythonTypeName("Item"),),
    )

    assert render_python_type_expr(expression) == "(First | Second)[Item]"
    assert python_type_expr_arguments(PythonTypeName("Item")) == ()
