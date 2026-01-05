"""Tests for schema version detection and features."""

from __future__ import annotations

import pytest

import datamodel_code_generator
from datamodel_code_generator.enums import JsonSchemaVersion, OpenAPIVersion
from datamodel_code_generator.parser.schema_version import (
    JsonSchemaFeatures,
    OpenAPISchemaFeatures,
    detect_jsonschema_version,
    detect_openapi_version,
)


class TestDetectJsonSchemaVersion:
    """Tests for detect_jsonschema_version function."""

    def test_detect_draft4_from_schema(self) -> None:
        """Test detection of Draft 4 from $schema field."""
        data = {"$schema": "http://json-schema.org/draft-04/schema#"}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft4

    def test_detect_draft6_from_schema(self) -> None:
        """Test detection of Draft 6 from $schema field."""
        data = {"$schema": "http://json-schema.org/draft-06/schema#"}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft6

    def test_detect_draft7_from_schema(self) -> None:
        """Test detection of Draft 7 from $schema field."""
        data = {"$schema": "http://json-schema.org/draft-07/schema#"}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft7

    def test_detect_2019_09_from_schema(self) -> None:
        """Test detection of Draft 2019-09 from $schema field."""
        data = {"$schema": "https://json-schema.org/draft/2019-09/schema"}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft201909

    def test_detect_2020_12_from_schema(self) -> None:
        """Test detection of Draft 2020-12 from $schema field."""
        data = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft202012

    def test_detect_from_defs_heuristic_with_prefix_items(self) -> None:
        """Test detection using $defs with prefixItems heuristic."""
        data = {"$defs": {"Foo": {"type": "string"}}, "prefixItems": [{"type": "string"}]}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft202012

    def test_detect_from_defs_heuristic_without_prefix_items(self) -> None:
        """Test detection using $defs without prefixItems heuristic."""
        data = {"$defs": {"Foo": {"type": "string"}}}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft201909

    def test_detect_from_definitions_heuristic(self) -> None:
        """Test detection using definitions heuristic."""
        data = {"definitions": {"Foo": {"type": "string"}}}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft7

    def test_fallback_to_draft7(self) -> None:
        """Test fallback to Draft 7 when no indicators present."""
        data = {"type": "object"}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft7

    def test_non_string_schema(self) -> None:
        """Test handling of non-string $schema value."""
        data = {"$schema": 123}
        assert detect_jsonschema_version(data) == JsonSchemaVersion.Draft7


class TestDetectOpenAPIVersion:
    """Tests for detect_openapi_version function."""

    def test_detect_openapi_30(self) -> None:
        """Test detection of OpenAPI 3.0."""
        data = {"openapi": "3.0.0"}
        assert detect_openapi_version(data) == OpenAPIVersion.V30

    def test_detect_openapi_30_patch(self) -> None:
        """Test detection of OpenAPI 3.0.x."""
        data = {"openapi": "3.0.3"}
        assert detect_openapi_version(data) == OpenAPIVersion.V30

    def test_detect_openapi_31(self) -> None:
        """Test detection of OpenAPI 3.1."""
        data = {"openapi": "3.1.0"}
        assert detect_openapi_version(data) == OpenAPIVersion.V31

    def test_fallback_to_31(self) -> None:
        """Test fallback to OpenAPI 3.1 when no version present."""
        data = {"info": {"title": "Test"}}
        assert detect_openapi_version(data) == OpenAPIVersion.V31

    def test_non_string_version(self) -> None:
        """Test handling of non-string openapi value."""
        data = {"openapi": 3.0}
        assert detect_openapi_version(data) == OpenAPIVersion.V31


