"""Tests for JSON Schema parser."""

from __future__ import annotations

import json
import socket
from ipaddress import ip_address
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

import pydantic
import pytest
import yaml

from datamodel_code_generator import AllOfMergeMode, Error, ReadOnlyWriteOnlyModelType
from datamodel_code_generator.http import _get_httpx
from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel
from datamodel_code_generator.parser.base import Parser, dump_templates
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    Types,
    _validate_schema_python_import_path,
    get_model_by_path,
)
from datamodel_code_generator.reference import SPECIAL_PATH_MARKER, Reference
from datamodel_code_generator.types import DataType
from tests.conftest import assert_output

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

DATA_PATH: Path = Path(__file__).parents[1] / "data" / "jsonschema"

EXPECTED_JSONSCHEMA_PATH = Path(__file__).parents[1] / "data" / "expected" / "parser" / "jsonschema"


@pytest.fixture(autouse=True)
def block_dns_by_default(mocker: MockerFixture) -> None:
    """Keep tests that mock httpx.get independent from external DNS."""
    mocker.patch("socket.getaddrinfo", side_effect=OSError)


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


def test_get_x_python_import_path_ignores_empty_extension() -> None:
    """Test empty x-python-import metadata is ignored."""
    parser = JsonSchemaParser("")

    assert parser._get_x_python_import_path({}) is None


def test_validate_schema_python_import_path_rejects_non_string() -> None:
    """Test schema import path validation rejects non-string values."""
    with pytest.raises(Error, match="customTypePath must be a dotted Python identifier path: 1"):
        _validate_schema_python_import_path(1, "customTypePath")


def test_json_schema_object_ref_url_json(mocker: MockerFixture) -> None:
    """Test JSON schema object reference with JSON URL."""
    parser = JsonSchemaParser("", allow_remote_refs=True)
    obj = JsonSchemaObject.model_validate({"$ref": "https://example.com/person.schema.json#/definitions/User"})
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
    )
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response")
    mock_fetch.return_value.status_code = 200
    mock_fetch.return_value.headers = {}
    mock_fetch.return_value.text = json.dumps(
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
    mock_fetch.assert_called_once_with(
        _get_httpx(),
        "https://example.com/person.schema.json",
        headers=None,
        verify=True,
        follow_redirects=False,
        query_parameters=None,
        timeout=30.0,
        pinned_host="example.com",
        pinned_ips=(ip_address("93.184.216.34"),),
    )


def test_json_schema_object_ref_url_yaml(mocker: MockerFixture) -> None:
    """Test JSON schema object reference with YAML URL."""
    parser = JsonSchemaParser("", allow_remote_refs=True)
    obj = JsonSchemaObject.model_validate({"$ref": "https://example.org/schema.yaml#/definitions/User"})
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
    )
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response")
    mock_fetch.return_value.status_code = 200
    mock_fetch.return_value.headers = {}
    mock_fetch.return_value.text = yaml.safe_dump(json.load((DATA_PATH / "user.json").open()))

    parser.parse_ref(obj, ["User"])
    assert (
        dump_templates(list(parser.results))
        == """class User(BaseModel):
    name: Optional[str] = Field(None, examples=['ken'])
    pets: List[User] = Field(default_factory=list)


class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])"""
    )
    parser.parse_ref(obj, [])
    mock_fetch.assert_called_once_with(
        _get_httpx(),
        "https://example.org/schema.yaml",
        headers=None,
        verify=True,
        follow_redirects=False,
        query_parameters=None,
        timeout=30.0,
        pinned_host="example.org",
        pinned_ips=(ip_address("93.184.216.34"),),
    )


