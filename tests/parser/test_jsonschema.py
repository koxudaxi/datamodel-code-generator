import json
from pathlib import Path
from typing import Dict
from unittest.mock import Mock, call

import pytest
from datamodel_code_generator.parser.base import Parser
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    get_model_by_path,
    parse_ref,
)

DATA_PATH: Path = Path(__file__).parents[1] / 'data'


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


def test_parse_ref():
    mock_parser = Mock(spec=Parser)
    external_parent_path = Path(DATA_PATH / 'external_parent.json')
    mock_parser.base_path = external_parent_path.parent
    mock_parser.excludes_ref_path = set()
    external_parent = external_parent_path.read_text()
    obj = JsonSchemaObject.parse_raw(external_parent)
    parse_ref(obj, mock_parser)
    mock_parser.parse_raw.assert_has_calls(
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
    mock_parser = Mock(spec=Parser)
    obj = JsonSchemaObject.parse_obj({'$ref': 'https://example.org'})
    with pytest.raises(NotImplementedError):
        parse_ref(obj, mock_parser)
