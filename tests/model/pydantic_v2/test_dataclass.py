"""Tests for Pydantic v2 dataclass generation."""

from __future__ import annotations

from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.pydantic_v2.dataclass import DataClass, DataModelField
from datamodel_code_generator.model.pydantic_v2.types import DataTypeManager
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, Types


def test_data_class() -> None:
    """Test basic DataClass generation with required field."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    data_class = DataClass(
        fields=[field],
        reference=Reference(name="test_model", path="test_model"),
    )

    assert data_class.name == "test_model"
    assert data_class.decorators == []
    rendered = data_class.render()
    assert "@dataclass" in rendered
    assert "class test_model:" in rendered
    assert "a: str" in rendered


def test_data_class_base_class() -> None:
    """Test DataClass generation with base class inheritance."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    data_class = DataClass(
        fields=[field],
        base_classes=[Reference(name="Base", original_name="Base", path="Base")],
        reference=Reference(name="test_model", path="test_model"),
    )

    assert data_class.name == "test_model"
    assert data_class.decorators == []
    rendered = data_class.render()
    assert "@dataclass" in rendered
    assert "class test_model(Base):" in rendered
    assert "a: str" in rendered


def test_data_class_optional() -> None:
    """Test DataClass generation with field default value."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), default="'abc'", required=False)

    data_class = DataClass(
        fields=[field],
        reference=Reference(name="test_model", path="test_model"),
    )

    assert data_class.name == "test_model"
    rendered = data_class.render()
    assert "@dataclass" in rendered
    assert "class test_model:" in rendered
    # pydantic v2 uses Optional[str] for optional fields
    assert "a:" in rendered


def test_data_class_get_data_type() -> None:
    """Test data type retrieval for DataClass fields."""
    data_type_manager = DataTypeManager()
    # Check that the type is correctly mapped
    result = data_type_manager.get_data_type(Types.integer)
    assert result.type == "int"


def test_data_class_field_ordering() -> None:
    """Test that fields are sorted: required first, defaults last."""
    required_field = DataModelFieldBase(name="required_field", data_type=DataType(type="str"), required=True)
    optional_field = DataModelFieldBase(
        name="optional_field", data_type=DataType(type="str"), default="None", required=False
    )

    # Pass fields in wrong order (optional first)
    data_class = DataClass(
        fields=[optional_field, required_field],
        reference=Reference(name="test_model", path="test_model"),
    )

    # Required field should come first after sorting
    assert data_class.fields[0].name == "required_field"
    assert data_class.fields[1].name == "optional_field"


def test_data_class_frozen() -> None:
    """Test DataClass with frozen=True."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    data_class = DataClass(
        fields=[field],
        reference=Reference(name="test_model", path="test_model"),
        frozen=True,
    )

    assert data_class.dataclass_arguments.get("frozen") is True
    assert "@dataclass(frozen=True)" in data_class.render()


def test_data_class_kw_only() -> None:
    """Test DataClass with keyword_only=True."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    data_class = DataClass(
        fields=[field],
        reference=Reference(name="test_model", path="test_model"),
        keyword_only=True,
    )

    assert data_class.dataclass_arguments.get("kw_only") is True
    assert "@dataclass(kw_only=True)" in data_class.render()


def test_data_class_with_description() -> None:
    """Test DataClass with docstring description."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    data_class = DataClass(
        fields=[field],
        reference=Reference(name="test_model", path="test_model"),
        description="This is a test model.",
    )

    rendered = data_class.render()
    assert "class test_model:" in rendered
    assert '"""' in rendered
    assert "This is a test model." in rendered


def test_data_model_field() -> None:
    """Test DataModelField creation."""
    field = DataModelField(
        name="test_field",
        data_type=DataType(type="str"),
        required=True,
    )

    assert field.name == "test_field"
    assert field.required is True


def test_create_reuse_model() -> None:
    """Test creating a reuse model from existing DataClass."""
    field = DataModelFieldBase(name="a", data_type=DataType(type="str"), required=True)

    data_class = DataClass(
        fields=[field],
        reference=Reference(name="test_model", path="test_model"),
        frozen=True,
    )

    base_ref = Reference(name="BaseModel", path="base_model")
    reuse_model = data_class.create_reuse_model(base_ref)

    assert reuse_model.fields == []
    assert len(reuse_model.base_classes) == 1
    # base_classes are wrapped in BaseClassDataType which has a reference attribute
    assert reuse_model.base_classes[0].reference is base_ref
    assert reuse_model.frozen is True