def test_json_schema_object_cached_ref_url_yaml(mocker: MockerFixture) -> None:
    """Test JSON schema object cached reference with YAML URL."""
    parser = JsonSchemaParser("", allow_remote_refs=True)

    obj = JsonSchemaObject.model_validate(
        {
            "type": "object",
            "properties": {
                "pet": {"$ref": "https://example.org/schema.yaml#/definitions/Pet"},
                "user": {"$ref": "https://example.org/schema.yaml#/definitions/User"},
            },
        },
    )
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
    )
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response")
    mock_fetch.return_value.status_code = 200
    mock_fetch.return_value.headers = {}
    mock_fetch.return_value.text = yaml.safe_dump(json.load((DATA_PATH / "user.json").open()))

    parser.parse_ref(obj, [])
    assert (
        dump_templates(list(parser.results))
        == """class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])


class User(BaseModel):
    name: Optional[str] = Field(None, examples=['ken'])
    pets: List[User] = Field(default_factory=list)"""
    )
    mock_fetch.assert_called_once_with(
        _get_httpx(),
        "https://example.org/schema.yaml",
        headers=None,
        verify=True,
        follow_redirects=False,
        query_parameters=None,
        timeout=30.0,
        pinned_host="example.org",
        pinned_ips=(ip_address("93.184.216.34"),),
    )


def test_json_schema_ref_url_json(mocker: MockerFixture) -> None:
    """Test JSON schema reference with JSON URL."""
    parser = JsonSchemaParser("", allow_remote_refs=True)
    obj = {
        "type": "object",
        "properties": {"user": {"$ref": "https://example.org/schema.json#/definitions/User"}},
    }
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
    )
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response")
    mock_fetch.return_value.status_code = 200
    mock_fetch.return_value.headers = {}
    mock_fetch.return_value.text = json.dumps(json.load((DATA_PATH / "user.json").open()))

    parser.parse_raw_obj("Model", obj, ["Model"])
    assert (
        dump_templates(list(parser.results))
        == """class Model(BaseModel):
    user: Optional[User] = None


class User(BaseModel):
    name: Optional[str] = Field(None, examples=['ken'])
    pets: List[User] = Field(default_factory=list)


class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])"""
    )
    mock_fetch.assert_called_once_with(
        _get_httpx(),
        "https://example.org/schema.json",
        headers=None,
        verify=True,
        follow_redirects=False,
        query_parameters=None,
        timeout=30.0,
        pinned_host="example.org",
        pinned_ips=(ip_address("93.184.216.34"),),
    )


def test_json_schema_ref_url_from_local_http_path(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test HTTP JSON schema references resolved from a local schema store."""
    schema_store = tmp_path / "schemas"
    local_schema = schema_store / "example.com" / "application" / "package" / "element" / "sub-element.json"
    local_schema.parent.mkdir(parents=True)
    local_schema.write_text(
        json.dumps(
            {
                "$id": "http://example.com/application/package/element/sub-element",
                "title": "SubElement",
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    parser = JsonSchemaParser("", allow_remote_refs=False, http_local_ref_path=schema_store)
    mock_get = mocker.patch("httpx.get")

    parser.parse_raw_obj(
        "Model",
        {
            "type": "object",
            "properties": {
                "sub_element": {
                    "$ref": "http://example.com/application/package/element/sub-element",
                },
            },
        },
        ["Model"],
    )

    assert (
        dump_templates(list(parser.results))
        == """class Model(BaseModel):
    sub_element: Optional[SubElement] = None


class SubElement(BaseModel):
    name: Optional[str] = None"""
    )
    mock_get.assert_not_called()


def test_json_schema_ref_url_from_local_http_path_with_extension(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test HTTP JSON schema references with an extension resolved from a local schema store."""
    schema_store = tmp_path / "schemas"
    local_schema = schema_store / "example.com" / "application" / "package" / "element" / "sub-element.json"
    local_schema.parent.mkdir(parents=True)
    local_schema.write_text(
        json.dumps(
            {
                "title": "SubElement",
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                    },
                },
            },
        ),
        encoding="utf-8",
    )

    parser = JsonSchemaParser("", allow_remote_refs=False, http_local_ref_path=schema_store)
    mock_get = mocker.patch("httpx.get")

    assert parser._get_ref_body_from_url("http://example.com/application/package/element/sub-element.json") == {
        "title": "SubElement",
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
        },
    }
    mock_get.assert_not_called()


@pytest.mark.parametrize(
    "ref",
    [
        "http:///application/package/element/sub-element",
        "http://example.com/application/package/../sub-element",
        "http://example.com/..%5C..%5CWindows%5Cwin.ini",
        "http://example.com/path%2Fwith-slash",
    ],
)
def test_json_schema_ref_url_from_local_http_path_invalid_path(tmp_path: Path, ref: str) -> None:
    """Test invalid local HTTP JSON schema reference paths are rejected."""
    parser = JsonSchemaParser("", allow_remote_refs=False, http_local_ref_path=tmp_path)

    with pytest.raises(Error, match="Unsupported local HTTP \\$ref URL path"):
        parser._get_ref_body_from_url(ref)


