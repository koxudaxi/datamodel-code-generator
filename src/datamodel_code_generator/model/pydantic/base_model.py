"""Pydantic v1 BaseModel implementation.

Provides Constraints, DataModelField, and BaseModel for Pydantic v1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.pydantic.imports import IMPORT_EXTRA
from datamodel_code_generator.model.pydantic_base import (
    BaseModelBase,
    Constraints,
)
from datamodel_code_generator.model.pydantic_base import (
    DataModelField as _DataModelFieldBase,
)
from datamodel_code_generator.util import model_validate

if TYPE_CHECKING:
    from collections import defaultdict
    from pathlib import Path

    from datamodel_code_generator.model import DataModelFieldBase
    from datamodel_code_generator.reference import Reference

# Re-export shared classes
__all__ = ["BaseModel", "BaseModelBase", "Constraints", "DataModelField"]


class DataModelField(_DataModelFieldBase):
    """Field implementation for Pydantic v1 models."""

    _PARSE_METHOD: ClassVar[str] = "parse_obj"

    def _process_data_in_str(self, data: dict[str, Any]) -> None:
        if self.const:
            data["const"] = True

        if self.use_frozen_field and self.read_only:
            data["allow_mutation"] = False

    def _process_annotated_field_arguments(self, field_arguments: list[str]) -> list[str]:  # noqa: PLR6301
        return field_arguments


class BaseModel(BaseModelBase):
    """Pydantic v1 BaseModel implementation."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic/BaseModel.jinja2"
    BASE_CLASS: ClassVar[str] = "pydantic.BaseModel"
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True

    def __init__(  # noqa: PLR0912, PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, Any] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        treat_dot_as_module: bool | None = None,
    ) -> None:
        """Initialize the BaseModel with Config and extra fields support."""
        super().__init__(
            reference=reference,
            fields=fields,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            path=path,
            description=description,
            default=default,
            nullable=nullable,
            keyword_only=keyword_only,
            treat_dot_as_module=treat_dot_as_module,
        )
        config_parameters: dict[str, Any] = {}

        additional_properties = self.extra_template_data.get("additionalProperties")
        unevaluated_properties = self.extra_template_data.get("unevaluatedProperties")
        allow_extra_fields = self.extra_template_data.get("allow_extra_fields")
        extra_fields = self.extra_template_data.get("extra_fields")

        if (
            allow_extra_fields
            or extra_fields
            or additional_properties is not None
            or unevaluated_properties is not None
        ):
            self._additional_imports.append(IMPORT_EXTRA)

        if allow_extra_fields:
            config_parameters["extra"] = "Extra.allow"
        elif extra_fields:
            config_parameters["extra"] = f"Extra.{extra_fields}"
        elif additional_properties is True:
            config_parameters["extra"] = "Extra.allow"
        elif additional_properties is False:
            config_parameters["extra"] = "Extra.forbid"
        elif unevaluated_properties is True:
            config_parameters["extra"] = "Extra.allow"
        elif unevaluated_properties is False:
            config_parameters["extra"] = "Extra.forbid"

        for config_attribute in "allow_population_by_field_name", "allow_mutation":
            if config_attribute in self.extra_template_data:
                config_parameters[config_attribute] = self.extra_template_data[config_attribute]

        if "validate_assignment" not in config_parameters and any(
            field.use_frozen_field and field.read_only for field in self.fields
        ):
            config_parameters["validate_assignment"] = True

        for data_type in self.all_data_types:
            if data_type.is_custom_type:  # pragma: no cover
                config_parameters["arbitrary_types_allowed"] = True
                break

        if isinstance(self.extra_template_data.get("config"), dict):
            for key, value in self.extra_template_data["config"].items():
                config_parameters[key] = value  # noqa: PERF403

        if config_parameters:
            from datamodel_code_generator.model.pydantic import Config  # noqa: PLC0415

            self.extra_template_data["config"] = model_validate(Config, config_parameters)  # ty: ignore
