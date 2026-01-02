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

    def test_field_with_alias(self) -> None:
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
        user_name:
          type: string
      x-alias:
        user_name: userName
"""
        models = generate_dynamic_models(schema, input_file_type=InputFileType.OpenAPI)
        assert "User" in models

    def test_field_with_description(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The user's name",
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Model" in models
        instance = models["Model"](name="Test")
        assert instance.name == "Test"

    def test_standalone_enum_type(self) -> None:
        schema = {
            "$defs": {
                "Status": {
                    "type": "string",
                    "enum": ["active", "inactive", "pending"],
                }
            },
            "type": "object",
            "properties": {"status": {"$ref": "#/$defs/Status"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Status" in models
        assert "Model" in models

    def test_any_of_union(self) -> None:
        schema = {
            "type": "object",
            "properties": {"value": {"anyOf": [{"type": "string"}, {"type": "integer"}]}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance1 = models["Model"](value="test")
        assert instance1.value == "test"

        instance2 = models["Model"](value=42)
        assert instance2.value == 42

    def test_one_of_union(self) -> None:
        schema = {
            "type": "object",
            "properties": {"data": {"oneOf": [{"type": "boolean"}, {"type": "number"}]}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](data=True)
        assert instance.data is True

    def test_time_format(self) -> None:
        schema = {
            "type": "object",
            "properties": {"time_value": {"type": "string", "format": "time"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        from datetime import time

        instance = models["Model"](time_value=time(12, 30, 0))
        assert instance.time_value == time(12, 30, 0)

    def test_decimal_format(self) -> None:
        schema = {
            "type": "object",
            "properties": {"amount": {"type": "string", "format": "decimal"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        from decimal import Decimal

        instance = models["Model"](amount=Decimal("123.45"))
        assert instance.amount == Decimal("123.45")

    def test_bytes_type(self) -> None:
        schema = {
            "type": "object",
            "properties": {"data": {"type": "string", "format": "binary"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](data=b"hello")
        assert instance.data == b"hello"

    def test_array_without_items(self) -> None:
        schema = {
            "type": "object",
            "properties": {"items": {"type": "array"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](items=[1, "two", 3.0])
        assert instance.items == [1, "two", 3.0]

    def test_object_without_properties(self) -> None:
        schema = {
            "type": "object",
            "properties": {"data": {"type": "object"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](data={"any": "value"})
        assert instance.data == {"any": "value"}

    def test_nested_allof_multiple_refs(self) -> None:
        schema = {
            "$defs": {
                "Named": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                "Aged": {
                    "type": "object",
                    "properties": {"age": {"type": "integer"}},
                },
                "Person": {
                    "allOf": [
                        {"$ref": "#/$defs/Named"},
                        {"$ref": "#/$defs/Aged"},
                    ]
                },
            },
            "$ref": "#/$defs/Person",
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Person" in models
        person = models["Person"](name="John", age=30)
        assert person.name == "John"
        assert person.age == 30

    def test_deep_nested_refs(self) -> None:
        schema = {
            "$defs": {
                "Inner": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
                "Middle": {
                    "type": "object",
                    "properties": {"inner": {"$ref": "#/$defs/Inner"}},
                },
                "Outer": {
                    "type": "object",
                    "properties": {"middle": {"$ref": "#/$defs/Middle"}},
                },
            },
            "$ref": "#/$defs/Outer",
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        inner = models["Inner"](value="test")
        middle = models["Middle"](inner=inner)
        outer = models["Outer"](middle=middle)
        assert outer.middle.inner.value == "test"

    def test_additional_properties_typed(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "meta": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](meta={"count": 10, "total": 100})
        assert instance.meta["count"] == 10

    def test_required_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["name", "email"],
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        with pytest.raises(ValidationError):
            models["Model"](name="John")

        instance = models["Model"](name="John", email="john@test.com")
        assert instance.name == "John"

    def test_ge_constraint(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "value": {"type": "integer", "minimum": 10},
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](value=10)
        models["Model"](value=15)

        with pytest.raises(ValidationError):
            models["Model"](value=9)

    def test_le_constraint(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "value": {"type": "integer", "maximum": 100},
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        models["Model"](value=100)
        models["Model"](value=50)

        with pytest.raises(ValidationError):
            models["Model"](value=101)

    def test_forward_ref_resolution(self) -> None:
        schema = {
            "type": "object",
            "properties": {"item": {"$ref": "#/$defs/Item"}},
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        item = models["Item"](name="Widget")
        model = models["Model"](item=item)
        assert model.item.name == "Widget"

    def test_auto_input_type_detection(self) -> None:
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        models = generate_dynamic_models(schema)

        assert "Model" in models
        instance = models["Model"](name="Test")
        assert instance.name == "Test"

    def test_graphql_not_supported(self) -> None:
        schema = """
        type Query {
            hello: String
        }
        """

        from datamodel_code_generator import Error

        with pytest.raises(Error, match="GraphQL is not yet supported"):
            generate_dynamic_models(schema, input_file_type=InputFileType.GraphQL)

    def test_tuple_type(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "coords": {
                    "type": "array",
                    "prefixItems": [{"type": "number"}, {"type": "number"}],
                    "items": False,
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Model" in models

    def test_typed_dict_additional_properties(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        instance = models["Model"](data={"a": 1, "b": 2})
        assert instance.data["a"] == 1

    def test_json_schema_unique_items(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                    "minItems": 1,
                    "maxItems": 10,
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Model" in models

    def test_min_max_properties(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "minProperties": 1,
                    "maxProperties": 5,
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)

        assert "Model" in models


@pytest.mark.skipif(not PYDANTIC_V2, reason="Dynamic models require Pydantic v2")
class TestCreatorEdgeCases:
    def test_empty_parser_results(self) -> None:
        schema = {}

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)
        assert models == {} or isinstance(models, dict)

    def test_field_with_pattern_constraint(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "code": {"type": "string", "pattern": "^[A-Z]{3}$"},
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)
        instance = models["Model"](code="ABC")
        assert instance.code == "ABC"

        with pytest.raises(ValidationError):
            models["Model"](code="abc")


@pytest.mark.skipif(not PYDANTIC_V2, reason="Dynamic models require Pydantic v2")
class TestTypeResolver:
    def test_set_with_typed_items(self) -> None:
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
        instance = models["Model"](tags=["a", "b"])
        assert "a" in instance.tags

    def test_dict_with_key_value_types(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "mapping": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                }
            },
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)
        instance = models["Model"](mapping={"key": "value"})
        assert instance.mapping["key"] == "value"

    def test_format_date_type(self) -> None:
        from datetime import date

        schema = {
            "type": "object",
            "properties": {"birthday": {"type": "string", "format": "date"}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)
        instance = models["Model"](birthday=date(1990, 1, 1))
        assert instance.birthday == date(1990, 1, 1)

    def test_forward_ref_already_resolved(self) -> None:
        schema = {
            "$defs": {
                "Address": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                },
                "Person": {
                    "type": "object",
                    "properties": {
                        "home": {"$ref": "#/$defs/Address"},
                        "work": {"$ref": "#/$defs/Address"},
                    },
                },
            },
            "$ref": "#/$defs/Person",
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)
        addr = models["Address"](city="NYC")
        person = models["Person"](home=addr, work=addr)
        assert person.home.city == "NYC"

    def test_union_with_multiple_types(self) -> None:
        schema = {
            "type": "object",
            "properties": {"value": {"anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "boolean"}]}},
        }

        models = generate_dynamic_models(schema, input_file_type=InputFileType.JsonSchema)
        assert models["Model"](value="test").value == "test"
        assert models["Model"](value=42).value == 42
        assert models["Model"](value=True).value is True


@pytest.mark.skipif(not PYDANTIC_V2, reason="Dynamic models require Pydantic v2")
class TestExceptions:
    def test_type_resolution_error(self) -> None:
        from datamodel_code_generator.dynamic.exceptions import TypeResolutionError
        from datamodel_code_generator.types import DataType

        dt = DataType(type="unknown_type")
        error = TypeResolutionError(dt, "TestModel", "test_field")
        assert "test_field" in str(error)
        assert "TestModel" in str(error)
        assert error.type_info == dt
        assert error.model_name == "TestModel"
        assert error.field_name == "test_field"

    def test_circular_reference_error(self) -> None:
        from datamodel_code_generator.dynamic.exceptions import CircularReferenceError

        error = CircularReferenceError(["A", "B", "C", "A"])
        assert "A -> B -> C -> A" in str(error)
        assert error.cycle_path == ["A", "B", "C", "A"]

    def test_constraint_conversion_error(self) -> None:
        from datamodel_code_generator.dynamic.exceptions import ConstraintConversionError

        error = ConstraintConversionError("min_value", -1, "must be positive")
        assert "min_value" in str(error)
        assert "-1" in str(error)
        assert "must be positive" in str(error)
        assert error.constraint_name == "min_value"
        assert error.constraint_value == -1
        assert error.reason == "must be positive"

    def test_unsupported_model_type_error(self) -> None:
        from datamodel_code_generator.dynamic.exceptions import UnsupportedModelTypeError

        error = UnsupportedModelTypeError("CustomType")
        assert "CustomType" in str(error)
        assert error.model_type == "CustomType"

    def test_dynamic_model_error_base(self) -> None:
        from datamodel_code_generator.dynamic.exceptions import DynamicModelError

        error = DynamicModelError("base error message")
        assert str(error) == "base error message"
