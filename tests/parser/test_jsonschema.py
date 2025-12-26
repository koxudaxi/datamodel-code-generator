"""Tests for JSON Schema parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union
from unittest.mock import call

import pydantic
import pytest
import yaml

from datamodel_code_generator import AllOfMergeMode
from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.model.pydantic.base_model import BaseModel
from datamodel_code_generator.parser.base import Parser, dump_templates
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    Types,
    get_model_by_path,
)
from datamodel_code_generator.reference import SPECIAL_PATH_MARKER, Reference
from datamodel_code_generator.types import DataType
from datamodel_code_generator.util import model_dump, model_validate
from tests.conftest import assert_output

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

DATA_PATH: Path = Path(__file__).parents[1] / "data" / "jsonschema"

EXPECTED_JSONSCHEMA_PATH = Path(__file__).parents[1] / "data" / "expected" / "parser" / "jsonschema"


@pytest.mark.parametrize(
    ("schema", "path", "model"),
    [
        ({"foo": "bar"}, None, {"foo": "bar"}),
        ({"a": {"foo": "bar"}}, "a", {"foo": "bar"}),
        ({"a": {"b": {"foo": "bar"}}}, "a/b", {"foo": "bar"}),
        ({"a": {"b": {"c": {"foo": "bar"}}}}, "a/b", {"c": {"foo": "bar"}}),
        ({"a": {"b": {"c": {"foo": "bar"}}}}, "a/b/c", {"foo": "bar"}),
    ],
)
def test_get_model_by_path(schema: dict, path: str, model: dict) -> None:
    """Test model retrieval by path."""
    assert get_model_by_path(schema, path.split("/") if path else []) == model


def test_json_schema_object_ref_url_json(mocker: MockerFixture) -> None:
    """Test JSON schema object reference with JSON URL."""
    parser = JsonSchemaParser("")
    obj = model_validate(JsonSchemaObject, {"$ref": "https://example.com/person.schema.json#/definitions/User"})
    mock_get = mocker.patch("httpx.get")
    mock_get.return_value.text = json.dumps(
        {
            "$id": "https://example.com/person.schema.json",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "User": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                        }
                    },
                }
            },
        },
    )

    parser.parse_ref(obj, ["Model"])
    assert (
        dump_templates(list(parser.results))
        == """class User(BaseModel):
    name: Optional[str] = None"""
    )
    parser.parse_ref(obj, ["Model"])
    mock_get.assert_has_calls([
        call(
            "https://example.com/person.schema.json",
            headers=None,
            verify=True,
            follow_redirects=True,
            params=None,
            timeout=30.0,
        ),
    ])


def test_json_schema_object_ref_url_yaml(mocker: MockerFixture) -> None:
    """Test JSON schema object reference with YAML URL."""
    parser = JsonSchemaParser("")
    obj = model_validate(JsonSchemaObject, {"$ref": "https://example.org/schema.yaml#/definitions/User"})
    mock_get = mocker.patch("httpx.get")
    mock_get.return_value.text = yaml.safe_dump(json.load((DATA_PATH / "user.json").open()))

    parser.parse_ref(obj, ["User"])
    assert (
        dump_templates(list(parser.results))
        == """class User(BaseModel):
    name: Optional[str] = Field(None, example='ken')
    pets: List[User] = Field(default_factory=list)


class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])"""
    )
    parser.parse_ref(obj, [])
    mock_get.assert_called_once_with(
        "https://example.org/schema.yaml",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )


def test_json_schema_object_cached_ref_url_yaml(mocker: MockerFixture) -> None:
    """Test JSON schema object cached reference with YAML URL."""
    parser = JsonSchemaParser("")

    obj = model_validate(
        JsonSchemaObject,
        {
            "type": "object",
            "properties": {
                "pet": {"$ref": "https://example.org/schema.yaml#/definitions/Pet"},
                "user": {"$ref": "https://example.org/schema.yaml#/definitions/User"},
            },
        },
    )
    mock_get = mocker.patch("httpx.get")
    mock_get.return_value.text = yaml.safe_dump(json.load((DATA_PATH / "user.json").open()))

    parser.parse_ref(obj, [])
    assert (
        dump_templates(list(parser.results))
        == """class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])


