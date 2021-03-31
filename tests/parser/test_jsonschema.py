import json
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import call

import pytest
import yaml

from datamodel_code_generator.imports import IMPORT_OPTIONAL, Import
from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.parser.base import dump_templates
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    get_model_by_path,
)
from datamodel_code_generator.types import DataType

DATA_PATH: Path = Path(__file__).parents[1] / 'data' / 'jsonschema'

EXPECTED_JSONSCHEMA_PATH = (
    Path(__file__).parents[1] / 'data' / 'expected' / 'parser' / 'jsonschema'
)


@pytest.mark.parametrize(
    'schema,path,model',
    [
        ({'foo': 'bar'}, None, {'foo': 'bar'}),
        ({'a': {'foo': 'bar'}}, 'a', {'foo': 'bar'}),
        ({'a': {'b': {'foo': 'bar'}}}, 'a/b', {'foo': 'bar'}),
        ({'a': {'b': {'c': {'foo': 'bar'}}}}, 'a/b', {'c': {'foo': 'bar'}}),
        ({'a': {'b': {'c': {'foo': 'bar'}}}}, 'a/b/c', {'foo': 'bar'}),
    ],
)
def test_get_model_by_path(schema: Dict, path: str, model: Dict):
    assert get_model_by_path(schema, path.split('/') if path else []) == model


# def test_json_schema_parser_parse_ref():
#     parser = JsonSchemaParser()
#     parser.parse_raw_obj = Mock()
#     external_parent_path = Path(DATA_PATH / 'external_parent.json')
#     parser.base_path = external_parent_path.parent
#     parser.excludes_ref_path = set()
#     external_parent = external_parent_path.read_text()
#     obj = JsonSchemaObject.parse_raw(external_parent)
#
#     parser.parse_ref(obj, [])
#     # parser.parse_raw_obj.assert_has_calls(
#     #     [
#     #         call(
#     #             'Yaml',
#     #             {'properties': {'firstName': {'type': 'string'}}, 'type': 'object'},
#     #         ),
#     #         call(
#     #             'Json',
#     #             {'properties': {'firstName': {'type': 'string'}}, 'type': 'object'},
#     #         ),
#     #     ]
#     # )


def test_json_schema_object_ref_url_json(mocker):
    parser = JsonSchemaParser('')
    obj = JsonSchemaObject.parse_obj(
        {'$ref': 'https://example.com/person.schema.json#/definitions/User'}
    )
    mock_get = mocker.patch('httpx.get')
    mock_get.return_value.text = json.dumps(
        {
            "$id": "https://example.com/person.schema.json",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "User": {"type": "object", "properties": {"name": {"type": "string",}},}
            },
        },
    )

    parser.parse_ref(obj, ['Model'])
    assert (
        dump_templates(list(parser.results))
        == '''class User(BaseModel):
    name: Optional[str] = None'''
    )
    parser.parse_ref(obj, ['Model'])
    mock_get.assert_has_calls(
        [call('https://example.com/person.schema.json'),]
    )


def test_json_schema_object_ref_url_yaml(mocker):
    parser = JsonSchemaParser('')
    obj = JsonSchemaObject.parse_obj(
        {'$ref': 'https://example.org/schema.yaml#/definitions/User'}
    )
    mock_get = mocker.patch('httpx.get')
    mock_get.return_value.text = yaml.safe_dump(
        json.load((DATA_PATH / 'user.json').open())
    )

    parser.parse_ref(obj, ['User'])
    assert (
        dump_templates(list(parser.results))
        == '''class User(BaseModel):
    name: Optional[str] = Field(None, example='ken')


class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])'''
    )
    parser.parse_ref(obj, [])
    mock_get.assert_called_once_with('https://example.org/schema.yaml',)


def test_json_schema_object_cached_ref_url_yaml(mocker):
    parser = JsonSchemaParser('')

    obj = JsonSchemaObject.parse_obj(
        {
            'type': 'object',
            'properties': {
                'pet': {'$ref': 'https://example.org/schema.yaml#/definitions/Pet'},
                'user': {'$ref': 'https://example.org/schema.yaml#/definitions/User'},
            },
        }
    )
    mock_get = mocker.patch('httpx.get')
    mock_get.return_value.text = yaml.safe_dump(
        json.load((DATA_PATH / 'user.json').open())
    )

    parser.parse_ref(obj, [])
    assert (
        dump_templates(list(parser.results))
        == '''class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])


class User(BaseModel):
    name: Optional[str] = Field(None, example='ken')'''
    )
    mock_get.assert_called_once_with('https://example.org/schema.yaml',)


def test_json_schema_ref_url_json(mocker):
    parser = JsonSchemaParser('')
    obj = {
        "type": "object",
        "properties": {
            "user": {'$ref': 'https://example.org/schema.json#/definitions/User'}
        },
    }
    mock_get = mocker.patch('httpx.get')
    mock_get.return_value.text = json.dumps(json.load((DATA_PATH / 'user.json').open()))

    parser.parse_raw_obj('Model', obj, ['Model'])
    assert (
        dump_templates(list(parser.results))
        == '''class Model(BaseModel):
    user: Optional[User] = None


class User(BaseModel):
    name: Optional[str] = Field(None, example='ken')


class Pet(BaseModel):
    name: Optional[str] = Field(None, examples=['dog', 'cat'])'''
    )
    mock_get.assert_called_once_with('https://example.org/schema.json',)


