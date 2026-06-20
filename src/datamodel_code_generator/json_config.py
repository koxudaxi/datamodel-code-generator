"""JSON configuration loading and validation helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from io import TextIOBase
from pathlib import Path
from typing import Any, ClassVar, Literal, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError

from datamodel_code_generator.deprecations import warn_deprecated
from datamodel_code_generator.validators import ValidatorsConfig, format_validation_error

DEFAULT_ENCODING = "utf-8"
JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"

JsonConfigSource: TypeAlias = str | Path | TextIOBase | dict[str, Any] | None


class JsonConfigError(Exception):
    """Error raised when a JSON configuration value cannot be loaded or validated."""


class StringMappingConfig(RootModel[dict[str, str]]):
    """JSON object with string keys and string values."""


class StringOrStringListMappingConfig(RootModel[dict[str, str | list[str]]]):
    """JSON object with string keys and string or list-of-string values."""


class EnumFieldAsLiteralMapConfig(RootModel[dict[str, Literal["literal", "enum"]]]):
    """Per-field enum/literal generation override mapping."""


class DuplicateNameSuffixConfig(RootModel[dict[Literal["model", "enum", "default"], str]]):
    """Duplicate-name suffix mapping."""


class DefaultValuesConfig(RootModel[dict[str, Any]]):
    """Default value override mapping."""


class ExtraTemplateDataConfig(RootModel[dict[str, dict[str, Any]]]):
    """Extra template data mapping."""


class LegacyExtraTemplateDataConfig(RootModel[dict[str, Any]]):
    """Legacy extra template data mapping accepted during strict-validation migration."""


class JsonConfigSchemasPayload(BaseModel):
    """Strict JSON configuration schemas accepted by datamodel-code-generator."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, protected_namespaces=())

    aliases: StringOrStringListMappingConfig | None = Field(default=None)
    base_class_map: StringOrStringListMappingConfig | None = Field(default=None, alias="base-class-map")
    custom_formatters_kwargs: StringMappingConfig | None = Field(default=None, alias="custom-formatters-kwargs")
    default_values: DefaultValuesConfig | None = Field(default=None, alias="default-values")
    duplicate_name_suffix: DuplicateNameSuffixConfig | None = Field(default=None, alias="duplicate-name-suffix")
    enum_field_as_literal_map: EnumFieldAsLiteralMapConfig | None = Field(
        default=None, alias="enum-field-as-literal-map"
    )
    extra_template_data: ExtraTemplateDataConfig | None = Field(default=None, alias="extra-template-data")
    model_name_map: StringMappingConfig | None = Field(default=None, alias="model-name-map")
    serialization_aliases: StringMappingConfig | None = Field(default=None, alias="serialization-aliases")
    type_overrides: StringMappingConfig | None = Field(default=None, alias="type-overrides")
    validators: ValidatorsConfig | None = Field(default=None)


def _dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def json_config_json_schema() -> str:
    """Return JSON Schema for strict JSON configuration payloads."""
    return _dump_json({
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        **JsonConfigSchemasPayload.model_json_schema(mode="validation"),
    })


def _invalid_json_message(option_name: str, error: json.JSONDecodeError, load_error_name: str | None) -> str:
    if load_error_name:
        return f"Unable to load {load_error_name}: {error}"
    if option_name:
        return f"Invalid JSON for {option_name}: {error}"
    return f"Invalid JSON: {error}"


def _path_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _read_json_or_inline(value: str) -> str:
    path = Path(value).expanduser()
    if not _path_is_file(path):
        return value

    try:
        return path.read_text(encoding=DEFAULT_ENCODING)
    except (OSError, UnicodeDecodeError) as e:
        msg = f"Unable to read JSON file {value!r}: {e}"
        raise JsonConfigError(msg) from e


def _loads_json(value: str, *, option_name: str, load_error_name: str | None) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        msg = _invalid_json_message(option_name, e, load_error_name)
        raise JsonConfigError(msg) from e


def _load_json_source(value: JsonConfigSource, *, option_name: str, load_error_name: str | None = None) -> Any:
    match value:
        case None:
            return None
        case dict():
            return value
        case TextIOBase() as data:
            with data:
                try:
                    return json.load(data)
                except json.JSONDecodeError as e:
                    msg = _invalid_json_message(option_name, e, load_error_name)
                    raise JsonConfigError(msg) from e

    return _loads_json(_read_json_or_inline(str(value)), option_name=option_name, load_error_name=load_error_name)


