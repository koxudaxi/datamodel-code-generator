"""Tests for schema version detection and features."""

from __future__ import annotations

from pathlib import Path

import pytest
from inline_snapshot import snapshot

import datamodel_code_generator
from datamodel_code_generator.enums import JsonSchemaVersion, OpenAPIVersion, VersionMode
from datamodel_code_generator.parser.schema_version import (
    JsonSchemaFeatures,
    OpenAPISchemaFeatures,
    detect_jsonschema_version,
    detect_openapi_version,
)

# Path to test data
JSON_SCHEMA_DATA_PATH = Path(__file__).parent.parent / "data" / "jsonschema"


def test_detect_jsonschema_version_draft4() -> None:
    """Test detection of Draft 4 from $schema field."""
    assert detect_jsonschema_version({"$schema": "http://json-schema.org/draft-04/schema#"}) == snapshot(
        JsonSchemaVersion.Draft4
    )


def test_detect_jsonschema_version_draft6() -> None:
    """Test detection of Draft 6 from $schema field."""
    assert detect_jsonschema_version({"$schema": "http://json-schema.org/draft-06/schema#"}) == snapshot(
        JsonSchemaVersion.Draft6
    )


def test_detect_jsonschema_version_draft7() -> None:
    """Test detection of Draft 7 from $schema field."""
    assert detect_jsonschema_version({"$schema": "http://json-schema.org/draft-07/schema#"}) == snapshot(
        JsonSchemaVersion.Draft7
    )


def test_detect_jsonschema_version_2019_09() -> None:
    """Test detection of Draft 2019-09 from $schema field."""
    assert detect_jsonschema_version({"$schema": "https://json-schema.org/draft/2019-09/schema"}) == snapshot(
        JsonSchemaVersion.Draft201909
    )


def test_detect_jsonschema_version_2020_12() -> None:
    """Test detection of Draft 2020-12 from $schema field."""
    assert detect_jsonschema_version({"$schema": "https://json-schema.org/draft/2020-12/schema"}) == snapshot(
        JsonSchemaVersion.Draft202012
    )


def test_detect_jsonschema_version_defs_heuristic() -> None:
    """Test detection using $defs heuristic defaults to latest."""
    assert detect_jsonschema_version({"$defs": {"Foo": {"type": "string"}}}) == snapshot(JsonSchemaVersion.Draft202012)


def test_detect_jsonschema_version_definitions_heuristic() -> None:
    """Test detection using definitions heuristic."""
    assert detect_jsonschema_version({"definitions": {"Foo": {"type": "string"}}}) == snapshot(JsonSchemaVersion.Draft7)


def test_detect_jsonschema_version_fallback() -> None:
    """Test fallback to Draft 7 when no indicators present."""
    assert detect_jsonschema_version({"type": "object"}) == snapshot(JsonSchemaVersion.Draft7)


def test_detect_jsonschema_version_non_string_schema() -> None:
    """Test handling of non-string $schema value."""
    assert detect_jsonschema_version({"$schema": 123}) == snapshot(JsonSchemaVersion.Draft7)


def test_detect_openapi_version_30() -> None:
    """Test detection of OpenAPI 3.0."""
    assert detect_openapi_version({"openapi": "3.0.0"}) == snapshot(OpenAPIVersion.V30)


def test_detect_openapi_version_30_patch() -> None:
    """Test detection of OpenAPI 3.0.x."""
    assert detect_openapi_version({"openapi": "3.0.3"}) == snapshot(OpenAPIVersion.V30)


def test_detect_openapi_version_31() -> None:
    """Test detection of OpenAPI 3.1."""
    assert detect_openapi_version({"openapi": "3.1.0"}) == snapshot(OpenAPIVersion.V31)


def test_detect_openapi_version_fallback() -> None:
    """Test fallback to OpenAPI 3.1 when no version present."""
    assert detect_openapi_version({"info": {"title": "Test"}}) == snapshot(OpenAPIVersion.V31)


def test_detect_openapi_version_non_string() -> None:
    """Test handling of non-string openapi value."""
    assert detect_openapi_version({"openapi": 3.0}) == snapshot(OpenAPIVersion.V31)


