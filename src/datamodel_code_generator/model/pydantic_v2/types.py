"""Pydantic v2 type manager.

Maps schema types to Pydantic v2 specific types with AwareDatetime, NaiveDatetime, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from datamodel_code_generator.format import DateClassType, DatetimeClassType
from datamodel_code_generator.model.pydantic import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.pydantic.imports import IMPORT_CONSTR
from datamodel_code_generator.model.pydantic_v2.imports import (
    IMPORT_AWARE_DATETIME,
    IMPORT_BASE64STR,
    IMPORT_FUTURE_DATE,
    IMPORT_FUTURE_DATETIME,
    IMPORT_NAIVE_DATETIME,
    IMPORT_PAST_DATE,
    IMPORT_PAST_DATETIME,
    IMPORT_SERIALIZE_AS_ANY,
)
from datamodel_code_generator.types import (
    DataType,
    PythonVersion,
    PythonVersionMin,
    StrictTypes,
    Types,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from datamodel_code_generator.imports import Import

HOSTNAME_REGEX = (
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*"
    r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])$"
)


class PydanticV2DataType(DataType):
    """Pydantic v2-specific DataType with SerializeAsAny support."""

    def _should_wrap_with_serialize_as_any(self) -> bool:
        if not self.use_serialize_as_any:
            return False

        assert self.reference is not None

        from datamodel_code_generator.model.base import DataModel  # noqa: PLC0415

        return any(isinstance(child, DataModel) and child.fields for child in self.reference.children)

    def _get_wrapped_reference_type_hint(self, type_: str) -> str:
        if self._should_wrap_with_serialize_as_any():
            return f"SerializeAsAny[{type_}]"

        return type_

    @property
    def imports(self) -> Iterator[Import]:
        """Yield imports including SerializeAsAny when needed."""
        yield from super().imports

        if "SerializeAsAny" in self.type_hint:
            yield IMPORT_SERIALIZE_AS_ANY


class DataTypeManager(_DataTypeManager):
    """Type manager for Pydantic v2 with pattern key support."""

    PATTERN_KEY: ClassVar[str] = "pattern"
    HOSTNAME_REGEX: ClassVar[str] = HOSTNAME_REGEX

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        python_version: PythonVersion = PythonVersionMin,
        use_standard_collections: bool = False,  # noqa: FBT001, FBT002
        use_generic_container_types: bool = False,  # noqa: FBT001, FBT002
        strict_types: Sequence[StrictTypes] | None = None,
        use_non_positive_negative_number_constrained_types: bool = False,  # noqa: FBT001, FBT002
        use_decimal_for_multiple_of: bool = False,  # noqa: FBT001, FBT002
        use_union_operator: bool = False,  # noqa: FBT001, FBT002
        use_pendulum: bool = False,  # noqa: FBT001, FBT002
        use_standard_primitive_types: bool = False,  # noqa: FBT001, FBT002, ARG002
        target_datetime_class: DatetimeClassType | None = None,
        target_date_class: DateClassType | None = None,
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        use_serialize_as_any: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize with pydantic v2-specific DataType."""
        self._target_date_class = target_date_class
        super().__init__(
            python_version=python_version,
            use_standard_collections=use_standard_collections,
            use_generic_container_types=use_generic_container_types,
            strict_types=strict_types,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            use_decimal_for_multiple_of=use_decimal_for_multiple_of,
            use_union_operator=use_union_operator,
            use_pendulum=use_pendulum,
            target_datetime_class=target_datetime_class,
            target_date_class=target_date_class,
            treat_dot_as_module=treat_dot_as_module,
            use_serialize_as_any=use_serialize_as_any,
        )

        # Override the data_type with our pydantic v2 version
        from pydantic import create_model  # noqa: PLC0415

        self.data_type: type[DataType] = create_model(
            "PydanticV2ContextDataType",
            python_version=(PythonVersion, python_version),
            use_standard_collections=(bool, use_standard_collections),
            use_generic_container=(bool, use_generic_container_types),
            use_union_operator=(bool, use_union_operator),
            treat_dot_as_module=(bool, treat_dot_as_module),
            use_serialize_as_any=(bool, use_serialize_as_any),
            __base__=PydanticV2DataType,
        )

    def type_map_factory(
        self,
        data_type: type[DataType],
        strict_types: Sequence[StrictTypes],
        pattern_key: str,
        target_datetime_class: DatetimeClassType | None = None,
        target_date_class: DateClassType | None = None,
    ) -> dict[Types, DataType]:
        """Create type mapping with Pydantic v2 specific types and datetime classes."""
        effective_date_class = target_date_class or getattr(self, "_target_date_class", None)
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
            Types.date_time_local: data_type.from_import(IMPORT_NAIVE_DATETIME),
        }
        if target_datetime_class == DatetimeClassType.Awaredatetime:
            result[Types.date_time] = data_type.from_import(IMPORT_AWARE_DATETIME)
        elif target_datetime_class == DatetimeClassType.Naivedatetime:
            result[Types.date_time] = data_type.from_import(IMPORT_NAIVE_DATETIME)
        elif target_datetime_class == DatetimeClassType.Pastdatetime:
            result[Types.date_time] = data_type.from_import(IMPORT_PAST_DATETIME)
        elif target_datetime_class == DatetimeClassType.Futuredatetime:
            result[Types.date_time] = data_type.from_import(IMPORT_FUTURE_DATETIME)
        if effective_date_class == DateClassType.Pastdate:
            result[Types.date] = data_type.from_import(IMPORT_PAST_DATE)
        elif effective_date_class == DateClassType.Futuredate:
            result[Types.date] = data_type.from_import(IMPORT_FUTURE_DATE)
        return result
