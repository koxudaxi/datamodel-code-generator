from __future__ import annotations

import pytest

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.sqlmodel import BaseModel, DataModelField, DataTypeManager
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType, Types


def test_sqlmodel_base() -> None:
    data_class = BaseModel(
        fields=[],
        reference=Reference(name="Base", path="Base"),
    )

    assert data_class.name == "Base"
    assert data_class.fields == []
    assert data_class.decorators == []
    assert data_class.render() == "class Base(SQLModel):\n    pass"


def test_sqlmodel_model() -> None:
    field = DataModelField(name="a", data_type=DataType(type="str"), required=True)

    data_class = BaseModel(
        fields=[field],
        base_classes=[Reference(name="Base", original_name="Base", path="Base")],
        reference=Reference(name="test_model", path="test_model"),
    )

    assert data_class.name == "test_model"
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert data_class.render() == "class test_model(Base):\n    a: str"


def test_model_inheritance() -> None:
    field = DataModelField(name="a", data_type=DataType(type="str"), required=True)

    data_class = BaseModel(
        fields=[field],
        base_classes=[
            Reference(name="Base", original_name="Base", path="Base"),
            Reference(name="test_base_model", original_name="test_base_model", path="test_base_model"),
        ],
        reference=Reference(name="test_model", path="test_model"),
    )

    assert data_class.name == "test_model"
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert data_class.render() == "class test_model(Base, test_base_model):\n    a: str"


def test_optional_field() -> None:
    field = DataModelField(name="a", data_type=DataType(type="str"), default="abc", required=False)

    data_class = BaseModel(
        fields=[field],
        base_classes=[Reference(name="Base", original_name="Base", path="Base")],
        reference=Reference(name="test_model", path="test_model"),
    )

    assert data_class.name == "test_model"
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert data_class.render() == "class test_model(Base):\n    a: Optional[str] = 'abc'"


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Types.integer, "int"),
        (Types.boolean, "bool"),
        (Types.string, "str"),
        (Types.number, "float"),
    ],
)
def test_get_simple_data_type(input_type: Types, expected: str) -> None:
    data_type_manager = DataTypeManager()
    assert data_type_manager.get_data_type(input_type) == data_type_manager.data_type(type=expected)


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Types.date, "datetime.date"),
        (Types.date_time, "datetime.datetime"),
        (Types.decimal, "decimal.Decimal"),
    ],
)
def test_import_data_type(input_type: Types, expected: str) -> None:
    module, name = expected.rsplit(".", 1)

    data_type_manager = DataTypeManager()
    assert data_type_manager.get_data_type(input_type) == data_type_manager.data_type(
        type=name, import_=Import(from_=module, import_=name)
    )
