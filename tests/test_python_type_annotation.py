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
    PythonTypeEllipsis,
    PythonTypeExpr,
    PythonTypeName,
    PythonTypeParameterList,
    PythonTypeQualifiedName,
    PythonTypeSubscript,
    PythonTypeText,
    PythonTypeUnion,
    _runtime_origin_expr,
    _runtime_simple_expr,
    encode_literal_enum_member,
    python_callable_expr_from_runtime_args,
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


def test_render_python_type_expr_rejects_unknown_node() -> None:
    """The renderer fails closed when a new node has no explicit spelling policy."""

    class UnsupportedExpr(PythonTypeExpr):
        pass

    with pytest.raises(TypeError, match="Unsupported Python type expression: UnsupportedExpr"):
        render_python_type_expr(UnsupportedExpr())