class User(BaseModel):
    name: Optional[str] = Field(None, example='ken')
    pets: List[User] = Field(default_factory=list)"""
    )
    mock_get.assert_called_once_with(
        "https://example.org/schema.yaml",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )


def test_json_schema_ref_url_json(mocker: MockerFixture) -> None:
    """Test JSON schema reference with JSON URL."""
    parser = JsonSchemaParser("")
    obj = {
        "type": "object",
        "properties": {"user": {"$ref": "https://example.org/schema.json#/definitions/User"}},
    }
    mock_get = mocker.patch("httpx.get")
    mock_get.return_value.text = json.dumps(json.load((DATA_PATH / "user.json").open()))

    parser.parse_raw_obj("Model", obj, ["Model"])
    assert (
        dump_templates(list(parser.results))
        == """class Model(BaseModel):
    user: Optional[User] = None


class User(BaseModel):
    name: Optional[str] = Field(None, example='ken')
    pets: List[User] = Field(default_factory=list)


class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])"""
    )
    mock_get.assert_called_once_with(
        "https://example.org/schema.json",
        headers=None,
        verify=True,
        follow_redirects=True,
        params=None,
        timeout=30.0,
    )


@pytest.mark.parametrize(
    ("source_obj", "generated_classes"),
    [
        (
            {
                "$id": "https://example.com/person.schema.json",
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Person",
                "type": "object",
                "properties": {
                    "firstName": {
                        "type": "string",
                        "description": "The person's first name.",
                    },
                    "lastName": {
                        "type": "string",
                        "description": "The person's last name.",
                    },
                    "age": {
                        "description": "Age in years which must be equal to or greater than zero.",
                        "type": "integer",
                        "minimum": 0,
                    },
                },
            },
            """class Person(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    age: Optional[conint(ge=0)] = None""",
        ),
        (
            {
                "$id": "https://example.com/person.schema.json",
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "person-object",
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The person's name.",
                    },
                    "home-address": {
                        "$ref": "#/definitions/home-address",
                        "description": "The person's home address.",
                    },
                },
                "definitions": {
                    "home-address": {
                        "type": "object",
                        "properties": {
                            "street-address": {"type": "string"},
                            "city": {"type": "string"},
                            "state": {"type": "string"},
                        },
                        "required": ["street_address", "city", "state"],
                    }
                },
            },
            """class Person(BaseModel):
    name: Optional[str] = None
    home_address: Optional[HomeAddress] = None""",
        ),
    ],
)
def test_parse_object(source_obj: dict[str, Any], generated_classes: str) -> None:
    """Test parsing JSON schema objects."""
    parser = JsonSchemaParser(
        data_model_field_type=DataModelFieldBase,
        source="",
    )
    parser.parse_object("Person", model_validate(JsonSchemaObject, source_obj), [])
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    ("source_obj", "generated_classes"),
    [
        (
            {
                "$id": "https://example.com/person.schema.json",
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "AnyJson",
                "description": "This field accepts any object",
                "discriminator": "type",
            },
            """class AnyObject(BaseModel):
    __root__: Any = Field(..., description='This field accepts any object', discriminator='type', title='AnyJson')""",
        )
    ],
)
def test_parse_any_root_object(source_obj: dict[str, Any], generated_classes: str) -> None:
    """Test parsing any root object."""
    parser = JsonSchemaParser("")
    parser.parse_root_type("AnyObject", model_validate(JsonSchemaObject, source_obj), [])
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    ("source_obj", "generated_classes"),
    [
        (
            yaml.safe_load((DATA_PATH / "oneof.json").read_text()),
            (DATA_PATH / "oneof.json.snapshot").read_text(),
        )
    ],
)
def test_parse_one_of_object(source_obj: dict[str, Any], generated_classes: str) -> None:
    """Test parsing oneOf schema objects."""
    parser = JsonSchemaParser("")
    parser.parse_raw_obj("onOfObject", source_obj, [])
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    ("source_obj", "generated_classes"),
    [
        (
            {
                "$id": "https://example.com/person.schema.json",
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "defaults",
                "type": "object",
                "properties": {
                    "string": {
                        "type": "string",
                        "default": "default string",
                    },
                    "string_on_field": {
                        "type": "string",
                        "default": "default string",
                        "description": "description",
                    },
                    "number": {"type": "number", "default": 123},
                    "number_on_field": {
                        "type": "number",
                        "default": 123,
                        "description": "description",
                    },
                    "number_array": {"type": "array", "default": [1, 2, 3]},
                    "string_array": {"type": "array", "default": ["a", "b", "c"]},
                    "object": {"type": "object", "default": {"key": "value"}},
                },
            },
            """class Defaults(BaseModel):
    string: Optional[str] = 'default string'
    string_on_field: Optional[str] = Field('default string', description='description')
    number: Optional[float] = 123
    number_on_field: Optional[float] = Field(123, description='description')
    number_array: Optional[List[Any]] = [1, 2, 3]
    string_array: Optional[List[Any]] = ['a', 'b', 'c']
    object: Optional[Dict[str, Any]] = {'key': 'value'}""",
        )
    ],
)
def test_parse_default(source_obj: dict[str, Any], generated_classes: str) -> None:
    """Test parsing default values in schemas."""
    parser = JsonSchemaParser("")
    parser.parse_raw_obj("Defaults", source_obj, [])
    assert dump_templates(list(parser.results)) == generated_classes


def test_parse_array_schema() -> None:
    """Test parsing array schemas."""
    parser = JsonSchemaParser("")
    parser.parse_raw_obj("schema", {"type": "object", "properties": {"name": True}}, [])
    assert (
        dump_templates(list(parser.results))
        == """class Schema(BaseModel):
    name: Optional[Any] = None"""
    )


def test_parse_nested_array(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test parsing nested array schemas."""
    monkeypatch.chdir(tmp_path)
    parser = JsonSchemaParser(
        DATA_PATH / "nested_array.json",
        data_model_field_type=DataModelFieldBase,
    )
    parser.parse()
    assert_output(dump_templates(list(parser.results)), DATA_PATH / "nested_array.json.snapshot")


@pytest.mark.parametrize(
    ("schema_type", "schema_format", "result_type", "from_", "import_", "use_pendulum"),
    [
        ("integer", "int32", "int", None, None, False),
        ("integer", "int64", "int", None, None, False),
        ("integer", "date-time", "datetime", "datetime", "datetime", False),
        ("integer", "date-time", "DateTime", "pendulum", "DateTime", True),
        ("integer", "unix-time", "int", None, None, False),
        ("number", "float", "float", None, None, False),
        ("number", "double", "float", None, None, False),
        ("number", "time", "time", "datetime", "time", False),
        ("number", "time", "Time", "pendulum", "Time", True),
        ("number", "date-time", "datetime", "datetime", "datetime", False),
        ("number", "date-time", "DateTime", "pendulum", "DateTime", True),
        ("string", None, "str", None, None, False),
        ("string", "byte", "str", None, None, False),
        ("string", "binary", "bytes", None, None, False),
        ("boolean", None, "bool", None, None, False),
        ("string", "date", "date", "datetime", "date", False),
        ("string", "date", "Date", "pendulum", "Date", True),
        ("string", "date-time", "datetime", "datetime", "datetime", False),
        ("string", "date-time", "DateTime", "pendulum", "DateTime", True),
        ("string", "duration", "timedelta", "datetime", "timedelta", False),
        ("string", "duration", "Duration", "pendulum", "Duration", True),
        ("number", "time-delta", "timedelta", "datetime", "timedelta", False),
        ("number", "time-delta", "Duration", "pendulum", "Duration", True),
        ("string", "path", "Path", "pathlib", "Path", False),
        ("string", "password", "SecretStr", "pydantic", "SecretStr", False),
        ("string", "email", "EmailStr", "pydantic", "EmailStr", False),
        ("string", "uri", "AnyUrl", "pydantic", "AnyUrl", False),
        ("string", "uri-reference", "str", None, None, False),
        ("string", "uuid", "UUID", "uuid", "UUID", False),
        ("string", "uuid1", "UUID1", "pydantic", "UUID1", False),
        ("string", "uuid2", "UUID2", "pydantic", "UUID2", False),
        ("string", "uuid3", "UUID3", "pydantic", "UUID3", False),
        ("string", "uuid4", "UUID4", "pydantic", "UUID4", False),
        ("string", "uuid5", "UUID5", "pydantic", "UUID5", False),
        ("string", "ulid", "ULID", "ulid", "ULID", False),
        ("string", "ipv4", "IPv4Address", "ipaddress", "IPv4Address", False),
        ("string", "ipv6", "IPv6Address", "ipaddress", "IPv6Address", False),
        ("string", "unknown-type", "str", None, None, False),
    ],
)
def test_get_data_type(
    schema_type: str,
    schema_format: str,
    result_type: str,
    from_: str | None,
    import_: str | None,
    use_pendulum: bool,
) -> None:
    """Test data type resolution from schema type and format."""
    if from_ and import_:
        import_: Import | None = Import(from_=from_, import_=import_)
    else:
        import_ = None

    parser = JsonSchemaParser("", use_pendulum=use_pendulum)
    assert model_dump(parser.get_data_type(JsonSchemaObject(type=schema_type, format=schema_format))) == model_dump(
        DataType(type=result_type, import_=import_)
    )


@pytest.mark.parametrize(
    ("schema_types", "result_types"),
    [
        (["integer", "number"], ["int", "float"]),
        (["integer", "null"], ["int"]),
    ],
)
def test_get_data_type_array(schema_types: list[str], result_types: list[str]) -> None:
    """Test data type resolution for array of types."""
    parser = JsonSchemaParser("")
    assert parser.get_data_type(JsonSchemaObject(type=schema_types)) == parser.data_type(
        data_types=[
            parser.data_type(
                type=r,
            )
            for r in result_types
        ],
        is_optional="null" in schema_types,
    )


def test_additional_imports() -> None:
    """Test that additional imports are inside imports container."""
    new_parser = JsonSchemaParser(source="", additional_imports=["collections.deque"])
    assert len(new_parser.imports) == 1
    assert new_parser.imports["collections"] == {"deque"}


def test_no_additional_imports() -> None:
    """Test that not additional imports are not affecting imports container."""
    new_parser = JsonSchemaParser(
        source="",
    )
    assert len(new_parser.imports) == 0


def test_class_decorators() -> None:
    """Test that class decorators are stored in parser."""
    new_parser = JsonSchemaParser(source="", class_decorators=["@dataclass_json"])
    assert new_parser.class_decorators == ["@dataclass_json"]


def test_class_decorators_multiple() -> None:
    """Test that multiple class decorators are stored in parser."""
    new_parser = JsonSchemaParser(source="", class_decorators=["@dataclass_json", "@my_decorator"])
    assert new_parser.class_decorators == ["@dataclass_json", "@my_decorator"]


def test_no_class_decorators() -> None:
    """Test that no class decorators results in empty list."""
    new_parser = JsonSchemaParser(source="")
    assert new_parser.class_decorators == []


@pytest.mark.parametrize(
    ("source_obj", "generated_classes"),
    [
        (
            {
                "$id": "https://example.com/person.schema.json",
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Person",
                "type": "object",
                "properties": {
                    "firstName": {
                        "type": "string",
                        "description": "The person's first name.",
                        "alt_type": "integer",
                    },
                    "lastName": {
                        "type": "string",
                        "description": "The person's last name.",
                        "alt_type": "integer",
                    },
                    "age": {
                        "description": "Age in years which must be equal to or greater than zero.",
                        "type": "integer",
                        "minimum": 0,
                        "alt_type": "number",
                    },
                    "real_age": {
                        "description": "Age in years which must be equal to or greater than zero.",
                        "type": "integer",
                        "minimum": 0,
                    },
                },
            },
            """class Person(BaseModel):
    firstName: Optional[int] = None
    lastName: Optional[int] = None
    age: Optional[confloat(ge=0.0)] = None
    real_age: Optional[conint(ge=0)] = None""",
        ),
    ],
)
@pytest.mark.skipif(pydantic.VERSION < "2.0.0", reason="Require Pydantic version 2.0.0 or later ")
def test_json_schema_parser_extension(source_obj: dict[str, Any], generated_classes: str) -> None:
    """Test JSON schema parser extension with alt_type support."""

    class AltJsonSchemaObject(JsonSchemaObject):
        properties: Optional[dict[str, Union[AltJsonSchemaObject, bool]]] = None  # noqa: UP007, UP045
        alt_type: Optional[str] = None  # noqa: UP045

        def model_post_init(self, context: Any) -> None:  # noqa: ARG002
            if self.alt_type:
                self.type = self.alt_type

    class AltJsonSchemaParser(JsonSchemaParser):
        SCHEMA_OBJECT_TYPE = AltJsonSchemaObject

    parser = AltJsonSchemaParser(
        data_model_field_type=DataModelFieldBase,
        source="",
    )
    parser.parse_object("Person", model_validate(AltJsonSchemaObject, source_obj), [])
    assert dump_templates(list(parser.results)) == generated_classes


def test_create_data_model_with_frozen_dataclasses() -> None:
    """Test _create_data_model when frozen_dataclasses attribute exists."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.frozen_dataclasses = True

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_with_keyword_only() -> None:
    """Test _create_data_model when keyword_only attribute exists."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.keyword_only = True

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_with_both_frozen_and_keyword_only() -> None:
    """Test _create_data_model when both frozen_dataclasses and keyword_only exist."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.frozen_dataclasses = True
    parser.keyword_only = True

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_with_existing_dataclass_arguments() -> None:
    """Test _create_data_model when existing dataclass_arguments are provided in kwargs."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.frozen_dataclasses = True
    parser.keyword_only = True

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
        dataclass_arguments={"slots": True, "order": True},
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_without_existing_dataclass_arguments() -> None:
    """Test _create_data_model when no existing dataclass_arguments (else branch)."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.frozen_dataclasses = False
    parser.keyword_only = False

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_frozen_and_keyword_only_cleanup() -> None:
    """Test that frozen and keyword_only are popped from kwargs when existing args present."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.frozen_dataclasses = True
    parser.keyword_only = True

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
        dataclass_arguments={"slots": True},
        frozen=False,
        keyword_only=False,
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_with_complex_existing_arguments() -> None:
    """Test _create_data_model with complex existing dataclass_arguments that get merged."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.frozen_dataclasses = True
    parser.keyword_only = True

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
        dataclass_arguments={
            "slots": True,
            "order": True,
            "unsafe_hash": False,
            "match_args": True,
        },
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_none_dataclass_arguments() -> None:
    """Test _create_data_model when dataclass_arguments is explicitly None."""
    parser = JsonSchemaParser(
        "",
        data_model_type=DataClass,
        data_model_root_type=DataClass,
    )
    parser.frozen_dataclasses = True
    parser.keyword_only = True

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
        dataclass_arguments=None,
    )

    assert isinstance(result, DataClass)
    assert result.name == "TestModel"


def test_create_data_model_non_dataclass_with_dataclass_arguments() -> None:
    """Test _create_data_model removes dataclass_arguments for non-DataClass models."""
    parser = JsonSchemaParser(
        "",
        data_model_type=BaseModel,
        data_model_root_type=BaseModel,
    )

    field = DataModelFieldBase(name="test_field", data_type=DataType(type="str"), required=True)

    # Pass dataclass_arguments even though model is not DataClass - should be removed
    result = parser._create_data_model(
        reference=Reference(name="TestModel", path="test_model"),
        fields=[field],
        dataclass_arguments={"frozen": True},
    )

    assert isinstance(result, BaseModel)
    assert result.name == "TestModel"


def test_parse_type_mappings_invalid_format() -> None:
    """Test _parse_type_mappings raises ValueError for invalid format."""
    with pytest.raises(ValueError, match="Invalid type mapping format"):
        Parser._parse_type_mappings(["invalid_without_equals"])


def test_parse_type_mappings_valid_formats() -> None:
    """Test _parse_type_mappings with valid formats."""
    result = Parser._parse_type_mappings(["binary=string", "string+date=string"])
    assert result == {
        ("string", "binary"): "string",
        ("string", "date"): "string",
    }


def test_get_type_with_mappings_to_format() -> None:
    """Test _get_type_with_mappings mapping to a format within type_formats."""
    parser = JsonSchemaParser(
        source="",
        type_mappings=["binary=byte"],
    )
    result = parser._get_type_with_mappings("string", "binary")
    assert result == Types.byte


def test_get_type_with_mappings_to_type_default() -> None:
    """Test _get_type_with_mappings mapping to a top-level type's default."""
    parser = JsonSchemaParser(
        source="",
        type_mappings=["binary=boolean"],
    )
    result = parser._get_type_with_mappings("string", "binary")
    assert result == Types.boolean


def test_get_type_with_mappings_unknown_target_fallback() -> None:
    """Test _get_type_with_mappings falls back to _get_type for unknown target."""
    parser = JsonSchemaParser(
        source="",
        type_mappings=["binary=unknown_format"],
    )
    result = parser._get_type_with_mappings("string", "binary")
    assert result == Types.binary


@pytest.mark.parametrize(
    ("frozen_dataclasses", "keyword_only", "parser_dataclass_args", "kwargs_dataclass_args", "expected"),
    [
        (False, False, None, None, {}),
        (True, False, None, None, {"frozen": True}),
        (False, True, None, None, {"kw_only": True}),
        (True, True, None, None, {"frozen": True, "kw_only": True}),
        (False, False, {"slots": True}, None, {"slots": True}),
        (True, True, {"slots": True}, None, {"slots": True}),
        (True, True, {"slots": True}, {"order": True}, {"order": True}),
    ],
)
def test_create_data_model_dataclass_arguments(
    frozen_dataclasses: bool,
    keyword_only: bool,
    parser_dataclass_args: dict | None,
    kwargs_dataclass_args: dict | None,
    expected: dict,
) -> None:
    """Test _create_data_model handles dataclass_arguments correctly."""
    parser = JsonSchemaParser(
        source="",
        data_model_type=DataClass,
        frozen_dataclasses=frozen_dataclasses,
        keyword_only=keyword_only,
    )
    parser.dataclass_arguments = parser_dataclass_args

    reference = Reference(path="test", original_name="Test", name="Test")
    kwargs: dict[str, Any] = {"reference": reference, "fields": []}
    if kwargs_dataclass_args is not None:
        kwargs["dataclass_arguments"] = kwargs_dataclass_args
    result = parser._create_data_model(**kwargs)
    assert isinstance(result, DataClass)
    assert result.dataclass_arguments == expected


def test_get_ref_body_from_url_file_unc_path(mocker: MockerFixture) -> None:
    """Test _get_ref_body_from_url handles UNC file:// URLs correctly."""
    parser = JsonSchemaParser("")
    mock_load = mocker.patch(
        "datamodel_code_generator.parser.jsonschema.load_data_from_path",
        return_value={"type": "object"},
    )

    result = parser._get_ref_body_from_url("file://server/share/schemas/pet.json")

    assert result == {"type": "object"}
    mock_load.assert_called_once()
    called_path = mock_load.call_args[0][0]
    # On Windows, UNC paths have \\server\share\ as a single "drive" part
    # On POSIX, they're separate: /, server, share, schemas, pet.json
    path_str = str(called_path)
    assert "server" in path_str
    assert "share" in path_str
    assert called_path.parts[-2:] == ("schemas", "pet.json")


def test_get_ref_body_from_url_file_local_path(mocker: MockerFixture) -> None:
    """Test _get_ref_body_from_url handles local file:// URLs (no netloc)."""
    parser = JsonSchemaParser("")
    mock_load = mocker.patch(
        "datamodel_code_generator.parser.jsonschema.load_data_from_path",
        return_value={"type": "string"},
    )

    result = parser._get_ref_body_from_url("file:///home/user/schemas/pet.json")

    assert result == {"type": "string"}
    mock_load.assert_called_once()
    called_path = mock_load.call_args[0][0]
    assert called_path.parts[-4:] == ("home", "user", "schemas", "pet.json")


def test_merge_ref_with_schema_no_ref() -> None:
    """Test _merge_ref_with_schema returns object unchanged when no $ref is present."""
    parser = JsonSchemaParser("")
    obj = model_validate(JsonSchemaObject, {"type": "string", "minLength": 5})
    result = parser._merge_ref_with_schema(obj)
    assert result is obj


def test_has_ref_with_schema_keywords_extras_with_schema_affecting_keys() -> None:
    """Test has_ref_with_schema_keywords when extras contains schema-affecting keys."""
    # const is stored in extras and is schema-affecting
    obj = model_validate(
        JsonSchemaObject,
        {
            "$ref": "#/$defs/Base",
            "const": "active",
        },
    )
    # Verify extras contains schema-affecting key
    assert obj.extras
    assert "const" in obj.extras
    assert obj.has_ref_with_schema_keywords is True


def test_has_ref_with_schema_keywords_extras_with_metadata_only_keys() -> None:
    """Test has_ref_with_schema_keywords when extras contains only metadata keys."""
    # $comment is metadata-only, should not trigger merge
    obj = model_validate(
        JsonSchemaObject,
        {
            "$ref": "#/$defs/Base",
            "$comment": "this is a comment",
        },
    )
    # Verify extras contains only metadata key
    assert obj.extras
    assert "$comment" in obj.extras
    assert obj.has_ref_with_schema_keywords is False


def test_has_ref_with_schema_keywords_no_extras() -> None:
    """Test has_ref_with_schema_keywords when extras is empty."""
    # Only $ref and a schema-affecting field, no extras
    obj = model_validate(
        JsonSchemaObject,
        {
            "$ref": "#/$defs/Base",
            "minLength": 10,
        },
    )
    # Verify extras is empty but minLength triggers merge
    assert not obj.extras
    assert obj.has_ref_with_schema_keywords is True


def test_parse_combined_schema_anyof_with_ref_and_schema_keywords() -> None:
    """Test parse_combined_schema merges $ref with schema-affecting keywords in anyOf."""
    parser = JsonSchemaParser("")
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "value": {
                "anyOf": [
                    {
                        "$ref": "#/$defs/BaseString",
                        "minLength": 10,
                    },
                    {
                        "type": "integer",
                    },
                ]
            }
        },
        "$defs": {
            "BaseString": {
                "type": "string",
                "maxLength": 100,
            }
        },
    }
    parser.parse_raw_obj("Model", schema, [])
    results = list(parser.results)
    assert len(results) >= 1