def test_jsonschema_features_draft4() -> None:
    """Test Draft 4 features."""
    assert JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft4) == snapshot(
        JsonSchemaFeatures(
            null_in_type_array=False,
            defs_not_definitions=False,
            prefix_items=False,
            boolean_schemas=False,
            id_field="id",
            definitions_key="definitions",
        )
    )


def test_jsonschema_features_draft6() -> None:
    """Test Draft 6 features."""
    assert JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft6) == snapshot(
        JsonSchemaFeatures(
            null_in_type_array=False,
            defs_not_definitions=False,
            prefix_items=False,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="definitions",
        )
    )


def test_jsonschema_features_draft7() -> None:
    """Test Draft 7 features."""
    assert JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft7) == snapshot(
        JsonSchemaFeatures(
            null_in_type_array=False,
            defs_not_definitions=False,
            prefix_items=False,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="definitions",
        )
    )


def test_jsonschema_features_2019_09() -> None:
    """Test Draft 2019-09 features."""
    assert JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft201909) == snapshot(
        JsonSchemaFeatures(
            null_in_type_array=False,
            defs_not_definitions=True,
            prefix_items=False,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="$defs",
        )
    )


def test_jsonschema_features_2020_12() -> None:
    """Test Draft 2020-12 features."""
    assert JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft202012) == snapshot(
        JsonSchemaFeatures(
            null_in_type_array=True,
            defs_not_definitions=True,
            prefix_items=True,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="$defs",
        )
    )


def test_jsonschema_features_auto() -> None:
    """Test Auto version defaults to latest features."""
    assert JsonSchemaFeatures.from_version(JsonSchemaVersion.Auto) == snapshot(
        JsonSchemaFeatures(
            null_in_type_array=True,
            defs_not_definitions=True,
            prefix_items=True,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="$defs",
        )
    )


def test_jsonschema_features_frozen() -> None:
    """Test that features are immutable."""
    features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft7)
    with pytest.raises(AttributeError):
        features.null_in_type_array = True  # type: ignore[misc]


def test_openapi_features_v30() -> None:
    """Test OpenAPI 3.0 features."""
    assert OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V30) == snapshot(
        OpenAPISchemaFeatures(
            null_in_type_array=False,
            defs_not_definitions=False,
            prefix_items=False,
            boolean_schemas=False,
            id_field="$id",
            definitions_key="definitions",
            nullable_keyword=True,
            discriminator_support=True,
        )
    )


def test_openapi_features_v31() -> None:
    """Test OpenAPI 3.1 features."""
    assert OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V31) == snapshot(
        OpenAPISchemaFeatures(
            null_in_type_array=True,
            defs_not_definitions=True,
            prefix_items=True,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="$defs",
            nullable_keyword=False,
            discriminator_support=True,
        )
    )


def test_openapi_features_auto() -> None:
    """Test Auto version defaults to latest features."""
    assert OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.Auto) == snapshot(
        OpenAPISchemaFeatures(
            null_in_type_array=True,
            defs_not_definitions=True,
            prefix_items=True,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="$defs",
            nullable_keyword=False,
            discriminator_support=True,
        )
    )


def test_openapi_features_inherits_jsonschema() -> None:
    """Test that OpenAPISchemaFeatures inherits from JsonSchemaFeatures."""
    features = OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V31)
    assert isinstance(features, JsonSchemaFeatures)
    assert features.prefix_items == snapshot(True)


def test_openapi_features_frozen() -> None:
    """Test that features are immutable."""
    features = OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V30)
    with pytest.raises(AttributeError):
        features.nullable_keyword = False  # type: ignore[misc]


def test_lazy_import_detect_jsonschema_version() -> None:
    """Test that detect_jsonschema_version can be imported from main module."""
    detect_func = datamodel_code_generator.detect_jsonschema_version
    assert detect_func({"$schema": "http://json-schema.org/draft-07/schema#"}) == snapshot(JsonSchemaVersion.Draft7)


def test_lazy_import_detect_openapi_version() -> None:
    """Test that detect_openapi_version can be imported from main module."""
    detect_func = datamodel_code_generator.detect_openapi_version
    assert detect_func({"openapi": "3.1.0"}) == snapshot(OpenAPIVersion.V31)


