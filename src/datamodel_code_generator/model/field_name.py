"""Lightweight output-owned field-name policies."""

from __future__ import annotations

from keyword import iskeyword
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel as PydanticBaseModel

from datamodel_code_generator.reference import FieldNameResolver

if TYPE_CHECKING:
    from datamodel_code_generator.model import base as model_base


def _explicit_alias_conflicts_with_pydantic(field: model_base.DataModelFieldBase, name: str) -> bool:
    """Respect generated namespace configuration without importing custom bases."""
    if name == "model_config" or name.startswith("_"):
        return True
    if not hasattr(PydanticBaseModel, name):
        return False
    from datamodel_code_generator.model.base import _find_base_classes  # noqa: PLC0415

    namespaces = ("model_validate", "model_dump")
    pending = [cast("model_base.DataModel", field.parent)]
    while pending:
        model = pending.pop()
        config = model.extra_template_data.get("config")
        if (configured := getattr(config, "protected_namespaces", None)) is not None:
            namespaces = configured
            break
        base_classes = _find_base_classes(model)
        if not base_classes and model.custom_base_class and model.custom_base_class != "pydantic.BaseModel":
            # This later external base may override any earlier generated base's namespaces.
            return False
        pending.extend(base_classes)
    return name.startswith(namespaces)


class PydanticFieldNameResolver(FieldNameResolver):
    """Resolve field names according to Pydantic BaseModel ownership rules."""

    EXPLICIT_ALIAS_CONFLICT_CHECKER = staticmethod(_explicit_alias_conflicts_with_pydantic)

    def get_valid_name(
        self,
        name: str,
        excludes: set[str] | None = None,
        ignore_snake_case_field: bool = False,  # noqa: FBT001, FBT002
        upper_camel: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """Convert a name to a valid Pydantic field name."""
        if (
            fast_name := self._get_valid_name_fast_path(
                name,
                excludes,
                ignore_snake_case_field,
                upper_camel,
            )
        ) is not None:
            return fast_name
        return super().get_valid_name(name, excludes, ignore_snake_case_field, upper_camel)

    def _get_valid_name_fast_path(
        self,
        name: str,
        excludes: set[str] | None,
        ignore_snake_case_field: bool,  # noqa: FBT001
        upper_camel: bool,  # noqa: FBT001
    ) -> str | None:
        """Skip normalization for ordinary Pydantic field names."""
        if type(self) is not PydanticFieldNameResolver:
            return None
        if not name.isascii() or not name.isidentifier() or name.startswith("_"):
            return None
        if iskeyword(name) or self.capitalise_enum_members or upper_camel:
            return None
        if self.snake_case_field and not ignore_snake_case_field:
            return None
        if excludes and name in excludes:
            return None
        return name if self._validate_field_name(name) else None

    def _validate_field_name(self, field_name: str) -> bool:  # noqa: PLR6301
        """Check whether a field would shadow a Pydantic BaseModel attribute."""
        return not hasattr(PydanticBaseModel, field_name)


class MsgspecFieldNameResolver(FieldNameResolver):
    """Avoid shadowing the output-owned msgspec ``field`` import."""

    FIELD_ASSIGNMENT_HELPER = "field"

    def _validate_field_name(self, field_name: str) -> bool:  # noqa: PLR6301
        return field_name != "field"


PydanticFieldNameResolver.__module__ = "datamodel_code_generator.reference"
MsgspecFieldNameResolver.__module__ = "datamodel_code_generator.reference"
