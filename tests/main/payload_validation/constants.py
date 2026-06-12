"""Constants for schema-derived payload validation tests."""

from __future__ import annotations

from datamodel_code_generator.format import PythonVersion, is_supported_in_black
from tests.main.conftest import CURRENT_PYTHON_VERSION
from tests.main.payload_validation.models import PayloadBackend

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
    "jsonschema/decimal_fractional_constraints.json": (
        "format decimal strings from hypothesis-jsonschema are arbitrary text that Decimal cannot parse"
    ),
    "jsonschema/integer_fractional_constraints.json": (
        "hypothesis-jsonschema emits integers near float precision limits where multipleOf checks are unstable"
    ),
    "jsonschema/msgspec_decimal_constraints.json": (
        "format decimal strings from hypothesis-jsonschema are arbitrary text that Decimal cannot parse"
    ),
    "jsonschema/non_finite_container_defaults.json": (
        "non-finite defaults cannot be represented in the JSON payloads hypothesis-jsonschema generates"
    ),
    "jsonschema/non_finite_number_values.json": (
        "non-finite bounds cannot be satisfied by any JSON payload hypothesis-jsonschema generates"
    ),
    "jsonschema/uuid_format_versions.json": ("versioned uuid formats reject the fixed version-4 uuid example payloads"),
    "jsonschema/prefix_items_fixed_unevaluated_tail_schema.json": (
        "hypothesis-jsonschema cannot satisfy fixed prefixItems with unevaluatedItems tail constraints"
    ),
    "jsonschema/string_min_max_items_compat.json": (
        "compatibility fixture maps string minItems/maxItems to Pydantic length constraints, "
        "which is stricter than JSON Schema"
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
ROUND_TRIP_EXCLUDED_CASES: dict[str, str] = {
    "jsonschema/default_factory_nested_model_with_dict.json": (
        "pydantic union branch normalization can dump a oneOf value into a shape that matches multiple branches"
    ),
    "jsonschema/external_child_root.json": (
        "schema requires a property absent from properties, so the generated model has no field to dump"
    ),
    "jsonschema/nested_json_pointer.json": (
        "schema requires a property absent from properties, so the generated model has no field to dump"
    ),
    "jsonschema/strict_types_matrix.json": (
        "pydantic serializes Decimal JSON values as strings while the source schema requires number"
    ),
    "openapi/allof_array_ref_override.yaml::components.schemas.DataType": (
        "schema requires a property absent from properties, so the generated model has no field to dump"
    ),
    "openapi/issue_2953.yaml::components.schemas.DataType": (
        "schema requires a property absent from properties, so the generated model has no field to dump"
    ),
}
PYDANTIC_V2_FULL_PAYLOAD_RUNTIME_MIN_VERSION = "2.5.0"
PYDANTIC_V2_LEGACY_RUNTIME_EXCLUDED_CASES: dict[PayloadBackend, dict[str, str]] = {
    PayloadBackend.PYDANTIC_V2: {
        "jsonschema/lookaround_anyof_nullable.json": (
            "Pydantic before 2.5.0 cannot apply regex_engine='python-re' to lookaround pattern validators"
        ),
        "jsonschema/lookaround_dict.json": (
            "Pydantic before 2.5.0 cannot apply regex_engine='python-re' to lookaround pattern validators"
        ),
        "jsonschema/lookaround_mixed_constraints.json": (
            "Pydantic before 2.5.0 cannot apply regex_engine='python-re' to lookaround pattern validators"
        ),
        "jsonschema/lookaround_union_types.json": (
            "Pydantic before 2.5.0 cannot apply regex_engine='python-re' to lookaround pattern validators"
        ),
        "jsonschema/nested_lookaround_array.json": (
            "Pydantic before 2.5.0 cannot apply regex_engine='python-re' to nested lookaround pattern validators"
        ),
        "openapi/pattern_lookaround.yaml::components.schemas.info": (
            "Pydantic before 2.5.0 cannot apply regex_engine='python-re' to OpenAPI lookaround pattern validators"
        ),
        "jsonschema/use_decimal_for_multiple_of.json": (
            "Pydantic before 2.5.0 can reject schema-valid Decimal multipleOf values near float boundaries"
        ),
        "openapi/allof_with_required_inherited_coverage.yaml::components.schemas.MultipleOfBase": (
            "Pydantic before 2.5.0 can reject schema-valid inherited Decimal multipleOf values"
        ),
    },
}
PYDANTIC_V2_LEGACY_RUNTIME_ROUND_TRIP_EXCLUDED_CASES: dict[PayloadBackend, dict[str, str]] = {
    PayloadBackend.PYDANTIC_V2: {
        "jsonschema/property_names_anyof_ref.json": (
            "Pydantic before 2.5.0 emits JSON-mode serializer warnings for enum dictionary keys"
        ),
        "jsonschema/property_names_ref_enum.json": (
            "Pydantic before 2.5.0 emits JSON-mode serializer warnings for enum dictionary keys"
        ),
    },
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
