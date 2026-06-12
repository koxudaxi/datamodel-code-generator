"""Pydantic v2 BaseModel implementation.

Provides Constraints, DataModelField, and BaseModel for Pydantic v2
with support for Field() constraints and ConfigDict.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from datamodel_code_generator import Error
from datamodel_code_generator.imports import IMPORT_ANY, IMPORT_DICT, Import
from datamodel_code_generator.model import _rebuild_model_with_datamodel_namespace
from datamodel_code_generator.model.base import (
    ALL_MODEL,
    UNDEFINED,
    BaseClassDataType,
    DataModelFieldBase,
)
from datamodel_code_generator.model.imports import IMPORT_CLASSVAR
from datamodel_code_generator.model.pydantic_base import BaseModelBase
from datamodel_code_generator.model.pydantic_base import Constraints as _Constraints
from datamodel_code_generator.model.pydantic_base import (
    DataModelField as _PydanticBaseDataModelField,
)
from datamodel_code_generator.model.pydantic_v2._config import (
    ConfigAttribute,
    build_base_config_parameters,
)
from datamodel_code_generator.model.pydantic_v2.imports import (
    IMPORT_ALIAS_CHOICES,
    IMPORT_BASE_MODEL,
    IMPORT_CONFIG_DICT,
    IMPORT_FIELD,
    IMPORT_FIELD_VALIDATOR,
    IMPORT_VALIDATION_INFO,
    IMPORT_VALIDATOR_FUNCTION_WRAP_HANDLER,
)
from datamodel_code_generator.model.pydantic_v2.version import PYDANTIC_V2_FIELD_DEPRECATED_NEEDS_JSON_SCHEMA_EXTRA
from datamodel_code_generator.reference import ModelResolver
from datamodel_code_generator.types import chain_as_tuple
from datamodel_code_generator.validators import format_validation_error, normalize_validators

if TYPE_CHECKING:
    from pathlib import Path

    from datamodel_code_generator.reference import Reference
    from datamodel_code_generator.types import DataType


class _RawRepr:
    """Wrapper to prevent repr() from adding quotes around a value."""

    __slots__ = ("value",)

    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return self.value


class Constraints(_Constraints):
    """Pydantic v2 field constraints with pattern support."""

    # To override existing pattern alias
    regex: Optional[str] = Field(None, alias="regex")  # noqa: UP045
    pattern: Optional[str] = Field(None, alias="pattern")  # noqa: UP045

    @model_validator(mode="before")  # ty: ignore
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


DataModelFieldV1 = _PydanticBaseDataModelField  # deprecated re-export, pydantic-v1 output removed in #3031

_PYDANTIC_V2_BASE_FIELD_KEYS: frozenset[str] = frozenset({
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
})


if PYDANTIC_V2_FIELD_DEPRECATED_NEEDS_JSON_SCHEMA_EXTRA:
    _PYDANTIC_V2_DEFAULT_FIELD_KEYS = _PYDANTIC_V2_BASE_FIELD_KEYS
else:
    _PYDANTIC_V2_DEFAULT_FIELD_KEYS = _PYDANTIC_V2_BASE_FIELD_KEYS | {"deprecated"}


class DataModelField(_PydanticBaseDataModelField):
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
    _DEFAULT_FIELD_KEYS: ClassVar[frozenset[str]] = _PYDANTIC_V2_DEFAULT_FIELD_KEYS
    constraints: Optional[Constraints] = None  # ty: ignore  # noqa: UP045
    can_have_extra_keys: ClassVar[bool] = False
    _PYDANTIC_EXTRA_FIELD_NAME: ClassVar[str] = "__pydantic_extra__"

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

    def _requires_null_default_field(self) -> bool:
        if self.required or self.default is not None or self.has_default_factory:
            return False
        return self.data_type.type == "None"

    def _has_field_statement(self) -> bool:
        return self._requires_null_default_field() or super()._has_field_statement()

    def __str__(self) -> str:
        """Return Field(None) when stringification would omit an explicit null default."""
        field = super().__str__()
        if self._requires_null_default_field() and not field:
            return "Field(None)"
        return field

    @property
    def use_pydantic_extra_annotation_assignment(self) -> bool:
        """Return whether this field needs runtime annotation assignment."""
        return self.name == self._PYDANTIC_EXTRA_FIELD_NAME

    @property
    def pydantic_extra_type_hint(self) -> str:
        """Return a Dict-based type hint for Pydantic 2.0 typed extras."""
        type_hint = self.type_hint
        if not type_hint.startswith("dict["):
            return type_hint
        return f"Dict[{type_hint.removeprefix('dict[')}"

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

        has_alias = "alias" in data
        alias = data.get("alias")

        # Handle multiple aliases using AliasChoices (Pydantic v2 feature)
        if self.validation_aliases:
            unique_validation_aliases = list(dict.fromkeys(self.validation_aliases))
            serialization_alias = (
                self.serialization_alias
                if self.serialization_alias is not None
                else alias
                if has_alias
                else unique_validation_aliases[0]
            )
            # Remove single alias if present (validation_aliases takes precedence)
            data.pop("alias", None)
            # Format as AliasChoices(...) - use _RawRepr to prevent double-quoting
            aliases_repr = ", ".join(repr(a) for a in unique_validation_aliases)
            data["validation_alias"] = _RawRepr(f"AliasChoices({aliases_repr})")
            if self.use_serialization_alias and serialization_alias is not None and serialization_alias != self.name:
                data["serialization_alias"] = serialization_alias

        if self.serialization_alias is not None and (self.serialization_alias != self.name or has_alias):
            data["serialization_alias"] = self.serialization_alias

        if self.use_serialization_alias and "alias" in data:
            serialization_alias = self.serialization_alias if self.serialization_alias is not None else data["alias"]
            data.pop("alias")
            if serialization_alias != self.name:
                data["serialization_alias"] = serialization_alias

        # **extra is not supported in pydantic 2.0
        extra_field_keys = tuple(k for k in data if k not in self._DEFAULT_FIELD_KEYS)
        existing_json_schema_extra = data.get("json_schema_extra") or {}
        json_schema_extra = {
            **existing_json_schema_extra,
            **{k: data[k] for k in extra_field_keys},
        }
        if json_schema_extra:
            data["json_schema_extra"] = json_schema_extra
            for key in extra_field_keys:
                data.pop(key)

    def _has_discriminator_in_data_type(self) -> bool:
        """Check if any nested DataType has a discriminator."""
        return any(dt.discriminator for dt in self.data_type.all_data_types)

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get all required imports including AliasChoices and Field for discriminator."""
        base_imports = super().imports
        extra_imports: list[Import] = []
        if self.is_class_var:
            extra_imports.append(IMPORT_CLASSVAR)
        if self.validation_aliases:
            extra_imports.append(IMPORT_ALIAS_CHOICES)
        if self._has_discriminator_in_data_type():
            extra_imports.append(IMPORT_FIELD)
        if self.use_pydantic_extra_annotation_assignment:
            extra_imports.append(IMPORT_DICT)
        if extra_imports:
            return chain_as_tuple(base_imports, tuple(extra_imports))
        return base_imports


