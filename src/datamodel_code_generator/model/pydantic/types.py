"""Pydantic v1 type manager.

Maps schema types to Pydantic v1 specific types (constr, conint, AnyUrl, etc.).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator.format import DateClassType, DatetimeClassType, PythonVersion, PythonVersionMin
from datamodel_code_generator.imports import (
    IMPORT_ANY,
    IMPORT_DATE,
    IMPORT_DATETIME,
    IMPORT_DECIMAL,
    IMPORT_PATH,
    IMPORT_PENDULUM_DATE,
    IMPORT_PENDULUM_DATETIME,
    IMPORT_PENDULUM_DURATION,
    IMPORT_PENDULUM_TIME,
    IMPORT_TIME,
    IMPORT_TIMEDELTA,
    IMPORT_ULID,
    IMPORT_UUID,
)
from datamodel_code_generator.model.pydantic.imports import (
    IMPORT_ANYURL,
    IMPORT_CONBYTES,
    IMPORT_CONDECIMAL,
    IMPORT_CONFLOAT,
    IMPORT_CONINT,
    IMPORT_CONSTR,
    IMPORT_EMAIL_STR,
    IMPORT_IPV4ADDRESS,
    IMPORT_IPV4NETWORKS,
    IMPORT_IPV6ADDRESS,
    IMPORT_IPV6NETWORKS,
    IMPORT_NEGATIVE_FLOAT,
    IMPORT_NEGATIVE_INT,
    IMPORT_NON_NEGATIVE_FLOAT,
    IMPORT_NON_NEGATIVE_INT,
    IMPORT_NON_POSITIVE_FLOAT,
    IMPORT_NON_POSITIVE_INT,
    IMPORT_POSITIVE_FLOAT,
    IMPORT_POSITIVE_INT,
    IMPORT_SECRET_STR,
    IMPORT_STRICT_BOOL,
    IMPORT_STRICT_BYTES,
    IMPORT_STRICT_FLOAT,
    IMPORT_STRICT_INT,
    IMPORT_STRICT_STR,
    IMPORT_UUID1,
    IMPORT_UUID2,
    IMPORT_UUID3,
    IMPORT_UUID4,
    IMPORT_UUID5,
)
from datamodel_code_generator.types import DataType, StrictTypes, Types, UnionIntFloat
from datamodel_code_generator.types import DataTypeManager as _DataTypeManager

if TYPE_CHECKING:
    from collections.abc import Sequence


def type_map_factory(
    data_type: type[DataType],
    strict_types: Sequence[StrictTypes],
    pattern_key: str,
    use_pendulum: bool,  # noqa: FBT001
) -> dict[Types, DataType]:
    """Create a mapping of schema types to Pydantic v1 data types."""
    data_type_int = data_type(type="int")
    data_type_float = data_type(type="float")
    data_type_str = data_type(type="str")
    result = {
        Types.integer: data_type_int,
        Types.int32: data_type_int,
        Types.int64: data_type_int,
        Types.number: data_type_float,
        Types.float: data_type_float,
        Types.double: data_type_float,
        Types.decimal: data_type.from_import(IMPORT_DECIMAL),
        Types.time: data_type.from_import(IMPORT_TIME),
        Types.string: data_type_str,
        Types.byte: data_type_str,  # base64 encoded string
        Types.binary: data_type(type="bytes"),
        Types.date: data_type.from_import(IMPORT_DATE),
        Types.date_time: data_type.from_import(IMPORT_DATETIME),
        Types.date_time_local: data_type.from_import(IMPORT_DATETIME),
        Types.time_local: data_type.from_import(IMPORT_TIME),
        Types.timedelta: data_type.from_import(IMPORT_TIMEDELTA),
        Types.path: data_type.from_import(IMPORT_PATH),
        Types.password: data_type.from_import(IMPORT_SECRET_STR),
        Types.email: data_type.from_import(IMPORT_EMAIL_STR),
        Types.uuid: data_type.from_import(IMPORT_UUID),
        Types.uuid1: data_type.from_import(IMPORT_UUID1),
        Types.uuid2: data_type.from_import(IMPORT_UUID2),
        Types.uuid3: data_type.from_import(IMPORT_UUID3),
        Types.uuid4: data_type.from_import(IMPORT_UUID4),
        Types.uuid5: data_type.from_import(IMPORT_UUID5),
        Types.ulid: data_type.from_import(IMPORT_ULID),
        Types.uri: data_type.from_import(IMPORT_ANYURL),
        Types.hostname: data_type.from_import(
            IMPORT_CONSTR,
            strict=StrictTypes.str in strict_types,
            # https://github.com/horejsek/python-fastjsonschema/blob/61c6997a8348b8df9b22e029ca2ba35ef441fbb8/fastjsonschema/draft04.py#L31
            kwargs={
                pattern_key: r"r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*"
                r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])\Z'",
                **({"strict": True} if StrictTypes.str in strict_types else {}),
            },
        ),
        Types.ipv4: data_type.from_import(IMPORT_IPV4ADDRESS),
        Types.ipv6: data_type.from_import(IMPORT_IPV6ADDRESS),
        Types.ipv4_network: data_type.from_import(IMPORT_IPV4NETWORKS),
        Types.ipv6_network: data_type.from_import(IMPORT_IPV6NETWORKS),
        Types.boolean: data_type(type="bool"),
        Types.object: data_type.from_import(IMPORT_ANY, is_dict=True),
        Types.null: data_type(type="None"),
        Types.array: data_type.from_import(IMPORT_ANY, is_list=True),
        Types.any: data_type.from_import(IMPORT_ANY),
    }
    if use_pendulum:
        result[Types.date] = data_type.from_import(IMPORT_PENDULUM_DATE)
        result[Types.date_time] = data_type.from_import(IMPORT_PENDULUM_DATETIME)
        result[Types.time] = data_type.from_import(IMPORT_PENDULUM_TIME)
        result[Types.timedelta] = data_type.from_import(IMPORT_PENDULUM_DURATION)

    return result


def strict_type_map_factory(data_type: type[DataType]) -> dict[StrictTypes, DataType]:
    """Create a mapping of strict types to Pydantic v1 strict data types."""
    return {
        StrictTypes.int: data_type.from_import(IMPORT_STRICT_INT, strict=True),
        StrictTypes.float: data_type.from_import(IMPORT_STRICT_FLOAT, strict=True),
        StrictTypes.bytes: data_type.from_import(IMPORT_STRICT_BYTES, strict=True),
        StrictTypes.bool: data_type.from_import(IMPORT_STRICT_BOOL, strict=True),
        StrictTypes.str: data_type.from_import(IMPORT_STRICT_STR, strict=True),
    }


number_kwargs: set[str] = {
    "exclusiveMinimum",
    "minimum",
    "exclusiveMaximum",
    "maximum",
    "multipleOf",
}

string_kwargs: set[str] = {"minItems", "maxItems", "minLength", "maxLength", "pattern"}

bytes_kwargs: set[str] = {"minLength", "maxLength"}

escape_characters = str.maketrans({
    "'": r"\'",
    "\b": r"\b",
    "\f": r"\f",
    "\n": r"\n",
    "\r": r"\r",
    "\t": r"\t",
})

HOSTNAME_REGEX = (  # Pydantic v1 requires \Z anchor (not $) to avoid matching trailing newline
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*"
    r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])\Z"
)


class DataTypeManager(_DataTypeManager):
    """Manage data type mappings for Pydantic v1 models."""

    PATTERN_KEY: ClassVar[str] = "regex"
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
        target_date_class: DateClassType | None = None,  # noqa: ARG002
        treat_dot_as_module: bool | None = None,  # noqa: FBT001
        use_serialize_as_any: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize the DataTypeManager with Pydantic v1 type mappings."""
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

        self.type_map: dict[Types, DataType] = self.type_map_factory(
            self.data_type,
            strict_types=self.strict_types,
            pattern_key=self.PATTERN_KEY,
            target_datetime_class=self.target_datetime_class,
        )
        self.strict_type_map: dict[StrictTypes, DataType] = strict_type_map_factory(
            self.data_type,
        )

        self.kwargs_schema_to_model: dict[str, str] = {
            "exclusiveMinimum": "gt",
            "minimum": "ge",
            "exclusiveMaximum": "lt",
            "maximum": "le",
            "multipleOf": "multiple_of",
            "minItems": "min_items",
            "maxItems": "max_items",
            "minLength": "min_length",
            "maxLength": "max_length",
            "pattern": self.PATTERN_KEY,
        }

    def type_map_factory(
        self,
        data_type: type[DataType],
        strict_types: Sequence[StrictTypes],
        pattern_key: str,
        target_datetime_class: DatetimeClassType | None,  # noqa: ARG002
    ) -> dict[Types, DataType]:
        """Create type mapping with Pydantic v1 specific types."""
        return type_map_factory(
            data_type,
            strict_types,
            pattern_key,
            self.use_pendulum,
        )

    def transform_kwargs(self, kwargs: dict[str, Any], filter_: set[str]) -> dict[str, str]:
        """Transform schema kwargs to Pydantic v1 field kwargs."""
        return {self.kwargs_schema_to_model.get(k, k): v for (k, v) in kwargs.items() if v is not None and k in filter_}

    def get_data_int_type(  # noqa: PLR0911
        self,
        types: Types,
        **kwargs: Any,
    ) -> DataType:
        """Get int data type with constraints (conint, PositiveInt, etc.)."""
        data_type_kwargs: dict[str, Any] = self.transform_kwargs(kwargs, number_kwargs)
        strict = StrictTypes.int in self.strict_types
        if data_type_kwargs:
            if not strict:
                if data_type_kwargs == {"gt": 0}:
                    return self.data_type.from_import(IMPORT_POSITIVE_INT)
                if data_type_kwargs == {"lt": 0}:
                    return self.data_type.from_import(IMPORT_NEGATIVE_INT)
                if data_type_kwargs == {"ge": 0} and self.use_non_positive_negative_number_constrained_types:
                    return self.data_type.from_import(IMPORT_NON_NEGATIVE_INT)
                if data_type_kwargs == {"le": 0} and self.use_non_positive_negative_number_constrained_types:
                    return self.data_type.from_import(IMPORT_NON_POSITIVE_INT)
            kwargs = {k: int(v) for k, v in data_type_kwargs.items()}
            if strict:
                kwargs["strict"] = True
            return self.data_type.from_import(IMPORT_CONINT, kwargs=kwargs)
        if strict:
            return self.strict_type_map[StrictTypes.int]
        return self.type_map[types]

    def get_data_float_type(  # noqa: PLR0911
        self,
        types: Types,
        **kwargs: Any,
    ) -> DataType:
        """Get float data type with constraints (confloat, PositiveFloat, etc.)."""
        data_type_kwargs = self.transform_kwargs(kwargs, number_kwargs)
        strict = StrictTypes.float in self.strict_types
        if data_type_kwargs:
            # Use Decimal instead of float when multipleOf is present to avoid floating-point precision issues
            if self.use_decimal_for_multiple_of and "multiple_of" in data_type_kwargs:
                return self.data_type.from_import(
                    IMPORT_CONDECIMAL,
                    kwargs={k: Decimal(str(v)) for k, v in data_type_kwargs.items()},
                )
            if not strict:
                if data_type_kwargs == {"gt": 0}:
                    return self.data_type.from_import(IMPORT_POSITIVE_FLOAT)
                if data_type_kwargs == {"lt": 0}:
                    return self.data_type.from_import(IMPORT_NEGATIVE_FLOAT)
                if data_type_kwargs == {"ge": 0} and self.use_non_positive_negative_number_constrained_types:
                    return self.data_type.from_import(IMPORT_NON_NEGATIVE_FLOAT)
                if data_type_kwargs == {"le": 0} and self.use_non_positive_negative_number_constrained_types:
                    return self.data_type.from_import(IMPORT_NON_POSITIVE_FLOAT)
            kwargs = {k: float(v) for k, v in data_type_kwargs.items()}
            if strict:
                kwargs["strict"] = True
            return self.data_type.from_import(IMPORT_CONFLOAT, kwargs=kwargs)
        if strict:
            return self.strict_type_map[StrictTypes.float]
        return self.type_map[types]

    def get_data_decimal_type(self, types: Types, **kwargs: Any) -> DataType:
        """Get decimal data type with constraints (condecimal)."""
        data_type_kwargs = self.transform_kwargs(kwargs, number_kwargs)
        if data_type_kwargs:
            return self.data_type.from_import(
                IMPORT_CONDECIMAL,
                kwargs={k: Decimal(str(v) if isinstance(v, UnionIntFloat) else v) for k, v in data_type_kwargs.items()},
            )
        return self.type_map[types]

    def get_data_str_type(self, types: Types, **kwargs: Any) -> DataType:
        """Get string data type with constraints (constr)."""
        data_type_kwargs: dict[str, Any] = self.transform_kwargs(kwargs, string_kwargs)
        strict = StrictTypes.str in self.strict_types
        if data_type_kwargs:
            if strict:
                data_type_kwargs["strict"] = True
            if self.PATTERN_KEY in data_type_kwargs:
                escaped_regex = data_type_kwargs[self.PATTERN_KEY].translate(escape_characters)
                # TODO: remove unneeded escaped characters
                data_type_kwargs[self.PATTERN_KEY] = f"r'{escaped_regex}'"
            return self.data_type.from_import(IMPORT_CONSTR, kwargs=data_type_kwargs)
        if strict:
            return self.strict_type_map[StrictTypes.str]
        return self.type_map[types]

    def get_data_bytes_type(self, types: Types, **kwargs: Any) -> DataType:
        """Get bytes data type with constraints (conbytes)."""
        data_type_kwargs: dict[str, Any] = self.transform_kwargs(kwargs, bytes_kwargs)
        strict = StrictTypes.bytes in self.strict_types
        if data_type_kwargs and not strict:
            return self.data_type.from_import(IMPORT_CONBYTES, kwargs=data_type_kwargs)
        # conbytes doesn't accept strict argument
        # https://github.com/samuelcolvin/pydantic/issues/2489
        if strict:
            return self.strict_type_map[StrictTypes.bytes]
        return self.type_map[types]

    def get_data_type(  # noqa: PLR0911
        self,
        types: Types,
        *,
        field_constraints: bool = False,
        **kwargs: Any,
    ) -> DataType:
        """Get data type with appropriate constraints for the given type."""
        if types == Types.string:
            return self.get_data_str_type(types, **kwargs)
        if types in {Types.int32, Types.int64, Types.integer}:
            return self.get_data_int_type(types, **kwargs)
        if types in {Types.float, Types.double, Types.number, Types.time}:
            return self.get_data_float_type(types, **kwargs)
        if types == Types.decimal:
            return self.get_data_decimal_type(types, **kwargs)
        if types == Types.binary:
            return self.get_data_bytes_type(types, **kwargs)
        if types == Types.boolean and StrictTypes.bool in self.strict_types:
            return self.strict_type_map[StrictTypes.bool]
        if types == Types.hostname and field_constraints:
            strict = StrictTypes.str in self.strict_types
            if strict:
                return self.strict_type_map[StrictTypes.str]
            return self.data_type(type="str")

        return self.type_map[types]
