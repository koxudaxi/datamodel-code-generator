"""Generated-model conformance policy for invalid payload checks."""

from __future__ import annotations

from typing import Final

from .models import PayloadBackend, SchemaCase

PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS: Final[dict[str, str]] = {
    "additionalProperties": "generated pydantic v2 models forbid extra object properties for closed schemas",
    "required": "generated pydantic v2 models require schema-required object properties",
}
PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS: Final[dict[str, str]] = {
    "additionalItems": "tuple additionalItems semantics are not represented by generated models",
    "allOf": "combined schema applicator semantics need a dedicated generated-model compatibility policy",
    "anyOf": "combined schema applicator semantics need a dedicated generated-model compatibility policy",
    "contains": "contains/minContains/maxContains membership semantics are not represented by generated models",
    "const": "JSON Schema equality semantics can differ from generated Python literal validation",
    "dependentRequired": "object dependency semantics are not represented by generated models",
    "dependentSchemas": "dependent schema applicator semantics are not represented by generated models",
    "dependencies": "draft7 dependencies object dependency semantics are not represented by generated models",
    "else": "if/then/else conditional semantics are not represented by generated models",
    "enum": "JSON Schema equality semantics can differ from generated Python enum and literal validation",
    "exclusiveMaximum": "numeric exclusive upper bounds are not enforced by generated models by default",
    "exclusiveMinimum": "numeric exclusive lower bounds are not enforced by generated models by default",
    "if": "if/then/else conditional semantics are not represented by generated models",
    "maximum": "numeric upper bounds are not enforced by generated models by default",
    "maxItems": "array length upper bounds are not enforced by generated models by default",
    "maxLength": "string length upper bounds are not enforced by generated models by default",
    "maxProperties": "object property-count upper bounds are not enforced by generated models by default",
    "minimum": "numeric lower bounds are not enforced by generated models by default",
    "minItems": "array length lower bounds are not enforced by generated models by default",
    "minLength": "string length lower bounds are not enforced by generated models by default",
    "minProperties": "object property-count lower bounds are not enforced by generated models by default",
    "multipleOf": "numeric multipleOf constraints are not enforced by generated models by default",
    "not": "not applicator semantics are not represented by generated models",
    "oneOf": "combined schema applicator semantics need a dedicated generated-model compatibility policy",
    "pattern": "string pattern constraints are not enforced by generated models by default",
    "patternProperties": "dynamic-key semantics are not represented by generated models",
    "prefixItems": "tuple prefix item semantics are not represented by generated models",
    "propertyNames": "object key-validation semantics are not represented by generated models",
    "then": "if/then/else conditional semantics are not represented by generated models",
    "type": "primitive type strictness differs because generated pydantic v2 models use non-strict types by default",
    "unevaluatedItems": "annotation-dependent array semantics are not represented by generated models",
    "unevaluatedProperties": "annotation-dependent object semantics are not represented by generated models",
    "uniqueItems": "array uniqueness semantics are not represented by generated models",
}

PYDANTIC_V2_DATACLASS_REJECTED_MUTATION_CONSTRAINTS: Final[dict[str, str]] = {
    "additionalProperties": "generated pydantic v2 dataclasses forbid extra object properties for closed schemas",
    "required": "generated pydantic v2 dataclasses require schema-required object properties",
}
PYDANTIC_V2_DATACLASS_UNASSERTED_MUTATION_CONSTRAINTS: Final[dict[str, str]] = {
    **PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS,
}

MSGSPEC_REJECTED_MUTATION_CONSTRAINTS: Final[dict[str, str]] = {
    "required": "generated msgspec.Struct classes require schema-required object properties",
}
MSGSPEC_UNASSERTED_MUTATION_CONSTRAINTS: Final[dict[str, str]] = {
    **PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS,
    "additionalProperties": "generated msgspec.Struct classes ignore unknown object properties by default",
}

