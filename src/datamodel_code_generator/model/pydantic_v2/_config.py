"""Shared Pydantic v2 ConfigDict generation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional  # noqa: UP035

from pydantic import BaseModel as _BaseModel

from datamodel_code_generator.enums import TargetPydanticVersion

if TYPE_CHECKING:
    from collections.abc import Iterable

    from datamodel_code_generator.types import DataType


class ConfigAttribute(NamedTuple):
    """Configuration attribute mapping for ConfigDict conversion."""

    from_: str
    to: str
    invert: bool


def get_config_extra(extra_template_data: dict[str, Any]) -> str | None:
    """Get extra field configuration for ConfigDict."""
    additional_properties = extra_template_data.get("additionalProperties")
    unevaluated_properties = extra_template_data.get("unevaluatedProperties")
    allow_extra_fields = extra_template_data.get("allow_extra_fields")
    extra_fields = extra_template_data.get("extra_fields")

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


def get_config_attributes(
    extra_template_data: dict[str, Any],
    *,
    config_attributes_v2: list[ConfigAttribute],
    config_attributes_v2_11: list[ConfigAttribute],
) -> list[ConfigAttribute]:
    """Get config attributes based on target Pydantic version."""
    target_version = extra_template_data.get("target_pydantic_version")
    if target_version == TargetPydanticVersion.V2_11:
        return config_attributes_v2_11
    return config_attributes_v2


def build_base_config_parameters(
    *,
    extra_template_data: dict[str, Any],
    all_data_types: Iterable[DataType],
    config_attributes_v2: list[ConfigAttribute],
    config_attributes_v2_11: list[ConfigAttribute],
    include_extra: bool = True,
) -> dict[str, Any]:
    """Build shared ConfigDict parameters for Pydantic v2 models."""
    config_parameters: dict[str, Any] = {}

    if include_extra and (extra := get_config_extra(extra_template_data)):
        config_parameters["extra"] = extra

    config_attributes = get_config_attributes(
        extra_template_data,
        config_attributes_v2=config_attributes_v2,
        config_attributes_v2_11=config_attributes_v2_11,
    )
    for from_, to, invert in config_attributes:
        if from_ in extra_template_data:
            config_parameters[to] = not extra_template_data[from_] if invert else extra_template_data[from_]

    for data_type in all_data_types:
        if data_type.is_custom_type:  # pragma: no cover
            config_parameters["arbitrary_types_allowed"] = True
            break

    return config_parameters


class ConfigDict(_BaseModel):
    """Pydantic v2 model_config options."""

    extra: Optional[str] = None  # noqa: UP045
    title: Optional[str] = None  # noqa: UP045
    populate_by_name: Optional[bool] = None  # noqa: UP045  # deprecated in v2.11+
    validate_by_name: Optional[bool] = None  # noqa: UP045  # v2.11+
    validate_by_alias: Optional[bool] = None  # noqa: UP045  # v2.11+
    allow_extra_fields: Optional[bool] = None  # noqa: UP045
    extra_fields: Optional[str] = None  # noqa: UP045
    from_attributes: Optional[bool] = None  # noqa: UP045
    frozen: Optional[bool] = None  # noqa: UP045
    arbitrary_types_allowed: Optional[bool] = None  # noqa: UP045
    protected_namespaces: Optional[tuple[str, ...]] = None  # noqa: UP045
    regex_engine: Optional[str] = None  # noqa: UP045
    use_enum_values: Optional[bool] = None  # noqa: UP045
    coerce_numbers_to_str: Optional[bool] = None  # noqa: UP045
    use_attribute_docstrings: Optional[bool] = None  # noqa: UP045
    json_schema_extra: Optional[Dict[str, Any]] = None  # noqa: UP006, UP045

    def dict(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
        """Return dict for templates."""
        return self.model_dump(**kwargs)
