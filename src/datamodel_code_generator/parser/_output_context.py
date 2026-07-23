"""Output model capabilities shared by schema parsers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datamodel_code_generator.model.base import DataModel, DataModelFieldBase
    from datamodel_code_generator.types import DataTypeManager


class OutputModelContext:
    """Resolved capabilities for a configured set of output model types."""

    __slots__ = (
        "_data_model_root_type",
        "_data_model_type",
        "requires_additional_properties_reference_classes",
        "requires_tagged_union_discriminator",
        "supports_annotated_constraints",
        "supports_boolean_literals",
    )

    def __init__(  # noqa: PLR0913
        self,
        *,
        data_model_type: type[DataModel],
        data_model_root_type: type[DataModel],
        supports_annotated_constraints: bool,
        supports_boolean_literals: bool,
        requires_tagged_union_discriminator: bool,
        requires_additional_properties_reference_classes: bool,
    ) -> None:
        self._data_model_type = data_model_type
        self._data_model_root_type = data_model_root_type
        self.supports_annotated_constraints = supports_annotated_constraints
        self.supports_boolean_literals = supports_boolean_literals
        self.requires_tagged_union_discriminator = requires_tagged_union_discriminator
        self.requires_additional_properties_reference_classes = requires_additional_properties_reference_classes

    @classmethod
    def from_generation_types(  # noqa: PLR0913
        cls,
        *,
        data_model_type: type[DataModel],
        data_model_root_type: type[DataModel],
        data_model_field_type: type[DataModelFieldBase],
        data_type_manager_type: type[DataTypeManager],
        configured_types_are_builtin: bool,
        use_annotated: bool,
    ) -> OutputModelContext:
        """Resolve compatible capabilities without depending on an output backend."""
        context = data_model_type.ANNOTATED_CONSTRAINTS_CONTEXT
        root_context = data_model_root_type.ANNOTATED_CONSTRAINTS_CONTEXT
        supports_annotated_constraints = (
            use_annotated
            and configured_types_are_builtin
            and context is not None
            and data_model_type.SUPPORTS_ANNOTATED_CONSTRAINTS
            and data_model_root_type.SUPPORTS_ANNOTATED_CONSTRAINTS
            and data_model_field_type.SUPPORTS_ANNOTATED_CONSTRAINTS
            and data_type_manager_type.SUPPORTS_ANNOTATED_CONSTRAINTS
            and data_model_field_type.ANNOTATED_CONSTRAINTS_CONTEXT is context
            and data_type_manager_type.ANNOTATED_CONSTRAINTS_CONTEXT is context
            and (root_context is None or root_context is context)
        )
        return cls(
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            supports_annotated_constraints=supports_annotated_constraints,
            supports_boolean_literals=data_model_type.SUPPORTS_BOOLEAN_LITERAL,
            requires_tagged_union_discriminator=data_model_type.REQUIRES_TAGGED_UNION_DISCRIMINATOR,
            requires_additional_properties_reference_classes=(
                data_model_type.REQUIRES_ADDITIONAL_PROPERTIES_REFERENCE_CLASSES
            ),
        )

    def resolve_nested_constrained_model_type(self) -> type[DataModel]:
        """Return the root model used for an inline constrained value."""
        return self._data_model_type.resolve_nested_constrained_model_type(self._data_model_root_type)
