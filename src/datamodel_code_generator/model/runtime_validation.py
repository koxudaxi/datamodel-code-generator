"""Structured runtime validation rules derived from source schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datamodel_code_generator.types import DataType

InputNames = tuple[str, ...]
RequiredGroup = tuple[InputNames, ...]
RequiredGroups = tuple[RequiredGroup, ...]
Condition = tuple[tuple[InputNames, tuple[object, ...]], ...]


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


@dataclass
class SchemaRuntimeValidation:
    """Schema-derived runtime validation rules for a generated model."""

    pattern_properties: list[PatternPropertiesRule] = field(default_factory=list)
    required_groups: list[RequiredGroupsRule] = field(default_factory=list)
    conditional_required: list[ConditionalRequiredRule] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Return whether any runtime validation rule is registered."""
        return bool(self.pattern_properties or self.required_groups or self.conditional_required)

    @property
    def data_types(self) -> tuple[DataType, ...]:
        """Return all generated data types referenced by runtime rules."""
        return tuple(data_type for rule in self.pattern_properties for data_type in rule.data_types)
