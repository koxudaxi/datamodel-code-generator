"""Schema version features and detection utilities.

Provides SchemaFeatures classes for version-dependent feature flags
and utility functions for detecting schema versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from datamodel_code_generator.enums import JsonSchemaVersion, OpenAPIVersion


@dataclass(frozen=True)
class JsonSchemaFeatures:
    """Feature flags for JSON Schema versions.

    This is the base class for schema features. OpenAPISchemaFeatures
    extends this to add OpenAPI-specific features.

    Attributes:
        null_in_type_array: Draft 2020-12 allows null in type arrays.
        defs_not_definitions: Draft 2019-09+ uses $defs instead of definitions.
        prefix_items: Draft 2020-12 uses prefixItems instead of items array.
        boolean_schemas: Draft 6+ allows boolean values as schemas.
        id_field: The field name for schema ID ("id" for Draft 4, "$id" for Draft 6+).
        definitions_key: The key for definitions ("definitions" or "$defs").
    """

    null_in_type_array: bool
    defs_not_definitions: bool
    prefix_items: bool
    boolean_schemas: bool
    id_field: str
    definitions_key: str

    @classmethod
    def from_version(cls, version: JsonSchemaVersion) -> JsonSchemaFeatures:
        """Create JsonSchemaFeatures from a JSON Schema version."""
        if version == JsonSchemaVersion.Draft4:
            return cls(
                null_in_type_array=False,
                defs_not_definitions=False,
                prefix_items=False,
                boolean_schemas=False,
                id_field="id",
                definitions_key="definitions",
            )
        if version in {JsonSchemaVersion.Draft6, JsonSchemaVersion.Draft7}:
            return cls(
                null_in_type_array=False,
                defs_not_definitions=False,
                prefix_items=False,
                boolean_schemas=True,
                id_field="$id",
                definitions_key="definitions",
            )
        if version == JsonSchemaVersion.Draft201909:
            return cls(
                null_in_type_array=False,
                defs_not_definitions=True,
                prefix_items=False,
                boolean_schemas=True,
                id_field="$id",
                definitions_key="$defs",
            )
        # Draft 2020-12 or Auto (default to latest features in lenient mode)
        return cls(
            null_in_type_array=True,
            defs_not_definitions=True,
            prefix_items=True,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="$defs",
        )


@dataclass(frozen=True)
class OpenAPISchemaFeatures(JsonSchemaFeatures):
    """Feature flags for OpenAPI versions.

    Extends JsonSchemaFeatures with OpenAPI-specific features.

    Attributes:
        nullable_keyword: OpenAPI 3.0 uses nullable: true (deprecated in 3.1).
        discriminator_support: All OpenAPI versions support discriminator.
    """

    nullable_keyword: bool
    discriminator_support: bool

    @classmethod
    def from_openapi_version(cls, version: OpenAPIVersion) -> OpenAPISchemaFeatures:
        """Create OpenAPISchemaFeatures from an OpenAPI version."""
        if version == OpenAPIVersion.V30:
            # OpenAPI 3.0 does not support boolean schemas (only 3.1+ does)
            return cls(
                null_in_type_array=False,
                defs_not_definitions=False,
                prefix_items=False,
                boolean_schemas=False,
                id_field="$id",
                definitions_key="definitions",
                nullable_keyword=True,
                discriminator_support=True,
            )
        # OpenAPI 3.1 or Auto (default to latest features in lenient mode)
        return cls(
            null_in_type_array=True,
            defs_not_definitions=True,
            prefix_items=True,
            boolean_schemas=True,
            id_field="$id",
            definitions_key="$defs",
            nullable_keyword=False,
            discriminator_support=True,
        )


# Type variable for SchemaFeatures subclasses
SchemaFeaturesT = TypeVar("SchemaFeaturesT", bound=JsonSchemaFeatures)


def detect_jsonschema_version(data: dict[str, Any]) -> JsonSchemaVersion:  # noqa: PLR0911
    """Detect JSON Schema version from $schema field or heuristics.

    Detection priority:
    1. $schema field explicit declaration
    2. Heuristics ($defs vs definitions, etc.)
    3. Fallback: Draft7 (most widely used)

    Note: In Lenient mode, detection result is only used for optimization hints.
          In Strict mode, detection result is used to warn on version violations.

    Args:
        data: The schema dictionary to analyze.

    Returns:
        The detected JSON Schema version.
    """
    schema_url = data.get("$schema", "")
    if isinstance(schema_url, str):
        if "draft-04" in schema_url:
            return JsonSchemaVersion.Draft4
        if "draft-06" in schema_url:
            return JsonSchemaVersion.Draft6
        if "draft-07" in schema_url:
            return JsonSchemaVersion.Draft7
        if "2019-09" in schema_url:
            return JsonSchemaVersion.Draft201909
        if "2020-12" in schema_url:
            return JsonSchemaVersion.Draft202012

    # Heuristic detection (when $schema is missing)
    if "$defs" in data:
        # $defs was introduced in Draft 2019-09
        # prefixItems is specific to Draft 2020-12
        if "prefixItems" in data:
            return JsonSchemaVersion.Draft202012
        return JsonSchemaVersion.Draft201909
    if "definitions" in data:
        return JsonSchemaVersion.Draft7

    # Fallback: Draft7 is the most widely used
    return JsonSchemaVersion.Draft7


def detect_openapi_version(data: dict[str, Any]) -> OpenAPIVersion:
    """Detect OpenAPI version from openapi field.

    Args:
        data: The schema dictionary to analyze.

    Returns:
        The detected OpenAPI version.
    """
    version = data.get("openapi", "")
    if isinstance(version, str):
        if version.startswith("3.1"):
            return OpenAPIVersion.V31
        if version.startswith("3.0"):
            return OpenAPIVersion.V30
    # Fallback: 3.1 (latest, best JSON Schema compatibility)
    return OpenAPIVersion.V31


__all__ = [
    "JsonSchemaFeatures",
    "OpenAPISchemaFeatures",
    "SchemaFeaturesT",
    "detect_jsonschema_version",
    "detect_openapi_version",
]