def test_parse_enum_empty_enum_not_nullable() -> None:
    """Test parse_enum returns null type when enum_fields is empty and not nullable."""
    parser = JsonSchemaParser("")
    obj = model_validate(JsonSchemaObject, {"type": "integer", "enum": []})
    result = parser.parse_enum("EmptyEnum", obj, ["EmptyEnum"])
    assert result.type == "None"


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "array", "items": {"type": "string"}}, False),
        ({"allOf": [{"type": "string"}]}, False),
        ({"oneOf": [{"type": "string"}]}, False),
        ({"anyOf": [{"type": "string"}]}, False),
        ({"properties": {"name": {"type": "string"}}}, False),
        ({"patternProperties": {".*": {"type": "string"}}}, False),
        ({"type": "object"}, False),
        ({"enum": ["a", "b"]}, False),
        ({"type": "string"}, True),
        ({"type": "string", "minLength": 1}, True),
    ],
)
def test_is_root_model_schema(schema: dict[str, Any], expected: bool) -> None:
    """Test _is_root_model_schema returns correct value for various schema types."""
    parser = JsonSchemaParser("")
    obj = model_validate(JsonSchemaObject, schema)
    assert parser._is_root_model_schema(obj) is expected


def test_merge_primitive_schemas_for_allof_single_item() -> None:
    """Test _merge_primitive_schemas_for_allof returns unchanged item when single."""
    parser = JsonSchemaParser("")
    item = model_validate(JsonSchemaObject, {"type": "string", "minLength": 1})
    result = parser._merge_primitive_schemas_for_allof([item])
    assert result == item