class TestJsonSchemaFeatures:
    """Tests for JsonSchemaFeatures class."""

    def test_from_version_draft4(self) -> None:
        """Test Draft 4 features."""
        features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft4)
        assert features.null_in_type_array is False
        assert features.defs_not_definitions is False
        assert features.prefix_items is False
        assert features.boolean_schemas is False
        assert features.id_field == "id"
        assert features.definitions_key == "definitions"

    def test_from_version_draft6(self) -> None:
        """Test Draft 6 features."""
        features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft6)
        assert features.null_in_type_array is False
        assert features.defs_not_definitions is False
        assert features.prefix_items is False
        assert features.boolean_schemas is True
        assert features.id_field == "$id"
        assert features.definitions_key == "definitions"

    def test_from_version_draft7(self) -> None:
        """Test Draft 7 features."""
        features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft7)
        assert features.null_in_type_array is False
        assert features.defs_not_definitions is False
        assert features.prefix_items is False
        assert features.boolean_schemas is True
        assert features.id_field == "$id"
        assert features.definitions_key == "definitions"

    def test_from_version_2019_09(self) -> None:
        """Test Draft 2019-09 features."""
        features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft201909)
        assert features.null_in_type_array is False
        assert features.defs_not_definitions is True
        assert features.prefix_items is False
        assert features.boolean_schemas is True
        assert features.id_field == "$id"
        assert features.definitions_key == "$defs"

    def test_from_version_2020_12(self) -> None:
        """Test Draft 2020-12 features."""
        features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft202012)
        assert features.null_in_type_array is True
        assert features.defs_not_definitions is True
        assert features.prefix_items is True
        assert features.boolean_schemas is True
        assert features.id_field == "$id"
        assert features.definitions_key == "$defs"

    def test_from_version_auto(self) -> None:
        """Test Auto version defaults to latest features."""
        features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Auto)
        assert features.null_in_type_array is True
        assert features.defs_not_definitions is True
        assert features.prefix_items is True
        assert features.boolean_schemas is True

    def test_frozen(self) -> None:
        """Test that features are immutable."""
        features = JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft7)
        with pytest.raises(AttributeError):
            features.null_in_type_array = True  # type: ignore[misc]


class TestOpenAPISchemaFeatures:
    """Tests for OpenAPISchemaFeatures class."""

    def test_from_openapi_version_v30(self) -> None:
        """Test OpenAPI 3.0 features."""
        features = OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V30)
        assert features.nullable_keyword is True
        assert features.discriminator_support is True
        assert features.boolean_schemas is False  # OpenAPI 3.0 does not support boolean schemas
        assert features.definitions_key == "definitions"

    def test_from_openapi_version_v31(self) -> None:
        """Test OpenAPI 3.1 features."""
        features = OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V31)
        assert features.nullable_keyword is False
        assert features.discriminator_support is True
        assert features.null_in_type_array is True
        assert features.definitions_key == "$defs"

    def test_from_openapi_version_auto(self) -> None:
        """Test Auto version defaults to latest features."""
        features = OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.Auto)
        assert features.nullable_keyword is False
        assert features.discriminator_support is True
        assert features.null_in_type_array is True

    def test_inherits_jsonschema_features(self) -> None:
        """Test that OpenAPISchemaFeatures inherits from JsonSchemaFeatures."""
        features = OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V31)
        assert isinstance(features, JsonSchemaFeatures)
        assert features.prefix_items is True

    def test_frozen(self) -> None:
        """Test that features are immutable."""
        features = OpenAPISchemaFeatures.from_openapi_version(OpenAPIVersion.V30)
        with pytest.raises(AttributeError):
            features.nullable_keyword = False  # type: ignore[misc]


class TestLazyImports:
    """Tests for lazy imports from datamodel_code_generator module."""

    def test_detect_jsonschema_version_lazy_import(self) -> None:
        """Test that detect_jsonschema_version can be imported from main module."""
        detect_func = datamodel_code_generator.detect_jsonschema_version
        result = detect_func({"$schema": "http://json-schema.org/draft-07/schema#"})
        assert result == JsonSchemaVersion.Draft7

    def test_detect_openapi_version_lazy_import(self) -> None:
        """Test that detect_openapi_version can be imported from main module."""
        detect_func = datamodel_code_generator.detect_openapi_version
        result = detect_func({"openapi": "3.1.0"})
        assert result == OpenAPIVersion.V31

    def test_jsonschema_version_enum_export(self) -> None:
        """Test that JsonSchemaVersion is exported from main module."""
        assert datamodel_code_generator.JsonSchemaVersion is JsonSchemaVersion

    def test_openapi_version_enum_export(self) -> None:
        """Test that OpenAPIVersion is exported from main module."""
        assert datamodel_code_generator.OpenAPIVersion is OpenAPIVersion

    def test_version_mode_enum_export(self) -> None:
        """Test that VersionMode is exported from main module."""
        from datamodel_code_generator.enums import VersionMode

        assert datamodel_code_generator.VersionMode is VersionMode