BACKEND_REJECTED_MUTATION_CONSTRAINTS: Final[dict[PayloadBackend, dict[str, str]]] = {
    PayloadBackend.PYDANTIC_V2: PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS,
    PayloadBackend.PYDANTIC_V2_DATACLASS: PYDANTIC_V2_DATACLASS_REJECTED_MUTATION_CONSTRAINTS,
    PayloadBackend.MSGSPEC: MSGSPEC_REJECTED_MUTATION_CONSTRAINTS,
}
BACKEND_UNASSERTED_MUTATION_CONSTRAINTS: Final[dict[PayloadBackend, dict[str, str]]] = {
    PayloadBackend.PYDANTIC_V2: PYDANTIC_V2_UNASSERTED_MUTATION_CONSTRAINTS,
    PayloadBackend.PYDANTIC_V2_DATACLASS: PYDANTIC_V2_DATACLASS_UNASSERTED_MUTATION_CONSTRAINTS,
    PayloadBackend.MSGSPEC: MSGSPEC_UNASSERTED_MUTATION_CONSTRAINTS,
}
PYDANTIC_V2_DATACLASS_BUILTIN_NAME_EXCLUDED_CASES: Final[dict[str, str]] = {
    "jsonschema/builtin_field_names.json": (
        "pydantic dataclass forward-reference evaluation is confused by fields named like builtins"
    ),
    "jsonschema/field_type_collision_rename_type_double.json": (
        "pydantic dataclass forward-reference evaluation is confused by generated field/type name collisions"
    ),
    "jsonschema/has_default_value.json": (
        "pydantic dataclass forward-reference evaluation is confused by fields named like builtins"
    ),
    "jsonschema/space_field_enum.json": (
        "pydantic dataclass forward-reference evaluation is confused by generated enum field aliases"
    ),
    "openapi/builtin_type_field_names.yaml::components.schemas.BuiltinTypeFieldNames": (
        "pydantic dataclass forward-reference evaluation is confused by fields named like builtins"
    ),
}
PYDANTIC_V2_DATACLASS_REGEX_EXCLUDED_CASES: Final[dict[str, str]] = {
    "jsonschema/lookaround_mixed_constraints.json": (
        "root-level oneOf generates a bare TypeAliasType with no consuming dataclass to carry "
        "ConfigDict(regex_engine='python-re'), so TypeAdapter construction still rejects the lookaround pattern"
    ),
    "openapi/pattern_lookaround.yaml::components.schemas.info": (
        "pydantic dataclass schema construction rejects lookaround regex constraints"
    ),
}
PYDANTIC_V2_DATACLASS_MUTABLE_DEFAULT_EXCLUDED_CASES: Final[dict[str, str]] = {
    "jsonschema/has_classvar_extra_set.json": (
        "dataclass output needs default_factory handling for generated mutable defaults"
    ),
    "jsonschema/pydantic_v2_dataclass_field.json": (
        "dataclass output needs default_factory handling for generated mutable defaults"
    ),
    "jsonschema/root_model_default_value_branches.json": (
        "dataclass output needs default_factory handling for generated mutable defaults"
    ),
    "openapi/allof_partial_override_deeply_nested_array.yaml::components.schemas.Thing": (
        "dataclass output needs default_factory handling for generated mutable defaults"
    ),
    "openapi/allof_partial_override_nested_array_items.yaml::components.schemas.Thing": (
        "dataclass output needs default_factory handling for generated mutable defaults"
    ),
    "openapi/unique_items_default_set.yaml::components.schemas.TestModel": (
        "dataclass output needs default_factory handling for generated mutable defaults"
    ),
}
PYDANTIC_V2_DATACLASS_DEFINITION_RESOLUTION_EXCLUDED_CASES: Final[dict[str, str]] = {
    "jsonschema/collapse_root_models_name_strategy_child.json": (
        "pydantic 2.7 dataclass schema construction cannot resolve generated collapsed-root definitions"
    ),
    "jsonschema/collapse_root_models_name_strategy_complex.json": (
        "pydantic 2.7 dataclass schema construction cannot resolve generated collapsed-root definitions"
    ),
    "jsonschema/collapse_root_models_name_strategy_direct_refs.json": (
        "pydantic 2.7 dataclass schema construction cannot resolve generated collapsed-root definitions"
    ),
    "jsonschema/collapse_root_models_name_strategy_multiple_wrappers.json": (
        "pydantic 2.7 dataclass schema construction cannot resolve generated collapsed-root definitions"
    ),
    "jsonschema/collapse_root_models_name_strategy_nested_wrappers.json": (
        "pydantic 2.7 dataclass schema construction cannot resolve generated collapsed-root definitions"
    ),
    "jsonschema/collapse_root_models_name_strategy_parent.json": (
        "pydantic 2.7 dataclass schema construction cannot resolve generated collapsed-root definitions"
    ),
    "jsonschema/collapse_root_models_name_strategy_with_inheritance.json": (
        "pydantic 2.7 dataclass schema construction cannot resolve generated collapsed-root definitions"
    ),
}
PYDANTIC_V2_DATACLASS_IMPORT_EXCLUDED_CASES: Final[dict[str, str]] = {
    **PYDANTIC_V2_DATACLASS_BUILTIN_NAME_EXCLUDED_CASES,
    **PYDANTIC_V2_DATACLASS_DEFINITION_RESOLUTION_EXCLUDED_CASES,
    **PYDANTIC_V2_DATACLASS_REGEX_EXCLUDED_CASES,
    **PYDANTIC_V2_DATACLASS_MUTABLE_DEFAULT_EXCLUDED_CASES,
    "jsonschema/discriminator_no_literal.json": (
        "dataclass output cannot import when inherited optional discriminator fields precede required fields"
    ),
    "jsonschema/field_has_same_name.json": (
        "pydantic dataclass forward-reference evaluation is confused by a generated field named Field"
    ),
}
PYDANTIC_V2_DATACLASS_VALIDATION_EXCLUDED_CASES: Final[dict[str, str]] = {
    "jsonschema/deprecated_dataclass.json": (
        "pydantic dataclass validation emits deprecation warnings that the test suite treats as failures"
    ),
    "jsonschema/field_name_shadows_class_name.json": (
        "pydantic dataclass validation resolves a generated field/type name collision to the field value"
    ),
    "openapi/enum_models.yaml::components.schemas.nestedNullableEnum": (
        "pydantic dataclass schema construction warns for defaults attached to nullable enum aliases"
    ),
}
DATACLASS_FIELD_ORDER_EXCLUDED_CASES: Final[dict[str, str]] = {
    "jsonschema/discriminator_no_literal.json": (
        "dataclass-like backends cannot import when inherited optional discriminator fields precede required fields"
    ),
}
MSGSPEC_VALIDATION_EXCLUDED_CASES: Final[dict[str, str]] = {
    "jsonschema/array_combined.py.json": (
        "msgspec conversion cannot validate generated empty Enum classes from array-valued enum schemas"
    ),
    "jsonschema/all_of_ref_self.json": (
        "msgspec 0.18 cannot evaluate generated null-only union aliases during conversion"
    ),
    "jsonschema/builtin_field_names.json": (
        "msgspec forward-reference evaluation is confused by fields named like builtins"
    ),
    "openapi/builtin_type_field_names.yaml::components.schemas.BuiltinTypeFieldNames": (
        "msgspec forward-reference evaluation is confused by fields named like builtins"
    ),
    "jsonschema/combine_any_of_object.json": (
        "msgspec conversion requires tagged Struct unions for combined object schemas"
    ),
    "jsonschema/combine_one_of_object.json": (
        "msgspec conversion requires tagged Struct unions for combined object schemas"
    ),
    "jsonschema/collapse_root_models_empty_union.json": (
        "msgspec 0.18 cannot evaluate generated null-only union aliases during conversion"
    ),
    "jsonschema/default_factory_nested_model_with_dict.json": (
        "msgspec conversion rejects unions containing multiple dict-like runtime types"
    ),
    "jsonschema/enum_complex_values_literal.json": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "jsonschema/enum_member_typed_defaults.json": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "jsonschema/enum_object_values.json": (
        "msgspec conversion cannot validate generated empty Enum classes from object-valued enum schemas"
    ),
    "jsonschema/falsy_default_enum_member.json": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "jsonschema/field_has_same_name.json": ("msgspec conversion cannot evaluate generated field/type name collisions"),
    "jsonschema/field_name_shadows_class_name.json": (
        "msgspec conversion cannot evaluate generated field/type name collisions"
    ),
    "jsonschema/field_type_collision_rename_type_double.json": (
        "msgspec conversion cannot evaluate generated field/type name collisions"
    ),
    "jsonschema/has_default_value.json": "msgspec conversion cannot evaluate generated fields named like builtins",
    "openapi/discriminator_float_mapping.yaml::components.schemas.Bar": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "openapi/discriminator_float_mapping.yaml::components.schemas.Foo": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "openapi/enum_models.yaml::components.schemas.Pet": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "openapi/enum_models.yaml::components.schemas.version": (
        "msgspec conversion does not accept nullable enum aliases generated from OpenAPI schemas"
    ),
    "jsonschema/nullable_enum_literal_typed_dict.json": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "jsonschema/oneof_const_enum_bool.json": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "jsonschema/oneof_const_enum_float.json": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "jsonschema/oneof_const_enum_object.yaml": (
        "msgspec conversion cannot validate generated empty Enum classes from object-valued const schemas"
    ),
    "jsonschema/property_names_anyof_ref.json": (
        "msgspec conversion rejects unions containing multiple string Enum types"
    ),
    "jsonschema/property_names_ref_enum.json": (
        "msgspec conversion does not support generated property-name Enum key aliases"
    ),
    "jsonschema/ref_type_has_null.json": (
        "msgspec 0.18 cannot evaluate generated null-only union aliases during conversion"
    ),
    "jsonschema/recursive_ref.json": "msgspec conversion cannot evaluate generated recursive Struct aliases",
    "jsonschema/recursive_ref_in_defs.json": ("msgspec conversion cannot evaluate generated recursive Struct aliases"),
    "jsonschema/recursive_ref_no_anchor.json": (
        "msgspec conversion cannot evaluate generated recursive Struct aliases"
    ),
    "jsonschema/special_enum.json": (
        "msgspec conversion only supports Enum classes with homogeneous str or int values"
    ),
    "jsonschema/space_field_enum.json": (
        "msgspec conversion cannot evaluate generated enum field/type name collisions"
    ),
    "jsonschema/strict_types_matrix.json": (
        "msgspec conversion rejects numeric constraint metadata attached to Decimal types"
    ),
    "jsonschema/anyof_const_with_constraints.json": (
        "msgspec conversion rejects constrained scalar unions that differ from JSON Schema branch semantics"
    ),
    "jsonschema/invalid_model_name.json": (
        "msgspec conversion does not accept nullable alias shapes generated for this schema"
    ),
    "jsonschema/msgspec_null_field.json": (
        "msgspec conversion does not accept null-only field aliases generated from JSON Schema"
    ),
    "jsonschema/person.json": ("msgspec conversion does not accept nullable alias shapes generated for this schema"),
    "jsonschema/pydantic_v2_dataclass_field.json": (
        "msgspec conversion rejects fractional multipleOf constraint metadata for scalar fields"
    ),
    "jsonschema/use_decimal_for_multiple_of.json": (
        "msgspec conversion rejects fractional multipleOf constraint metadata for scalar fields"
    ),
    "openapi/msgspec_oneof_with_null.yaml::components.schemas.Model": (
        "msgspec conversion rejects nullable oneOf metadata attached to generated aliases"
    ),
    "openapi/type_mappings_byte_to_binary.yaml::components.schemas.Foo": (
        "msgspec conversion treats binary string mappings as strict bytes while JSON Schema treats encoding as "
        "annotation"
    ),
    "jsonschema/pydantic_v2_model_default_dict_non_empty.json": (
        "msgspec default_factory conversion does not preserve dict-of-model defaults for payload construction"
    ),
    "jsonschema/reduce_duplicate_field_types.json": (
        "msgspec conversion requires tagged Struct unions for combined object schemas"
    ),
    "jsonschema/ref_merge_field_metadata.json": (
        "msgspec conversion rejects length metadata attached to generated Literal types"
    ),
    "jsonschema/reuse_model_collapse_root_models_constraints.json": (
        "msgspec conversion requires tagged Struct unions for combined object schemas"
    ),
    "jsonschema/root_model_with_additional_properties.json": (
        "msgspec conversion requires tagged Struct unions for combined object schemas"
    ),
    "jsonschema/json_pointer.json": ("msgspec conversion requires tagged Struct unions for combined object schemas"),
    "jsonschema/nested_json_pointer.json": (
        "msgspec conversion requires tagged Struct unions for combined object schemas"
    ),
    "jsonschema/object_has_one_of.json": (
        "msgspec conversion requires tagged Struct unions for combined object schemas"
    ),
    "jsonschema/lookaround_anyof_nullable.json": (
        "msgspec conversion rejects generated lookaround regex metadata in non-string containers"
    ),
    "jsonschema/lookaround_dict.json": (
        "msgspec conversion rejects generated lookaround regex metadata in non-string containers"
    ),
    "jsonschema/lookaround_mixed_constraints.json": (
        "msgspec conversion rejects generated lookaround regex metadata in non-string containers"
    ),
    "jsonschema/lookaround_union_types.json": (
        "msgspec conversion rejects generated lookaround regex metadata in non-string containers"
    ),
    "jsonschema/nested_lookaround_array.json": (
        "msgspec conversion rejects generated lookaround regex metadata in non-string containers"
    ),
    "openapi/pattern_lookaround.yaml::components.schemas.info": (
        "msgspec conversion rejects generated lookaround regex metadata in non-string containers"
    ),
}
BACKEND_FULL_MATRIX_EXCLUDED_CASES: Final[dict[PayloadBackend, dict[str, str]]] = {
    PayloadBackend.PYDANTIC_V2_DATACLASS: {
        **PYDANTIC_V2_DATACLASS_IMPORT_EXCLUDED_CASES,
        **PYDANTIC_V2_DATACLASS_VALIDATION_EXCLUDED_CASES,
    },
    PayloadBackend.MSGSPEC: {
        **DATACLASS_FIELD_ORDER_EXCLUDED_CASES,
        **MSGSPEC_VALIDATION_EXCLUDED_CASES,
    },
}
BACKEND_ACCEPTANCE_EXCLUDED_CASES: Final[dict[PayloadBackend, dict[str, str]]] = BACKEND_FULL_MATRIX_EXCLUDED_CASES
BACKEND_REJECTION_EXCLUDED_CASES: Final[dict[PayloadBackend, dict[str, str]]] = BACKEND_FULL_MATRIX_EXCLUDED_CASES
DATACLASSES_FULL_MATRIX_EXCLUSION_REASON: Final[str] = (
    "plain dataclasses remain representative because native construction has no JSON Schema runtime validation"
)
OPENAPI_FULL_MATRIX_EXCLUSION_REASONS: Final[dict[PayloadBackend, str]] = {
    PayloadBackend.PYDANTIC_V2_DATACLASS: (
        "OpenAPI pydantic dataclass full-matrix coverage remains representative until backend-specific "
        "alias, default, and composition limits are reduced"
    ),
    PayloadBackend.MSGSPEC: (
        "OpenAPI msgspec full-matrix coverage remains representative until backend-specific enum, null, "
        "and composition limits are reduced"
    ),
}
PAYLOAD_VALIDATION_BACKENDS: Final[tuple[PayloadBackend, ...]] = (
    PayloadBackend.PYDANTIC_V2,
    PayloadBackend.PYDANTIC_V2_DATACLASS,
    PayloadBackend.MSGSPEC,
)


