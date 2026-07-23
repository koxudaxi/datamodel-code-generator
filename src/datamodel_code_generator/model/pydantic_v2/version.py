"""Pydantic v2 runtime feature boundaries used by the generator."""

from __future__ import annotations

import re

from pydantic import VERSION as PYDANTIC_VERSION

_PYDANTIC_V2_MODEL_MODULE_PREFIX = "datamodel_code_generator.model.pydantic_v2."


def _version_tuple(version: str) -> tuple[int, int, int]:
    match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", version)
    if match is None:
        return (0, 0, 0)
    major, minor, patch = match.groups(default="0")
    return int(major), int(minor), int(patch)


PYDANTIC_VERSION_TUPLE = _version_tuple(PYDANTIC_VERSION)
PYDANTIC_V2_DATACLASS_ALIAS_FIXED_VERSION = (2, 4, 0)
PYDANTIC_V2_FIELD_DEPRECATED_FIXED_VERSION = (2, 7, 0)
PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_FIXED_VERSION = (2, 8, 0)
PYDANTIC_V2_REGEX_ENGINE_FIXED_VERSION = (2, 5, 0)
PYDANTIC_V2_DATACLASS_ALIAS_NEEDS_FALLBACK = PYDANTIC_VERSION_TUPLE < PYDANTIC_V2_DATACLASS_ALIAS_FIXED_VERSION
PYDANTIC_V2_FIELD_DEPRECATED_NEEDS_JSON_SCHEMA_EXTRA = (
    PYDANTIC_VERSION_TUPLE < PYDANTIC_V2_FIELD_DEPRECATED_FIXED_VERSION
)
PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_NEEDS_SORTING = (
    PYDANTIC_VERSION_TUPLE < PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_FIXED_VERSION
)
PYDANTIC_V2_REGEX_ENGINE_UNSUPPORTED = PYDANTIC_VERSION_TUPLE < PYDANTIC_V2_REGEX_ENGINE_FIXED_VERSION


def _is_builtin_pydantic_v2_model(model_type: type[object]) -> bool:
    return model_type.__module__.startswith(_PYDANTIC_V2_MODEL_MODULE_PREFIX)


_DICT_KEY_REFERENCE_CLASSES_CAPABILITY = (
    staticmethod(_is_builtin_pydantic_v2_model) if PYDANTIC_V2_ROOT_MODEL_DICT_KEY_FORWARD_REF_NEEDS_SORTING else None
)


def _get_dict_key_reference_classes_capability() -> staticmethod[[type[object]], bool] | None:
    """Return the shared dict-key dependency capability for built-in Pydantic v2 models."""
    return _DICT_KEY_REFERENCE_CLASSES_CAPABILITY
