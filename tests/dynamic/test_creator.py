# ruff: noqa: D103
"""Tests for dynamic model generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from inline_snapshot import snapshot
from pydantic import VERSION, ValidationError

from datamodel_code_generator import InputFileType, generate_dynamic_models

PYDANTIC_V2 = VERSION.startswith("2.")
DATA_DIR = Path(__file__).parent.parent / "data" / "dynamic"

pytestmark = pytest.mark.skipif(not PYDANTIC_V2, reason="Dynamic models require Pydantic v2")


def test_simple_model() -> None:
    models = generate_dynamic_models(DATA_DIR / "simple.json")
    assert "Model" in models
    instance = models["Model"](name="John", age=30)
    assert instance.name == snapshot("John")
    assert instance.age == snapshot(30)


def test_nested_models() -> None:
    models = generate_dynamic_models(DATA_DIR / "nested.json")
    assert "Model" in models
    assert "User" in models
    user = models["User"](name="Alice")
    model = models["Model"](user=user)
    assert model.user.name == snapshot("Alice")


def test_numeric_constraints() -> None:
    models = generate_dynamic_models(DATA_DIR / "numeric_constraints.json")
    models["Model"](count=50)
    with pytest.raises(ValidationError):
        models["Model"](count=-1)
    with pytest.raises(ValidationError):
        models["Model"](count=7)


def test_array_constraints() -> None:
    models = generate_dynamic_models(DATA_DIR / "array_constraints.json")
    models["Model"](tags=["a", "b", "c"])
    with pytest.raises(ValidationError):
        models["Model"](tags=[])
    with pytest.raises(ValidationError):
        models["Model"](tags=["a", "b", "c", "d", "e", "f"])


def test_circular_reference() -> None:
    models = generate_dynamic_models(DATA_DIR / "circular.json")
    assert "Node" in models
    node_class = models["Node"]
    node = node_class(value="root", children=[node_class(value="child", children=[])])
    assert node.children[0].value == snapshot("child")


def test_enum_values() -> None:
    models = generate_dynamic_models(DATA_DIR / "enum.json")
    models["Model"](status="active")
    with pytest.raises(ValidationError):
        models["Model"](status="invalid")


def test_optional_field() -> None:
    models = generate_dynamic_models(DATA_DIR / "optional.json")
    instance = models["Model"](name="John")
    assert instance.name == snapshot("John")
    assert instance.nickname is None


def test_default_value() -> None:
    models = generate_dynamic_models(DATA_DIR / "default.json")
    instance = models["Model"]()
    assert instance.count == snapshot(10)


def test_allof_inheritance() -> None:
    models = generate_dynamic_models(DATA_DIR / "allof.json")
    child = models["Child"](id=1, name="Test")
    assert child.id == snapshot(1)
    assert child.name == snapshot("Test")


def test_openapi_schema() -> None:
    models = generate_dynamic_models(DATA_DIR / "openapi.yaml", input_file_type=InputFileType.OpenAPI)
    assert "User" in models
    user = models["User"](name="John", email="john@example.com")
    assert user.name == snapshot("John")
    assert user.email == snapshot("john@example.com")


def test_string_constraints() -> None:
    models = generate_dynamic_models(DATA_DIR / "string_constraints.json")
    models["Model"](code="ABC")
    with pytest.raises(ValidationError):
        models["Model"](code="A")
    with pytest.raises(ValidationError):
        models["Model"](code="abc")


def test_exclusive_constraints() -> None:
    models = generate_dynamic_models(DATA_DIR / "exclusive_constraints.json")
    models["Model"](value=50)
    with pytest.raises(ValidationError):
        models["Model"](value=0)
    with pytest.raises(ValidationError):
        models["Model"](value=100)


def test_formats() -> None:
    from datetime import date, datetime, time, timezone
    from decimal import Decimal
    from uuid import uuid4

    models = generate_dynamic_models(DATA_DIR / "formats.json")
    test_uuid = uuid4()
    instance = models["Model"](
        date_field=date(2024, 1, 1),
        datetime_field=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        uuid_field=test_uuid,
        time_field=time(12, 30),
        decimal_field=Decimal("123.45"),
        binary_field=b"hello",
    )
    assert instance.date_field == snapshot(date(2024, 1, 1))
    assert instance.uuid_field == test_uuid
    assert instance.time_field == snapshot(time(12, 30))
    assert instance.decimal_field == snapshot(Decimal("123.45"))
    assert instance.binary_field == snapshot(b"hello")


def test_types() -> None:
    models = generate_dynamic_models(DATA_DIR / "types.json")
    instance = models["Model"](
        bool_field=True, float_field=19.99, string_field="test", nullable_field=None, const_field="active"
    )
    assert instance.bool_field is True
    assert instance.float_field == snapshot(19.99)
    assert instance.nullable_field is None
    assert instance.const_field == snapshot("active")


def test_objects() -> None:
    models = generate_dynamic_models(DATA_DIR / "objects.json")
    instance = models["Model"](
        dict_str={"key": "value"},
        dict_int={"count": 10},
        plain_object={"any": "value"},
        plain_array=[1, "two", 3.0],
    )
    assert instance.dict_str == snapshot({"key": "value"})
    assert instance.dict_int == snapshot({"count": 10})


def test_unions() -> None:
    models = generate_dynamic_models(DATA_DIR / "unions.json")
    assert models["Model"](anyof_field="test").anyof_field == snapshot("test")
    assert models["Model"](anyof_field=42).anyof_field == snapshot(42)
    assert models["Model"](oneof_field=True).oneof_field is True
    assert models["Model"](multi_union="str").multi_union == snapshot("str")


def test_refs() -> None:
    models = generate_dynamic_models(DATA_DIR / "refs.json")
    for name in ["Address", "Inner", "Middle", "Model", "Outer"]:
        assert name in models
    address = models["Address"](city="Tokyo")
    inner = models["Inner"](value="test")
    middle = models["Middle"](inner=inner)
    outer = models["Outer"](middle=middle)
    instance = models["Model"](address=address, outer=outer)
    assert instance.address.city == snapshot("Tokyo")
    assert instance.outer.middle.inner.value == snapshot("test")


def test_standalone_enum() -> None:
    models = generate_dynamic_models(DATA_DIR / "standalone_enum.json")
    assert "Model" in models
    assert "Status" in models


def test_multiple_allof() -> None:
    models = generate_dynamic_models(DATA_DIR / "multiple_allof.json")
    person = models["Person"](name="John", age=30)
    assert person.name == snapshot("John")
    assert person.age == snapshot(30)


def test_required_field() -> None:
    models = generate_dynamic_models(DATA_DIR / "required.json")
    with pytest.raises(ValidationError):
        models["Model"](name="John")
    instance = models["Model"](name="John", email="john@test.com")
    assert instance.email == snapshot("john@test.com")


def test_tuple_type() -> None:
    models = generate_dynamic_models(DATA_DIR / "tuple.json")
    assert "Model" in models


def test_unique_items() -> None:
    models = generate_dynamic_models(DATA_DIR / "unique_items.json")
    instance = models["Model"](tags=["a", "b"], constrained_tags=["x"])
    assert "a" in instance.tags


def test_min_max_properties() -> None:
    models = generate_dynamic_models(DATA_DIR / "min_max_properties.json")
    assert "Model" in models


def test_description() -> None:
    models = generate_dynamic_models(DATA_DIR / "description.json")
    instance = models["Model"](name="Test")
    assert instance.name == snapshot("Test")
    field_info = models["Model"].model_fields["name"]
    assert field_info.description == snapshot("The user's name")


def test_graphql_not_supported() -> None:
    from datamodel_code_generator import Error

    with pytest.raises(Error, match="GraphQL is not yet supported"):
        generate_dynamic_models("type Query { hello: String }", input_file_type=InputFileType.GraphQL)


def test_type_resolution_error() -> None:
    from unittest.mock import MagicMock, patch

    from datamodel_code_generator.dynamic.creator import DynamicModelCreator
    from datamodel_code_generator.dynamic.exceptions import TypeResolutionError

    mock_parser = MagicMock()
    creator = DynamicModelCreator(mock_parser)
    mock_field = MagicMock()
    mock_field.name = "test_field"
    mock_field.data_type = MagicMock()
    mock_data_model = MagicMock()
    mock_data_model.class_name = "TestModel"
    mock_data_model.fields = [mock_field]
    mock_data_model.base_classes = []
    mock_data_model.reference = None

    with patch.object(creator._type_resolver, "resolve_with_constraints", side_effect=ValueError("test error")):
        with pytest.raises(TypeResolutionError) as exc_info:
            creator._create_pydantic_model(mock_data_model)
        assert "test_field" in str(exc_info.value)
