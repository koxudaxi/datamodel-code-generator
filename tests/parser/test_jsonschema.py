from pathlib import Path
from typing import Dict
from unittest.mock import Mock, call

import pytest
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.base import Parser
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    get_model_by_path,
)

DATA_PATH: Path = Path(__file__).parents[1] / 'data'


class Parser(JsonSchemaParser):
    def parse_raw_obj(self, name: str, raw: Dict) -> None:
        pass

    def parse_raw(self) -> None:
        pass


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
    parser = Parser(BaseModel, CustomRootType)
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
    parser = Parser(BaseModel, CustomRootType)
    obj = JsonSchemaObject.parse_obj({'$ref': 'https://example.org'})
    with pytest.raises(NotImplementedError):
        parser.parse_ref(obj)
