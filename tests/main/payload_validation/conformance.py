"""Generated-model conformance policy for invalid payload checks."""

from __future__ import annotations

from typing import Final

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


def rejected_mutation_reason(constraint: str) -> str | None:
    """Return the policy reason for generated-model rejection."""
    return PYDANTIC_V2_REJECTED_MUTATION_CONSTRAINTS.get(constraint)