def test_lazy_import_jsonschema_version_enum() -> None:
    """Test that JsonSchemaVersion is exported from main module."""
    assert datamodel_code_generator.JsonSchemaVersion is JsonSchemaVersion


def test_lazy_import_openapi_version_enum() -> None:
    """Test that OpenAPIVersion is exported from main module."""
    assert datamodel_code_generator.OpenAPIVersion is OpenAPIVersion


def test_lazy_import_version_mode_enum() -> None:
    """Test that VersionMode is exported from main module."""
    assert datamodel_code_generator.VersionMode is VersionMode


def test_get_data_formats_jsonschema() -> None:
    """Test that JsonSchema formats exclude OpenAPI-specific formats."""
    from datamodel_code_generator.parser.schema_version import get_data_formats
    from datamodel_code_generator.types import Types

    assert get_data_formats(is_openapi=False) == snapshot({
        "integer": {
            "int32": Types.int32,
            "int64": Types.int64,
            "default": Types.integer,
            "date-time": Types.date_time,
            "unix-time": Types.int64,
            "unixtime": Types.int64,
        },
        "number": {
            "float": Types.float,
            "double": Types.double,
            "decimal": Types.decimal,
            "date-time": Types.date_time,
            "time": Types.time,
            "time-delta": Types.timedelta,
            "default": Types.number,
            "unixtime": Types.int64,
        },
        "string": {
            "default": Types.string,
            "byte": Types.byte,
            "date": Types.date,
            "date-time": Types.date_time,
            "timestamp with time zone": Types.date_time,
            "date-time-local": Types.date_time_local,
            "duration": Types.timedelta,
            "time": Types.time,
            "time-local": Types.time_local,
            "path": Types.path,
            "email": Types.email,
            "idn-email": Types.email,
            "uuid": Types.uuid,
            "uuid1": Types.uuid1,
            "uuid2": Types.uuid2,
            "uuid3": Types.uuid3,
            "uuid4": Types.uuid4,
            "uuid5": Types.uuid5,
            "uri": Types.uri,
            "uri-reference": Types.string,
            "hostname": Types.hostname,
            "ipv4": Types.ipv4,
            "ipv4-network": Types.ipv4_network,
            "ipv6": Types.ipv6,
            "ipv6-network": Types.ipv6_network,
            "decimal": Types.decimal,
            "integer": Types.integer,
            "unixtime": Types.int64,
            "ulid": Types.ulid,
        },
        "boolean": {"default": Types.boolean},
        "object": {"default": Types.object},
        "null": {"default": Types.null},
        "array": {"default": Types.array},
    })


def test_get_data_formats_openapi() -> None:
    """Test that OpenAPI formats include OpenAPI-specific formats."""
    from datamodel_code_generator.parser.schema_version import get_data_formats
    from datamodel_code_generator.types import Types

    assert get_data_formats(is_openapi=True) == snapshot({
        "integer": {
            "int32": Types.int32,
            "int64": Types.int64,
            "default": Types.integer,
            "date-time": Types.date_time,
            "unix-time": Types.int64,
            "unixtime": Types.int64,
        },
        "number": {
            "float": Types.float,
            "double": Types.double,
            "decimal": Types.decimal,
            "date-time": Types.date_time,
            "time": Types.time,
            "time-delta": Types.timedelta,
            "default": Types.number,
            "unixtime": Types.int64,
        },
        "string": {
            "default": Types.string,
            "byte": Types.byte,
            "date": Types.date,
            "date-time": Types.date_time,
            "timestamp with time zone": Types.date_time,
            "date-time-local": Types.date_time_local,
            "duration": Types.timedelta,
            "time": Types.time,
            "time-local": Types.time_local,
            "path": Types.path,
            "email": Types.email,
            "idn-email": Types.email,
            "uuid": Types.uuid,
            "uuid1": Types.uuid1,
            "uuid2": Types.uuid2,
            "uuid3": Types.uuid3,
            "uuid4": Types.uuid4,
            "uuid5": Types.uuid5,
            "uri": Types.uri,
            "uri-reference": Types.string,
            "hostname": Types.hostname,
            "ipv4": Types.ipv4,
            "ipv4-network": Types.ipv4_network,
            "ipv6": Types.ipv6,
            "ipv6-network": Types.ipv6_network,
            "decimal": Types.decimal,
            "integer": Types.integer,
            "unixtime": Types.int64,
            "ulid": Types.ulid,
            "binary": Types.binary,
            "password": Types.password,
        },
        "boolean": {"default": Types.boolean},
        "object": {"default": Types.object},
        "null": {"default": Types.null},
        "array": {"default": Types.array},
    })


