"""Schema version features and detection utilities.

Provides SchemaFeatures classes for version-dependent feature flags,
format registries for schema-specific data formats,
and utility functions for detecting schema versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

from datamodel_code_generator.enums import JsonSchemaVersion, OpenAPIVersion

if TYPE_CHECKING:
    from datamodel_code_generator.types import Types


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
        match version:
            case JsonSchemaVersion.Draft4:
                return cls(
                    null_in_type_array=False,
                    defs_not_definitions=False,
                    prefix_items=False,
                    boolean_schemas=False,
                    id_field="id",
                    definitions_key="definitions",
                )
            case JsonSchemaVersion.Draft6 | JsonSchemaVersion.Draft7:
                return cls(
                    null_in_type_array=False,
                    defs_not_definitions=False,
                    prefix_items=False,
                    boolean_schemas=True,
                    id_field="$id",
                    definitions_key="definitions",
                )
            case JsonSchemaVersion.Draft201909:
                return cls(
                    null_in_type_array=False,
                    defs_not_definitions=True,
                    prefix_items=False,
                    boolean_schemas=True,
                    id_field="$id",
                    definitions_key="$defs",
                )
            case _:
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
        match version:
            case OpenAPIVersion.V30:
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
            case _:
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


SchemaFeaturesT = TypeVar("SchemaFeaturesT", bound=JsonSchemaFeatures)

_JsonSchemaVersionPatterns: TypeAlias = dict[str, JsonSchemaVersion]

_JSONSCHEMA_VERSION_PATTERNS: _JsonSchemaVersionPatterns = {
    "draft-04": JsonSchemaVersion.Draft4,
    "draft-06": JsonSchemaVersion.Draft6,
    "draft-07": JsonSchemaVersion.Draft7,
    "2019-09": JsonSchemaVersion.Draft201909,
    "2020-12": JsonSchemaVersion.Draft202012,
}


def detect_jsonschema_version(data: dict[str, Any]) -> JsonSchemaVersion:
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
    if isinstance(schema_url := data.get("$schema", ""), str):
        for pattern, version in _JSONSCHEMA_VERSION_PATTERNS.items():
            if pattern in schema_url:
                return version

    if "$defs" in data:
        return JsonSchemaVersion.Draft202012
    if "definitions" in data:
        return JsonSchemaVersion.Draft7
    return JsonSchemaVersion.Draft7


def detect_openapi_version(data: dict[str, Any]) -> OpenAPIVersion:
    """Detect OpenAPI version from openapi field.

    Args:
        data: The schema dictionary to analyze.

    Returns:
        The detected OpenAPI version.
    """
    if isinstance(version := data.get("openapi", ""), str):
        if version.startswith("3.1"):
            return OpenAPIVersion.V31
        if version.startswith("3.0"):
            return OpenAPIVersion.V30
    return OpenAPIVersion.V31


DataFormatMapping: TypeAlias = "dict[str, dict[str, Types]]"


def _get_common_data_formats() -> DataFormatMapping:
    """Get common data formats valid for both JsonSchema and OpenAPI."""
    from datamodel_code_generator.types import Types  # noqa: PLC0415

    return {
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
    }


def _get_openapi_only_formats() -> DataFormatMapping:
    """Get formats specific to OpenAPI (not valid in pure JsonSchema)."""
    from datamodel_code_generator.types import Types  # noqa: PLC0415

    return {
        "string": {
            "binary": Types.binary,
            "password": Types.password,
        },
    }


def get_data_formats(*, is_openapi: bool = False) -> DataFormatMapping:
    """Get merged data formats based on schema type.

    Args:
        is_openapi: If True, includes OpenAPI-specific formats.

    Returns:
        Merged dictionary of data formats.
    """
    formats = _get_common_data_formats()
    if is_openapi:
        for type_key, type_formats in _get_openapi_only_formats().items():
            if type_key in formats:
                formats[type_key] = {**formats[type_key], **type_formats}
            else:
                formats[type_key] = type_formats
    return formats


__all__ = [
    "DataFormatMapping",
    "JsonSchemaFeatures",
    "OpenAPISchemaFeatures",
    "SchemaFeaturesT",
    "detect_jsonschema_version",
    "detect_openapi_version",
    "get_data_formats",
]