@pytest.mark.parametrize(
    'source_obj,generated_classes',
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
                    "name": {"type": "string", "description": "The person's name.",},
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
def test_parse_object(source_obj, generated_classes):
    parser = JsonSchemaParser(data_model_field_type=DataModelFieldBase, source='')
    parser.parse_object('Person', JsonSchemaObject.parse_obj(source_obj), [])
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    'source_obj,generated_classes',
    [
        (
            {
                "$id": "https://example.com/person.schema.json",
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "AnyJson",
                "description": "This field accepts any object",
            },
            """class AnyObject(BaseModel):
    __root__: Any = Field(..., description='This field accepts any object')""",
        )
    ],
)
def test_parse_any_root_object(source_obj, generated_classes):
    parser = JsonSchemaParser('')
    parser.parse_root_type('AnyObject', JsonSchemaObject.parse_obj(source_obj), [])
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    'source_obj,generated_classes',
    [
        (
            yaml.safe_load((DATA_PATH / 'oneof.json').read_text()),
            (DATA_PATH / 'oneof.json.snapshot').read_text(),
        )
    ],
)
def test_parse_one_of_object(source_obj, generated_classes):
    parser = JsonSchemaParser('')
    parser.parse_raw_obj('onOfObject', source_obj, [])
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    'source_obj,generated_classes',
    [
        (
            {
                "$id": "https://example.com/person.schema.json",
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "defaults",
                "type": "object",
                "properties": {
                    "string": {"type": "string", "default": "default string",},
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
    number_array: Optional[List] = [1, 2, 3]
    string_array: Optional[List] = ['a', 'b', 'c']
    object: Optional[Dict[str, Any]] = {'key': 'value'}""",
        )
    ],
)
def test_parse_default(source_obj, generated_classes):
    parser = JsonSchemaParser('')
    parser.parse_raw_obj('Defaults', source_obj, [])
    assert dump_templates(list(parser.results)) == generated_classes


def test_parse_nested_array():
    parser = JsonSchemaParser(
        DATA_PATH / 'nested_array.json', data_model_field_type=DataModelFieldBase,
    )
    parser.parse()
    assert (
        dump_templates(list(parser.results))
        == (DATA_PATH / 'nested_array.json.snapshot').read_text()
    )


@pytest.mark.parametrize(
    'schema_type,schema_format,result_type,from_,import_',
    [
        ('integer', 'int32', 'int', None, None),
        ('integer', 'int64', 'int', None, None),
        ('integer', 'unix-time', 'int', None, None),
        ('number', 'float', 'float', None, None),
        ('number', 'double', 'float', None, None),
        ('number', 'time', 'time', 'datetime', 'time'),
        ('string', None, 'str', None, None),
        ('string', 'byte', 'str', None, None),
        ('string', 'binary', 'bytes', None, None),
        ('boolean', None, 'bool', None, None),
        ('string', 'date', 'date', 'datetime', 'date'),
        ('string', 'date-time', 'datetime', 'datetime', 'datetime'),
        ('string', 'password', 'SecretStr', 'pydantic', 'SecretStr'),
        ('string', 'email', 'EmailStr', 'pydantic', 'EmailStr'),
        ('string', 'uri', 'AnyUrl', 'pydantic', 'AnyUrl'),
        ('string', 'uri-reference', 'str', None, None),
        ('string', 'uuid', 'UUID', 'uuid', 'UUID'),
        ('string', 'uuid1', 'UUID1', 'pydantic', 'UUID1'),
        ('string', 'uuid2', 'UUID2', 'pydantic', 'UUID2'),
        ('string', 'uuid3', 'UUID3', 'pydantic', 'UUID3'),
        ('string', 'uuid4', 'UUID4', 'pydantic', 'UUID4'),
        ('string', 'uuid5', 'UUID5', 'pydantic', 'UUID5'),
        ('string', 'ipv4', 'IPv4Address', 'pydantic', 'IPv4Address'),
        ('string', 'ipv6', 'IPv6Address', 'pydantic', 'IPv6Address'),
        ('string', 'unknown-type', 'str', None, None),
    ],
)
def test_get_data_type(schema_type, schema_format, result_type, from_, import_):
    if from_ and import_:
        import_: Optional[Import] = Import(from_=from_, import_=import_)
    else:
        import_ = None

    parser = JsonSchemaParser('')
    assert (
        parser.get_data_type(
            JsonSchemaObject(type=schema_type, format=schema_format)
        ).dict()
        == DataType(type=result_type, import_=import_).dict()
    )


@pytest.mark.parametrize(
    'schema_types,result_types',
    [(['integer', 'number'], ['int', 'float']), (['integer', 'null'], ['int']),],
)
def test_get_data_type_array(schema_types, result_types):
    parser = JsonSchemaParser('')
    assert parser.get_data_type(
        JsonSchemaObject(type=schema_types)
    ) == parser.data_type(
        data_types=[parser.data_type(type=r,) for r in result_types],
        is_optional='null' in schema_types,
        imports=[IMPORT_OPTIONAL] if 'null' in schema_types else [],
    )
