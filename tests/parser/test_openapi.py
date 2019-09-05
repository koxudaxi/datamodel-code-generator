from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

import pytest
from datamodel_code_generator.model.base import TemplateBase
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.base import DataType, JsonSchemaObject
from datamodel_code_generator.parser.openapi import (
    OpenAPIParser,
    dump_templates,
    get_data_type,
)
from datamodel_code_generator.types import Import

DATA_PATH: Path = Path(__file__).parents[1] / 'data'


class A(TemplateBase):
    def __init__(self, filename: str, data: str):
        self._data = data
        super().__init__(filename)

    def render(self) -> str:
        return self._data


@pytest.mark.parametrize(
    "schema_type,schema_format,result_type,from_,import_",
    [
        ('integer', 'int32', 'int', None, None),
        ('integer', 'int64', 'int', None, None),
        ('number', 'float', 'float', None, None),
        ('number', 'double', 'float', None, None),
        ('number', 'time', 'time', None, None),
        ('string', None, 'str', None, None),
        ('string', 'byte', 'str', None, None),
        ('string', 'binary', 'bytes', None, None),
        ('boolean', None, 'bool', None, None),
        ('string', 'date', 'date', 'datetime', 'date'),
        ('string', 'date-time', 'datetime', 'datetime', 'datetime'),
        ('string', 'password', 'SecretStr', 'pydantic', 'SecretStr'),
        ('string', 'email', 'EmailStr', 'pydantic', 'EmailStr'),
        ('string', 'uri', 'UrlStr', 'pydantic', 'UrlStr'),
        ('string', 'uuid', 'UUID', 'pydantic', 'UUID'),
        ('string', 'uuid1', 'UUID1', 'pydantic', 'UUID1'),
        ('string', 'uuid2', 'UUID2', 'pydantic', 'UUID2'),
        ('string', 'uuid3', 'UUID3', 'pydantic', 'UUID3'),
        ('string', 'uuid4', 'UUID4', 'pydantic', 'UUID4'),
        ('string', 'uuid5', 'UUID5', 'pydantic', 'UUID5'),
        ('string', 'ipv4', 'IPv4Address', 'pydantic', 'IPv4Address'),
        ('string', 'ipv6', 'IPv6Address', 'pydantic', 'IPv6Address'),
    ],
)
def test_get_data_type(schema_type, schema_format, result_type, from_, import_):
    if from_ and import_:
        import_obj: Optional[Import] = Import(from_=from_, import_=import_)
    else:
        import_obj = None
    assert get_data_type(
        JsonSchemaObject(type=schema_type, format=schema_format), BaseModel
    ) == DataType(type=result_type, import_=import_obj)


def test_get_data_type_invalid_obj():
    with pytest.raises(ValueError, match='invalid schema object'):
        get_data_type(JsonSchemaObject(), BaseModel)


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
            '''class Kind(BaseModel):
    name: Optional[str] = None


class Pets(BaseModel):
    Kind: Optional[Kind] = None''',
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
                        'type': 'array',
                        'items': [
                            {
                                'type': 'object',
                                'properties': {'name': {'type': 'string'}},
                            }
                        ],
                    }
                }
            },
            '''class KindItem(BaseModel):
    name: Optional[str] = None


class Pets(BaseModel):
    kind: Optional[List[KindItem]] = None''',
        ),
        (
            {'properties': {'kind': {'type': 'array', 'items': []}}},
            '''class Pets(BaseModel):
    kind: Optional[List] = None''',
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
    __root__: List[Pet]''',
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
    __root__: List[Pet]''',
        ),
    ],
)
def test_parse_array(source_obj, generated_classes):
    parser = OpenAPIParser(BaseModel, CustomRootType)
    parsed_templates = parser.parse_array(
        'Pets', JsonSchemaObject.parse_obj(source_obj)
    )
    assert dump_templates(list(parsed_templates)) == generated_classes


@pytest.mark.parametrize(
    "source_obj,generated_classes",
    [
        (
            {'type': 'string', 'nullable': True},
            '''class Name(BaseModel):
    __root__: Optional[str] = None''',
        ),
        (
            {'type': 'string', 'nullable': False},
            '''class Name(BaseModel):
    __root__: str''',
        ),
    ],
)
def test_parse_root_type(source_obj, generated_classes):
    parser = OpenAPIParser(BaseModel, CustomRootType)
    parsed_templates = parser.parse_root_type(
        'Name', JsonSchemaObject.parse_obj(source_obj)
    )
    assert dump_templates(list(parsed_templates)) == generated_classes