def test_merge_primitive_schemas_for_allof_nomerge_mode() -> None:
    """Test _merge_primitive_schemas_for_allof overwrites constraints in NoMerge mode."""
    parser = JsonSchemaParser("")
    parser.allof_merge_mode = AllOfMergeMode.NoMerge
    items = [
        model_validate(JsonSchemaObject, {"type": "string", "pattern": "^a.*"}),
        model_validate(JsonSchemaObject, {"minLength": 5}),
    ]
    result = parser._merge_primitive_schemas_for_allof(items)
    assert result.pattern == "^a.*"
    assert result.minLength == 5


def test_merge_primitive_schemas_for_allof_nomerge_mode_with_format() -> None:
    """Test _merge_primitive_schemas_for_allof handles format in NoMerge mode."""
    parser = JsonSchemaParser("")
    parser.allof_merge_mode = AllOfMergeMode.NoMerge
    items = [
        model_validate(JsonSchemaObject, {"type": "string"}),
        model_validate(JsonSchemaObject, {"format": "email"}),
    ]
    result = parser._merge_primitive_schemas_for_allof(items)
    assert result.format == "email"


def test_merge_primitive_schemas_for_allof_constraints_mode_with_format() -> None:
    """Test _merge_primitive_schemas_for_allof handles format in Constraints mode."""
    parser = JsonSchemaParser("")
    parser.allof_merge_mode = AllOfMergeMode.Constraints
    items = [
        model_validate(JsonSchemaObject, {"type": "string", "pattern": "^a.*"}),
        model_validate(JsonSchemaObject, {"format": "email"}),
    ]
    result = parser._merge_primitive_schemas_for_allof(items)
    assert result.format == "email"


