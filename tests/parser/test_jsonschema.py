from pathlib import Path
from typing import Dict
from unittest.mock import Mock, call

import pytest

from datamodel_code_generator import DataModelField
from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.base import dump_templates
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    get_model_by_path,
)

DATA_PATH: Path = Path(__file__).parents[1] / 'data' / 'jsonschema'


@pytest.mark.parametrize(
    'schema,path,model',
    [
        ({'a': {'foo': 'bar'}}, 'a', {'foo': 'bar'}),
        ({'a': {'b': {'foo': 'bar'}}}, 'a/b', {'foo': 'bar'}),
        ({'a': {'b': {'c': {'foo': 'bar'}}}}, 'a/b', {'c': {'foo': 'bar'}}),
        ({'a': {'b': {'c': {'foo': 'bar'}}}}, 'a/b/c', {'foo': 'bar'}),
    ],
)
def test_get_model_by_path(schema: Dict, path: str, model: Dict):
    assert get_model_by_path(schema, path.split('/')) == model


def test_json_schema_parser_parse_ref():
    parser = JsonSchemaParser(
        BaseModel, CustomRootType, data_model_field_type=DataModelField
    )
    parser.parse_raw_obj = Mock()
    external_parent_path = Path(DATA_PATH / 'external_parent.json')
    parser.base_path = external_parent_path.parent
    parser.excludes_ref_path = set()
    external_parent = external_parent_path.read_text()
    obj = JsonSchemaObject.parse_raw(external_parent)

    parser.parse_ref(obj)
    parser.parse_raw_obj.assert_has_calls(
        [
            call(
                'Yaml',
                {'properties': {'firstName': {'type': 'string'}}, 'type': 'object'},
            ),
            call(
                'Json',
                {'properties': {'firstName': {'type': 'string'}}, 'type': 'object'},
            ),
        ]
    )


def test_json_schema_object_ref_url():
    parser = JsonSchemaParser(
        BaseModel, CustomRootType, data_model_field_type=DataModelField
    )
    obj = JsonSchemaObject.parse_obj({'$ref': 'https://example.org'})
    with pytest.raises(NotImplementedError):
        parser.parse_ref(obj)


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
    parser = JsonSchemaParser(BaseModel, CustomRootType)
    parser.parse_object('Person', JsonSchemaObject.parse_obj(source_obj))
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
    __root__: Any""",
        )
    ],
)
def test_parse_any_root_object(source_obj, generated_classes):
    parser = JsonSchemaParser(
        BaseModel, CustomRootType, data_model_field_type=DataModelField
    )
    parser.parse_root_type('AnyObject', JsonSchemaObject.parse_obj(source_obj))
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    'source_obj,generated_classes',
    [
        (
            {
                "properties": {
                    "item": {
                        "properties": {
                            "timeout": {
                                "oneOf": [{"type": "string"}, {"type": "integer"}]
                            }
                        },
                        "type": "object",
                    }
                }
            },
            """class Item(BaseModel):
    timeout: Optional[Union[str, int]] = None


class OnOfObject(BaseModel):
    item: Optional[Item] = None""",
        )
    ],
)
def test_parse_one_of_object(source_obj, generated_classes):
    parser = JsonSchemaParser(
        BaseModel, CustomRootType, data_model_field_type=DataModelField
    )
    parser.parse_raw_obj('onOfObject', source_obj)
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    'type_,default,expected',
    [
        ('string', 'abc', "'abc'"),
        ('number', 123, 123),
        ('boolean', 'true', True),
        ('boolean', 'false', False),
        ('null', 'null', None),
        ('object', {'abc': 123, 'efg': 'hij'}, {'abc': 123, 'efg': 'hij'}),
    ],
)
def test_typed_default(type_, default, expected):
    assert JsonSchemaObject(type=type_, default=default).typed_default == expected
