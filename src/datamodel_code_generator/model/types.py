"""Base type manager for model modules.

Provides DataTypeManager implementation with type mapping factory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator import DateClassType, DatetimeClassType, PythonVersion, PythonVersionMin
from datamodel_code_generator.imports import (
    IMPORT_ANY,
    IMPORT_DECIMAL,
    IMPORT_IPV4ADDRESS,
    IMPORT_IPV4NETWORK,
    IMPORT_IPV6ADDRESS,
    IMPORT_IPV6NETWORK,
    IMPORT_PATH,
    IMPORT_TIMEDELTA,
    IMPORT_UUID,
)
from datamodel_code_generator.types import DataType, StrictTypes, Types
from datamodel_code_generator.types import DataTypeManager as _DataTypeManager

if TYPE_CHECKING:
    from collections.abc import Sequence

HOSTNAME_REGEX = (
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*"
    r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])$"
)


def type_map_factory(data_type: type[DataType]) -> dict[Types, DataType]:
    """Create type mapping for common schema types to Python types."""
    data_type_int = data_type(type="int")
    data_type_float = data_type(type="float")
    data_type_str = data_type(type="str")
    return {
        # TODO: Should we support a special type such UUID?
        Types.integer: data_type_int,
        Types.int32: data_type_int,
        Types.int64: data_type_int,
        Types.number: data_type_float,
        Types.float: data_type_float,
        Types.double: data_type_float,
        Types.decimal: data_type.from_import(IMPORT_DECIMAL),
        Types.time: data_type_str,
        Types.string: data_type_str,
        Types.byte: data_type_str,  # base64 encoded string
        Types.binary: data_type(type="bytes"),
        Types.date: data_type_str,
        Types.date_time: data_type_str,
        Types.date_time_local: data_type_str,
        Types.time_local: data_type_str,
        Types.timedelta: data_type.from_import(IMPORT_TIMEDELTA),
        Types.password: data_type_str,
        Types.email: data_type_str,
        Types.uuid: data_type_str,
        Types.uuid1: data_type_str,
        Types.uuid2: data_type_str,
        Types.uuid3: data_type_str,
        Types.uuid4: data_type_str,
        Types.uuid5: data_type_str,
        Types.ulid: data_type_str,
        Types.uri: data_type_str,
        Types.hostname: data_type_str,
        Types.ipv4: data_type_str,
        Types.ipv6: data_type_str,
        Types.ipv4_network: data_type_str,
        Types.ipv6_network: data_type_str,
        Types.path: data_type_str,
        Types.boolean: data_type(type="bool"),
        Types.object: data_type.from_import(IMPORT_ANY, is_dict=True),
        Types.null: data_type(type="None"),
        Types.array: data_type.from_import(IMPORT_ANY, is_list=True),
        Types.any: data_type.from_import(IMPORT_ANY),
    }


def standard_primitive_type_map_factory(data_type: type[DataType]) -> dict[Types, DataType]:
    """Create type mapping for standard library primitive types.

    Maps string formats to their corresponding Python standard library types
    (UUID, IPv4Address, IPv6Address, Path, etc.) instead of plain str.
    """
    uuid_type = data_type.from_import(IMPORT_UUID)
    return {
        Types.uuid: uuid_type,
        Types.uuid1: uuid_type,
        Types.uuid2: uuid_type,
        Types.uuid3: uuid_type,
        Types.uuid4: uuid_type,
        Types.uuid5: uuid_type,
        Types.ipv4: data_type.from_import(IMPORT_IPV4ADDRESS),
        Types.ipv6: data_type.from_import(IMPORT_IPV6ADDRESS),
        Types.ipv4_network: data_type.from_import(IMPORT_IPV4NETWORK),
        Types.ipv6_network: data_type.from_import(IMPORT_IPV6NETWORK),
        Types.path: data_type.from_import(IMPORT_PATH),
    }


class DataTypeManager(_DataTypeManager):
    """Base type manager for model modules."""

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
        use_standard_primitive_types: bool = False,  # noqa: FBT001, FBT002
        target_datetime_class: DatetimeClassType | None = None,
        target_date_class: DateClassType | None = None,  # noqa: ARG002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        use_serialize_as_any: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize type manager with basic type mapping."""
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
            treat_dot_as_module=treat_dot_as_module,
            use_serialize_as_any=use_serialize_as_any,
        )

        standard_primitive_map = (
            standard_primitive_type_map_factory(self.data_type) if use_standard_primitive_types else {}
        )

        self.type_map: dict[Types, DataType] = {
            **type_map_factory(self.data_type),
            **standard_primitive_map,
        }

    def get_data_type(
        self,
        types: Types,
        *,
        field_constraints: bool = False,  # noqa: ARG002
        **_: Any,
    ) -> DataType:
        """Get data type for schema type."""
        if types in self.type_map:
            return self.type_map[types]
        msg = (
            f"Type mapping for {types.name!r} not implemented. "
            f"Please report this at https://github.com/koxudaxi/datamodel-code-generator/issues"
        )
        raise NotImplementedError(msg)