def test_handle_allof_root_model_special_path_marker() -> None:
    """Test _handle_allof_root_model_with_constraints returns None for special path."""
    parser = JsonSchemaParser("")
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"$ref": "#/definitions/Base"},
                {"minLength": 1},
            ]
        },
    )
    path = [f"test{SPECIAL_PATH_MARKER}inline"]
    result = parser._handle_allof_root_model_with_constraints("Test", obj, path)
    assert result is None


def test_handle_allof_root_model_multiple_refs() -> None:
    """Test _handle_allof_root_model_with_constraints returns None for multiple refs."""
    parser = JsonSchemaParser("")
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"$ref": "#/definitions/Base1"},
                {"$ref": "#/definitions/Base2"},
            ]
        },
    )
    result = parser._handle_allof_root_model_with_constraints("Test", obj, ["test"])
    assert result is None


def test_handle_allof_root_model_no_refs() -> None:
    """Test _handle_allof_root_model_with_constraints returns None when no refs."""
    parser = JsonSchemaParser("")
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"type": "string"},
                {"minLength": 1},
            ]
        },
    )
    result = parser._handle_allof_root_model_with_constraints("Test", obj, ["test"])
    assert result is None


def test_handle_allof_root_model_no_constraint_items() -> None:
    """Test _handle_allof_root_model_with_constraints returns None when no constraints."""
    parser = JsonSchemaParser("")
    parser._load_ref_schema_object = lambda _ref: model_validate(JsonSchemaObject, {"type": "string"})
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"$ref": "#/definitions/Base"},
            ]
        },
    )
    result = parser._handle_allof_root_model_with_constraints("Test", obj, ["test"])
    assert result is None


