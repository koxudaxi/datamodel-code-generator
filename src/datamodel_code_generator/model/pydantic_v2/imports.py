from __future__ import annotations

from datamodel_code_generator.imports import Import

IMPORT_CONFIG_DICT = Import.from_full_path("pydantic.ConfigDict")
IMPORT_AWARE_DATETIME = Import.from_full_path("pydantic.AwareDatetime")
IMPORT_NAIVE_DATETIME = Import.from_full_path("pydantic.NaiveDatetime")
IMPORT_BASE64STR = Import.from_full_path("pydantic.Base64Str")
"""
Used for OpenAPI strings with format "byte" (base64 encoded characters).
"""
