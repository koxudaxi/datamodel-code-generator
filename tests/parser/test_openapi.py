from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional

import pytest

from datamodel_code_generator import PythonVersion
from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.base import TemplateBase
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.base import DataType, dump_templates
from datamodel_code_generator.parser.jsonschema import JsonSchemaObject
from datamodel_code_generator.parser.openapi import OpenAPIParser

DATA_PATH: Path = Path(__file__).parents[1] / 'data' / 'openapi'


class A(TemplateBase):
    def __init__(self, filename: str, data: str):
        self._data = data
        super().__init__(Path(filename))

    def render(self) -> str:
        return self._data


@pytest.mark.parametrize(
    'schema_type,schema_format,result_type,from_,import_',
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
        ('string', 'uri', 'AnyUrl', 'pydantic', 'AnyUrl'),
        ('string', 'uuid', 'UUID', 'uuid', 'UUID'),
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
        imports_: Optional[List[Import]] = [Import(from_=from_, import_=import_)]
    else:
        imports_ = None

    parser = OpenAPIParser(BaseModel, CustomRootType)
    assert parser.get_data_type(
        JsonSchemaObject(type=schema_type, format=schema_format)
    ) == [DataType(type=result_type, imports_=imports_)]


@pytest.mark.parametrize(
    'schema_types,result_types',
    [(['integer', 'number'], ['int', 'float']), (['integer', 'null'], ['int']),],
)
def test_get_data_type_array(schema_types, result_types):
    parser = OpenAPIParser(BaseModel, CustomRootType)
    assert parser.get_data_type(JsonSchemaObject(type=schema_types)) == [
        DataType(type=r) for r in result_types
    ]


def test_get_data_type_invalid_obj():
    with pytest.raises(ValueError, match='invalid schema object'):
        parser = OpenAPIParser(BaseModel, CustomRootType)
        assert parser.get_data_type(JsonSchemaObject())


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
    'source_obj,generated_classes',
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
    parser.parse_object('Pets', JsonSchemaObject.parse_obj(source_obj))
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    'source_obj,generated_classes',
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
    parser.parse_array('Pets', JsonSchemaObject.parse_obj(source_obj))
    assert dump_templates(list(parser.results)) == generated_classes


@pytest.mark.parametrize(
    'source_obj,generated_classes',
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
    'with_import, format_, base_class, result',
    [
        (
            True,
            True,
            None,
            '''from __future__ import annotations

from typing import List, Optional

from pydantic import AnyUrl, BaseModel


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
    apiUrl: Optional[AnyUrl] = None
    apiDocumentationUrl: Optional[AnyUrl] = None


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
    apiUrl: Optional[AnyUrl] = None
    apiDocumentationUrl: Optional[AnyUrl] = None


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
            '''from pydantic import AnyUrl, BaseModel
from typing import List, Optional
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
    apiUrl: Optional[AnyUrl] = None
    apiDocumentationUrl: Optional[AnyUrl] = None


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

from pydantic import AnyUrl

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
    apiUrl: Optional[AnyUrl] = None
    apiDocumentationUrl: Optional[AnyUrl] = None


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
        text=Path(DATA_PATH / 'api.yaml').read_text(),
        base_class=base_class,
    )
    assert parser.parse(with_import=with_import, format_=format_) == result


@pytest.mark.parametrize(
    'source_obj,generated_classes',
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
    parser.parse_root_type('Name', JsonSchemaObject.parse_obj(source_obj))
    assert dump_templates(list(parser.results)) == generated_classes


def test_openapi_parser_parse_duplicate_models():
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'duplicate_models.yaml').read_text(),
    )
    assert (
        parser.parse()
        == '''from __future__ import annotations

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


class Event_1(BaseModel):
    event: Optional[Event] = None


class DuplicateObject2(BaseModel):
    event: Optional[Event_1] = None


class DuplicateObject3(BaseModel):
    __root__: Event
'''
    )


def test_openapi_parser_parse_resolved_models():
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'resolved_models.yaml').read_text(),
    )
    assert (
        parser.parse()
        == '''from __future__ import annotations

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
'''
    )


def test_openapi_parser_parse_lazy_resolved_models():
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'lazy_resolved_models.yaml').read_text(),
    )
    assert (
        parser.parse()
        == '''from __future__ import annotations

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
    event: Optional[Event] = None


class Events(BaseModel):
    __root__: List[Event]


class Results(BaseModel):
    envets: Optional[List[Events]] = None
    event: Optional[List[Event]] = None
'''
    )


def test_openapi_parser_parse_enum_models():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, text=Path(DATA_PATH / 'enum_models.yaml').read_text()
    )
    assert (
        parser.parse()
        == '''from __future__ import annotations

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


class EnumRoot(Enum):
    a = 'a'
    b = 'b'


class IntEnum(Enum):
    number_1 = 1
    number_2 = 2


class AliasEnum(Enum):
    a = 1
    b = 2
    c = 3
'''
    )

    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'enum_models.yaml').read_text(),
        target_python_version=PythonVersion.PY_36,
    )
    assert (
        parser.parse()
        == '''from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List['Pet']


class Error(BaseModel):
    code: int
    message: str


class Type(Enum):
    a = 'a'
    b = 'b'


class EnumObject(BaseModel):
    type: Optional['Type'] = None


class EnumRoot(Enum):
    a = 'a'
    b = 'b'


class IntEnum(Enum):
    number_1 = 1
    number_2 = 2


class AliasEnum(Enum):
    a = 1
    b = 2
    c = 3
'''
    )


