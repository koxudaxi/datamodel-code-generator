"""Lightweight output-owned field-name policies."""

from __future__ import annotations

from keyword import iskeyword

from pydantic import BaseModel as PydanticBaseModel

from datamodel_code_generator.reference import FieldNameResolver


class PydanticFieldNameResolver(FieldNameResolver):
    """Resolve field names according to Pydantic BaseModel ownership rules."""

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

    def _validate_field_name(self, field_name: str) -> bool:  # noqa: PLR6301
        return field_name != "field"


PydanticFieldNameResolver.__module__ = "datamodel_code_generator.reference"
MsgspecFieldNameResolver.__module__ = "datamodel_code_generator.reference"
