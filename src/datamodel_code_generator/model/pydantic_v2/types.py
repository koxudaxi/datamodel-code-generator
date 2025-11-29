"""Pydantic v2 type manager.

Maps schema types to Pydantic v2 specific types with AwareDatetime, NaiveDatetime, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from datamodel_code_generator.format import DatetimeClassType
from datamodel_code_generator.model.pydantic import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.pydantic.imports import IMPORT_CONSTR
from datamodel_code_generator.model.pydantic_v2.imports import (
    IMPORT_AWARE_DATETIME,
    IMPORT_BASE64STR,
    IMPORT_NAIVE_DATETIME,
)
from datamodel_code_generator.types import DataType, StrictTypes, Types

if TYPE_CHECKING:
    from collections.abc import Sequence


class DataTypeManager(_DataTypeManager):
    """Type manager for Pydantic v2 with pattern key support."""

    PATTERN_KEY: ClassVar[str] = "pattern"

    def type_map_factory(
        self,
        data_type: type[DataType],
        strict_types: Sequence[StrictTypes],
        pattern_key: str,
        target_datetime_class: DatetimeClassType | None = None,
    ) -> dict[Types, DataType]:
        """Create type mapping with Pydantic v2 specific types and datetime classes."""
        result = {
            **super().type_map_factory(
                data_type,
                strict_types,
                pattern_key,
                target_datetime_class or DatetimeClassType.Datetime,
            ),
            Types.hostname: self.data_type.from_import(
                IMPORT_CONSTR,
                strict=StrictTypes.str in strict_types,
                # https://github.com/horejsek/python-fastjsonschema/blob/61c6997a8348b8df9b22e029ca2ba35ef441fbb8/fastjsonschema/draft04.py#L31
                kwargs={
                    pattern_key: r"r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*"
                    r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])$'",
                    **({"strict": True} if StrictTypes.str in strict_types else {}),
                },
            ),
            Types.byte: self.data_type.from_import(
                IMPORT_BASE64STR,
                strict=StrictTypes.str in strict_types,
            ),
        }
        if target_datetime_class == DatetimeClassType.Awaredatetime:
            result[Types.date_time] = data_type.from_import(IMPORT_AWARE_DATETIME)
        elif target_datetime_class == DatetimeClassType.Naivedatetime:
            result[Types.date_time] = data_type.from_import(IMPORT_NAIVE_DATETIME)
        return result
