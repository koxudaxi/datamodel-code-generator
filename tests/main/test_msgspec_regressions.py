"""Regression tests for msgspec.Struct output."""

from __future__ import annotations

import importlib.util
import sys
from typing import TYPE_CHECKING, Any

import msgspec
import pytest

from datamodel_code_generator import DataModelType, Formatter, InputFileType, generate

if TYPE_CHECKING:
    from pathlib import Path


def _generate_msgspec_code(schema: dict[str, Any], **kwargs: Any) -> str:
    result = generate(
        schema,
        input_file_type=InputFileType.JsonSchema,
        output_model_type=DataModelType.MsgspecStruct,
        disable_timestamp=True,
        formatters=[Formatter.BLACK, Formatter.ISORT],
        **kwargs,
    )
    if not isinstance(result, str):  # pragma: no cover
        pytest.fail("Expected code generation to return a string")
    return result


def _assert_contains(code: str, expected: str) -> None:
    if expected not in code:  # pragma: no cover
        pytest.fail(f"Expected generated code to contain {expected!r}")


def _assert_not_contains(code: str, expected: str) -> None:
    if expected in code:  # pragma: no cover
        pytest.fail(f"Expected generated code not to contain {expected!r}")


def _assert_before(code: str, expected: str, following: str) -> None:
    expected_index = code.find(expected)
    following_index = code.find(following)
    if expected_index == -1 or following_index == -1 or expected_index >= following_index:  # pragma: no cover
        pytest.fail(f"Expected {expected!r} to appear before {following!r}")


def _assert_equal(actual: Any, expected: Any) -> None:
    if actual != expected:  # pragma: no cover
        pytest.fail(f"Expected {expected!r}, got {actual!r}")


def _import_generated_code(code: str, tmp_path: Path) -> Any:
    module_path = tmp_path / "generated_msgspec.py"
    module_path.write_text(code, encoding="utf-8")
    module_name = f"generated_msgspec_{tmp_path.name}_{abs(hash(code))}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None:  # pragma: no cover
        pytest.fail("Expected generated module spec")
    if spec.loader is None:  # pragma: no cover
        pytest.fail("Expected generated module loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_msgspec_allof_inheritance_uses_kw_only(tmp_path: Path) -> None:
    """Avoid required child fields following optional inherited fields."""
    code = _generate_msgspec_code({
        "definitions": {
            "Base": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "default": "base"},
                    "note": {"type": "string"},
                },
            },
            "Child": {
                "allOf": [
                    {"$ref": "#/definitions/Base"},
                    {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
                ]
            },
        }
    })

    _assert_contains(code, "class Child(Base, kw_only=True):")
    module = _import_generated_code(code, tmp_path)
    _assert_equal(module.Child(id=1).id, 1)


def test_msgspec_required_alias_field_sorts_before_optional(tmp_path: Path) -> None:
    """Treat alias-only required fields as required for Struct field ordering."""
    code = _generate_msgspec_code({
        "title": "Rec",
        "type": "object",
        "properties": {"opt": {"type": "string"}, "req-id": {"type": "integer"}},
        "required": ["req-id"],
    })

    _assert_before(code, "req_id: int = field(name='req-id')", "opt: str | UnsetType = UNSET")
    _import_generated_code(code, tmp_path)


def test_msgspec_keyword_only_preserves_declared_field_order(tmp_path: Path) -> None:
    """Keep declared order for keyword-only Structs because assignment order is allowed."""
    code = _generate_msgspec_code(
        {
            "title": "Rec",
            "type": "object",
            "properties": {"opt": {"type": "string"}, "req-id": {"type": "integer"}},
            "required": ["req-id"],
        },
        keyword_only=True,
    )

    _assert_contains(code, "class Rec(Struct, kw_only=True):")
    _assert_before(code, "opt: str | UnsetType = UNSET", "req_id: int = field(name='req-id')")
    _import_generated_code(code, tmp_path)


def test_msgspec_required_nullable_field_has_no_default(tmp_path: Path) -> None:
    """Keep required nullable fields required instead of rendering '= None'."""
    code = _generate_msgspec_code({
        "title": "M",
        "type": "object",
        "properties": {"a": {"type": ["string", "null"]}, "b": {"type": "integer"}},
        "required": ["a", "b"],
    })

    _assert_contains(code, "a: str | None\n")
    _assert_not_contains(code, "a: str | None = None")
    module = _import_generated_code(code, tmp_path)
    _assert_equal(module.M(a=None, b=1).a, None)


def test_msgspec_array_length_constraints_use_meta(tmp_path: Path) -> None:
    """Render array length constraints through msgspec.Meta."""
    code = _generate_msgspec_code(
        {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5}},
        },
        field_constraints=True,
        use_annotated=True,
    )

    _assert_contains(code, "Annotated[list[str], Meta(")
    _assert_contains(code, "max_length=5")
    _assert_contains(code, "min_length=1")
    module = _import_generated_code(code, tmp_path)
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"items": []}, type=module.Model)
    _assert_equal(msgspec.convert({"items": ["ok"]}, type=module.Model).items, ["ok"])
