"""Constants for schema-derived payload validation tests."""

from __future__ import annotations

from datamodel_code_generator.format import PythonVersion, is_supported_in_black
from tests.main.conftest import CURRENT_PYTHON_VERSION

PAYLOAD_CLASS_NAME = "Payload"
PAYLOAD_CURRENT_PYTHON_VERSION = PythonVersion(CURRENT_PYTHON_VERSION)
SCHEMA_FILE_SUFFIXES = {".json", ".yaml", ".yml"}
COMBINED_SCHEMA_KEYS = ("allOf", "anyOf", "oneOf")
JSON_SCHEMA_KEYS = {
    "$defs",
    "$id",
    "$ref",
    "$schema",
    "additionalProperties",
    *COMBINED_SCHEMA_KEYS,
    "definitions",
    "enum",
    "items",
    "properties",
    "type",
}
OBJECT_SCHEMA_KEYWORDS = {
    "additionalProperties",
    "maxProperties",
    "minProperties",
    "properties",
    "propertyNames",
    "required",
    "unevaluatedProperties",
}
ARRAY_SCHEMA_KEYWORDS = {
    "additionalItems",
    "contains",
    "items",
    "maxContains",
    "maxItems",
    "minContains",
    "minItems",
    "prefixItems",
    "unevaluatedItems",
    "uniqueItems",
}
SIMPLE_ALLOF_IGNORED_KEYS = {"description", "title"}
SIMPLE_ALLOF_SUPPORTED_KEYS = {
    "const",
    "enum",
    "exclusiveMaximum",
    "exclusiveMinimum",
    "format",
    "maximum",
    "maxItems",
    "maxLength",
    "minimum",
    "minItems",
    "minLength",
    "multipleOf",
    "type",
    "uniqueItems",
}
PAYLOAD_FORMAT_ENUMS = {
    "byte": ["", "MA==", "Zm9v"],
    "date-time-local": ["2023-12-25T10:30:00"],
    "duration": ["P1D", "PT1S"],
    "ipv4": ["127.0.0.1"],
    "ipv6": ["::1"],
    "uuid": ["00000000-0000-4000-8000-000000000000"],
}
EXCLUDED_FILES: dict[str, str] = {
    "jsonschema/allof_class_hierarchy.json": "intentionally invalid JSON fixture",
    "jsonschema/non_dict_files/list_only.json": "input is JSON data, not a JSON Schema document",
    "jsonschema/non_dict_files/list_only.yaml": "input is YAML data, not a JSON Schema document",
    "jsonschema/non_dict_files/whitespace_only.yaml": "empty YAML fixture",
    "jsonschema/non_json_object.json": "input is JSON data, not a JSON Schema document",
    "jsonschema/null.json": "intentionally invalid JSON fixture",
    "jsonschema/ref_to_json_list/list.json": "referenced JSON data list, not a schema document",
    "jsonschema/unknown_format.json": "unknown format fixture intentionally emits a generator warning",
    "openapi/complex_reference.json": "intentionally invalid JSON fixture",
    "openapi/list.json": "input is JSON data, not an OpenAPI document",
    "openapi/not.json": "intentionally invalid JSON fixture",
    "openapi/subclass_enum.json": "intentionally invalid JSON fixture",
}
EXCLUDED_CASES: dict[str, str] = {
    "jsonschema/all_of_any_of_base_class_ref.json": "hypothesis-jsonschema cannot satisfy the allOf/anyOf constraints",
    "jsonschema/prefix_items_fixed_unevaluated_tail_schema.json": (
        "hypothesis-jsonschema cannot satisfy fixed prefixItems with unevaluatedItems tail constraints"
    ),
    "jsonschema/typed_dict_allof_constraint_extra_items.json": (
        "TypedDict-only e2e fixture intentionally emits a generator warning; Pydantic payload validation "
        "uses the same schema corpus but does not target this output mode"
    ),
    "openapi/allof.yaml::components.schemas.AllOfNested3": (
        "hypothesis-jsonschema cannot satisfy the nested allOf component constraints"
    ),
    "openapi/allof_with_required_inherited_complex_allof.yaml::components.schemas.ProjectedItem": (
        "hypothesis-jsonschema generates this nested allOf schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_comprehensive.yaml::components.schemas.Entity": (
        "hypothesis-jsonschema generates this inherited allOf schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_comprehensive.yaml::components.schemas.ProjectedEntity": (
        "hypothesis-jsonschema generates this inherited allOf schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_coverage.yaml::components.schemas.EdgeCasesCoverage": (
        "hypothesis-jsonschema generates this inherited allOf coverage schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_edge_cases.yaml::components.schemas.EdgeCases": (
        "hypothesis-jsonschema generates this inherited allOf edge-case schema inconsistently"
    ),
    "openapi/allof_with_required_inherited_edge_cases.yaml::components.schemas.ProjectedEdgeCases": (
        "hypothesis-jsonschema generates this allOf edge-case schema inconsistently"
    ),
    "openapi/discriminator.yaml::components.schemas.Demo": (
        "discriminator branches overlap under JSON Schema validation; see payload_validation_future_work.md"
    ),
    "openapi/discriminator_float_mapping.yaml::components.schemas.Base": (
        "numeric discriminator mapping needs an explicit backend compatibility policy; "
        "see payload_validation_future_work.md"
    ),
    "openapi/discriminator_in_array_oneof.yaml::components.schemas.Demo": (
        "array item discriminator tags conflict with inherited JSON Schema constraints; "
        "see payload_validation_future_work.md"
    ),
    "openapi/discriminator_without_mapping.yaml::components.schemas.Demo": (
        "implicit discriminator tags conflict with source enum constraints; see payload_validation_future_work.md"
    ),
    "openapi/ref_nullable.yaml::components.schemas.NullableChild": (
        "top-level nullable object components need a wrapper policy; nullable refs are covered via Parent"
    ),
}


def _payload_target_python_version() -> str:
    if is_supported_in_black(PAYLOAD_CURRENT_PYTHON_VERSION):
        return CURRENT_PYTHON_VERSION
    supported_versions = [
        python_version
        for python_version in PythonVersion
        if python_version.version_key <= PAYLOAD_CURRENT_PYTHON_VERSION.version_key
        and is_supported_in_black(python_version)
    ]
    return max(supported_versions, key=lambda python_version: python_version.version_key).value


PAYLOAD_TARGET_PYTHON_VERSION = _payload_target_python_version()
