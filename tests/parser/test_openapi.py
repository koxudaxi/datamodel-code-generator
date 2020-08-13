from pathlib import Path
from typing import List, Optional

import pytest

from datamodel_code_generator import DataModelField, PythonVersion
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.base import Reference, dump_templates
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
    parser = OpenAPIParser(BaseModel, CustomRootType)
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
    parser = OpenAPIParser(BaseModel, CustomRootType)
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
    parser = OpenAPIParser(BaseModel, CustomRootType)
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
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'api.yaml').read_text(),
        base_class=base_class,
    )
    expected_file = get_expected_file(
        'openapi_parser_parse', with_import, format_, base_class
    )
    assert (
        parser.parse(with_import=with_import, format_=format_)
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
    parser = OpenAPIParser(BaseModel, CustomRootType)
    parser.parse_root_type('Name', JsonSchemaObject.parse_obj(source_obj), [])
    assert dump_templates(list(parser.results)) == generated_classes


def test_openapi_parser_parse_duplicate_models():
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'duplicate_models.yaml').read_text(),
    )
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH
            / 'openapi_parser_parse_duplicate_models'
            / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_resolved_models():
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'resolved_models.yaml').read_text(),
    )
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH
            / 'openapi_parser_parse_resolved_models'
            / 'output.py'
        ).read_text()
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
    expected_dir = EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_enum_models'
    assert parser.parse() == (expected_dir / 'output_py37.py').read_text()

    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'enum_models.yaml').read_text(),
        target_python_version=PythonVersion.PY_36,
    )
    assert parser.parse() == (expected_dir / 'output_py36.py').read_text()


def test_openapi_parser_parse_anyof():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, text=Path(DATA_PATH / 'anyof.yaml').read_text()
    )
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_anyof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_nested_anyof():
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        data_model_field_type=DataModelField,
        text=Path(DATA_PATH / 'nested_anyof.yaml').read_text(),
    )
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_nested_anyof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_allof():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, text=Path(DATA_PATH / 'allof.yaml').read_text()
    )
    assert (
        parser.parse()
        == (
            EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_allof' / 'output.py'
        ).read_text()
    )


def test_openapi_parser_parse_alias():
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        data_model_field_type=DataModelField,
        text=Path(DATA_PATH / 'alias.yaml').read_text(),
    )
    results = {'/'.join(p): r for p, r in parser.parse().items()}
    openapi_parser_parse_alias_dir = (
        EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_alias'
    )
    for path in openapi_parser_parse_alias_dir.rglob('*.py'):
        key = str(path.relative_to(openapi_parser_parse_alias_dir))
        assert results.pop(key) == path.read_text()


@pytest.mark.parametrize(
    'with_import, format_, base_class', [(True, True, None)],
)
def test_openapi_parser_parse_modular(with_import, format_, base_class):
    parser = OpenAPIParser(
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'modular.yaml').read_text(),
        base_class=base_class,
    )
    modules = parser.parse(with_import=with_import, format_=format_)
    main_modular_dir = EXPECTED_OPEN_API_PATH / 'openapi_parser_parse_modular'

    for paths, result in modules.items():
        expected = main_modular_dir.joinpath(*paths).read_text()
        assert result == expected


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
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'additional_properties.yaml').read_text(),
        base_class=base_class,
    )

    assert (
        parser.parse(with_import=with_import, format_=format_)
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
        BaseModel,
        CustomRootType,
        text=Path(DATA_PATH / 'array_enum.yaml').read_text(),
        base_class=base_class,
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
        BaseModel,
        CustomRootType,
        base_class=base_class,
        text=(DATA_PATH / 'refs.yaml').read_text(),
    )
    expected_file = get_expected_file(
        'openapi_parser_parse_remote_ref', with_import, format_, base_class
    )

    assert (
        parser.parse(with_import=with_import, format_=format_)
        == expected_file.read_text()
    )


def test_openapi_model_resolver():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, text=Path(DATA_PATH / 'api.yaml').read_text(),
    )
    parser.parse()

    assert parser.model_resolver.references == {
        '#/components/schemas/Error': Reference(
            path=['#/components', 'schemas', 'Error'],
            original_name='Error',
            name='Error',
            loaded=True,
        ),
        '#/components/schemas/Event': Reference(
            path=['#/components', 'schemas', 'Event'],
            original_name='Event',
            name='Event',
            loaded=True,
        ),
        '#/components/schemas/Id': Reference(
            path=['#/components', 'schemas', 'Id'],
            original_name='Id',
            name='Id',
            loaded=True,
        ),
        '#/components/schemas/Pet': Reference(
            path=['#/components', 'schemas', 'Pet'],
            original_name='Pet',
            name='Pet',
            loaded=True,
        ),
        '#/components/schemas/Pets': Reference(
            path=['#/components', 'schemas', 'Pets'],
            original_name='Pets',
            name='Pets',
            loaded=True,
        ),
        '#/components/schemas/Result': Reference(
            path=['#/components', 'schemas', 'Result'],
            original_name='Result',
            name='Result',
            loaded=True,
        ),
        '#/components/schemas/Rules': Reference(
            path=['#/components', 'schemas', 'Rules'],
            original_name='Rules',
            name='Rules',
            loaded=True,
        ),
        '#/components/schemas/Users': Reference(
            path=['#/components', 'schemas', 'Users'],
            original_name='Users',
            name='Users',
            loaded=True,
        ),
        '#/components/schemas/Users/Users': Reference(
            path=['#/components', 'schemas', 'Users', 'Users'],
            original_name='Users',
            name='User',
            loaded=True,
        ),
        '#/components/schemas/apis': Reference(
            path=['#/components', 'schemas', 'apis'],
            original_name='apis',
            name='Apis',
            loaded=True,
        ),
        '#/components/schemas/apis/Apis': Reference(
            path=['#/components', 'schemas', 'apis', 'Apis'],
            original_name='Apis',
            name='Api',
            loaded=True,
        ),
    }