def test_handle_allof_root_model_constraint_with_properties() -> None:
    """Test _handle_allof_root_model_with_constraints returns None when constraint has properties."""
    parser = JsonSchemaParser("")
    parser._load_ref_schema_object = lambda _ref: model_validate(JsonSchemaObject, {"type": "string"})
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"$ref": "#/definitions/Base"},
                {"properties": {"name": {"type": "string"}}},
            ]
        },
    )
    result = parser._handle_allof_root_model_with_constraints("Test", obj, ["test"])
    assert result is None


def test_handle_allof_root_model_constraint_with_items() -> None:
    """Test _handle_allof_root_model_with_constraints returns None when constraint has items."""
    parser = JsonSchemaParser("")
    parser._load_ref_schema_object = lambda _ref: model_validate(JsonSchemaObject, {"type": "string"})
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"$ref": "#/definitions/Base"},
                {"items": {"type": "string"}},
            ]
        },
    )
    result = parser._handle_allof_root_model_with_constraints("Test", obj, ["test"])
    assert result is None


def test_handle_allof_root_model_incompatible_types() -> None:
    """Test _handle_allof_root_model_with_constraints returns None for incompatible types."""
    parser = JsonSchemaParser("")
    parser._load_ref_schema_object = lambda _ref: model_validate(JsonSchemaObject, {"type": "string"})
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"$ref": "#/definitions/Base"},
                {"type": "boolean"},
            ]
        },
    )
    result = parser._handle_allof_root_model_with_constraints("Test", obj, ["test"])
    assert result is None


def test_handle_allof_root_model_ref_to_non_root() -> None:
    """Test _handle_allof_root_model_with_constraints returns None when ref is not root model."""
    parser = JsonSchemaParser("")
    parser._load_ref_schema_object = lambda _ref: model_validate(
        JsonSchemaObject,
        {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
        },
    )
    obj = model_validate(
        JsonSchemaObject,
        {
            "allOf": [
                {"$ref": "#/definitions/Base"},
                {"minLength": 1},
            ]
        },
    )
    result = parser._handle_allof_root_model_with_constraints("Test", obj, ["test"])
    assert result is None


def test_timestamp_with_time_zone_format() -> None:
    """Test that PostgreSQL timestamp with time zone format maps to datetime."""
    from datamodel_code_generator.parser.jsonschema import json_schema_data_formats

    # Verify the format is mapped correctly
    assert json_schema_data_formats["string"]["timestamp with time zone"] == Types.date_time