class BaseModel(BaseModelBase):
    """Pydantic v2 BaseModel with ConfigDict and pattern-based regex_engine support."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/BaseModel.jinja2"
    BASE_CLASS: ClassVar[str] = "pydantic.BaseModel"
    BASE_CLASS_NAME: ClassVar[str] = "BaseModel"
    BASE_CLASS_ALIAS: ClassVar[str] = "_BaseModel"
    SUPPORTS_DISCRIMINATOR: ClassVar[bool] = True
    SUPPORTS_FIELD_RENAMING: ClassVar[bool] = True
    SUPPORTS_CONFIG_EXTRA: ClassVar[bool] = True
    SUPPORTS_ARBITRARY_TYPES_ALLOWED: ClassVar[bool] = True
    TYPED_EXTRA_FIELD_NAME: ClassVar[str] = "__pydantic_extra__"
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

    @classmethod
    def create_typed_extra_field(
        cls,
        *,
        field_model: type[DataModelFieldBase],
        data_type: DataType,
    ) -> DataModelFieldBase:
        """Create the Pydantic v2 typed extra field."""
        return field_model(
            name=cls.TYPED_EXTRA_FIELD_NAME,
            data_type=data_type,
            required=True,
            original_name=cls.TYPED_EXTRA_FIELD_NAME,
        )

    def __init__(  # noqa: PLR0913
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
        config_parameters = build_base_config_parameters(
            extra_template_data=self.extra_template_data,
            all_data_types=self.all_data_types if self.SUPPORTS_ARBITRARY_TYPES_ALLOWED else (),
            config_attributes_v2=self._CONFIG_ATTRIBUTES_V2,
            config_attributes_v2_11=self._CONFIG_ATTRIBUTES_V2_11,
            include_extra=self.SUPPORTS_CONFIG_EXTRA,
        )

        if self._has_lookaround_pattern():
            config_parameters["regex_engine"] = '"python-re"'

        if isinstance(config := self.extra_template_data.get("config"), dict):
            for key, value in config.items():
                config_parameters[key] = value

        # Handle json_schema_extra from schema extensions (x-* fields)
        model_extras = self.extra_template_data.get("model_extras")
        if model_extras:
            existing = cast("dict[str, Any]", config_parameters.get("json_schema_extra") or {})
            config_parameters["json_schema_extra"] = {**existing, **model_extras}

        if config_parameters:
            from datamodel_code_generator.model.pydantic_v2 import ConfigDict  # noqa: PLC0415

            self.extra_template_data["config"] = ConfigDict.model_validate(config_parameters)  # ty: ignore
            self._additional_imports.append(IMPORT_CONFIG_DICT)

        self._process_validators()

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

    def _process_validators(self) -> None:
        """Process validator definitions and prepare them for template rendering."""
        self.extra_template_data.pop("prepared_validators", None)
        validators = self.extra_template_data.get("validators")
        if not validators:
            return

        try:
            validators = normalize_validators(validators)
        except ValidationError as e:
            msg = f"Invalid validators configuration: {format_validation_error(e)}"
            raise Error(msg) from e

        prepared_validators: list[dict[str, Any]] = []
        scoped_resolver = ModelResolver(custom_class_name_generator=lambda name: name)
        for validator in validators:
            fields = validator.get("fields") or [validator.get("field")]
            fields = [f for f in fields if f]
            if not fields:
                continue

            function_path: str = validator["function"]
            function_name = function_path.rsplit(".", 1)[-1]
            mode = validator.get("mode", "after")

            fields_str = ", ".join(repr(f) for f in fields)

            base_method_name = f"{function_name}_validator"
            method_name = scoped_resolver.add([base_method_name], base_method_name, unique=True, class_name=True).name

            mode_str = f"mode={mode!r}"

            prepared_validators.append({
                "fields_str": fields_str,
                "mode_str": mode_str,
                "method_name": method_name,
                "function_name": function_name,
                "mode": mode,
            })

            self._additional_imports.append(Import.from_full_path(function_path))

        if prepared_validators:
            self.extra_template_data["prepared_validators"] = prepared_validators  # ty: ignore
            self._additional_imports.append(IMPORT_FIELD_VALIDATOR)
            self._additional_imports.append(IMPORT_ANY)

            modes = {v["mode"] for v in prepared_validators}
            if modes - {"plain"}:
                self._additional_imports.append(IMPORT_VALIDATION_INFO)
            if "wrap" in modes:
                self._additional_imports.append(IMPORT_VALIDATOR_FUNCTION_WRAP_HANDLER)

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


_rebuild_model_with_datamodel_namespace(DataModelField)