def test_openapi_parser_parse_anyof():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, text=Path(DATA_PATH / 'anyof.yaml').read_text()
    )
    assert (
        parser.parse()
        == '''from __future__ import annotations

from datetime import date
from typing import List, Optional, Union

from pydantic import BaseModel


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Car(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class AnyOfItemItem(BaseModel):
    name: Optional[str] = None


class AnyOfItem(BaseModel):
    __root__: Union[Pet, Car, AnyOfItemItem]


class itemItem(BaseModel):
    name: Optional[str] = None


class AnyOfobj(BaseModel):
    item: Optional[Union[Pet, Car, itemItem]] = None


class AnyOfArrayItem(BaseModel):
    name: Optional[str] = None
    birthday: Optional[date] = None


class AnyOfArray(BaseModel):
    __root__: List[Union[Pet, Car, AnyOfArrayItem]]


class Error(BaseModel):
    code: int
    message: str
'''
    )


def test_openapi_parser_parse_allof():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, text=Path(DATA_PATH / 'allof.yaml').read_text()
    )
    assert (
        parser.parse()
        == '''from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, conint


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Car(BaseModel):
    number: str


class AllOfref(Pet, Car):
    pass


class AllOfobj(BaseModel):
    name: Optional[str] = None
    number: Optional[str] = None


class AllOfCombine(Pet):
    birthdate: Optional[date] = None
    size: Optional[conint(ge=1.0)] = None


class AnyOfCombine(Pet, Car):
    age: Optional[str] = None


class item(Pet, Car):
    age: Optional[str] = None


class AnyOfCombineInObject(BaseModel):
    item: Optional[item] = None


class AnyOfCombineInArrayItem(Pet, Car):
    age: Optional[str] = None


class AnyOfCombineInArray(BaseModel):
    __root__: List[AnyOfCombineInArrayItem]


class AnyOfCombineInRoot(Pet, Car):
    age: Optional[str] = None
    birthdate: Optional[datetime] = None


class Error(BaseModel):
    code: int
    message: str
'''
    )


def test_openapi_parser_parse_alias():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, text=Path(DATA_PATH / 'alias.yaml').read_text()
    )
    assert (
        parser.parse()
        == '''from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Pet(Enum):
    ca_t = 'ca-t'
    dog_ = 'dog*'


class Error(BaseModel):
    code: int
    message: str
'''
    )


@pytest.mark.parametrize(
    'with_import, format_, base_class, result',
    [
        (
            True,
            True,
            None,
            {
                (
                    '__init__.py',
                ): '''\
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from . import models


class Id(BaseModel):
    __root__: str


class Error(BaseModel):
    code: int
    message: str


class Result(BaseModel):
    event: Optional[models.Event] = None


class Source(BaseModel):
    country: Optional[str] = None
''',
                (
                    'models.py',
                ): '''\
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class Species(Enum):
    dog = 'dog'
    cat = 'cat'
    snake = 'snake'


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None
    species: Optional[Species] = None


class User(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Event(BaseModel):
    name: Optional[Union[str, float, int, bool, Dict[str, Any], List[str]]] = None
''',
                (
                    'collections.py',
                ): '''\
from __future__ import annotations

from typing import List, Optional

from pydantic import AnyUrl, BaseModel

from . import models


class Pets(BaseModel):
    __root__: List[models.Pet]


class Users(BaseModel):
    __root__: List[models.User]


class Rules(BaseModel):
    __root__: List[str]


class api(BaseModel):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None
    apiUrl: Optional[AnyUrl] = None
    apiDocumentationUrl: Optional[AnyUrl] = None


class apis(BaseModel):
    __root__: List[api]
''',
                (
                    'foo',
                    '__init__.py',
                ): '''\
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .. import Id


class Tea(BaseModel):
    flavour: Optional[str] = None
    id: Optional[Id] = None


class Cocoa(BaseModel):
    quality: Optional[int] = None
''',
                (
                    'foo',
                    'bar.py',
                ): '''\
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Thing(BaseModel):
    attributes: Optional[Dict[str, Any]] = None


class Thang(BaseModel):
    attributes: Optional[List[Dict[str, Any]]] = None


class Clone(Thing):
    pass
''',
                ('woo', '__init__.py'): '',
                (
                    'woo',
                    'boo.py',
                ): '''\
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .. import Source, foo


class Chocolate(BaseModel):
    flavour: Optional[str] = None
    source: Optional[Source] = None
    cocoa: Optional[foo.Cocoa] = None
''',
            },
        )
    ],
)
def test_openapi_parser_parse_modular(with_import, format_, base_class, result):
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'modular.yaml').read_text(),
        base_class=base_class,
    )
    modules = parser.parse(with_import=with_import, format_=format_)
    assert modules == result


@pytest.mark.parametrize(
    'with_import, format_, base_class, result',
    [
        (
            True,
            True,
            None,
            '''from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Extra


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class User(BaseModel):
    class Config:
        extra = Extra.allow

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
    class Config:
        extra = Extra.allow

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
            '''from pydantic import BaseModel, Extra
from typing import List, Optional
from __future__ import annotations


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class User(BaseModel):
    class Config:
        extra = Extra.allow
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

from pydantic import Extra

from custom_module import Base


class Pet(Base):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(Base):
    __root__: List[Pet]


class User(Base):
    class Config:
        extra = Extra.allow

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


class Event(Base):
    name: Optional[str] = None


class Result(Base):
    event: Optional[Event] = None
''',
        ),
    ],
)
def test_openapi_parser_parse_additional_properties(
    with_import, format_, base_class, result
):
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'additional_properties.yaml').read_text(),
        base_class=base_class,
    )
    assert parser.parse(with_import=with_import, format_=format_) == result
