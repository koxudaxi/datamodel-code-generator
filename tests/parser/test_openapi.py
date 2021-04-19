import platform
from pathlib import Path
from typing import List, Optional

import pytest

from datamodel_code_generator import PythonVersion
from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.parser.base import dump_templates
from datamodel_code_generator.parser.jsonschema import JsonSchemaObject
from datamodel_code_generator.parser.openapi import OpenAPIParser

DATA_PATH: Path = Path(__file__).parents[1] / 'data' / 'openapi'

EXPECTED_OPEN_API_PATH = (
    Path(__file__).parents[1] / 'data' / 'expected' / 'parser' / 'openapi'
)


def get_expected_file(
    test_name: str,
    with_import: bool,
    format_: bool,
    base_class: Optional[str] = None,
    prefix: Optional[str] = None,
) -> Path:
    params: List[str] = []
    if with_import:
        params.append('with_import')
    if format_:
        params.append('format')
    if base_class:
        params.append(base_class)
    file_name = '_'.join(params or 'output')

    return EXPECTED_OPEN_API_PATH / test_name / (prefix or '') / f'{file_name}.py'


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
    parser = OpenAPIParser('')
    parser.parse_object('Pets', JsonSchemaObject.parse_obj(source_obj), [])
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
        (
            {'type': 'array', 'items': {},},
            '''class Pets(BaseModel):
    __root__: List''',
        ),
    ],
)
def test_parse_array(source_obj, generated_classes):
    parser = OpenAPIParser('')
    parser.parse_array('Pets', JsonSchemaObject.parse_obj(source_obj), [])
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
    parser = OpenAPIParser('')
    parsed_templates = parser.parse_root_type(
        'Name', JsonSchemaObject.parse_obj(source_obj)
    )
    assert dump_templates(list(parsed_templates)) == generated_classes


@pytest.mark.parametrize(
    'with_import, format_, base_class',
    [
        (True, True, None,),
        (False, True, None,),
        (True, False, None,),
        (True, True, 'custom_module.Base'),
    ],
)
def test_openapi_parser_parse(with_import, format_, base_class):
    parser = OpenAPIParser(
        data_model_field_type=DataModelFieldBase,
        source=Path(DATA_PATH / 'api.yaml'),
        base_class=base_class,
    )
    expected_file = get_expected_file(
        'openapi_parser_parse', with_import, format_, base_class
    )
    assert (
        parser.parse(
            with_import=with_import, format_=format_, settings_path=DATA_PATH.parent
        )
        == expected_file.read_text()
    )


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
    parser = OpenAPIParser('')
    parser.parse_root_type('Name', JsonSchemaObject.parse_obj(source_obj), [])
    assert dump_templates(list(parser.results)) == generated_classes


def test_openapi_parser_parse_duplicate_models():
    parser = OpenAPIParser(Path(DATA_PATH / 'duplicate_models.yaml'),)
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH
            / 'openapi_parser_parse_duplicate_models'
            / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_resolved_models():
    parser = OpenAPIParser(Path(DATA_PATH / 'resolved_models.yaml'),)
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH
            / 'openapi_parser_parse_resolved_models'
            / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_lazy_resolved_models():
    parser = OpenAPIParser(Path(DATA_PATH / 'lazy_resolved_models.yaml'),)
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


def test_openapi_parser_parse_x_enum_varnames():
    parser = OpenAPIParser(Path(DATA_PATH / 'x_enum_varnames.yaml'),)
    print(parser.parse())
    assert (
        parser.parse()
        == '''from __future__ import annotations

from enum import Enum


class String(Enum):
    dog = 'dog'
    cat = 'cat'
    snake = 'snake'


class UnknownTypeString(Enum):
    dog = 'dog'
    cat = 'cat'
    snake = 'snake'


class NamedString(Enum):
    EQ = '='
    NE = '!='
    GT = '>'
    LT = '<'
    GE = '>='
    LE = '<='


class NamedNumber(Enum):
    one = 1
    two = 2
    three = 3


class Number(Enum):
    number_1 = 1
    number_2 = 2
    number_3 = 3


class UnknownTypeNumber(Enum):
    int_1 = 1
    int_2 = 2
    int_3 = 3
'''
    )


def test_openapi_parser_parse_enum_models():
    parser = OpenAPIParser(Path(DATA_PATH / 'enum_models.yaml').read_text(),)
    expected_dir = EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_enum_models'
    assert parser.parse() == (expected_dir / 'output_py37.py').read_text()

    parser = OpenAPIParser(
        Path(DATA_PATH / 'enum_models.yaml').read_text(),
        target_python_version=PythonVersion.PY_36,
    )
    assert parser.parse() == (expected_dir / 'output_py36.py').read_text()


def test_openapi_parser_parse_anyof():
    parser = OpenAPIParser(Path(DATA_PATH / 'anyof.yaml'),)
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_anyof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_nested_anyof():
    parser = OpenAPIParser(Path(DATA_PATH / 'nested_anyof.yaml').read_text(),)
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_nested_anyof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_oneof():
    parser = OpenAPIParser(Path(DATA_PATH / 'oneof.yaml'),)
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_oneof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_nested_oneof():
    parser = OpenAPIParser(Path(DATA_PATH / 'nested_oneof.yaml').read_text(),)
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_nested_oneof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_allof():
    parser = OpenAPIParser(Path(DATA_PATH / 'allof.yaml'),)
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_allof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_alias():
    parser = OpenAPIParser(Path(DATA_PATH / 'alias.yaml'),)
    if platform.system() == 'Windows':
        delimiter = '\\'
    else:
        delimiter = '/'
    results = {delimiter.join(p): r for p, r in parser.parse().items()}
    openapi_parser_parse_alias_dir = (
        EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_alias'
    )
    for path in openapi_parser_parse_alias_dir.rglob('*.py'):
        key = str(path.relative_to(openapi_parser_parse_alias_dir))
        assert results.pop(key).body == path.read_text()