@pytest.mark.parametrize(
    "with_import, format_, base_class, result",
    [
        (
            True,
            True,
            None,
            '''from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, UrlStr


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class User(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Users(BaseModel):
    __root__: List[User]


class Id(BaseModel):
    __root__: str


class Rules(BaseModel):
    __root__: List[str]


class Error(BaseModel):
    code: int
    message: str


class api(BaseModel):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None
    apiUrl: Optional[UrlStr] = None
    apiDocumentationUrl: Optional[UrlStr] = None


class apis(BaseModel):
    __root__: List[api]


class Event(BaseModel):
    name: Optional[str] = None


class Result(BaseModel):
    event: Optional[Event] = None
''',
        ),
        (
            False,
            True,
            None,
            '''class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class User(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Users(BaseModel):
    __root__: List[User]


class Id(BaseModel):
    __root__: str


class Rules(BaseModel):
    __root__: List[str]


class Error(BaseModel):
    code: int
    message: str


class api(BaseModel):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None
    apiUrl: Optional[UrlStr] = None
    apiDocumentationUrl: Optional[UrlStr] = None


class apis(BaseModel):
    __root__: List[api]


class Event(BaseModel):
    name: Optional[str] = None


class Result(BaseModel):
    event: Optional[Event] = None
''',
        ),
        (
            True,
            False,
            None,
            '''from typing import List, Optional
from pydantic import BaseModel, UrlStr
from __future__ import annotations


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class User(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Users(BaseModel):
    __root__: List[User]


class Id(BaseModel):
    __root__: str


class Rules(BaseModel):
    __root__: List[str]


class Error(BaseModel):
    code: int
    message: str


class api(BaseModel):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None
    apiUrl: Optional[UrlStr] = None
    apiDocumentationUrl: Optional[UrlStr] = None


class apis(BaseModel):
    __root__: List[api]


class Event(BaseModel):
    name: Optional[str] = None


class Result(BaseModel):
    event: Optional[Event] = None''',
        ),
        (
            True,
            True,
            'custom_module.Base',
            '''from __future__ import annotations

from typing import List, Optional

from pydantic import UrlStr

from custom_module import Base


class Pet(Base):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(Base):
    __root__: List[Pet]


class User(Base):
    id: int
    name: str
    tag: Optional[str] = None


class Users(Base):
    __root__: List[User]


class Id(Base):
    __root__: str


class Rules(Base):
    __root__: List[str]


class Error(Base):
    code: int
    message: str


class api(Base):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None
    apiUrl: Optional[UrlStr] = None
    apiDocumentationUrl: Optional[UrlStr] = None


class apis(Base):
    __root__: List[api]


class Event(Base):
    name: Optional[str] = None


class Result(Base):
    event: Optional[Event] = None
''',
        ),
    ],
)
def test_openapi_parser_parse(with_import, format_, base_class, result):
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        filename=str(DATA_PATH / 'api.yaml'),
        base_class=base_class,
    )
    assert parser.parse(with_import=with_import, format_=format_) == result


@pytest.mark.parametrize(
    "source_obj,generated_classes",
    [
        (
            {'type': 'string', 'nullable': True},
            '''class Name(BaseModel):
    __root__: Optional[str] = None''',
        ),
        (
            {'type': 'string', 'nullable': False},
            '''class Name(BaseModel):
    __root__: str''',
        ),
    ],
)
def test_parse_root_type(source_obj, generated_classes):
    parser = OpenAPIParser(BaseModel, CustomRootType)
    parsed_templates = parser.parse_root_type(
        'Name', JsonSchemaObject.parse_obj(source_obj)
    )
    assert dump_templates(list(parsed_templates)) == generated_classes


def test_openapi_parser_parse_duplicate_models():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, filename=str(DATA_PATH / 'duplicate_models.yaml')
    )
    assert (
        parser.parse()
        == """from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class Error(BaseModel):
    code: int
    message: str


class Event(BaseModel):
    name: Optional[str] = None


class Result(BaseModel):
    event: Optional[Event] = None


class Events(BaseModel):
    __root__: List[Event]


class EventRoot(BaseModel):
    __root__: Event


class EventObject(BaseModel):
    event: Optional[Event] = None


class DuplicateObject1(BaseModel):
    event: Optional[List[Event]] = None


class Event(BaseModel):
    event: Optional[Event] = None


class DuplicateObject2(BaseModel):
    event: Optional[Event] = None


class DuplicateObject3(BaseModel):
    __root__: Event
"""
    )


def test_openapi_parser_parse_resolved_models():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, filename=str(DATA_PATH / 'resolved_models.yaml')
    )
    assert (
        parser.parse()
        == """from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class Error(BaseModel):
    code: int
    message: str


class Resolved(BaseModel):
    resolved: Optional[List[str]] = None
"""
    )


def test_openapi_parser_parse_lazy_resolved_models():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, filename=str(DATA_PATH / 'lazy_resolved_models.yaml')
    )
    assert (
        parser.parse()
        == """from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class Error(BaseModel):
    code: int
    message: str


class Results(BaseModel):
    envets: Optional[List[Events]] = None
    event: Optional[List[Event]] = None


class Events(BaseModel):
    __root__: List[Event]


class Event(BaseModel):
    name: Optional[str] = None
"""
    )


def test_openapi_parser_parse_enum_models():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, filename=str(DATA_PATH / 'enum_models.yaml')
    )
    print(parser.parse())
    assert (
        parser.parse()
        == """from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class Error(BaseModel):
    code: int
    message: str


class Type(Enum):
    a = 'a'
    b = 'b'


class EnumObject(BaseModel):
    type: Optional[Type] = None


class EnumRoot1(Enum):
    a = 'a'
    b = 'b'


class IntEnum1(Enum):
    number_1 = 1
    number_2 = 2
"""
    )
