"""Schema version features and detection utilities.

Provides SchemaFeatures classes for version-dependent feature flags,
format registries for schema-specific data formats,
and utility functions for detecting schema versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypeVar

from typing_extensions import TypedDict

from datamodel_code_generator.enums import JsonSchemaVersion, OpenAPIVersion

if TYPE_CHECKING:
    from datamodel_code_generator.types import Types


class FeatureMetadata(TypedDict):
    """Metadata for schema feature documentation.

    This metadata is used by scripts/build_schema_docs.py to generate
    the feature compatibility matrix in docs/supported_formats.md.
    """

    introduced: str
    """Version when feature was introduced (e.g., "Draft 6", "2020-12", "OAS 3.0")."""
    doc_name: str
    """Display name for documentation (e.g., "prefixItems", "Null in type array")."""
    description: str
    """User-facing description of the feature."""
    status: Literal["supported", "partial", "not_supported"]
    """Implementation status: supported, partial, or not_supported."""


@dataclass(frozen=True)
class JsonSchemaFeatures:
    """Feature flags for JSON Schema versions.

    This is the base class for schema features. OpenAPISchemaFeatures
    extends this to add OpenAPI-specific features.

    Each field includes metadata for documentation generation.
    Use `dataclasses.fields(JsonSchemaFeatures)` to access metadata.
    """

    null_in_type_array: bool = field(
        default=False,
        metadata=FeatureMetadata(
            introduced="2020-12",
            doc_name="Null in type array",
            description="Allows `type: ['string', 'null']` syntax for nullable types",
            status="supported",
        ),
    )
    defs_not_definitions: bool = field(
        default=False,
        metadata=FeatureMetadata(
            introduced="2019-09",
            doc_name="$defs",
            description="Uses `$defs` instead of `definitions` for schema definitions",
            status="supported",
        ),
    )
    prefix_items: bool = field(
        default=False,
        metadata=FeatureMetadata(
            introduced="2020-12",
            doc_name="prefixItems",
            description="Tuple validation using `prefixItems` keyword",
            status="supported",
        ),
    )
    boolean_schemas: bool = field(
        default=False,
        metadata=FeatureMetadata(
            introduced="Draft 6",
            doc_name="Boolean schemas",
            description="Allows `true` and `false` as valid schemas",
            status="supported",
        ),
    )
    id_field: str = field(
        default="$id",
        metadata=FeatureMetadata(
            introduced="Draft 6",
            doc_name="$id",
            description="Schema identifier field (`id` in Draft 4, `$id` in Draft 6+)",
            status="supported",
        ),
    )
    definitions_key: str = field(
        default="$defs",
        metadata=FeatureMetadata(
            introduced="Draft 4",
            doc_name="definitions/$defs",
            description="Key for reusable schema definitions",
            status="supported",
        ),
    )
    exclusive_as_number: bool = field(
        default=False,
        metadata=FeatureMetadata(
            introduced="Draft 6",
            doc_name="exclusiveMinimum/Maximum as number",
            description="Numeric `exclusiveMinimum`/`exclusiveMaximum` (boolean in Draft 4)",
            status="supported",
        ),
    )
    read_only_write_only: bool = field(
        default=False,
        metadata=FeatureMetadata(
            introduced="Draft 7",
            doc_name="readOnly/writeOnly",
            description="Field visibility hints for read-only and write-only properties",
            status="supported",
        ),
    )

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
                    exclusive_as_number=False,
                    read_only_write_only=False,
                )
            case JsonSchemaVersion.Draft6:
                return cls(
                    null_in_type_array=False,
                    defs_not_definitions=False,
                    prefix_items=False,
                    boolean_schemas=True,
                    id_field="$id",
                    definitions_key="definitions",
                    exclusive_as_number=True,
                    read_only_write_only=False,
                )
            case JsonSchemaVersion.Draft7:
                return cls(
                    null_in_type_array=False,
                    defs_not_definitions=False,
                    prefix_items=False,
                    boolean_schemas=True,
                    id_field="$id",
                    definitions_key="definitions",
                    exclusive_as_number=True,
                    read_only_write_only=True,
                )
            case JsonSchemaVersion.Draft201909:
                return cls(
                    null_in_type_array=False,
                    defs_not_definitions=True,
                    prefix_items=False,
                    boolean_schemas=True,
                    id_field="$id",
                    definitions_key="$defs",
                    exclusive_as_number=True,
                    read_only_write_only=True,
                )
            case _:
                return cls(
                    null_in_type_array=True,
                    defs_not_definitions=True,
                    prefix_items=True,
                    boolean_schemas=True,
                    id_field="$id",
                    definitions_key="$defs",
                    exclusive_as_number=True,
                    read_only_write_only=True,
                )


@dataclass(frozen=True)
class OpenAPISchemaFeatures(JsonSchemaFeatures):
    """Feature flags for OpenAPI versions.

    Extends JsonSchemaFeatures with OpenAPI-specific features.

    Each field includes metadata for documentation generation.
    Use `dataclasses.fields(OpenAPISchemaFeatures)` to access metadata.
    """

    nullable_keyword: bool = field(
        default=False,
        metadata=FeatureMetadata(
            introduced="OAS 3.0",
            doc_name="nullable",
            description="Uses `nullable: true` for nullable types (deprecated in 3.1)",
            status="supported",
        ),
    )
    discriminator_support: bool = field(
        default=True,
        metadata=FeatureMetadata(
            introduced="OAS 3.0",
            doc_name="discriminator",
            description="Polymorphism support via `discriminator` keyword",
            status="supported",
        ),
    )

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
                    exclusive_as_number=False,
                    read_only_write_only=True,
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
                    exclusive_as_number=True,
                    read_only_write_only=True,
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

    # Heuristic detection based on keywords
    # $defs was introduced in Draft 2019-09, but Draft 2020-12 also uses it.
    # Since 2020-12 is a superset of 2019-09, default to 2020-12 when $defs is present
    # to avoid false warnings in Strict mode for features valid in both versions.
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
            else:  # pragma: no cover
                formats[type_key] = type_formats
    return formats


__all__ = [
    "DataFormatMapping",
    "FeatureMetadata",
    "JsonSchemaFeatures",
    "OpenAPISchemaFeatures",
    "SchemaFeaturesT",
    "detect_jsonschema_version",
    "detect_openapi_version",
    "get_data_formats",
]