@pytest.mark.parametrize(
    'with_import, format_, base_class', [(True, True, None)],
)
def test_openapi_parser_parse_modular(with_import, format_, base_class):
    parser = OpenAPIParser(
        Path(DATA_PATH / 'modular.yaml'),
        base_class=base_class,
        data_model_field_type=DataModelFieldBase,
    )
    modules = parser.parse(with_import=with_import, format_=format_)
    main_modular_dir = EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_modular'

    for paths, result in modules.items():
        expected = main_modular_dir.joinpath(*paths).read_text()
        assert result.body == expected


@pytest.mark.parametrize(
    'with_import, format_, base_class',
    [
        (True, True, None,),
        (False, True, None,),
        (True, False, None,),
        (True, True, 'custom_module.Base',),
    ],
)
def test_openapi_parser_parse_additional_properties(with_import, format_, base_class):
    parser = OpenAPIParser(
        Path(DATA_PATH / 'additional_properties.yaml').read_text(),
        base_class=base_class,
        data_model_field_type=DataModelFieldBase,
    )

    assert (
        parser.parse(
            with_import=with_import, format_=format_, settings_path=DATA_PATH.parent
        )
        == get_expected_file(
            'openapi_parser_parse_additional_properties',
            with_import,
            format_,
            base_class,
        ).read_text()
    )


@pytest.mark.parametrize(
    'with_import, format_, base_class', [(True, True, None,),],
)
def test_openapi_parser_parse_array_enum(with_import, format_, base_class):
    parser = OpenAPIParser(
        source=Path(DATA_PATH / 'array_enum.yaml'), base_class=base_class
    )
    expected_file = get_expected_file(
        'openapi_parser_parse_array_enum', with_import, format_, base_class
    )
    assert (
        parser.parse(with_import=with_import, format_=format_)
        == expected_file.read_text()
    )


@pytest.mark.parametrize(
    'with_import, format_, base_class', [(True, True, None,),],
)
def test_openapi_parser_parse_remote_ref(with_import, format_, base_class):
    parser = OpenAPIParser(
        data_model_field_type=DataModelFieldBase,
        base_class=base_class,
        source=(DATA_PATH / 'refs.yaml').read_text(),
    )
    expected_file = get_expected_file(
        'openapi_parser_parse_remote_ref', with_import, format_, base_class
    )

    assert (
        parser.parse(with_import=with_import, format_=format_)
        == expected_file.read_text()
    )


def test_openapi_model_resolver():
    parser = OpenAPIParser(source=(DATA_PATH / 'api.yaml'))
    parser.parse()

    references = {
        k: v.dict(exclude={'source', 'module_name', 'actual_module_name'},)
        for k, v in parser.model_resolver.references.items()
    }
    assert references == {
        'api.yaml#/components/schemas/Error': {
            'loaded': True,
            'name': 'Error',
            'original_name': 'Error',
            'path': 'api.yaml#/components/schemas/Error',
        },
        'api.yaml#/components/schemas/Event': {
            'loaded': True,
            'name': 'Event',
            'original_name': 'Event',
            'path': 'api.yaml#/components/schemas/Event',
        },
        'api.yaml#/components/schemas/Id': {
            'loaded': True,
            'name': 'Id',
            'original_name': 'Id',
            'path': 'api.yaml#/components/schemas/Id',
        },
        'api.yaml#/components/schemas/Pet': {
            'loaded': True,
            'name': 'Pet',
            'original_name': 'Pet',
            'path': 'api.yaml#/components/schemas/Pet',
        },
        'api.yaml#/components/schemas/Pets': {
            'loaded': True,
            'name': 'Pets',
            'original_name': 'Pets',
            'path': 'api.yaml#/components/schemas/Pets',
        },
        'api.yaml#/components/schemas/Result': {
            'loaded': True,
            'name': 'Result',
            'original_name': 'Result',
            'path': 'api.yaml#/components/schemas/Result',
        },
        'api.yaml#/components/schemas/Rules': {
            'loaded': True,
            'name': 'Rules',
            'original_name': 'Rules',
            'path': 'api.yaml#/components/schemas/Rules',
        },
        'api.yaml#/components/schemas/Users': {
            'loaded': True,
            'name': 'Users',
            'original_name': 'Users',
            'path': 'api.yaml#/components/schemas/Users',
        },
        'api.yaml#/components/schemas/Users/Users/0#-datamodel-code-generator-#-object-#-special-#': {
            'loaded': True,
            'name': 'User',
            'original_name': 'Users',
            'path': 'api.yaml#/components/schemas/Users/Users/0#-datamodel-code-generator-#-object-#-special-#',
        },
        'api.yaml#/components/schemas/apis': {
            'loaded': True,
            'name': 'Apis',
            'original_name': 'apis',
            'path': 'api.yaml#/components/schemas/apis',
        },
        'api.yaml#/components/schemas/apis/apis/0#-datamodel-code-generator-#-object-#-special-#': {
            'loaded': True,
            'name': 'Api',
            'original_name': 'apis',
            'path': 'api.yaml#/components/schemas/apis/apis/0#-datamodel-code-generator-#-object-#-special-#',
        },
    }


def test_openapi_parser_parse_any():
    parser = OpenAPIParser(
        data_model_field_type=DataModelFieldBase, source=Path(DATA_PATH / 'any.yaml'),
    )
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_any' / 'output.py'
        ).read_text()
    )