def rejected_mutation_constraints(backend: PayloadBackend) -> frozenset[str]:
    """Return mutation constraints asserted for a backend."""
    return frozenset(BACKEND_REJECTED_MUTATION_CONSTRAINTS.get(backend, {}))


def rejected_mutation_reason(constraint: str, backend: PayloadBackend = PayloadBackend.PYDANTIC_V2) -> str | None:
    """Return the policy reason for generated-model rejection."""
    return BACKEND_REJECTED_MUTATION_CONSTRAINTS.get(backend, {}).get(constraint)


def backend_acceptance_exclusion_reason(case: SchemaCase, backend: PayloadBackend) -> str | None:
    """Return why a backend acceptance case is outside the full scheduled matrix."""
    if backend is PayloadBackend.DATACLASSES:
        return DATACLASSES_FULL_MATRIX_EXCLUSION_REASON
    if reason := BACKEND_ACCEPTANCE_EXCLUDED_CASES.get(backend, {}).get(case.id):
        return reason
    if case.input_file_type == "openapi":
        return OPENAPI_FULL_MATRIX_EXCLUSION_REASONS.get(backend)
    return None


def backend_rejection_exclusion_reason(case: SchemaCase, backend: PayloadBackend) -> str | None:
    """Return why a backend rejection case is outside the full scheduled matrix."""
    if reason := BACKEND_REJECTION_EXCLUDED_CASES.get(backend, {}).get(case.id):
        return reason
    if case.input_file_type == "openapi":
        return OPENAPI_FULL_MATRIX_EXCLUSION_REASONS.get(backend)
    return None
