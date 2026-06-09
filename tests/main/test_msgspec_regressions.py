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
    assert isinstance(result, str)
    return result


def _import_generated_code(code: str, tmp_path: Path) -> Any:
    module_path = tmp_path / "generated_msgspec.py"
    module_path.write_text(code, encoding="utf-8")
    module_name = f"generated_msgspec_{tmp_path.name}_{abs(hash(code))}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
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

    assert "class Child(Base, kw_only=True):" in code
    module = _import_generated_code(code, tmp_path)
    assert module.Child(id=1).id == 1


def test_msgspec_required_alias_field_sorts_before_optional(tmp_path: Path) -> None:
    """Treat alias-only required fields as required for Struct field ordering."""
    code = _generate_msgspec_code({
        "title": "Rec",
        "type": "object",
        "properties": {"opt": {"type": "string"}, "req-id": {"type": "integer"}},
        "required": ["req-id"],
    })

    assert code.index("req_id: int = field(name='req-id')") < code.index("opt: str | UnsetType = UNSET")
    _import_generated_code(code, tmp_path)


def test_msgspec_required_nullable_field_has_no_default(tmp_path: Path) -> None:
    """Keep required nullable fields required instead of rendering '= None'."""
    code = _generate_msgspec_code({
        "title": "M",
        "type": "object",
        "properties": {"a": {"type": ["string", "null"]}, "b": {"type": "integer"}},
        "required": ["a", "b"],
    })

    assert "a: str | None\n" in code
    assert "a: str | None = None" not in code
    module = _import_generated_code(code, tmp_path)
    assert module.M(a=None, b=1).a is None


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

    assert "Annotated[list[str], Meta(max_length=5, min_length=1)]" in code
    module = _import_generated_code(code, tmp_path)
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"items": []}, type=module.Model)
    assert msgspec.convert({"items": ["ok"]}, type=module.Model).items == ["ok"]