def test_json_schema_ref_url_from_local_http_path_missing_file(tmp_path: Path) -> None:
    """Test missing local HTTP JSON schema references show the attempted local paths."""
    parser = JsonSchemaParser("", allow_remote_refs=False, http_local_ref_path=tmp_path)

    with pytest.raises(Error, match=r"\$ref local file not found for http://example.com/schema"):
        parser._get_ref_body_from_url("http://example.com/schema")


def test_json_schema_ref_url_from_local_http_path_ignores_non_http_scheme(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test local HTTP path resolution does not handle non-HTTP URL schemes."""
    parser = JsonSchemaParser("", http_local_ref_path=tmp_path)
    mocker.patch.object(parser, "_get_text_from_url", return_value='{"type": "object"}')
    local_http_path = mocker.patch.object(parser, "_get_ref_body_from_local_http_path")

    assert parser._get_ref_body_from_url("ftp://example.com/schema.json") == {"type": "object"}
    local_http_path.assert_not_called()


def test_json_schema_ref_url_from_local_http_path_symlink_escape(tmp_path: Path) -> None:
    """Test local HTTP JSON schema references cannot escape the schema store through symlinks."""
    schema_store = tmp_path / "schemas"
    local_schema = schema_store / "example.com" / "schema.json"
    local_schema.parent.mkdir(parents=True)
    outside_schema = tmp_path / "outside.json"
    outside_schema.write_text('{"type": "object"}', encoding="utf-8")
    try:
        local_schema.symlink_to(outside_schema)
    except OSError as exc:  # pragma: no cover
        pytest.skip(f"symlink creation is not supported: {exc}")

    parser = JsonSchemaParser("", allow_remote_refs=False, http_local_ref_path=schema_store)

    with pytest.raises(Error, match="Unsupported local HTTP \\$ref URL path"):
        parser._get_ref_body_from_url("http://example.com/schema.json")


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
    parser.parse_object("Person", JsonSchemaObject.model_validate(source_obj), [])
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
            """class AnyObject(RootModel[Any]):
    root: Any = Field(..., description='This field accepts any object', discriminator='type', title='AnyJson')""",
        )
    ],
)
def test_parse_any_root_object(source_obj: dict[str, Any], generated_classes: str) -> None:
    """Test parsing any root object."""
    parser = JsonSchemaParser("")
    parser.parse_root_type("AnyObject", JsonSchemaObject.model_validate(source_obj), [])
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
        ("integer", "date-time", "AwareDatetime", "pydantic", "AwareDatetime", False),
        ("integer", "date-time", "AwareDatetime", "pydantic", "AwareDatetime", True),
        ("integer", "unix-time", "int", None, None, False),
        ("number", "float", "float", None, None, False),
        ("number", "double", "float", None, None, False),
        ("number", "time", "time", "datetime", "time", False),
        ("number", "time", "Time", "pendulum", "Time", True),
        ("number", "date-time", "AwareDatetime", "pydantic", "AwareDatetime", False),
        ("number", "date-time", "AwareDatetime", "pydantic", "AwareDatetime", True),
        ("string", None, "str", None, None, False),
        ("string", "byte", "Base64Str", "pydantic", "Base64Str", False),
        ("string", "binary", "bytes", None, None, False),
        ("boolean", None, "bool", None, None, False),
        ("string", "date", "date", "datetime", "date", False),
        ("string", "date", "Date", "pendulum", "Date", True),
        ("string", "date-time", "AwareDatetime", "pydantic", "AwareDatetime", False),
        ("string", "date-time", "AwareDatetime", "pydantic", "AwareDatetime", True),
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
        ("string", "uuid2", "UUID", "uuid", "UUID", False),
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
    assert (
        parser.get_data_type(JsonSchemaObject(type=schema_type, format=schema_format)).model_dump()
        == DataType(type=result_type, import_=import_).model_dump()
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
    assert (
        parser.get_data_type(JsonSchemaObject(type=schema_types)).model_dump()
        == parser.data_type(
            data_types=[
                parser.data_type(
                    type=r,
                )
                for r in result_types
            ],
            is_optional="null" in schema_types,
        ).model_dump()
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
    parser.parse_object("Person", AltJsonSchemaObject.model_validate(source_obj), [])
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
    parser = JsonSchemaParser("", allow_remote_refs=True)
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
    parser = JsonSchemaParser("", allow_remote_refs=True)
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
    obj = JsonSchemaObject.model_validate({"type": "string", "minLength": 5})
    result = parser._merge_ref_with_schema(obj)
    assert result is obj


def test_has_ref_with_schema_keywords_extras_with_schema_affecting_keys() -> None:
    """Test has_ref_with_schema_keywords when extras contains schema-affecting keys."""
    # const is stored in extras and is schema-affecting
    obj = JsonSchemaObject.model_validate(
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
    obj = JsonSchemaObject.model_validate(
        {
            "$ref": "#/$defs/Base",
            "$comment": "this is a comment",
        },
    )
    # Verify extras contains only metadata key
    assert obj.extras
    assert "$comment" in obj.extras
    assert obj.has_ref_with_schema_keywords is False


def test_has_ref_with_schema_keywords_extras_with_extension_keys() -> None:
    """Test has_ref_with_schema_keywords when extras contains only x-* extension keys.

    OpenAPI/JSON Schema extension fields (x-*) should be treated as metadata
    and not trigger schema merging, which prevents infinite recursion with
    self-referencing schemas.
    """
    # x-* extensions are vendor extensions, should not trigger merge
    obj = JsonSchemaObject.model_validate(
        {
            "$ref": "#/$defs/Base",
            "deprecated": False,  # metadata-only field
            "x-internalAPI": False,  # extension field
            "x-custom-field": "value",  # another extension field
        },
    )
    # Verify extras contains extension keys
    assert obj.extras
    assert "x-internalAPI" in obj.extras
    assert "x-custom-field" in obj.extras
    # Extension fields should NOT trigger schema merge
    assert obj.has_ref_with_schema_keywords is False


def test_has_ref_with_schema_keywords_no_extras() -> None:
    """Test has_ref_with_schema_keywords when extras is empty."""
    # Only $ref and a schema-affecting field, no extras
    obj = JsonSchemaObject.model_validate(
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
    obj = JsonSchemaObject.model_validate({"type": "integer", "enum": []})
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
    obj = JsonSchemaObject.model_validate(schema)
    assert parser._is_root_model_schema(obj) is expected


def test_merge_primitive_schemas_for_allof_single_item() -> None:
    """Test _merge_primitive_schemas_for_allof returns unchanged item when single."""
    parser = JsonSchemaParser("")
    item = JsonSchemaObject.model_validate({"type": "string", "minLength": 1})
    result = parser._merge_primitive_schemas_for_allof([item])
    assert result == item


def test_merge_primitive_schemas_for_allof_nomerge_mode() -> None:
    """Test _merge_primitive_schemas_for_allof overwrites constraints in NoMerge mode."""
    parser = JsonSchemaParser("")
    parser.allof_merge_mode = AllOfMergeMode.NoMerge
    items = [
        JsonSchemaObject.model_validate({"type": "string", "pattern": "^a.*"}),
        JsonSchemaObject.model_validate({"minLength": 5}),
    ]
    result = parser._merge_primitive_schemas_for_allof(items)
    assert result.pattern == "^a.*"
    assert result.minLength == 5


def test_merge_primitive_schemas_for_allof_nomerge_mode_with_format() -> None:
    """Test _merge_primitive_schemas_for_allof handles format in NoMerge mode."""
    parser = JsonSchemaParser("")
    parser.allof_merge_mode = AllOfMergeMode.NoMerge
    items = [
        JsonSchemaObject.model_validate({"type": "string"}),
        JsonSchemaObject.model_validate({"format": "email"}),
    ]
    result = parser._merge_primitive_schemas_for_allof(items)
    assert result.format == "email"


def test_merge_primitive_schemas_for_allof_constraints_mode_with_format() -> None:
    """Test _merge_primitive_schemas_for_allof handles format in Constraints mode."""
    parser = JsonSchemaParser("")
    parser.allof_merge_mode = AllOfMergeMode.Constraints
    items = [
        JsonSchemaObject.model_validate({"type": "string", "pattern": "^a.*"}),
        JsonSchemaObject.model_validate({"format": "email"}),
    ]
    result = parser._merge_primitive_schemas_for_allof(items)
    assert result.format == "email"


def test_handle_allof_root_model_special_path_marker() -> None:
    """Test _handle_allof_root_model_with_constraints returns None for special path."""
    parser = JsonSchemaParser("")
    obj = JsonSchemaObject.model_validate(
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
    obj = JsonSchemaObject.model_validate(
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
    obj = JsonSchemaObject.model_validate(
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
    parser._load_ref_schema_object = lambda _ref: JsonSchemaObject.model_validate({"type": "string"})
    obj = JsonSchemaObject.model_validate(
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
    parser._load_ref_schema_object = lambda _ref: JsonSchemaObject.model_validate({"type": "string"})
    obj = JsonSchemaObject.model_validate(
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
    parser._load_ref_schema_object = lambda _ref: JsonSchemaObject.model_validate({"type": "string"})
    obj = JsonSchemaObject.model_validate(
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
    parser._load_ref_schema_object = lambda _ref: JsonSchemaObject.model_validate({"type": "string"})
    obj = JsonSchemaObject.model_validate(
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
    parser._load_ref_schema_object = lambda _ref: JsonSchemaObject.model_validate(
        {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
        },
    )
    obj = JsonSchemaObject.model_validate(
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


@pytest.mark.parametrize(
    "format_",
    [
        "idn-hostname",
        "iri",
        "iri-reference",
        "uri-template",
        "json-pointer",
        "relative-json-pointer",
        "regex",
    ],
)
def test_json_schema_standard_string_formats_map_to_string(format_: str) -> None:
    """Test standard JSON Schema string formats without dedicated Python types."""
    from datamodel_code_generator.parser.jsonschema import json_schema_data_formats

    assert json_schema_data_formats["string"][format_] == Types.string


@pytest.mark.parametrize(
    ("x_python_type", "expected"),
    [
        # Direct matches for special container types
        ("Set[str]", {"is_set": True}),
        ("set[int]", {"is_set": True}),
        ("FrozenSet[int]", {"is_frozen_set": True}),
        ("frozenset[str]", {"is_frozen_set": True}),
        ("Sequence[str]", {"is_sequence": True}),
        ("MutableSequence[int]", {"is_sequence": True}),
        ("Mapping[str, int]", {"is_mapping": True}),
        ("MutableMapping[str, int]", {"is_mapping": True}),
        ("AbstractSet[str]", {"is_frozen_set": True}),
        ("MutableSet[int]", {"is_set": True}),
        # Union with special container type
        ("Union[Set[str], None]", {"is_set": True}),
        ("Optional[FrozenSet[int]]", {"is_frozen_set": True}),
        ("Set[int] | None", {"is_set": True}),
        ("Sequence[str] | int", {"is_sequence": True}),
        # Union without special container type (loop completes without match)
        ("Union[str, int]", {}),
        ("str | int", {}),
        ("Optional[str]", {}),
        ("Union[str, int, float]", {}),
        ("Union[List[str], None]", {}),  # List is not a special container
        ("Optional[Dict[str, int]]", {}),  # Dict is not a special container
        # Non-special container types
        ("List[str]", {}),
        ("Dict[str, int]", {}),
        ("Literal[-1]", {}),
        ("str", {}),
        ("int", {}),
        ("CustomType", {}),
    ],
)
def test_get_python_type_flags(x_python_type: str, expected: dict[str, bool]) -> None:
    """Test _get_python_type_flags extracts collection flags correctly."""
    parser = JsonSchemaParser("")
    obj = JsonSchemaObject.model_validate({"x-python-type": x_python_type})
    result = parser._get_python_type_flags(obj)
    assert result == expected


def test_merge_type_modifiers_preserves_container_flags() -> None:
    """Test inherited field type replacement preserves all container modifiers."""
    parser = JsonSchemaParser("")
    new_type = DataType(type="str")
    current_type = DataType(
        is_optional=True,
        is_dict=True,
        is_list=True,
        is_set=True,
        is_frozen_set=True,
        is_mapping=True,
        is_sequence=True,
    )

    parser._merge_type_modifiers(new_type, current_type)

    assert new_type.is_optional
    assert new_type.is_dict
    assert new_type.is_list
    assert new_type.is_set
    assert new_type.is_frozen_set
    assert new_type.is_mapping
    assert new_type.is_sequence


def test_resolve_type_import_from_defs() -> None:
    """Test _resolve_type_import_from_defs resolves imports from $defs with x-python-import."""
    schema_dict: dict[str, Any] = {
        "type": "object",
        "properties": {"status": {"$ref": "#/$defs/Status"}},
        "$defs": {
            "Status": {
                "type": "string",
                "enum": ["active", "inactive"],
                "x-python-import": {"module": "myapp.enums", "name": "Status"},
            }
        },
    }
    parser = JsonSchemaParser(json.dumps(schema_dict))
    parser.raw_obj = schema_dict  # Set raw_obj for _load_ref_schema_object to work

    # Call _resolve_type_import_from_defs directly
    result = parser._resolve_type_import_from_defs("Status")
    assert result is not None
    assert result.from_ == "myapp.enums"
    assert result.import_ == "Status"


def test_resolve_type_import_from_defs_not_found() -> None:
    """Test _resolve_type_import_from_defs returns None when type not in $defs."""
    schema_dict: dict[str, Any] = {"type": "object", "properties": {"name": {"type": "string"}}}
    parser = JsonSchemaParser(json.dumps(schema_dict))
    parser.raw_obj = schema_dict

    result = parser._resolve_type_import_from_defs("NonExistentType")
    assert result is None


def test_resolve_type_import_from_defs_no_x_python_import() -> None:
    """Test _resolve_type_import_from_defs returns None when $defs entry has no x-python-import."""
    schema_dict: dict[str, Any] = {
        "type": "object",
        "properties": {"status": {"$ref": "#/$defs/Status"}},
        "$defs": {"Status": {"type": "string", "enum": ["active", "inactive"]}},
    }
    parser = JsonSchemaParser(json.dumps(schema_dict))
    parser.raw_obj = schema_dict

    result = parser._resolve_type_import_from_defs("Status")
    assert result is None


def test_resolve_type_import_from_defs_exception_handling() -> None:
    """Test _resolve_type_import_from_defs handles exceptions gracefully.

    When raw_obj is None or invalid, _load_ref_schema_object will raise an exception,
    and _resolve_type_import_from_defs should catch it and return None.
    """
    schema_dict: dict[str, Any] = {"type": "object", "properties": {"name": {"type": "string"}}}
    parser = JsonSchemaParser(json.dumps(schema_dict))
    # Set raw_obj to None to trigger exception in _load_ref_schema_object
    parser.raw_obj = None  # pyright: ignore[reportAttributeAccessIssue]

    result = parser._resolve_type_import_from_defs("SomeType")
    assert result is None


def test_jsonschema_parser_edge_case_helpers() -> None:
    """Cover helper branches for boolean schemas and complex JSON values."""
    parser = JsonSchemaParser("", use_tuple_for_fixed_items=True)

    assert not parser._is_fixed_length_tuple(
        JsonSchemaObject.model_validate({
            "type": "array",
            "items": [{"type": "string"}, False],
            "minItems": 2,
            "maxItems": 2,
        })
    )
    assert JsonSchemaParser._property_names_forbids_all_keys(JsonSchemaObject.model_validate({"type": ["integer"]}))
    assert JsonSchemaParser._get_contains_count_constraints(JsonSchemaObject.model_validate({})) == (None, None)
    assert JsonSchemaParser._get_array_items_constraints(
        JsonSchemaObject.model_validate({"contains": True, "minContains": 1, "minItems": 2})
    ) == {"minItems": 2}
    assert parser._get_data_type_from_json_value(object()).type_hint == "Any"


def test_anchor_ref_path_escapes_json_pointer_segments() -> None:
    """Test anchor ref paths escape JSON Pointer segments."""
    parser = JsonSchemaParser("")

    assert parser._anchor_ref_path((), ["#", "$defs", "foo/bar", "tilde~key"]) == "#/$defs/foo~1bar/tilde~0key"

    parser.model_resolver.set_current_root([])
    parser._recursive_anchor_index[()] = ["#/$defs/foo~1bar"]
    recursive_ref = JsonSchemaObject.model_validate({"$recursiveRef": "#"})
    assert parser._resolve_recursive_ref(recursive_ref, ["#", "$defs", "foo/bar", "child"]) == "#/$defs/foo~1bar"


def test_preload_property_refs_skips_external_ref_mapping(tmp_path: Path, mocker: MockerFixture) -> None:
    """Test read/write preload does not load refs handled by external mapping."""
    external_schema = tmp_path / "external.json"
    parser = JsonSchemaParser(
        "",
        external_ref_mapping={str(external_schema): "external.models"},
        read_only_write_only_model_type=ReadOnlyWriteOnlyModelType.RequestResponse,
    )
    load_ref = mocker.patch.object(parser, "_load_ref_schema_object")

    parser._preload_property_refs_for_rw_models(
        JsonSchemaObject.model_validate({
            "properties": {
                "mapped": {"$ref": f"{external_schema}#/External"},
                "local": {"$ref": "#/$defs/Local"},
            },
        })
    )

    load_ref.assert_called_once_with("#/$defs/Local")


def test_json_schema_object_x_property_names_dict() -> None:
    """Test OpenAPI x-propertyNames dict is normalized to propertyNames."""
    obj = JsonSchemaObject.model_validate({"x-propertyNames": {"type": "string", "pattern": "^x-"}})
    ignored = JsonSchemaObject.model_validate({"x-propertyNames": "ignored"})

    assert isinstance(obj.propertyNames, JsonSchemaObject)
    assert obj.propertyNames.pattern == "^x-"
    assert "x-propertyNames" not in obj.extras
    assert ignored.propertyNames is None
    assert "x-propertyNames" not in ignored.extras


def test_set_additional_properties_schema_allows_extra_without_typed_runtime() -> None:
    """Test schema-valued additionalProperties allows extras without typed extra validation."""
    parser = JsonSchemaParser("", use_closed_typed_dict=False)
    parser.extra_template_data["#/Model"] = {}
    parser.set_additional_properties(
        "#/Model",
        JsonSchemaObject.model_validate({"additionalProperties": {"type": "string"}}),
    )
    assert parser.extra_template_data["#/Model"] == {"additionalProperties": True}


def test_set_additional_properties_schema_keeps_typed_dict_extra_items_metadata() -> None:
    """Test schema-valued additionalProperties still feeds PEP 728 TypedDict metadata."""
    parser = JsonSchemaParser("", use_closed_typed_dict=True)
    parser.extra_template_data["#/Model"] = {}

    parser.set_additional_properties(
        "#/Model",
        JsonSchemaObject.model_validate({"additionalProperties": {"type": "string"}}),
    )

    assert parser.extra_template_data["#/Model"] == {
        "additionalProperties": True,
        "additionalPropertiesType": "str",
        "use_typeddict_backport": True,
    }


def test_set_unevaluated_properties_schema_allows_extra_without_typed_runtime() -> None:
    """Test schema-valued unevaluatedProperties allows extras without typed extra validation."""
    parser = JsonSchemaParser("")
    parser.extra_template_data["#/Model"] = {}

    parser.set_unevaluated_properties(
        "#/Model",
        JsonSchemaObject.model_validate({"unevaluatedProperties": {"type": "integer"}}),
    )

    assert parser.extra_template_data["#/Model"] == {"unevaluatedProperties": True}


def test_standard_schema_metadata_is_included_in_field_extras() -> None:
    """Test standard metadata keys are preserved as field extras by default."""
    parser = JsonSchemaParser("")
    obj = JsonSchemaObject.model_validate({
        "type": "string",
        "contentEncoding": "base64",
        "contentMediaType": "application/json",
        "contentSchema": {"type": "object"},
        "externalDocs": {"url": "https://example.com/field"},
        "xml": {"name": "field"},
    })

    assert parser.get_field_extras(obj) == {
        "contentEncoding": "base64",
        "contentMediaType": "application/json",
        "contentSchema": {"type": "object"},
        "externalDocs": {"url": "https://example.com/field"},
        "xml": {"name": "field"},
    }


def test_field_extra_keys_without_x_prefix_removes_exact_prefix() -> None:
    """Test x-prefixed field extras remove only the exact extension prefix."""
    parser = JsonSchemaParser("", field_extra_keys_without_x_prefix={"x-xml"})
    obj = JsonSchemaObject.model_validate({"type": "string", "x-xml": {"name": "field"}})

    assert parser.get_field_extras(obj) == {"xml": {"name": "field"}}


def test_standard_schema_metadata_is_included_in_model_extras() -> None:
    """Test standard metadata keys are preserved as model extras by default."""
    parser = JsonSchemaParser("")
    parser.extra_template_data["#/Model"] = {}
    obj = JsonSchemaObject.model_validate({
        "type": "object",
        "externalDocs": {"url": "https://example.com/model"},
        "xml": {"name": "model"},
    })

    parser.set_schema_extensions("#/Model", obj)

    assert parser.extra_template_data["#/Model"] == {
        "model_extras": {
            "externalDocs": {"url": "https://example.com/model"},
            "xml": {"name": "model"},
        }
    }


@pytest.mark.parametrize(
    ("schema", "type_hint"),
    [
        ({"allOf": [True]}, "Any"),
        ({"enum": ["x"]}, "Literal['x']"),
        ({"allOf": [True, {"type": "string"}]}, "str"),
        ({"type": "array", "prefixItems": [{"type": "string"}], "items": True}, "List[Union[str, Any]]"),
        ({"type": "array", "prefixItems": [{"type": "string"}, False], "items": {"type": "integer"}}, "List[str]"),
        ({"type": "array", "prefixItems": [{"type": "string"}]}, "List[str]"),
        (
            {"type": "array", "prefixItems": [{"type": "string"}], "items": {"type": "integer"}},
            "List[Union[str, int]]",
        ),
        (
            {"type": "array", "prefixItems": [{"type": "string"}], "unevaluatedItems": {"type": "integer"}},
            "List[Union[str, int]]",
        ),
        ({"type": "array", "prefixItems": [{"type": "string"}], "unevaluatedItems": True}, "List[Union[str, Any]]"),
        ({"type": "array", "items": [{"type": "string"}], "additionalItems": True}, "List[Union[str, Any]]"),
        ({"type": "array"}, "List[Any]"),
        ({"type": "array", "unevaluatedItems": {"type": "integer"}}, "List[int]"),
        ({"type": "array", "unevaluatedItems": True}, "List[Any]"),
        ({"enum": ["x", {"a": 1}, None]}, "Optional[Union[Literal['x'], Dict[str, int]]]"),
        ({"anyOf": [False, True]}, "Any"),
    ],
)
def test_build_lightweight_type_edge_cases(schema: dict[str, Any], type_hint: str) -> None:
    """Test lightweight type inference for boolean and complex schemas."""
    parser = JsonSchemaParser("")
    data_type = parser._build_lightweight_type(JsonSchemaObject.model_validate(schema))
    assert data_type is not None
    assert data_type.type_hint == type_hint


def test_build_lightweight_type_allof_false() -> None:
    """Test allOf false produces no lightweight type."""
    parser = JsonSchemaParser("")
    assert parser._build_lightweight_type(JsonSchemaObject.model_validate({"allOf": [False]})) is None
    assert parser._build_lightweight_type(JsonSchemaObject.model_validate({"anyOf": [False]})) is None


def test_parse_array_fields_with_prefix_and_unevaluated_schema() -> None:
    """Test array field parsing combines prefix items with unevaluatedItems schema."""
    parser = JsonSchemaParser("")
    field = parser.parse_array_fields(
        "Model",
        JsonSchemaObject.model_validate({
            "type": "array",
            "prefixItems": [{"type": "string"}],
            "unevaluatedItems": {"type": "integer"},
        }),
        ["#"],
    )
    assert field.data_type.type_hint == "List[Union[str, int]]"


def test_parse_enum_as_literal_with_literal_and_complex_values() -> None:
    """Test literal enum parsing keeps scalar literals and infers complex value types."""
    parser = JsonSchemaParser("")
    data_type = parser.parse_enum_as_literal(JsonSchemaObject.model_validate({"enum": ["x", {"a": 1}, None]}))
    assert data_type.type_hint == "Optional[Union[Literal['x'], Dict[str, int]]]"
