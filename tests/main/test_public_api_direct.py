"""Direct public API usage tests for generate and parser classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import DataModelType, GenerateConfig, InputFileType, generate
from datamodel_code_generator.config import ParserConfig
from datamodel_code_generator.parser.graphql import GraphQLParser
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from datamodel_code_generator.parser.openapi import OpenAPIParser
from tests.conftest import assert_output
from tests.main.conftest import (
    EXPECTED_GRAPHQL_PATH,
    EXPECTED_JSON_SCHEMA_PATH,
    EXPECTED_OPENAPI_PATH,
    GRAPHQL_DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    OPEN_API_DATA_PATH,
)

if TYPE_CHECKING:
    from pathlib import Path

GENERATE_CASES = [
    pytest.param(
        JSON_SCHEMA_DATA_PATH / "person.json",
        EXPECTED_JSON_SCHEMA_PATH / "general.py",
        {
            "input_file_type": InputFileType.JsonSchema,
            "output_model_type": DataModelType.PydanticBaseModel,
        },
        id="jsonschema_person",
    ),
    pytest.param(
        OPEN_API_DATA_PATH / "additional_properties.yaml",
        EXPECTED_OPENAPI_PATH / "additional_properties.py",
        {
            "input_file_type": InputFileType.OpenAPI,
            "output_model_type": DataModelType.PydanticBaseModel,
            "extra_fields": "forbid",
        },
        id="openapi_additional_properties",
    ),
    pytest.param(
        GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        EXPECTED_GRAPHQL_PATH / "simple_star_wars.py",
        {
            "input_file_type": InputFileType.GraphQL,
            "output_model_type": DataModelType.PydanticBaseModel,
        },
        id="graphql_simple_star_wars",
    ),
]


PARSER_CASES = [
    pytest.param(
        JsonSchemaParser,
        JSON_SCHEMA_DATA_PATH / "person.json",
        EXPECTED_JSON_SCHEMA_PATH / "general.py",
        {
            "output_model_type": DataModelType.PydanticBaseModel,
        },
        id="jsonschema_person",
    ),
    pytest.param(
        OpenAPIParser,
        OPEN_API_DATA_PATH / "additional_properties.yaml",
        EXPECTED_OPENAPI_PATH / "additional_properties.py",
        {
            "output_model_type": DataModelType.PydanticBaseModel,
            "extra_fields": "forbid",
        },
        id="openapi_additional_properties",
    ),
    pytest.param(
        GraphQLParser,
        GRAPHQL_DATA_PATH / "simple-star-wars.graphql",
        EXPECTED_GRAPHQL_PATH / "simple_star_wars.py",
        {
            "output_model_type": DataModelType.PydanticBaseModel,
        },
        id="graphql_simple_star_wars",
    ),
]


@pytest.mark.parametrize("use_config", [False, True])
@pytest.mark.parametrize(("input_path", "expected_path", "options"), GENERATE_CASES)
def test_generate_public_api_direct(
    use_config: bool,
    input_path: Path,
    expected_path: Path,
    options: dict[str, object],
) -> None:
    """Call generate directly with options or config and compare output."""
    if use_config:
        config = GenerateConfig(**options)
        output = generate(input_path, config=config)
    else:
        output = generate(input_path, **options)
    assert_output(output, expected_path)


@pytest.mark.parametrize("use_config", [False, True])
@pytest.mark.parametrize(("parser_cls", "input_path", "expected_path", "options"), PARSER_CASES)
def test_parser_public_api_direct(
    use_config: bool,
    parser_cls: type[object],
    input_path: Path,
    expected_path: Path,
    options: dict[str, object],
) -> None:
    """Call parser classes directly with options or config and compare output."""
    if use_config:
        config = ParserConfig(**options)
        parser = parser_cls(input_path, config=config)
    else:
        parser = parser_cls(input_path, **options)
    output = parser.parse()
    assert_output(output, expected_path)
