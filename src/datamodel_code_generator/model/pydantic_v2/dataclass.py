"""Pydantic v2 dataclass model generator.

Generates pydantic.dataclasses.dataclass decorated classes with validation support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.dataclass import has_field_assignment
from datamodel_code_generator.model.pydantic_v2.base_model import Constraints
from datamodel_code_generator.model.pydantic_v2.base_model import (
    DataModelField as DataModelFieldV2,
)
from datamodel_code_generator.model.pydantic_v2.imports import (
    IMPORT_CONFIG_DICT,
    IMPORT_PYDANTIC_DATACLASS,
)
from datamodel_code_generator.reference import Reference

if TYPE_CHECKING:
    from collections import defaultdict
    from pathlib import Path

    from datamodel_code_generator import DataclassArguments
    from datamodel_code_generator.imports import Import


class DataClass(DataModel):
    """DataModel implementation for Pydantic v2 dataclasses."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/dataclass.jinja2"
    DEFAULT_IMPORTS: ClassVar[tuple[Import, ...]] = (IMPORT_PYDANTIC_DATACLASS,)
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_KW_ONLY: ClassVar[bool] = True

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        methods: list[str] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        frozen: bool = False,
        treat_dot_as_module: bool | None = None,
        dataclass_arguments: DataclassArguments | None = None,
    ) -> None:
        """Initialize pydantic v2 dataclass with sorted fields and ConfigDict support."""
        super().__init__(
            reference=reference,
            fields=sorted(fields, key=has_field_assignment),
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            methods=methods,
            path=path,
            description=description,
            default=default,
            nullable=nullable,
            keyword_only=keyword_only,
            frozen=frozen,
            treat_dot_as_module=treat_dot_as_module,
        )

        if dataclass_arguments is not None:
            self.dataclass_arguments = dataclass_arguments
        else:
            self.dataclass_arguments = {}
            if frozen:
                self.dataclass_arguments["frozen"] = True
            if keyword_only:
                self.dataclass_arguments["kw_only"] = True

        config_parameters: dict[str, Any] = {}

        extra = self._get_config_extra()
        if extra:
            config_parameters["extra"] = extra

        if self.extra_template_data.get("use_attribute_docstrings"):
            config_parameters["use_attribute_docstrings"] = True

        for data_type in self.all_data_types:
            if data_type.is_custom_type:  # pragma: no cover
                config_parameters["arbitrary_types_allowed"] = True
                break

        if config_parameters:
            self._additional_imports.append(IMPORT_CONFIG_DICT)
            self.extra_template_data["config"] = config_parameters

    def _get_config_extra(self) -> str | None:
        """Get extra field configuration for ConfigDict."""
        additional_properties = self.extra_template_data.get("additionalProperties")
        unevaluated_properties = self.extra_template_data.get("unevaluatedProperties")
        allow_extra_fields = self.extra_template_data.get("allow_extra_fields")
        extra_fields = self.extra_template_data.get("extra_fields")

        config_extra = None
        if allow_extra_fields or extra_fields == "allow":
            config_extra = "'allow'"
        elif extra_fields == "forbid":
            config_extra = "'forbid'"
        elif extra_fields == "ignore":
            config_extra = "'ignore'"
        elif additional_properties is True:
            config_extra = "'allow'"
        elif additional_properties is False:
            config_extra = "'forbid'"
        elif unevaluated_properties is True:
            config_extra = "'allow'"
        elif unevaluated_properties is False:
            config_extra = "'forbid'"
        return config_extra

    def create_reuse_model(self, base_ref: Reference) -> DataClass:
        """Create inherited model with empty fields pointing to base reference."""
        return self.__class__(
            fields=[],
            base_classes=[base_ref],
            description=self.description,
            reference=Reference(
                name=self.name,
                path=self.reference.path + "/reuse",
            ),
            custom_template_dir=self._custom_template_dir,
            custom_base_class=self.custom_base_class,
            keyword_only=self.keyword_only,
            frozen=self.frozen,
            treat_dot_as_module=self._treat_dot_as_module,
            dataclass_arguments=self.dataclass_arguments,
        )


class DataModelField(DataModelFieldV2):
    """Field implementation for Pydantic v2 dataclass models.

    Inherits pydantic v2 Field() constraint handling from DataModelFieldV2.
    """

    constraints: Constraints | None = None  # pyright: ignore[reportIncompatibleVariableOverride]

    def process_const(self) -> None:
        """Process const field constraint using literal type."""
        self._process_const_as_literal()
