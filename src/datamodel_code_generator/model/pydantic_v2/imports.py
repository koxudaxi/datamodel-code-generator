"""Import definitions for Pydantic v2 types.

Provides pre-defined Import objects for Pydantic v2 types (ConfigDict, AwareDatetime, etc.).
"""

from __future__ import annotations

from datamodel_code_generator.imports import Import

IMPORT_BASE_MODEL = Import.from_full_path("pydantic.BaseModel")
IMPORT_CONFIG_DICT = Import.from_full_path("pydantic.ConfigDict")
IMPORT_AWARE_DATETIME = Import.from_full_path("pydantic.AwareDatetime")
IMPORT_NAIVE_DATETIME = Import.from_full_path("pydantic.NaiveDatetime")
IMPORT_PAST_DATETIME = Import.from_full_path("pydantic.PastDatetime")
IMPORT_FUTURE_DATETIME = Import.from_full_path("pydantic.FutureDatetime")
IMPORT_PAST_DATE = Import.from_full_path("pydantic.PastDate")
IMPORT_FUTURE_DATE = Import.from_full_path("pydantic.FutureDate")
IMPORT_BASE64STR = Import.from_full_path("pydantic.Base64Str")
IMPORT_SERIALIZE_AS_ANY = Import.from_full_path("pydantic.SerializeAsAny")
IMPORT_PYDANTIC_DATACLASS = Import.from_full_path("pydantic.dataclasses.dataclass")
IMPORT_ROOT_MODEL = Import.from_full_path("pydantic.RootModel")
