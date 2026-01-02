# ruff: noqa: D101, D102
"""Tests for dynamic model generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import VERSION, ValidationError

from datamodel_code_generator import InputFileType, generate_dynamic_models

if TYPE_CHECKING:
    from pathlib import Path

PYDANTIC_V2 = VERSION.startswith("2.")


@pytest.mark.skipif(not PYDANTIC_V2, reason="Dynamic models require Pydantic v2")
class TestDynamicModelCreation:
    def test_simple_model(self) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Model" in models
        instance = models["Model"](name="John", age=30)
        assert instance.name == "John"
        assert instance.age == 30

    def test_nested_models(self) -> None:
        schema = {
            "type": "object",
            "properties": {"user": {"$ref": "#/$defs/User"}},
            "$defs": {
                "User": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "User" in models
        assert "Model" in models
        user = models["User"](name="Alice")
        model = models["Model"](user=user)
        assert model.user.name == "Alice"

    def test_string_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](email="test@example.com")
        assert instance.email == "test@example.com"

    def test_numeric_constraints(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "multipleOf": 5,
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](count=50)

        with pytest.raises(ValidationError):
            models["Model"](count=-1)

        with pytest.raises(ValidationError):
            models["Model"](count=7)

    def test_array_constraints(self) -> None:
        schema = {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](tags=["a", "b", "c"])

        with pytest.raises(ValidationError):
            models["Model"](tags=[])

        with pytest.raises(ValidationError):
            models["Model"](tags=["a", "b", "c", "d", "e", "f"])

    def test_circular_reference(self) -> None:
        schema = {
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
                    },
                }
            },
            "$ref": "#/$defs/Node",
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        node_class = models["Node"]
        node = node_class(value="root", children=[node_class(value="child", children=[])])
        assert node.children[0].value == "child"

    def test_enum_values(self) -> None:
        schema = {
            "type": "object",
            "properties": {"status": {"enum": ["pending", "active", "completed"]}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](status="active")

        with pytest.raises(ValidationError):
            models["Model"](status="invalid")

    def test_optional_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "nickname": {"type": "string"}},
            "required": ["name"],
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](name="John")
        assert instance.name == "John"
        assert instance.nickname is None

    def test_default_value(self) -> None:
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer", "default": 10}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"]()
        assert instance.count == 10

    def test_all_of_inheritance(self) -> None:
        schema = {
            "$defs": {
                "Base": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Child": {
                    "allOf": [
                        {"$ref": "#/$defs/Base"},
                        {"properties": {"name": {"type": "string"}}},
                    ]
                },
            },
            "$ref": "#/$defs/Child",
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        child = models["Child"](id=1, name="Test")
        assert child.id == 1
        assert child.name == "Test"

    def test_openapi_schema(self) -> None:
        schema = """
openapi: "3.0.0"
info:
  title: Test API
  version: "1.0"
paths: {}
components:
  schemas:
    User:
      type: object
      properties:
        name:
          type: string
        email:
          type: string
      required:
        - name
"""
        models = generate_dynamic_models(schema, input_file_type=InputFileType.OpenAPI)

        assert "User" in models
        user = models["User"](name="John", email="john@example.com")
        assert user.name == "John"
        assert user.email == "john@example.com"

    def test_empty_schema(self) -> None:
        schema = {"type": "object", "properties": {}}

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Model" in models
        instance = models["Model"]()
        assert instance is not None

    def test_string_constraints(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 10,
                    "pattern": "^[A-Z]+$",
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](code="ABC")

        with pytest.raises(ValidationError):
            models["Model"](code="A")

        with pytest.raises(ValidationError):
            models["Model"](code="abc")

    def test_exclusive_numeric_constraints(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "value": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "exclusiveMaximum": 100,
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](value=50)

        with pytest.raises(ValidationError):
            models["Model"](value=0)

        with pytest.raises(ValidationError):
            models["Model"](value=100)

    def test_date_format(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "created": {"type": "string", "format": "date"},
                "updated": {"type": "string", "format": "date-time"},
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        from datetime import date, datetime, timezone

        instance = models["Model"](created=date(2024, 1, 1), updated=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
        assert instance.created == date(2024, 1, 1)

    def test_uuid_format(self) -> None:
        schema = {
            "type": "object",
            "properties": {"id": {"type": "string", "format": "uuid"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        import uuid

        test_uuid = uuid.uuid4()
        instance = models["Model"](id=test_uuid)
        assert instance.id == test_uuid

    def test_dict_type(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](metadata={"key": "value"})
        assert instance.metadata == {"key": "value"}

    def test_set_type(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](tags=["a", "b", "c"])
        assert "a" in instance.tags

    def test_ref_type(self) -> None:
        schema = {
            "$defs": {
                "Address": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                }
            },
            "type": "object",
            "properties": {"address": {"$ref": "#/$defs/Address"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        address = models["Address"](city="Tokyo")
        instance = models["Model"](address=address)
        assert instance.address.city == "Tokyo"

    def test_literal_type(self) -> None:
        schema = {
            "type": "object",
            "properties": {"status": {"const": "active"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](status="active")
        assert instance.status == "active"

    def test_nullable_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": ["string", "null"]}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance1 = models["Model"](name="test")
        assert instance1.name == "test"

        instance2 = models["Model"](name=None)
        assert instance2.name is None

    def test_integer_enum(self) -> None:
        schema = {
            "type": "object",
            "properties": {"priority": {"enum": [1, 2, 3]}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](priority=2)

        with pytest.raises(ValidationError):
            models["Model"](priority=5)

    def test_boolean_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {"active": {"type": "boolean"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](active=True)
        assert instance.active is True

    def test_float_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {"price": {"type": "number"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](price=19.99)
        assert instance.price == 19.99

    def test_empty_results(self) -> None:
        schema = {}

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert isinstance(models, dict)

    def test_file_path_input(self, tmp_path: Path) -> None:
        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object", "properties": {"name": {"type": "string"}}}')

        models = generate_dynamic_models(str(schema_file), input_file_type=InputFileType.JsonSchema)

        assert "Model" in models
        instance = models["Model"](name="Test")
        assert instance.name == "Test"

    def test_path_object_input(self, tmp_path: Path) -> None:
        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object", "properties": {"value": {"type": "integer"}}}')

        models = generate_dynamic_models(schema_file, input_file_type=InputFileType.JsonSchema)

        assert "Model" in models
        instance = models["Model"](value=42)
        assert instance.value == 42