def test_jsonschema_parser_schema_features_detection() -> None:
    """Test that JsonSchemaParser detects schema version from $schema."""
    from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

    parser = JsonSchemaParser("")
    parser.raw_obj = {"$schema": "http://json-schema.org/draft-07/schema#"}
    features = parser.schema_features
    assert features.boolean_schemas == snapshot(True)
    assert features.definitions_key == snapshot("definitions")


def test_openapi_parser_schema_features_detection() -> None:
    """Test that OpenAPIParser detects OpenAPI version from openapi field."""
    from datamodel_code_generator.parser.openapi import OpenAPIParser

    parser = OpenAPIParser("")
    parser.raw_obj = {"openapi": "3.1.0"}
    features = parser.schema_features
    assert features.nullable_keyword == snapshot(False)
    assert features.null_in_type_array == snapshot(True)


def test_jsonschema_parser_config_version_override() -> None:
    """Test that JsonSchemaParser uses config version over auto-detection."""
    from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

    parser = JsonSchemaParser("", jsonschema_version=JsonSchemaVersion.Draft4)
    parser.raw_obj = {"$schema": "http://json-schema.org/draft-07/schema#"}
    features = parser.schema_features
    assert features.id_field == snapshot("id")
    assert features.boolean_schemas == snapshot(False)


def test_openapi_parser_config_version_override() -> None:
    """Test that OpenAPIParser uses config version over auto-detection."""
    from datamodel_code_generator.parser.openapi import OpenAPIParser

    parser = OpenAPIParser("", openapi_version=OpenAPIVersion.V30)
    parser.raw_obj = {"openapi": "3.1.0"}
    features = parser.schema_features
    assert features.nullable_keyword == snapshot(True)
    assert features.null_in_type_array == snapshot(False)


@pytest.mark.cli_doc(
    options=["--schema-version"],
    option_description="""Schema version to use for parsing.

The `--schema-version` option specifies the schema version to use instead of auto-detection.
Valid values depend on input type: JsonSchema (draft-04, draft-06, draft-07, 2019-09, 2020-12)
or OpenAPI (3.0, 3.1). Default is 'auto' (detected from $schema or openapi field).""",
    input_schema="jsonschema/simple_string.json",
    cli_args=["--schema-version", "draft-07"],
    golden_output="jsonschema/simple_string.py",
)
def test_cli_schema_version_jsonschema() -> None:
    """Test --schema-version option with JSON Schema input."""
    from datamodel_code_generator import generate

    result = generate(
        JSON_SCHEMA_DATA_PATH / "simple_string.json",
        input_file_type=datamodel_code_generator.InputFileType.JsonSchema,
        schema_version="draft-07",
    )
    assert result is not None
    assert "class Model" in result or "Model" in result


@pytest.mark.cli_doc(
    options=["--schema-version-mode"],
    option_description="""Schema version validation mode.

The `--schema-version-mode` option controls how schema version validation is performed.
'lenient' (default): accept all features regardless of version.
'strict': warn on features outside the declared/detected version.""",
    input_schema="jsonschema/simple_string.json",
    cli_args=["--schema-version-mode", "lenient"],
    golden_output="jsonschema/simple_string.py",
)
def test_cli_schema_version_mode() -> None:
    """Test --schema-version-mode option."""
    from datamodel_code_generator import generate

    result = generate(
        JSON_SCHEMA_DATA_PATH / "simple_string.json",
        input_file_type=datamodel_code_generator.InputFileType.JsonSchema,
        schema_version_mode=VersionMode.Lenient,
    )
    assert result is not None
