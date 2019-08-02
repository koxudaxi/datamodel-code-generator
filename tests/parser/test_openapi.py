from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from datamodel_code_generator.model.base import TemplateBase
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.base import DataType, JsonSchemaObject
from datamodel_code_generator.parser.openapi import (
    OpenAPIParser,
    dump_templates,
    get_data_type,
)

DATA_PATH: Path = Path(__file__).parents[1] / 'data'


class A(TemplateBase):
    def __init__(self, filename: str, data: str):
        self._data = data
        super().__init__(filename)

    def render(self) -> str:
        return self._data


@pytest.mark.parametrize(
    "schema_type,schema_format,result_type",
    [
        ('integer', 'int32', 'int'),
        ('integer', 'int64', 'int'),
        ('number', 'float', 'float'),
        ('number', 'double', 'float'),
        ('number', 'time', 'time'),
        ('string', None, 'str'),
        ('string', 'byte', 'str'),
        ('string', 'binary', 'bytes'),
        ('boolean', None, 'bool'),
        ('string', 'date', 'date'),
        ('string', 'date-time', 'datetime'),
        ('string', 'password', 'SecretStr'),
        ('string', 'email', 'EmailStr'),
        ('string', 'uri', 'UrlStr'),
        ('string', 'uuid', 'UUID'),
        ('string', 'uuid1', 'UUID1'),
        ('string', 'uuid2', 'UUID2'),
        ('string', 'uuid3', 'UUID3'),
        ('string', 'uuid4', 'UUID4'),
        ('string', 'uuid5', 'UUID5'),
        ('string', 'ipv4', 'IPv4Address'),
        ('string', 'ipv6', 'IPv6Address'),
    ],
)
def test_get_data_type(schema_type, schema_format, result_type):
    assert get_data_type(
        JsonSchemaObject(type=schema_type, format=schema_format)
    ) == DataType(type=result_type)


def test_get_data_type_invalid_obj():
    with pytest.raises(ValueError, match='invalid schema object'):
        get_data_type(JsonSchemaObject())


def test_dump_templates():
    with NamedTemporaryFile('w') as dummy_template:
        assert dump_templates(A(dummy_template.name, 'abc')) == 'abc'
        assert (
            dump_templates(
                [A(dummy_template.name, 'abc'), A(dummy_template.name, 'def')]
            )
            == 'abc\n\n\ndef'
        )


@pytest.mark.parametrize(
    "source_obj,generated_classes",
    [
        (
            {'properties': {'name': {'type': 'string'}}},
            '''class Pets(BaseModel):
    name: Optional[str] = None''',
        ),
        (
            {
                'properties': {
                    'kind': {
                        'type': 'object',
                        'properties': {'name': {'type': 'string'}},
                    }
                }
            },
            '''class Kind(BaseModel):
    name: Optional[str] = None


class Pets(BaseModel):
    kind: Optional[Kind] = None''',
        ),
        (
            {
                'properties': {
                    'Kind': {
                        'type': 'object',
                        'properties': {'name': {'type': 'string'}},
                    }
                }
            },
            '''class Kind_(BaseModel):
    name: Optional[str] = None


class Pets(BaseModel):
    Kind: Optional[Kind_] = None''',
        ),
        (
            {
                'properties': {
                    'pet_kind': {
                        'type': 'object',
                        'properties': {'name': {'type': 'string'}},
                    }
                }
            },
            '''class PetKind(BaseModel):
    name: Optional[str] = None


class Pets(BaseModel):
    pet_kind: Optional[PetKind] = None''',
        ),
        (
            {
                'properties': {
                    'kind': {
                        'type': 'object',
                        'items': {
                            'type': 'object',
                            'properties': {'name': {'type': 'string'}},
                        },
                    }
                }
            },
            '''class KindItem(BaseModel):
    name: Optional[str] = None


class Kind(BaseModel):
    __root__: List[KindItem] = None


class Pets(BaseModel):
    kind: Optional[Kind] = None''',
        ),
    ],
)
def test_parse_object(source_obj, generated_classes):
    parser = OpenAPIParser(BaseModel, CustomRootType)
    parsed_templates = parser.parse_object(
        'Pets', JsonSchemaObject.parse_obj(source_obj)
    )
    assert dump_templates(list(parsed_templates)) == generated_classes


@pytest.mark.parametrize(
    "source_obj,generated_classes",
    [
        (
            {
                'type': 'array',
                'items': {'type': 'object', 'properties': {'name': {'type': 'string'}}},
            },
            '''class Pet(BaseModel):
    name: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet] = None''',
        ),
        (
            {
                'type': 'array',
                'items': [
                    {'type': 'object', 'properties': {'name': {'type': 'string'}}}
                ],
            },
            '''class Pet(BaseModel):
    name: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet] = None''',
        ),
    ],
)
def test_parse_array(source_obj, generated_classes):
    parser = OpenAPIParser(BaseModel, CustomRootType)
    parsed_templates = parser.parse_array(
        'Pets', JsonSchemaObject.parse_obj(source_obj)
    )
    assert dump_templates(list(parsed_templates)) == generated_classes


def test_openapi_parser_parse():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, filename=str(DATA_PATH / 'api.yaml')
    )
    assert (
        parser.parse()
        == '''class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet] = None


class User(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Users(BaseModel):
    __root__: List[User] = None


class Id(BaseModel):
    __root__: str = None


class Rules(BaseModel):
    __root__: List[str] = None


class Error(BaseModel):
    code: int
    message: str


class api(BaseModel):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None


class apis(BaseModel):
    __root__: List[api] = None'''
    )