def _to_defaultdict(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return defaultdict(dict, {key: _to_defaultdict(child) for key, child in value.items()})


@dataclass(frozen=True)
class JsonConfigSpec:
    """Validation spec for a JSON configuration option."""

    option_name: str
    strict_model: type[Any]
    legacy_model: type[Any] | None = None
    as_defaultdict: bool = False
    load_error_name: str | None = None
    validation_error_name: str | None = None
    validation_error_message: str | None = None

    def validate(self, raw: Any, *, warn_on_legacy_fallback: bool = True) -> Any:
        """Validate a loaded JSON value and return the normalized config value."""
        try:
            result = self.strict_model.model_validate(raw).root
        except ValidationError as strict_error:
            result = self._validate_legacy(raw, strict_error, warn_on_legacy_fallback=warn_on_legacy_fallback)

        return _to_defaultdict(result) if self.as_defaultdict else result

    def _strict_validation_error(self, strict_error: ValidationError) -> JsonConfigError:
        error_message = self.validation_error_message or format_validation_error(strict_error)
        match self.validation_error_name, self.load_error_name:
            case str(name), _:
                msg = f"Invalid {name}: {error_message}"
            case None, str(name):
                msg = f"Unable to load {name}: {error_message}"
            case _:
                msg = f"Invalid {self.option_name}: {error_message}"
        return JsonConfigError(msg)

    def _validate_legacy(
        self,
        raw: Any,
        strict_error: ValidationError,
        *,
        warn_on_legacy_fallback: bool,
    ) -> Any:
        if self.legacy_model is None:
            raise self._strict_validation_error(strict_error) from strict_error

        try:
            result = self.legacy_model.model_validate(raw).root
        except ValidationError as legacy_error:
            msg = f"Invalid {self.option_name}: {format_validation_error(legacy_error)}"
            raise JsonConfigError(msg) from legacy_error

        if warn_on_legacy_fallback:
            warn_deprecated(
                "config.json-config-strict-validation",
                details=(
                    f"{self.option_name} currently falls back to legacy validation for compatibility, "
                    "but a future release will fail when the value does not match the documented JSON Schema. "
                    f"First validation issue: {format_validation_error(strict_error)}"
                ),
                stacklevel=4,
            )
        return result


class JsonConfigSpecs:
    """Registry of JSON configuration specs."""

    by_field_name: ClassVar[dict[str, JsonConfigSpec]] = {
        "aliases": JsonConfigSpec(
            "--aliases",
            StringOrStringListMappingConfig,
            load_error_name="alias mapping",
            validation_error_message=(
                "must be a JSON mapping with string keys and string or list of strings values "
                '(e.g. {"from": "to", "field": ["alias1", "alias2"]})'
            ),
        ),
        "base_class_map": JsonConfigSpec("--base-class-map", StringOrStringListMappingConfig),
        "custom_formatters_kwargs": JsonConfigSpec(
            "--custom-formatters-kwargs",
            StringMappingConfig,
            load_error_name="custom_formatters_kwargs mapping",
            validation_error_message='must be a JSON string mapping (e.g. {"key": "value", ...})',
        ),
        "default_values": JsonConfigSpec(
            "--default-values",
            DefaultValuesConfig,
            load_error_name="default values mapping",
            validation_error_message="must be a JSON object with string keys",
        ),
        "duplicate_name_suffix": JsonConfigSpec(
            "--duplicate-name-suffix",
            DuplicateNameSuffixConfig,
            legacy_model=StringMappingConfig,
        ),
        "enum_field_as_literal_map": JsonConfigSpec(
            "--enum-field-as-literal-map",
            EnumFieldAsLiteralMapConfig,
            legacy_model=StringMappingConfig,
        ),
        "extra_template_data": JsonConfigSpec(
            "--extra-template-data",
            ExtraTemplateDataConfig,
            legacy_model=LegacyExtraTemplateDataConfig,
            as_defaultdict=True,
            load_error_name="extra template data",
        ),
        "model_name_map": JsonConfigSpec("--model-name-map", StringMappingConfig),
        "serialization_aliases": JsonConfigSpec(
            "--serialization-aliases",
            StringMappingConfig,
            load_error_name="serialization alias mapping",
            validation_error_message='must be a JSON string mapping (e.g. {"key": "value", ...})',
        ),
        "type_overrides": JsonConfigSpec("--type-overrides", StringMappingConfig),
        "validators": JsonConfigSpec(
            "--validators",
            ValidatorsConfig,
            load_error_name="validators configuration",
            validation_error_name="validators configuration",
        ),
    }


def load_json_config_field(
    field_name: str,
    value: JsonConfigSource,
    *,
    warn_on_legacy_fallback: bool = True,
) -> Any:
    """Load and validate a JSON configuration field by Config field name."""
    spec = JsonConfigSpecs.by_field_name[field_name]
    if (raw := _load_json_source(value, option_name=spec.option_name, load_error_name=spec.load_error_name)) is None:
        return None
    return spec.validate(raw, warn_on_legacy_fallback=warn_on_legacy_fallback)


def validate_json_value_or_file(value: str, *, option_name: str = "") -> dict[str, object]:
    """Parse and validate a JSON object or JSON file path for argparse-compatible callers."""
    raw = _load_json_source(value, option_name=option_name)
    if not isinstance(raw, dict):
        msg = f"Expected a JSON object, got {type(raw).__name__}"
        raise JsonConfigError(msg)
    return cast("dict[str, object]", raw)
