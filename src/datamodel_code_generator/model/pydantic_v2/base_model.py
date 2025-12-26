"""Pydantic v2 BaseModel implementation.

Provides Constraints, DataModelField, and BaseModel for Pydantic v2
with support for Field() constraints and ConfigDict.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar, Literal, NamedTuple, Optional

from pydantic import Field

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.base import ALL_MODEL, UNDEFINED, BaseClassDataType, DataModelFieldBase
from datamodel_code_generator.model.pydantic.base_model import (
    BaseModelBase,
)
from datamodel_code_generator.model.pydantic.base_model import (
    Constraints as _Constraints,
)
from datamodel_code_generator.model.pydantic.base_model import (
    DataModelField as DataModelFieldV1,
)
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_BASE_MODEL, IMPORT_CONFIG_DICT
from datamodel_code_generator.util import field_validator, model_validate, model_validator

if TYPE_CHECKING:
    from pathlib import Path

    from datamodel_code_generator.reference import Reference


class Constraints(_Constraints):
    """Pydantic v2 field constraints with pattern support."""

    # To override existing pattern alias
    regex: Optional[str] = Field(None, alias="regex")  # noqa: UP045
    pattern: Optional[str] = Field(None, alias="pattern")  # noqa: UP045

    @model_validator(mode="before")
    def validate_min_max_items(cls, values: Any) -> dict[str, Any]:  # noqa: N805
        """Validate and convert minItems/maxItems to minLength/maxLength."""
        if not isinstance(values, dict):  # pragma: no cover
            return values
        min_items = values.pop("minItems", None)
        if min_items is not None:
            values["minLength"] = min_items
        max_items = values.pop("maxItems", None)
        if max_items is not None:
            values["maxLength"] = max_items
        return values


class DataModelField(DataModelFieldV1):
    """Pydantic v2 field with Field() constraints and json_schema_extra support."""

    _EXCLUDE_FIELD_KEYS: ClassVar[set[str]] = {
        "alias",
        "default",
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
        "min_length",
        "max_length",
        "pattern",
    }
    _DEFAULT_FIELD_KEYS: ClassVar[set[str]] = {
        "default",
        "default_factory",
        "alias",
        "alias_priority",
        "validation_alias",
        "serialization_alias",
        "title",
        "description",
        "examples",
        "exclude",
        "discriminator",
        "json_schema_extra",
        "frozen",
        "validate_default",
        "repr",
        "init_var",
        "kw_only",
        "pattern",
        "strict",
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
        "allow_inf_nan",
        "max_digits",
        "decimal_places",
        "min_length",
        "max_length",
        "union_mode",
    }
    constraints: Optional[Constraints] = None  # pyright: ignore[reportIncompatibleVariableOverride]  # noqa: UP045
    _PARSE_METHOD: ClassVar[str] = "model_validate"
    can_have_extra_keys: ClassVar[bool] = False

    @field_validator("extras")
    def validate_extras(cls, values: Any) -> dict[str, Any]:  # noqa: N805
        """Validate and convert example to examples list."""
        if not isinstance(values, dict):  # pragma: no cover
            return values
        if "examples" in values:
            return values

        if "example" in values:
            values["examples"] = [values.pop("example")]
        return values

    def process_const(self) -> None:
        """Process const field constraint using literal type."""
        self._process_const_as_literal()

    def _process_data_in_str(self, data: dict[str, Any]) -> None:
        if self.const:
            # const is removed in pydantic 2.0
            data.pop("const")

        # unique_items is not supported in pydantic 2.0
        data.pop("unique_items", None)

        if self.use_frozen_field and self.read_only:
            data["frozen"] = True

        if "union_mode" in data:
            if self.data_type.is_union:
                data["union_mode"] = data.pop("union_mode").value
            else:
                data.pop("union_mode")

        # **extra is not supported in pydantic 2.0
        json_schema_extra = {k: v for k, v in data.items() if k not in self._DEFAULT_FIELD_KEYS}
        if json_schema_extra:
            data["json_schema_extra"] = json_schema_extra
            for key in json_schema_extra:
                data.pop(key)

    def _process_annotated_field_arguments(  # noqa: PLR6301
        self,
        field_arguments: list[str],
    ) -> list[str]:
        return field_arguments


class ConfigAttribute(NamedTuple):
    """Configuration attribute mapping for ConfigDict conversion."""

    from_: str
    to: str
    invert: bool


class BaseModel(BaseModelBase):
    """Pydantic v2 BaseModel with ConfigDict and pattern-based regex_engine support."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/BaseModel.jinja2"
    BASE_CLASS: ClassVar[str] = "pydantic.BaseModel"
    BASE_CLASS_NAME: ClassVar[str] = "BaseModel"
    BASE_CLASS_ALIAS: ClassVar[str] = "_BaseModel"
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_FIELD_RENAMING: ClassVar[bool] = True
    SUPPORTS_WRAPPED_DEFAULT: ClassVar[bool] = True
    # In Pydantic 2.11+, populate_by_name is deprecated in favor of validate_by_name + validate_by_alias
    # Default to V2 compatible (populate_by_name) unless target_pydantic_version is specified
    _CONFIG_ATTRIBUTES_V2: ClassVar[list[ConfigAttribute]] = [
        ConfigAttribute("allow_population_by_field_name", "populate_by_name", False),  # noqa: FBT003
        ConfigAttribute("populate_by_name", "populate_by_name", False),  # noqa: FBT003
        ConfigAttribute("allow_mutation", "frozen", True),  # noqa: FBT003
        ConfigAttribute("frozen", "frozen", False),  # noqa: FBT003
        ConfigAttribute("use_attribute_docstrings", "use_attribute_docstrings", False),  # noqa: FBT003
    ]
    _CONFIG_ATTRIBUTES_V2_11: ClassVar[list[ConfigAttribute]] = [
        ConfigAttribute("allow_population_by_field_name", "validate_by_name", False),  # noqa: FBT003
        ConfigAttribute("populate_by_name", "validate_by_name", False),  # noqa: FBT003
        ConfigAttribute("allow_mutation", "frozen", True),  # noqa: FBT003
        ConfigAttribute("frozen", "frozen", False),  # noqa: FBT003
        ConfigAttribute("use_attribute_docstrings", "use_attribute_docstrings", False),  # noqa: FBT003
    ]

    def __init__(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        decorators: list[str] | None = None,
        base_classes: list[Reference] | None = None,
        custom_base_class: str | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, Any] | None = None,
        path: Path | None = None,
        description: str | None = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
        keyword_only: bool = False,
        treat_dot_as_module: bool | None = None,
    ) -> None:
        """Initialize BaseModel with ConfigDict generation from template data."""
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

        extra = self._get_config_extra()
        if extra:
            config_parameters["extra"] = extra

        # Select CONFIG_ATTRIBUTES based on target_pydantic_version
        config_attributes = self._get_config_attributes()
        for from_, to, invert in config_attributes:
            if from_ in self.extra_template_data:
                config_parameters[to] = (
                    not self.extra_template_data[from_] if invert else self.extra_template_data[from_]
                )
        for data_type in self.all_data_types:
            if data_type.is_custom_type:  # pragma: no cover
                config_parameters["arbitrary_types_allowed"] = True
                break

        if self._has_lookaround_pattern():
            config_parameters["regex_engine"] = '"python-re"'

        if isinstance(self.extra_template_data.get("config"), dict):
            for key, value in self.extra_template_data["config"].items():
                config_parameters[key] = value  # noqa: PERF403

        # Handle json_schema_extra from schema extensions (x-* fields)
        model_extras = self.extra_template_data.get("model_extras")
        if model_extras:
            existing = config_parameters.get("json_schema_extra") or {}
            config_parameters["json_schema_extra"] = {**existing, **model_extras}

        if config_parameters:
            from datamodel_code_generator.model.pydantic_v2 import ConfigDict  # noqa: PLC0415

            self.extra_template_data["config"] = model_validate(ConfigDict, config_parameters)  # pyright: ignore[reportArgumentType]
            self._additional_imports.append(IMPORT_CONFIG_DICT)

    def _get_config_extra(self) -> Literal["'allow'", "'forbid'", "'ignore'"] | None:
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

    def _get_config_attributes(self) -> list[ConfigAttribute]:
        """Get config attributes based on target Pydantic version.

        If target_pydantic_version is V2_11, use validate_by_name.
        Otherwise (V2 or not specified), use populate_by_name for compatibility.
        """
        from datamodel_code_generator import TargetPydanticVersion  # noqa: PLC0415

        target_version = self.extra_template_data.get("target_pydantic_version")
        if target_version == TargetPydanticVersion.V2_11:
            return self._CONFIG_ATTRIBUTES_V2_11
        return self._CONFIG_ATTRIBUTES_V2

    def _has_lookaround_pattern(self) -> bool:
        """Check if any field has a regex pattern with lookaround assertions."""
        lookaround_regex = re.compile(r"\(\?<?[=!]")
        for field in self.fields:
            pattern = isinstance(field.constraints, Constraints) and field.constraints.pattern
            if pattern and lookaround_regex.search(pattern):
                return True
            for data_type in field.data_type.all_data_types:
                pattern = (data_type.kwargs or {}).get("pattern")
                if pattern and lookaround_regex.search(pattern):
                    return True
        return False

    @classmethod
    def create_base_class_model(
        cls,
        config: dict[str, Any],
        reference: Reference,
        custom_template_dir: Path | None = None,
        keyword_only: bool = False,  # noqa: FBT001, FBT002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
    ) -> BaseModel | None:
        """Create a shared base class model for DRY configuration.

        Creates a BaseModel that inherits from pydantic's BaseModel (aliased as _BaseModel)
        with the specified configuration. Updates the reference path and name in place.
        """
        reference.path = f"#/{cls.BASE_CLASS_NAME}"
        reference.name = cls.BASE_CLASS_NAME

        extra_data: defaultdict[str, dict[str, Any]] = defaultdict(dict)
        for key, value in config.items():
            extra_data[ALL_MODEL][key] = value

        base_model = cls(
            reference=reference,
            fields=[],
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_data,
            keyword_only=keyword_only,
            treat_dot_as_module=treat_dot_as_module,
        )

        base_model.base_classes = [BaseClassDataType(type=cls.BASE_CLASS_ALIAS)]
        base_model._additional_imports = [
            imp
            for imp in base_model._additional_imports
            if not (imp.from_ == IMPORT_BASE_MODEL.from_ and imp.import_ == IMPORT_BASE_MODEL.import_)
        ]
        base_model._additional_imports.append(
            Import(from_=IMPORT_BASE_MODEL.from_, import_=IMPORT_BASE_MODEL.import_, alias=cls.BASE_CLASS_ALIAS)
        )

        return base_model
