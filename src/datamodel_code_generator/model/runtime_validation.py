"""Structured runtime validation rules derived from source schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, TypeAlias

if TYPE_CHECKING:
    from datamodel_code_generator.types import DataType

InputNames: TypeAlias = tuple[str, ...]
RequiredGroup: TypeAlias = tuple[InputNames, ...]
RequiredGroups: TypeAlias = tuple[RequiredGroup, ...]
Condition: TypeAlias = tuple[tuple[InputNames, tuple[object, ...]], ...]
_INTERNAL_SCHEMA_RUNTIME_VALIDATION_TOKEN = object()
_INTERNAL_SCHEMA_RUNTIME_VALIDATION_ERROR = "internal schema runtime validation must be created by the parser"


@dataclass(frozen=True)
class PatternPropertiesRule:
    """Runtime rule for JSON Schema patternProperties."""

    declared_properties: tuple[str, ...]
    pattern_properties: tuple[tuple[str, DataType], ...]
    rejected_patterns: tuple[str, ...] = ()
    additional_property_type: DataType | None = None
    allow_unmatched: bool = True

    @property
    def data_types(self) -> tuple[DataType, ...]:
        """Return all generated data types referenced by this rule."""
        data_types = tuple(data_type for _, data_type in self.pattern_properties)
        if self.additional_property_type is None:
            return data_types
        return (*data_types, self.additional_property_type)


@dataclass(frozen=True)
class RequiredGroupsRule:
    """Runtime rule for required-property oneOf/anyOf groups."""

    keyword: Literal["anyOf", "oneOf"]
    groups: RequiredGroups


@dataclass(frozen=True)
class ConditionalRequiredRule:
    """Runtime rule for if/then/else required-property conditions."""

    condition: Condition
    then_groups: RequiredGroups
    else_groups: RequiredGroups


@dataclass(frozen=True, slots=True)
class PropertyCountRule:
    """Runtime rule for JSON Schema object property-count bounds."""

    min_properties: int | None = None
    max_properties: int | None = None


@dataclass
class SchemaRuntimeValidation:
    """Schema-derived runtime validation rules for a generated model."""

    pattern_properties: list[PatternPropertiesRule] = field(default_factory=list)
    required_groups: list[RequiredGroupsRule] = field(default_factory=list)
    conditional_required: list[ConditionalRequiredRule] = field(default_factory=list)
    property_count: PropertyCountRule | None = None

    def __bool__(self) -> bool:
        """Return whether any runtime validation rule is registered."""
        return bool(self.pattern_properties or self.required_groups or self.conditional_required or self.property_count)

    @property
    def data_types(self) -> tuple[DataType, ...]:
        """Return all generated data types referenced by runtime rules."""
        return tuple(data_type for rule in self.pattern_properties for data_type in rule.data_types)


class _InternalSchemaRuntimeValidation(SchemaRuntimeValidation):
    """A parser-owned runtime-validation value safe for built-in templates."""

    __slots__ = ()

    def __init__(
        self,
        token: object,
        *,
        pattern_properties: list[PatternPropertiesRule] | None = None,
        required_groups: list[RequiredGroupsRule] | None = None,
        conditional_required: list[ConditionalRequiredRule] | None = None,
        property_count: PropertyCountRule | None = None,
    ) -> None:
        if token is not _INTERNAL_SCHEMA_RUNTIME_VALIDATION_TOKEN:
            raise TypeError(_INTERNAL_SCHEMA_RUNTIME_VALIDATION_ERROR)
        super().__init__(
            pattern_properties=[] if pattern_properties is None else pattern_properties,
            required_groups=[] if required_groups is None else required_groups,
            conditional_required=[] if conditional_required is None else conditional_required,
            property_count=property_count,
        )


def _make_internal_schema_runtime_validation(
    *,
    pattern_properties: list[PatternPropertiesRule] | None = None,
    required_groups: list[RequiredGroupsRule] | None = None,
    conditional_required: list[ConditionalRequiredRule] | None = None,
    property_count: PropertyCountRule | None = None,
) -> SchemaRuntimeValidation:
    """Create parser-owned runtime validation metadata for built-in rendering."""
    return _InternalSchemaRuntimeValidation(
        _INTERNAL_SCHEMA_RUNTIME_VALIDATION_TOKEN,
        pattern_properties=pattern_properties,
        required_groups=required_groups,
        conditional_required=conditional_required,
        property_count=property_count,
    )


def _is_internal_schema_runtime_validation(value: object) -> bool:
    """Return whether a value was created by the parser-owned factory."""
    return isinstance(value, _InternalSchemaRuntimeValidation)
