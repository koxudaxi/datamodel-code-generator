"""JSON Schema parser implementation.

Handles parsing of JSON Schema, JSON, YAML, Dict, and CSV inputs to generate
Python data models. Supports draft-04 through draft-2020-12 schemas.
"""

from __future__ import annotations

import enum as _enum
import importlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from contextlib import contextmanager, suppress
from functools import cached_property, lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Optional, Union
from urllib.parse import ParseResult, unquote
from warnings import warn

from pydantic import (
    Field,
)
from typing_extensions import Unpack

from datamodel_code_generator import (
    AllOfClassHierarchy,
    AllOfMergeMode,
    InvalidClassNameError,
    JsonSchemaVersion,
    ReadOnlyWriteOnlyModelType,
    SchemaParseError,
    VersionMode,
    YamlValue,
    load_data,
    load_data_from_path,
    snooper_to_methods,
)
from datamodel_code_generator.format import (
    DatetimeClassType,
)
from datamodel_code_generator.imports import IMPORT_ANY, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED, get_module_name, sanitize_module_name
from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.model.enum import (
    SPECIALIZED_ENUM_TYPE_MATCH,
    Enum,
    StrEnum,
)
from datamodel_code_generator.model.pydantic_v2.dataclass import DataClass as PydanticV2DataClass
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.parser.base import (
    SPECIAL_PATH_FORMAT,
    Parser,
    Source,
    escape_characters,
    get_special_path,
    title_to_class_name,
)
from datamodel_code_generator.reference import SPECIAL_PATH_MARKER, ModelType, Reference, is_url
from datamodel_code_generator.types import (
    ANY,
    DataType,
    EmptyDataType,
    Types,
    UnionIntFloat,
    extract_qualified_names,
    get_subscript_args,
    get_type_base_name,
)
from datamodel_code_generator.util import (
    BaseModel,
    field_validator,
    get_fields_set,
    is_pydantic_v2,
    model_copy,
    model_dump,
    model_validate,
    model_validator,
)

if is_pydantic_v2():
    from pydantic import ConfigDict

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Iterator

    from datamodel_code_generator._types import JSONSchemaParserConfigDict
    from datamodel_code_generator.config import JSONSchemaParserConfig
    from datamodel_code_generator.parser.schema_version import JsonSchemaFeatures


def unescape_json_pointer_segment(segment: str) -> str:
    """Unescape JSON pointer segment by converting escape sequences and percent-encoding."""
    # Unescape ~1, ~0, and percent-encoding
    return unquote(segment.replace("~1", "/").replace("~0", "~"))


def get_model_by_path(
    schema: dict[str, YamlValue] | list[YamlValue], keys: list[str] | list[int]
) -> dict[str, YamlValue]:
    """Retrieve a model from schema by traversing the given path keys."""
    if not keys:
        if isinstance(schema, dict):
            return schema
        msg = f"Does not support json pointer to array. schema={schema}, key={keys}"  # pragma: no cover
        raise NotImplementedError(msg)  # pragma: no cover
    # Unescape the key if it's a string (JSON pointer segment)
    key = keys[0]
    if isinstance(key, str):  # pragma: no branch
        key = unescape_json_pointer_segment(key)
    value = schema.get(str(key), {}) if isinstance(schema, dict) else schema[int(key)]
    if len(keys) == 1:
        if isinstance(value, dict):
            return value
        msg = f"Does not support json pointer to array. schema={schema}, key={keys}"  # pragma: no cover
        raise NotImplementedError(msg)  # pragma: no cover
    if isinstance(value, (dict, list)):
        return get_model_by_path(value, keys[1:])
    msg = f"Cannot traverse non-container value. schema={schema}, key={keys}"  # pragma: no cover
    raise NotImplementedError(msg)  # pragma: no cover


# TODO: This dictionary contains formats valid only for OpenAPI and not for
#       jsonschema and vice versa. They should be separated.
json_schema_data_formats: dict[str, dict[str, Types]] = {
    "integer": {
        "int32": Types.int32,
        "int64": Types.int64,
        "default": Types.integer,
        "date-time": Types.date_time,
        "unix-time": Types.int64,
        "unixtime": Types.int64,
    },
    "number": {
        "float": Types.float,
        "double": Types.double,
        "decimal": Types.decimal,
        "date-time": Types.date_time,
        "time": Types.time,
        "time-delta": Types.timedelta,
        "default": Types.number,
        "unixtime": Types.int64,
    },
    "string": {
        "default": Types.string,
        "byte": Types.byte,  # base64 encoded string
        "binary": Types.binary,
        "date": Types.date,
        "date-time": Types.date_time,
        "timestamp with time zone": Types.date_time,  # PostgreSQL format
        "date-time-local": Types.date_time_local,
        "duration": Types.timedelta,
        "time": Types.time,
        "time-local": Types.time_local,
        "password": Types.password,
        "path": Types.path,
        "email": Types.email,
        "idn-email": Types.email,
        "uuid": Types.uuid,
        "uuid1": Types.uuid1,
        "uuid2": Types.uuid2,
        "uuid3": Types.uuid3,
        "uuid4": Types.uuid4,
        "uuid5": Types.uuid5,
        "uri": Types.uri,
        "uri-reference": Types.string,
        "hostname": Types.hostname,
        "ipv4": Types.ipv4,
        "ipv4-network": Types.ipv4_network,
        "ipv6": Types.ipv6,
        "ipv6-network": Types.ipv6_network,
        "decimal": Types.decimal,
        "integer": Types.integer,
        "unixtime": Types.int64,
        "ulid": Types.ulid,
    },
    "boolean": {"default": Types.boolean},
    "object": {"default": Types.object},
    "null": {"default": Types.null},
    "array": {"default": Types.array},
}


class JSONReference(_enum.Enum):
    """Define types of JSON references."""

    LOCAL = "LOCAL"
    REMOTE = "REMOTE"
    URL = "URL"


class Discriminator(BaseModel):
    """Represent OpenAPI discriminator object.

    This is an OpenAPI-specific concept for supporting polymorphism.
    It identifies which schema applies based on a property value.
    Kept in jsonschema.py to avoid circular imports with openapi.py.
    """

    propertyName: str  # noqa: N815
    mapping: Optional[dict[str, str]] = None  # noqa: UP045


class JsonSchemaObject(BaseModel):
    """Represent a JSON Schema object with validation and parsing capabilities."""

    if not TYPE_CHECKING:  # pragma: no branch
        if is_pydantic_v2():

            @classmethod
            def get_fields(cls) -> dict[str, Any]:
                """Get fields for Pydantic v2 models."""
                return cls.model_fields

        else:

            @classmethod
            def get_fields(cls) -> dict[str, Any]:
                """Get fields for Pydantic v1 models."""
                return cls.__fields__

            @classmethod
            def model_rebuild(cls) -> None:
                """Rebuild model by updating forward references."""
                cls.update_forward_refs()

    __constraint_fields__: set[str] = {  # noqa: RUF012
        "exclusiveMinimum",
        "minimum",
        "exclusiveMaximum",
        "maximum",
        "multipleOf",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "pattern",
        "uniqueItems",
    }
    __extra_key__: str = SPECIAL_PATH_FORMAT.format("extras")
    __metadata_only_fields__: set[str] = {  # noqa: RUF012
        "title",
        "description",
        "id",
        "$id",
        "$schema",
        "$comment",
        "examples",
        "example",
        "x_enum_varnames",
        "x_enum_field_as_literal",
        "definitions",
        "$defs",
        "default",
        "readOnly",
        "writeOnly",
        "deprecated",
        "$recursiveRef",
        "recursiveRef",
        "$recursiveAnchor",
        "recursiveAnchor",
        "$dynamicRef",
        "dynamicRef",
        "$dynamicAnchor",
        "dynamicAnchor",
    }

    @model_validator(mode="before")
    def validate_exclusive_maximum_and_exclusive_minimum(cls, values: Any) -> Any:  # noqa: N805
        """Validate and convert boolean exclusive maximum and minimum to numeric values."""
        if not isinstance(values, dict):
            return values
        exclusive_maximum: float | bool | None = values.get("exclusiveMaximum")
        exclusive_minimum: float | bool | None = values.get("exclusiveMinimum")

        if exclusive_maximum is True:
            values["exclusiveMaximum"] = values["maximum"]
            del values["maximum"]
        elif exclusive_maximum is False:
            del values["exclusiveMaximum"]
        if exclusive_minimum is True:
            values["exclusiveMinimum"] = values["minimum"]
            del values["minimum"]
        elif exclusive_minimum is False:
            del values["exclusiveMinimum"]
        return values

    @field_validator("ref")
    def validate_ref(cls, value: Any) -> Any:  # noqa: N805
        """Validate and normalize $ref values."""
        if isinstance(value, str) and "#" in value:
            if value.endswith("#/"):
                return value[:-1]
            if "#/" in value or value[0] == "#" or value[-1] == "#":
                return value
            return value.replace("#", "#/")
        return value

    @field_validator("required", mode="before")
    def validate_required(cls, value: Any) -> Any:  # noqa: N805
        """Validate and normalize required field values."""
        if value is None:
            return []
        if isinstance(value, list):  # pragma: no branch  # noqa: PLR1702
            # Filter to only include valid strings, excluding invalid objects
            required_fields: list[str] = []
            for item in value:
                if isinstance(item, str):
                    required_fields.append(item)

                # In some cases, the required field can include "anyOf", "oneOf", or "allOf" as a dict (#2297)
                elif isinstance(item, dict):  # pragma: no branch
                    for key, val in item.items():
                        if isinstance(val, list):  # pragma: no branch
                            # If 'anyOf' or "oneOf" is present, we won't include it in required fields
                            if key in {"anyOf", "oneOf"}:
                                continue

                            if key == "allOf":  # pragma: no branch
                                # If 'allOf' is present, we include them as required fields
                                required_fields.extend(sub_item for sub_item in val if isinstance(sub_item, str))

            value = required_fields

        return value

    @field_validator("type", mode="before")
    def validate_null_type(cls, value: Any) -> Any:  # noqa: N805
        """Validate and convert unquoted null type to string "null"."""
        # TODO[openapi]: This should be supported only for OpenAPI 3.1+
        # See: https://github.com/koxudaxi/datamodel-code-generator/issues/2477#issuecomment-3192480591
        if value is None:
            value = "null"
        if isinstance(value, list) and None in value:
            value = [v if v is not None else "null" for v in value]
        return value

    items: Optional[Union[list[JsonSchemaObject], JsonSchemaObject, bool]] = None  # noqa: UP007, UP045
    prefixItems: Optional[list[JsonSchemaObject]] = None  # noqa: N815, UP045
    uniqueItems: Optional[bool] = None  # noqa: N815, UP045
    type: Optional[Union[str, list[str]]] = None  # noqa: UP007, UP045
    format: Optional[str] = None  # noqa: UP045
    pattern: Optional[str] = None  # noqa: UP045
    minLength: Optional[int] = None  # noqa:  N815,UP045
    maxLength: Optional[int] = None  # noqa:  N815,UP045
    minimum: Optional[UnionIntFloat] = None  # noqa:  UP045
    maximum: Optional[UnionIntFloat] = None  # noqa:  UP045
    minItems: Optional[int] = None  # noqa:  N815,UP045
    maxItems: Optional[int] = None  # noqa:  N815,UP045
    multipleOf: Optional[float] = None  # noqa: N815, UP045
    exclusiveMaximum: Optional[Union[float, bool]] = None  # noqa: N815, UP007, UP045
    exclusiveMinimum: Optional[Union[float, bool]] = None  # noqa: N815, UP007, UP045
    additionalProperties: Optional[Union[JsonSchemaObject, bool]] = None  # noqa: N815, UP007, UP045
    unevaluatedProperties: Optional[Union[JsonSchemaObject, bool]] = None  # noqa: N815, UP007, UP045
    patternProperties: Optional[dict[str, Union[JsonSchemaObject, bool]]] = None  # noqa: N815, UP007, UP045
    propertyNames: Optional[JsonSchemaObject] = None  # noqa: N815, UP045
    oneOf: list[JsonSchemaObject] = Field(default_factory=list)  # noqa: N815
    anyOf: list[JsonSchemaObject] = Field(default_factory=list)  # noqa: N815
    allOf: list[JsonSchemaObject] = Field(default_factory=list)  # noqa: N815
    enum: list[Any] = Field(default_factory=list)
    writeOnly: Optional[bool] = None  # noqa: N815, UP045
    readOnly: Optional[bool] = None  # noqa: N815, UP045
    properties: Optional[dict[str, Union[JsonSchemaObject, bool]]] = None  # noqa: UP007, UP045
    required: list[str] = Field(default_factory=list)
    ref: Optional[str] = Field(default=None, alias="$ref")  # noqa: UP045
    recursiveRef: Optional[str] = Field(default=None, alias="$recursiveRef")  # noqa: N815, UP045
    recursiveAnchor: Optional[bool] = Field(default=None, alias="$recursiveAnchor")  # noqa: N815, UP045
    dynamicRef: Optional[str] = Field(default=None, alias="$dynamicRef")  # noqa: N815, UP045
    dynamicAnchor: Optional[str] = Field(default=None, alias="$dynamicAnchor")  # noqa: N815, UP045
    nullable: Optional[bool] = None  # noqa: UP045
    x_enum_varnames: list[str] = Field(default_factory=list, alias="x-enum-varnames")
    x_enum_names: list[str] = Field(default_factory=list, alias="x-enumNames")
    x_enum_field_as_literal: Optional[bool] = Field(default=None, alias="x-enum-field-as-literal")  # noqa: UP045
    description: Optional[str] = None  # noqa: UP045
    title: Optional[str] = None  # noqa: UP045
    example: Any = None
    examples: Any = None
    default: Any = None
    id: Optional[str] = Field(default=None, alias="$id")  # noqa: UP045
    custom_type_path: Optional[str] = Field(default=None, alias="customTypePath")  # noqa: UP045
    custom_base_path: str | list[str] | None = Field(default=None, alias="customBasePath")
    extras: dict[str, Any] = Field(alias=__extra_key__, default_factory=dict)
    discriminator: Optional[Union[Discriminator, str]] = None  # noqa: UP007, UP045
    if is_pydantic_v2():
        model_config = ConfigDict(  # ty: ignore
            arbitrary_types_allowed=True,
            ignored_types=(cached_property,),
        )
    else:

        class Config:
            """Pydantic v1 configuration for JsonSchemaObject."""

            arbitrary_types_allowed = True
            keep_untouched = (cached_property,)
            smart_casts = True

    def __init__(self, **data: Any) -> None:
        """Initialize JsonSchemaObject with extra fields handling."""
        super().__init__(**data)
        # Restore extras from alias key (for dict -> parse_obj round-trip)
        alias_extras = data.get(self.__extra_key__, {})
        # Collect custom keys from raw data
        raw_extras = {k: v for k, v in data.items() if k not in EXCLUDE_FIELD_KEYS}
        # Merge: raw_extras takes precedence (original data is the source of truth)
        self.extras = {**alias_extras, **raw_extras}
        if "const" in alias_extras:  # pragma: no cover
            self.extras["const"] = alias_extras["const"]
        # Support x-propertyNames extension for OpenAPI 3.0
        if "x-propertyNames" in self.extras and self.propertyNames is None:
            x_prop_names = self.extras.pop("x-propertyNames")
            if isinstance(x_prop_names, dict):
                self.propertyNames = model_validate(JsonSchemaObject, x_prop_names)

    @cached_property
    def is_object(self) -> bool:
        """Check if the schema represents an object type."""
        return self.properties is not None or (
            self.type == "object" and not self.allOf and not self.oneOf and not self.anyOf and not self.ref
        )

    @cached_property
    def is_array(self) -> bool:
        """Check if the schema represents an array type."""
        return self.items is not None or self.prefixItems is not None or self.type == "array"

    @cached_property
    def ref_object_name(self) -> str:  # pragma: no cover
        """Extract the object name from the reference path."""
        return (self.ref or "").rsplit("/", 1)[-1]

    @field_validator("items", mode="before")
    def validate_items(cls, values: Any) -> Any:  # noqa: N805
        """Validate items field, converting empty dicts to None."""
        # this condition expects empty dict
        return values or None

    @cached_property
    def has_default(self) -> bool:
        """Check if the schema has a default value or default factory."""
        return "default" in get_fields_set(self) or "default_factory" in self.extras

    @cached_property
    def has_constraint(self) -> bool:
        """Check if the schema has any constraint fields set."""
        return bool(self.__constraint_fields__ & get_fields_set(self))

    @cached_property
    def ref_type(self) -> JSONReference | None:
        """Get the reference type (LOCAL, REMOTE, or URL)."""
        if self.ref:
            return get_ref_type(self.ref)
        return None  # pragma: no cover

    @cached_property
    def type_has_null(self) -> bool:
        """Check if the type list or oneOf/anyOf contains null."""
        if isinstance(self.type, list) and "null" in self.type:
            return True
        for item in self.oneOf + self.anyOf:
            if item.type == "null":
                return True
            if isinstance(item.type, list) and "null" in item.type:
                return True
        return False

    @cached_property
    def has_multiple_types(self) -> bool:
        """Check if the type is a list with multiple non-null types."""
        if not isinstance(self.type, list):
            return False
        non_null_types = [t for t in self.type if t != "null"]
        return len(non_null_types) > 1

    @cached_property
    def has_ref_with_schema_keywords(self) -> bool:
        """Check if schema has $ref combined with schema-affecting keywords.

        Metadata-only keywords (title, description, etc.) are excluded
        as they don't affect the schema structure. OpenAPI/JSON Schema
        extension fields (x-*) are also excluded as they are vendor
        extensions and don't affect the core schema structure.
        """
        if not self.ref:
            return False
        other_fields = get_fields_set(self) - {"ref"}
        schema_affecting_fields = other_fields - self.__metadata_only_fields__ - {"extras"}
        if self.extras:
            # Filter out metadata-only fields AND extension fields (x-* prefix)
            schema_affecting_extras = {
                k for k in self.extras if k not in self.__metadata_only_fields__ and not k.startswith("x-")
            }
            if schema_affecting_extras:
                schema_affecting_fields |= {"extras"}
        return bool(schema_affecting_fields)

    @cached_property
    def is_ref_with_nullable_only(self) -> bool:
        """Check if schema has $ref with only nullable: true (no other schema-affecting keywords).

        This is used to avoid creating duplicate models when a $ref is combined
        with nullable: true. In such cases, the reference should be used directly
        with Optional type annotation instead of merging schemas.
        """
        if not self.ref or self.nullable is not True:
            return False
        other_fields = get_fields_set(self) - {"ref", "nullable"} - self.__metadata_only_fields__ - {"extras"}
        if other_fields:
            return False
        if self.extras:
            schema_affecting_extras = {
                k for k in self.extras if k not in self.__metadata_only_fields__ and not k.startswith("x-")
            }
            if schema_affecting_extras:
                return False
        return True


@lru_cache
def get_ref_type(ref: str) -> JSONReference:
    """Determine the type of reference (LOCAL, REMOTE, or URL)."""
    if ref[0] == "#":
        return JSONReference.LOCAL
    if is_url(ref):
        return JSONReference.URL
    return JSONReference.REMOTE


def _get_type(
    type_: str,
    format__: str | None = None,
    data_formats: dict[str, dict[str, Types]] | None = None,
) -> Types:
    """Get the appropriate Types enum for a given JSON Schema type and format."""
    if data_formats is None:  # pragma: no cover
        data_formats = json_schema_data_formats
    if type_ not in data_formats:
        return Types.any
    if (type_format := data_formats[type_].get("default" if format__ is None else format__)) is not None:
        return type_format

    warn(f"format of {format__!r} not understood for {type_!r} - using default", stacklevel=2)
    return data_formats[type_]["default"]


JsonSchemaObject.model_rebuild()

DEFAULT_FIELD_KEYS: set[str] = {
    "example",
    "examples",
    "description",
    "discriminator",
    "title",
    "const",
    "default_factory",
    "deprecated",
}

EXCLUDE_FIELD_KEYS_IN_JSON_SCHEMA: set[str] = {
    "readOnly",
    "writeOnly",
}

EXCLUDE_FIELD_KEYS = (
    set(JsonSchemaObject.get_fields())  # ty: ignore
    - DEFAULT_FIELD_KEYS
    - EXCLUDE_FIELD_KEYS_IN_JSON_SCHEMA
) | {
    "$id",
    "$ref",
    "$recursiveRef",
    "$recursiveAnchor",
    "$dynamicRef",
    "$dynamicAnchor",
    JsonSchemaObject.__extra_key__,
}


@snooper_to_methods()  # noqa: PLR0904
class JsonSchemaParser(Parser["JSONSchemaParserConfig", "JsonSchemaFeatures"]):
    """Parser for JSON Schema, JSON, YAML, Dict, and CSV formats."""

    SCHEMA_PATHS: ClassVar[list[str]] = ["#/definitions", "#/$defs"]
    SCHEMA_OBJECT_TYPE: ClassVar[type[JsonSchemaObject]] = JsonSchemaObject

    COMPATIBLE_PYTHON_TYPES: ClassVar[dict[str, frozenset[str]]] = {
        "string": frozenset({"str", "String"}),
        "integer": frozenset({"int", "Integer"}),
        "number": frozenset({"float", "int", "Number"}),
        "boolean": frozenset({"bool", "Boolean"}),
        "array": frozenset({
            "list",
            "List",
            "set",
            "Set",
            "frozenset",
            "FrozenSet",
            "Sequence",
            "MutableSequence",
            "tuple",
            "Tuple",
            "AbstractSet",
            "MutableSet",
        }),
        "object": frozenset({"dict", "Dict", "Mapping", "MutableMapping", "TypedDict"}),
    }

    PYTHON_TYPE_IMPORTS: ClassVar[dict[str, Import]] = {
        # collections.abc
        "Callable": Import.from_full_path("collections.abc.Callable"),
        "Iterable": Import.from_full_path("collections.abc.Iterable"),
        "Iterator": Import.from_full_path("collections.abc.Iterator"),
        "Generator": Import.from_full_path("collections.abc.Generator"),
        "Awaitable": Import.from_full_path("collections.abc.Awaitable"),
        "Coroutine": Import.from_full_path("collections.abc.Coroutine"),
        "AsyncIterable": Import.from_full_path("collections.abc.AsyncIterable"),
        "AsyncIterator": Import.from_full_path("collections.abc.AsyncIterator"),
        "AsyncGenerator": Import.from_full_path("collections.abc.AsyncGenerator"),
        "Mapping": Import.from_full_path("collections.abc.Mapping"),
        "MutableMapping": Import.from_full_path("collections.abc.MutableMapping"),
        "Sequence": Import.from_full_path("collections.abc.Sequence"),
        "MutableSequence": Import.from_full_path("collections.abc.MutableSequence"),
        "Set": Import.from_full_path("collections.abc.Set"),
        "MutableSet": Import.from_full_path("collections.abc.MutableSet"),
        "Collection": Import.from_full_path("collections.abc.Collection"),
        "Reversible": Import.from_full_path("collections.abc.Reversible"),
        # collections
        "defaultdict": Import.from_full_path("collections.defaultdict"),
        "OrderedDict": Import.from_full_path("collections.OrderedDict"),
        "Counter": Import.from_full_path("collections.Counter"),
        "deque": Import.from_full_path("collections.deque"),
        "ChainMap": Import.from_full_path("collections.ChainMap"),
        # re
        "Pattern": Import.from_full_path("re.Pattern"),
        "Match": Import.from_full_path("re.Match"),
        # typing
        "Any": Import.from_full_path("typing.Any"),
        "Type": Import.from_full_path("typing.Type"),
        "Union": Import.from_full_path("typing.Union"),
        "Optional": Import.from_full_path("typing.Optional"),
        "Literal": Import.from_full_path("typing.Literal"),
        "Final": Import.from_full_path("typing.Final"),
        "ClassVar": Import.from_full_path("typing.ClassVar"),
        "Annotated": Import.from_full_path("typing.Annotated"),
        "TypeVar": Import.from_full_path("typing.TypeVar"),
        "TypeAlias": Import.from_full_path("typing.TypeAlias"),
        "Never": Import.from_full_path("typing.Never"),
        "NoReturn": Import.from_full_path("typing.NoReturn"),
        "Self": Import.from_full_path("typing.Self"),
        "LiteralString": Import.from_full_path("typing.LiteralString"),
        "TypeGuard": Import.from_full_path("typing.TypeGuard"),
        # pathlib
        "Path": Import.from_full_path("pathlib.Path"),
        "PurePath": Import.from_full_path("pathlib.PurePath"),
        # decimal
        "Decimal": Import.from_full_path("decimal.Decimal"),
        # uuid
        "UUID": Import.from_full_path("uuid.UUID"),
        # datetime
        "datetime": Import.from_full_path("datetime.datetime"),
        "date": Import.from_full_path("datetime.date"),
        "time": Import.from_full_path("datetime.time"),
        "timedelta": Import.from_full_path("datetime.timedelta"),
        # enum
        "Enum": Import.from_full_path("enum.Enum"),
        "IntEnum": Import.from_full_path("enum.IntEnum"),
        "StrEnum": Import.from_full_path("enum.StrEnum"),
        "Flag": Import.from_full_path("enum.Flag"),
        "IntFlag": Import.from_full_path("enum.IntFlag"),
        "BaseModel": Import.from_full_path("pydantic.BaseModel"),
    }

    # Types that require x-python-type override regardless of schema type
    PYTHON_TYPE_OVERRIDE_ALWAYS: ClassVar[frozenset[str]] = frozenset({
        "Callable",
        "Type",
        # collections types that have no JSON Schema equivalent
        "defaultdict",
        "OrderedDict",
        "Counter",
        "deque",
        "ChainMap",
    })

    _config_class_name: ClassVar[str] = "JSONSchemaParserConfig"

    def __init__(
        self,
        source: str | Path | list[Path] | ParseResult,
        *,
        config: JSONSchemaParserConfig | None = None,
        **options: Unpack[JSONSchemaParserConfigDict],
    ) -> None:
        """Initialize the JSON Schema parser with configuration options."""
        if config is None and options.get("target_datetime_class") is None:
            options["target_datetime_class"] = DatetimeClassType.Awaredatetime
        super().__init__(source=source, config=config, **options)

        self.remote_object_cache: DefaultPutDict[str, dict[str, YamlValue]] = DefaultPutDict()
        self.raw_obj: dict[str, YamlValue] = {}
        self._root_id: Optional[str] = None  # noqa: UP045
        self._root_id_base_path: Optional[str] = None  # noqa: UP045
        self.reserved_refs: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
        self._dynamic_anchor_index: dict[tuple[str, ...], dict[str, str]] = {}
        self._recursive_anchor_index: dict[tuple[str, ...], list[str]] = {}
        self.field_keys: set[str] = {
            *DEFAULT_FIELD_KEYS,
            *self.field_extra_keys,
            *self.field_extra_keys_without_x_prefix,
        }

        if self.data_model_field_type.can_have_extra_keys:
            self.get_field_extra_key: Callable[[str], str] = (
                lambda key: self.model_resolver.get_valid_field_name_and_alias(
                    key, model_type=self.field_name_model_type
                )[0]
            )

        else:
            self.get_field_extra_key = lambda key: key

    def get_field_extras(self, obj: JsonSchemaObject) -> dict[str, Any]:
        """Extract extra field metadata from a JSON Schema object."""
        if self.field_include_all_keys:
            extras = {
                self.get_field_extra_key(k.lstrip("x-") if k in self.field_extra_keys_without_x_prefix else k): v
                for k, v in obj.extras.items()
            }
        else:
            extras = {
                self.get_field_extra_key(k.lstrip("x-") if k in self.field_extra_keys_without_x_prefix else k): v
                for k, v in obj.extras.items()
                if k in self.field_keys
            }
        if self.default_field_extras:
            extras.update(self.default_field_extras)
        return extras

    @cached_property
    def _data_formats(self) -> dict[str, dict[str, Types]]:
        """Get data format mappings for this parser type.

        Returns all formats for backward compatibility.
        OpenAPI-specific formats will be separated in Strict mode (future).
        """
        return json_schema_data_formats

    def _get_type_with_mappings(self, type_: str, format_: str | None = None) -> Types:
        """Get the Types enum for a given type and format, applying custom type mappings.

        Custom mappings from --type-mappings are checked first, then falls back to
        the parser's data format mappings.
        """
        data_formats = self._data_formats
        if self.type_mappings and format_ is not None and (type_, format_) in self.type_mappings:
            target_format = self.type_mappings[type_, format_]
            for type_formats in data_formats.values():
                if target_format in type_formats:
                    return type_formats[target_format]
            if target_format in data_formats:
                return data_formats[target_format]["default"]

        return _get_type(type_, format_, data_formats)

    @cached_property
    def schema_paths(self) -> list[tuple[str, list[str]]]:
        """Get schema paths for definitions and defs.

        For JsonSchema, uses schema_features.definitions_key to determine
        the primary path, with fallback to the alternative in Lenient mode.
        OpenAPI subclass uses its own SCHEMA_PATHS (#/components/schemas).
        """
        # OpenAPI and other subclasses use their own SCHEMA_PATHS
        if self.SCHEMA_PATHS != ["#/definitions", "#/$defs"]:
            return [(s, s.lstrip("#/").split("/")) for s in self.SCHEMA_PATHS]

        # JsonSchema: use definitions_key from schema_features
        primary_key = self.schema_features.definitions_key
        primary_path = f"#/{primary_key}"
        fallback_key = "$defs" if primary_key == "definitions" else "definitions"
        fallback_path = f"#/{fallback_key}"

        # Strict mode: only use version-specific path
        if self.config.schema_version_mode == VersionMode.Strict:
            return [(str(primary_path), [str(primary_key)])]

        # Lenient mode (default): check both paths, primary first
        return [
            (str(primary_path), [str(primary_key)]),
            (str(fallback_path), [str(fallback_key)]),
        ]

    @cached_property
    def schema_features(self) -> JsonSchemaFeatures:
        """Get schema features based on config or detected version."""
        from datamodel_code_generator.parser.schema_version import (  # noqa: PLC0415
            JsonSchemaFeatures,
            detect_jsonschema_version,
        )

        config_version = getattr(self.config, "jsonschema_version", None)
        if config_version is not None and config_version != JsonSchemaVersion.Auto:
            return JsonSchemaFeatures.from_version(config_version)
        version = detect_jsonschema_version(self.raw_obj) if self.raw_obj else JsonSchemaVersion.Auto
        return JsonSchemaFeatures.from_version(version)

    @property
    def root_id(self) -> str | None:
        """Get the root $id from the model resolver."""
        return self.model_resolver.root_id

    @root_id.setter
    def root_id(self, value: str | None) -> None:
        """Set the root $id in the model resolver."""
        self.model_resolver.set_root_id(value)

    def should_parse_enum_as_literal(
        self,
        obj: JsonSchemaObject,
        property_name: str | None = None,
        property_obj: JsonSchemaObject | None = None,
    ) -> bool:
        """Determine if an enum should be parsed as a literal type.

        Priority (highest to lowest):
        1. x-enum-field-as-literal on the property schema
        2. enum_field_as_literal_map matching Model.field or field
        3. Global enum_field_as_literal setting
        """
        # Check x-enum-field-as-literal on property or obj
        target_obj = property_obj if property_obj is not None else obj
        if target_obj.x_enum_field_as_literal is not None:
            return target_obj.x_enum_field_as_literal

        # Check enum_field_as_literal_map for matching keys
        if property_name and self.enum_field_as_literal_map and property_name in self.enum_field_as_literal_map:
            return self.enum_field_as_literal_map[property_name] == "literal"

        # Fall back to global setting
        if self.enum_field_as_literal == LiteralType.All:
            return True
        if self.enum_field_as_literal == LiteralType.One:
            return len(obj.enum) == 1
        return False

    @classmethod
    def _extract_const_enum_from_combined(  # noqa: PLR0912
        cls, items: list[JsonSchemaObject], parent_type: str | list[str] | None
    ) -> tuple[list[Any], list[str], str | None, bool] | None:
        """Extract enum values from oneOf/anyOf const pattern."""
        enum_values: list[Any] = []
        varnames: list[str] = []
        nullable = False
        inferred_type: str | None = None

        for item in items:
            if item.type == "null" and "const" not in item.extras:
                nullable = True
                continue

            if "const" not in item.extras:
                return None

            if item.ref or item.properties or item.oneOf or item.anyOf or item.allOf:
                return None

            const_value = item.extras["const"]
            enum_values.append(const_value)

            if item.title:
                varnames.append(item.title)

            if inferred_type is None and const_value is not None:
                match const_value:
                    case str():
                        inferred_type = "string"
                    case bool():  # bool must come before int (bool is subclass of int)
                        inferred_type = "boolean"
                    case int():
                        inferred_type = "integer"
                    case float():
                        inferred_type = "number"

        if not enum_values:  # pragma: no cover
            return None

        final_type: str | None
        match parent_type:
            case str():
                final_type = parent_type
            case list():
                non_null_types = [t for t in parent_type if t != "null"]
                final_type = non_null_types[0] if non_null_types else inferred_type
                if "null" in parent_type:
                    nullable = True
            case _:
                final_type = inferred_type

        return (enum_values, varnames, final_type, nullable)

    def _create_synthetic_enum_obj(
        self,
        original: JsonSchemaObject,
        enum_values: list[Any],
        varnames: list[str],
        enum_type: str | None,
        nullable: bool,  # noqa: FBT001
    ) -> JsonSchemaObject:
        """Create a synthetic JsonSchemaObject for enum parsing."""
        final_enum = [*enum_values, None] if nullable else enum_values
        final_varnames = varnames if len(varnames) == len(enum_values) else []

        return self.SCHEMA_OBJECT_TYPE(
            type=enum_type,
            enum=final_enum,
            title=original.title,
            description=original.description,
            **({"x-enum-varnames": final_varnames} | ({"default": original.default} if original.has_default else {})),
        )

    def is_constraints_field(self, obj: JsonSchemaObject) -> bool:
        """Check if a field should include constraints."""
        return obj.is_array or (
            self.field_constraints
            and not (
                obj.ref
                or obj.anyOf
                or obj.oneOf
                or obj.allOf
                or obj.is_object
                or (obj.enum and not self.ignore_enum_constraints)
            )
        )

    def _is_fixed_length_tuple(self, obj: JsonSchemaObject) -> bool:
        """Check if an array field represents a fixed-length tuple."""
        if obj.prefixItems is not None and obj.items in {None, False}:
            return obj.minItems == obj.maxItems == len(obj.prefixItems)
        if self.use_tuple_for_fixed_items and isinstance(obj.items, list) and obj.prefixItems is None:
            return obj.minItems == obj.maxItems == len(obj.items)
        return False

    def _resolve_field_flag(self, obj: JsonSchemaObject, flag: Literal["readOnly", "writeOnly"]) -> bool:
        """Resolve a field flag (readOnly/writeOnly) from direct value, $ref, and compositions."""
        if getattr(obj, flag) is True:
            return True
        if (
            self.read_only_write_only_model_type
            and obj.ref
            and self._resolve_field_flag(self._load_ref_schema_object(obj.ref), flag)
        ):
            return True
        return any(self._resolve_field_flag(sub, flag) for sub in obj.allOf + obj.anyOf + obj.oneOf)

    def _collect_all_fields_for_request_response(
        self,
        fields: list[DataModelFieldBase],
        base_classes: list[Reference] | None,
    ) -> list[DataModelFieldBase]:
        """Collect all fields including those from base classes for Request/Response models.

        Order: parent → child, with child fields overriding parent fields of the same name.
        """
        all_fields: list[DataModelFieldBase] = []
        visited: set[str] = set()

        def iter_from_schema(obj: JsonSchemaObject, path: list[str]) -> Iterable[DataModelFieldBase]:
            module_name = get_module_name(path[-1] if path else "", None, treat_dot_as_module=self.treat_dot_as_module)
            if obj.properties:
                yield from self.parse_object_fields(obj, path, module_name)
            for item in obj.allOf:
                if item.ref:
                    if item.ref in visited:  # pragma: no cover
                        continue
                    visited.add(item.ref)
                    yield from iter_from_schema(self._load_ref_schema_object(item.ref), path)
                elif item.properties:
                    yield from self.parse_object_fields(item, path, module_name)

        for base_ref in base_classes or []:
            if isinstance(base_ref.source, DataModel):
                all_fields.extend(base_ref.source.iter_all_fields(visited))
            elif base_ref.path not in visited:  # pragma: no cover
                visited.add(base_ref.path)
                all_fields.extend(iter_from_schema(self._load_ref_schema_object(base_ref.path), []))
        all_fields.extend(fields)

        deduplicated: dict[str, DataModelFieldBase] = {}
        for field in all_fields:
            key = field.original_name or field.name
            if key:  # pragma: no cover
                deduplicated[key] = field.copy_deep()
        return list(deduplicated.values())

    def _should_generate_separate_models(
        self,
        fields: list[DataModelFieldBase],
        base_classes: list[Reference] | None,
    ) -> bool:
        """Determine if Request/Response models should be generated."""
        if self.read_only_write_only_model_type is None:
            return False
        all_fields = self._collect_all_fields_for_request_response(fields, base_classes)
        return any(field.read_only or field.write_only for field in all_fields)

    def _should_generate_base_model(self, *, generates_separate_models: bool = False) -> bool:
        """Determine if Base model should be generated."""
        if getattr(self, "_force_base_model_generation", False):
            return True
        if self.read_only_write_only_model_type is None:
            return True
        if self.read_only_write_only_model_type == ReadOnlyWriteOnlyModelType.All:
            return True
        return not generates_separate_models

    def _ref_schema_generates_variant(self, ref_path: str, suffix: str) -> bool:
        """Check if a referenced schema will generate a specific variant (Request or Response).

        For Request variant: schema must have readOnly fields AND at least one non-readOnly field.
        For Response variant: schema must have writeOnly fields AND at least one non-writeOnly field.
        """
        try:
            ref_schema = self._load_ref_schema_object(ref_path)
        except Exception:  # noqa: BLE001  # pragma: no cover
            return False

        has_read_only = False
        has_write_only = False
        has_non_read_only = False
        has_non_write_only = False

        for prop in (ref_schema.properties or {}).values():
            if not isinstance(prop, JsonSchemaObject):  # pragma: no cover
                continue
            is_read_only = self._resolve_field_flag(prop, "readOnly")
            is_write_only = self._resolve_field_flag(prop, "writeOnly")
            if is_read_only:
                has_read_only = True
            else:
                has_non_read_only = True
            if is_write_only:
                has_write_only = True
            else:
                has_non_write_only = True

        if suffix == "Request":
            return has_read_only and has_non_read_only
        if suffix == "Response":
            return has_write_only and has_non_write_only
        return False  # pragma: no cover

    def _ref_schema_has_model(self, ref_path: str) -> bool:
        """Check if a referenced schema will have a model (base or variant) generated.

        Returns False if the schema has only readOnly or only writeOnly fields in request-response mode,
        which would result in no model being generated at all.
        """
        try:
            ref_schema = self._load_ref_schema_object(ref_path)
        except Exception:  # noqa: BLE001  # pragma: no cover
            return True

        has_read_only = False
        has_write_only = False

        for prop in (ref_schema.properties or {}).values():
            if not isinstance(prop, JsonSchemaObject):  # pragma: no cover
                continue
            is_read_only = self._resolve_field_flag(prop, "readOnly")
            is_write_only = self._resolve_field_flag(prop, "writeOnly")
            if is_read_only:
                has_read_only = True
            elif is_write_only:
                has_write_only = True
            else:  # pragma: no cover
                return True

        if has_read_only and not has_write_only:
            return False
        return not (has_write_only and not has_read_only)

    def _update_data_type_ref_for_variant(self, data_type: DataType, suffix: str) -> None:
        """Recursively update data type references to point to variant models."""
        if data_type.reference:
            ref_path = data_type.reference.path
            if self._ref_schema_generates_variant(ref_path, suffix):
                path_parts = ref_path.split("/")
                base_name = path_parts[-1]
                variant_name = f"{base_name}{suffix}"
                unique_name = self.model_resolver.get_class_name(variant_name, unique=False).name
                path_parts[-1] = unique_name
                variant_ref = self.model_resolver.add(path_parts, unique_name, class_name=True, unique=False)
                data_type.reference = variant_ref
            elif not self._ref_schema_has_model(ref_path):  # pragma: no branch
                if not hasattr(self, "_force_base_model_refs"):
                    self._force_base_model_refs: set[str] = set()
                self._force_base_model_refs.add(ref_path)
        for nested_dt in data_type.data_types:
            self._update_data_type_ref_for_variant(nested_dt, suffix)

    def _update_field_refs_for_variant(
        self, model_fields: list[DataModelFieldBase], suffix: str
    ) -> list[DataModelFieldBase]:
        """Update field references in model_fields to point to variant models.

        For Request models, refs should point to Request variants.
        For Response models, refs should point to Response variants.
        """
        if self.read_only_write_only_model_type != ReadOnlyWriteOnlyModelType.RequestResponse:
            return model_fields
        for field in model_fields:
            if field.data_type:  # pragma: no branch
                self._update_data_type_ref_for_variant(field.data_type, suffix)
        return model_fields

    def _generate_forced_base_models(self) -> None:
        """Generate base models for schemas that are referenced as property types but lack models."""
        if not hasattr(self, "_force_base_model_refs"):
            return
        if not self._force_base_model_refs:  # pragma: no cover
            return

        existing_model_paths = {result.path for result in self.results}

        for ref_path in sorted(self._force_base_model_refs):
            if ref_path in existing_model_paths:  # pragma: no cover
                continue
            try:
                ref_schema = self._load_ref_schema_object(ref_path)
                path_parts = ref_path.split("/")
                schema_name = path_parts[-1]

                self._force_base_model_generation = True
                try:
                    self.parse_obj(schema_name, ref_schema, path_parts)
                finally:
                    self._force_base_model_generation = False
            except Exception:  # noqa: BLE001, S110  # pragma: no cover
                pass

    def _create_variant_model(  # noqa: PLR0913, PLR0917
        self,
        path: list[str],
        base_name: str,
        suffix: str,
        model_fields: list[DataModelFieldBase],
        obj: JsonSchemaObject,
        data_model_type_class: type[DataModel],
    ) -> None:
        """Create a Request or Response model variant."""
        if not model_fields:
            return
        # Update field refs to point to variant models when in request-response mode
        self._update_field_refs_for_variant(model_fields, suffix)
        variant_name = f"{base_name}{suffix}"
        unique_name = self.model_resolver.get_class_name(variant_name, unique=True).name
        model_path = [*path[:-1], unique_name]
        reference = self.model_resolver.add(model_path, unique_name, class_name=True, unique=False, loaded=True)
        self.set_schema_extensions(reference.path, obj)
        model = self._create_data_model(
            model_type=data_model_type_class,
            reference=reference,
            fields=model_fields,
            custom_base_class=self._resolve_base_class(unique_name, obj.custom_base_path),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description if self.use_schema_description else None,
            nullable=obj.type_has_null,
            keyword_only=self.keyword_only,
            treat_dot_as_module=self.treat_dot_as_module,
            dataclass_arguments=self.dataclass_arguments,
        )
        self.results.append(model)

    def _create_request_response_models(  # noqa: PLR0913, PLR0917
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        fields: list[DataModelFieldBase],
        data_model_type_class: type[DataModel],
        base_classes: list[Reference] | None = None,
    ) -> None:
        """Generate Request and Response model variants."""
        all_fields = self._collect_all_fields_for_request_response(fields, base_classes)

        # Request model: exclude readOnly fields
        if any(field.read_only for field in all_fields):
            self._create_variant_model(
                path,
                name,
                "Request",
                [field for field in all_fields if not field.read_only],
                obj,
                data_model_type_class,
            )
        # Response model: exclude writeOnly fields
        if any(field.write_only for field in all_fields):
            self._create_variant_model(
                path,
                name,
                "Response",
                [field for field in all_fields if not field.write_only],
                obj,
                data_model_type_class,
            )

    def get_object_field(  # noqa: PLR0913
        self,
        *,
        field_name: str | None,
        field: JsonSchemaObject,
        required: bool,
        field_type: DataType,
        alias: str | list[str] | None,
        original_field_name: str | None,
        effective_default: Any = None,
        effective_has_default: bool | None = None,
    ) -> DataModelFieldBase:
        """Create a data model field from a JSON Schema object field."""
        default_value = effective_default if effective_has_default is not None else field.default
        has_default = effective_has_default if effective_has_default is not None else field.has_default

        constraints = model_dump(field, exclude_none=True) if self.is_constraints_field(field) else None
        if constraints is not None and self.field_constraints and field.format == "hostname":
            constraints["pattern"] = self.data_type_manager.HOSTNAME_REGEX
        # Suppress minItems/maxItems for fixed-length tuples
        if constraints and self._is_fixed_length_tuple(field):
            constraints.pop("minItems", None)
            constraints.pop("maxItems", None)
        # Handle multiple aliases (Pydantic v2 AliasChoices)
        single_alias: str | None = None
        validation_aliases: list[str] | None = None
        if isinstance(alias, list):
            validation_aliases = alias
        else:
            single_alias = alias
        return self.data_model_field_type(
            name=field_name,
            default=default_value,
            data_type=field_type,
            required=required,
            alias=single_alias,
            validation_aliases=validation_aliases,
            constraints=constraints,
            nullable=field.nullable
            if self.strict_nullable and field.nullable is not None
            else (False if self.strict_nullable and (has_default or required) else None),
            strip_default_none=self.strip_default_none,
            extras=self.get_field_extras(field),
            use_annotated=self.use_annotated,
            use_serialize_as_any=self.use_serialize_as_any,
            use_field_description=self.use_field_description,
            use_field_description_example=self.use_field_description_example,
            use_inline_field_description=self.use_inline_field_description,
            use_default_kwarg=self.use_default_kwarg,
            original_name=original_field_name,
            has_default=has_default,
            type_has_null=field.type_has_null,
            read_only=self._resolve_field_flag(field, "readOnly"),
            write_only=self._resolve_field_flag(field, "writeOnly"),
            use_frozen_field=self.use_frozen_field,
            use_serialization_alias=self.use_serialization_alias,
            use_default_factory_for_optional_nested_models=self.use_default_factory_for_optional_nested_models,
        )

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        """Get the data type for a JSON Schema object."""
        python_type_override = self._get_python_type_override(obj)
        if python_type_override:  # pragma: no cover
            return python_type_override

        if "const" in obj.extras:
            return self.data_type(literals=[obj.extras["const"]])

        if obj.type is None:
            return self.data_type_manager.get_data_type(
                Types.any,
            )

        def _get_data_type(type_: str, format__: str) -> DataType:
            return self.data_type_manager.get_data_type(
                self._get_type_with_mappings(type_, format__),
                field_constraints=self.field_constraints,
                **model_dump(obj) if not self.field_constraints else {},
            )

        if isinstance(obj.type, list):
            return self.data_type(
                data_types=[_get_data_type(t, obj.format or "default") for t in obj.type if t != "null"],
                is_optional="null" in obj.type,
            )
        data_type = _get_data_type(obj.type, obj.format or "default")
        if self.strict_nullable and obj.nullable:
            return self.data_type(data_types=[data_type], is_optional=True)
        return data_type

    def get_ref_data_type(self, ref: str) -> DataType:
        """Get a data type from a reference string."""
        ref_schema = self._load_ref_schema_object(ref)
        x_python_import = ref_schema.extras.get("x-python-import")
        if isinstance(x_python_import, dict):
            module = x_python_import.get("module")
            type_name = x_python_import.get("name")
            if module and type_name:  # pragma: no branch
                full_path = f"{module}.{type_name}"
                import_ = Import.from_full_path(full_path)
                self.imports.append(import_)
                return self.data_type.from_import(import_)
        reference = self.model_resolver.add_ref(ref)
        is_optional = ref_schema.type == "null" or (self.strict_nullable and ref_schema.nullable is True)
        return self.data_type(reference=reference, is_optional=is_optional)

    def set_additional_properties(self, path: str, obj: JsonSchemaObject) -> None:
        """Set additional properties flag in extra template data.

        For TypedDict with PEP 728 support:
        - additionalProperties: false -> closed=True
        - additionalProperties: { type: X } -> extra_items=X

        This is controlled by use_closed_typed_dict option. When disabled,
        the additionalProperties constraint is not converted to PEP 728 syntax.
        """
        if not self.use_closed_typed_dict:
            return
        if isinstance(obj.additionalProperties, bool):
            self.extra_template_data[path]["additionalProperties"] = obj.additionalProperties
            if obj.additionalProperties is False and not self.target_python_version.has_typed_dict_closed:
                self.extra_template_data[path]["use_typeddict_backport"] = True
        elif isinstance(obj.additionalProperties, JsonSchemaObject):
            additional_props_type = self._build_lightweight_type(obj.additionalProperties)
            if additional_props_type:  # pragma: no branch
                self.extra_template_data[path]["additionalPropertiesType"] = additional_props_type.type_hint
                if not self.target_python_version.has_typed_dict_closed:  # pragma: no branch
                    self.extra_template_data[path]["use_typeddict_backport"] = True

    def set_unevaluated_properties(self, path: str, obj: JsonSchemaObject) -> None:
        """Set unevaluated properties flag in extra template data."""
        if isinstance(obj.unevaluatedProperties, bool):
            self.extra_template_data[path]["unevaluatedProperties"] = obj.unevaluatedProperties

    def set_title(self, path: str, obj: JsonSchemaObject) -> None:
        """Set title in extra template data."""
        if obj.title:
            self.extra_template_data[path]["title"] = obj.title

    def set_schema_id(self, path: str, obj: JsonSchemaObject) -> None:
        """Set $id in extra template data."""
        if obj.id:
            self.extra_template_data[path]["schema_id"] = obj.id

    def _set_schema_metadata(self, path: str, obj: JsonSchemaObject) -> None:
        """Set title, $id, additionalProperties and unevaluatedProperties in extra template data."""
        self.set_title(path, obj)
        self.set_schema_id(path, obj)
        self.set_additional_properties(path, obj)
        self.set_unevaluated_properties(path, obj)

    def set_schema_extensions(self, path: str, obj: JsonSchemaObject) -> None:
        """Set schema extensions (x-* fields) in extra template data."""
        extensions = {k: v for k, v in obj.extras.items() if k.startswith("x-")}
        if extensions:
            self.extra_template_data[path]["extensions"] = extensions

        if obj.extras.get("x-is-base-class"):
            self.extra_template_data[path]["is_base_class"] = True

        # Process model_extra_keys for json_schema_extra in ConfigDict
        if self.model_extra_keys or self.model_extra_keys_without_x_prefix:
            model_extras: dict[str, Any] = {}
            for k, v in obj.extras.items():
                if self.model_extra_keys and k in self.model_extra_keys:
                    model_extras[k] = v
                elif self.model_extra_keys_without_x_prefix and k in self.model_extra_keys_without_x_prefix:
                    # Strip the x- prefix
                    model_extras[k.lstrip("x-")] = v
            if model_extras:
                self.extra_template_data[path]["model_extras"] = model_extras

    def _get_python_type_flags(self, obj: JsonSchemaObject) -> dict[str, bool]:  # noqa: PLR6301
        """Get container type flags from x-python-type extension.

        Returns a dict with flags like is_set, is_frozen_set, is_mapping, is_sequence
        that can be passed to data_type() to override the default container type.

        Note: This is an instance method (not static) due to the snooper_to_methods
        class decorator which does not preserve staticmethod descriptors.
        """
        x_python_type = obj.extras.get("x-python-type")
        if not x_python_type or not isinstance(x_python_type, str):
            return {}

        type_to_flag: dict[str, dict[str, bool]] = {
            "Set": {"is_set": True},
            "set": {"is_set": True},
            "FrozenSet": {"is_frozen_set": True},
            "frozenset": {"is_frozen_set": True},
            "Mapping": {"is_mapping": True},
            "MutableMapping": {"is_mapping": True},
            "Sequence": {"is_sequence": True},
            "MutableSequence": {"is_sequence": True},
            "AbstractSet": {"is_frozen_set": True},
            "MutableSet": {"is_set": True},
        }

        base_type = get_type_base_name(x_python_type)
        if base_type in type_to_flag:
            return type_to_flag[base_type]

        if base_type in {"Union", "Optional"} or " | " in x_python_type:
            for arg in get_subscript_args(x_python_type):
                arg_base = get_type_base_name(arg)
                if arg_base in type_to_flag:
                    return type_to_flag[arg_base]

        return {}

    def _get_python_type_base(self, python_type: str) -> str:  # noqa: PLR6301
        """Extract base type from a Python type annotation string."""
        return get_type_base_name(python_type)

    def _is_compatible_python_type(self, schema_type: str | None, python_type: str) -> bool:
        """Check if x-python-type is compatible with the JSON Schema type."""
        base_type = self._get_python_type_base(python_type)
        if base_type in self.PYTHON_TYPE_OVERRIDE_ALWAYS:
            return False
        all_type_names = self._extract_all_type_names(python_type)
        if any(t in self.PYTHON_TYPE_OVERRIDE_ALWAYS for t in all_type_names):
            return False
        if " | " in python_type and schema_type is None:
            return False
        if schema_type is None:  # pragma: no cover
            return True
        if base_type in {"Union", "Optional"}:  # pragma: no cover
            return True
        compatible = self.COMPATIBLE_PYTHON_TYPES.get(schema_type, frozenset())
        return base_type in compatible

    def _extract_all_type_names(self, type_str: str) -> list[str]:  # noqa: PLR6301
        """Extract all type names from a type annotation string using AST parsing."""
        import ast  # noqa: PLC0415

        try:
            tree = ast.parse(type_str, mode="eval")
            return [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
        except SyntaxError:  # pragma: no cover
            # Fallback to regex for non-standard type strings
            pattern = r"(?<![.\w])([A-Za-z_]\w*)"
            return re.findall(pattern, type_str)

    @staticmethod
    @lru_cache(maxsize=256)
    def _resolve_type_import_dynamic(type_name: str) -> Import | None:
        """Dynamically resolve import for a type name from known modules."""
        modules_to_check = (
            "typing",
            "collections.abc",
            "collections",
            "pathlib",
            "decimal",
            "uuid",
            "datetime",
            "enum",
            "re",
        )
        for module_name in modules_to_check:
            with suppress(ImportError):
                module = importlib.import_module(module_name)
                if hasattr(module, type_name):
                    return Import.from_full_path(f"{module_name}.{type_name}")
        return None

    def _resolve_type_import(self, type_name: str) -> Import | None:
        """Resolve import for a type name, with dynamic fallback."""
        if type_name in self.PYTHON_TYPE_IMPORTS:
            return self.PYTHON_TYPE_IMPORTS[type_name]
        return self._resolve_type_import_dynamic(type_name)

    def _resolve_type_import_from_defs(self, type_name: str) -> Import | None:
        """Resolve import for a type name from $defs with x-python-import."""
        try:
            ref_schema = self._load_ref_schema_object(f"#/$defs/{type_name}")
            x_python_import = ref_schema.extras.get("x-python-import")
            if isinstance(x_python_import, dict):
                module = x_python_import.get("module")
                name = x_python_import.get("name")
                if module and name:  # pragma: no branch
                    return Import.from_full_path(f"{module}.{name}")
        except Exception:  # noqa: BLE001, S110
            pass
        return None

    def _get_python_type_override(self, obj: JsonSchemaObject) -> DataType | None:
        """Get DataType from x-python-type if it's incompatible with schema type."""
        x_python_type = obj.extras.get("x-python-type")
        if not x_python_type or not isinstance(x_python_type, str):
            return None

        schema_type = obj.type if isinstance(obj.type, str) else None
        if self._is_compatible_python_type(schema_type, x_python_type):
            return None

        base_type = self._get_python_type_base(x_python_type)
        import_ = self._resolve_type_import(base_type)

        # Convert fully qualified path to short name when import is added
        type_str = x_python_type
        prefix = x_python_type.split("[", maxsplit=1)[0]
        if "." in prefix:
            # Replace the fully qualified prefix with just the base type name
            type_str = base_type + x_python_type[len(prefix) :]
            if not import_:
                # If not in predefined imports, create import from the full path
                import_ = Import.from_full_path(prefix)

        # Collect imports for qualified names (e.g., module.path.ClassName)
        nested_imports: list[DataType] = []
        for qualified_name in extract_qualified_names(type_str):
            class_name = qualified_name.rsplit(".", 1)[-1]
            nested_import = self._resolve_type_import(class_name) or Import.from_full_path(qualified_name)
            nested_imports.append(self.data_type(import_=nested_import))
            type_str = type_str.replace(qualified_name, class_name)

        # Collect imports for all nested types (e.g., Iterable inside Callable[[Iterable[str]], str])
        for type_name in self._extract_all_type_names(type_str):
            if type_name != base_type:
                nested_import = self._resolve_type_import(type_name) or self._resolve_type_import_from_defs(type_name)
                if nested_import:
                    nested_imports.append(self.data_type(import_=nested_import))

        result = self.data_type(type=type_str, import_=import_)
        if nested_imports:
            result.data_types.extend(nested_imports)
        return result

    def _apply_title_as_name(self, name: str, obj: JsonSchemaObject) -> str:
        """Apply title as name if use_title_as_name is enabled."""
        if self.use_title_as_name and obj.title:
            return sanitize_module_name(obj.title, treat_dot_as_module=self.treat_dot_as_module)
        return name

    def _deep_merge(self, dict1: dict[Any, Any], dict2: dict[Any, Any]) -> dict[Any, Any]:
        """Deep merge two dictionaries, combining nested dicts and lists."""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(result[key], value)
                    continue
                if isinstance(result[key], list) and isinstance(value, list):
                    result[key] = result[key] + value  # noqa: PLR6104
                    continue
            result[key] = value
        return result

    def _load_ref_schema_object(self, ref: str) -> JsonSchemaObject:
        """Load a JsonSchemaObject from a $ref using standard resolve/load pipeline."""
        resolved_ref = self.model_resolver.resolve_ref(ref)
        file_part, fragment = ([*resolved_ref.split("#", 1), ""])[:2]
        raw_doc = self._get_ref_body(file_part) if file_part else self.raw_obj

        target_schema: dict[str, YamlValue] | YamlValue = raw_doc
        if fragment:
            pointer = [p for p in fragment.split("/") if p]
            target_schema = get_model_by_path(raw_doc, pointer)

        return model_validate(self.SCHEMA_OBJECT_TYPE, target_schema)

    def _build_anchor_indexes(self, obj: JsonSchemaObject, path: list[str]) -> None:
        """Build $recursiveAnchor and $dynamicAnchor indexes for a schema object."""
        root_key = tuple(self.model_resolver.current_root)
        root_len = len(root_key)
        if root_len < len(path):
            suffix_parts = path[root_len:]
            # Strip leading '#' from fragment markers (e.g. '#/$defs' -> '$defs')
            first = suffix_parts[0]
            if first.startswith("#"):
                suffix_parts = [first[1:].lstrip("/"), *suffix_parts[1:]]
            ref_path = "#/" + "/".join(suffix_parts)
        else:
            ref_path = "#"
        if obj.recursiveAnchor:
            self._recursive_anchor_index.setdefault(root_key, []).append(ref_path)
        if obj.dynamicAnchor:
            self._dynamic_anchor_index.setdefault(root_key, {}).setdefault(obj.dynamicAnchor, ref_path)

    def _resolve_recursive_ref(self, item: JsonSchemaObject, path: list[str]) -> str | None:
        """Resolve $recursiveRef to an equivalent $ref.

        Per JSON Schema 2019-09, $recursiveRef only allows "#" as value.
        Resolves to the nearest enclosing schema with $recursiveAnchor: true.
        For standalone JSON Schema files, this is the root "#".
        For OpenAPI, this is the component schema definition path.
        """
        if item.recursiveRef != "#":  # pragma: no cover
            return None
        root_key = tuple(self.model_resolver.current_root)
        anchors = self._recursive_anchor_index.get(root_key, [])
        if not anchors:
            return "#"
        # Build root-relative path for comparison
        root_len = len(root_key)
        if root_len < len(path):
            suffix_parts = path[root_len:]
            first = suffix_parts[0]
            if first.startswith("#"):
                suffix_parts = [first[1:].lstrip("/"), *suffix_parts[1:]]
            current_ref = "#/" + "/".join(suffix_parts)
        else:
            current_ref = "#"  # pragma: no cover
        # Find the best matching anchor: path prefix with longest match
        # best defaults to "#" (root anchor fallback)
        best = "#"
        best_len = 0
        for anchor_ref in anchors:
            if anchor_ref != "#" and (
                len(anchor_ref) > best_len
                and current_ref.startswith(anchor_ref)
                and (len(current_ref) == len(anchor_ref) or current_ref[len(anchor_ref)] == "/")
            ):
                best = anchor_ref
                best_len = len(anchor_ref)
        return best

    def _resolve_dynamic_ref(self, item: JsonSchemaObject) -> str | None:
        """Resolve $dynamicRef to an equivalent $ref.

        Per JSON Schema 2020-12:
        1. Resolve the URI like $ref first (fallback behavior)
        2. If target has $dynamicAnchor, override with outermost matching anchor

        In code generation, dynamic scope is resolved statically via index lookup.
        """
        ref = item.dynamicRef
        if not ref:  # pragma: no cover
            return None
        if ref.startswith("#"):
            anchor_name = ref[1:]
            root_key = tuple(self.model_resolver.current_root)
            anchor_map = self._dynamic_anchor_index.get(root_key, {})
            if anchor_name in anchor_map:
                return anchor_map[anchor_name]
            return ref  # pragma: no cover
        return ref  # pragma: no cover

    def _merge_ref_with_schema(self, obj: JsonSchemaObject) -> JsonSchemaObject:
        """Merge $ref schema with current schema's additional keywords.

        JSON Schema 2020-12 allows $ref alongside other keywords,
        which should be merged together.

        The local keywords take precedence over referenced schema.
        """
        if not obj.ref:
            return obj

        ref_schema = self._load_ref_schema_object(obj.ref)
        ref_dict = model_dump(ref_schema, exclude_unset=True, by_alias=True)
        current_dict = model_dump(obj, exclude={"ref"}, exclude_unset=True, by_alias=True)
        merged = self._deep_merge(ref_dict, current_dict)
        merged.pop("$ref", None)

        return model_validate(self.SCHEMA_OBJECT_TYPE, merged)

    def _merge_primitive_schemas(self, items: list[JsonSchemaObject]) -> JsonSchemaObject:
        """Merge multiple primitive schemas by computing the intersection of their constraints."""
        if len(items) == 1:
            return items[0]

        base_dict: dict[str, Any] = {}
        for item in items:  # pragma: no branch
            if item.type:  # pragma: no branch
                base_dict = model_dump(item, exclude_unset=True, by_alias=True)
                break

        for item in items:
            for field in JsonSchemaObject.__constraint_fields__:
                value = getattr(item, field, None)
                if value is None:
                    value = item.extras.get(field)
                if value is not None:
                    if field not in base_dict or base_dict[field] is None:
                        base_dict[field] = value
                    else:
                        base_dict[field] = JsonSchemaParser._intersect_constraint(field, base_dict[field], value)

        return model_validate(self.SCHEMA_OBJECT_TYPE, base_dict)

    def _merge_primitive_schemas_for_allof(self, items: list[JsonSchemaObject]) -> JsonSchemaObject | None:
        """Merge primitive schemas for allOf, respecting allof_merge_mode setting."""
        if len(items) == 1:
            return items[0]  # pragma: no cover

        formats = {item.format for item in items if item.format}
        if len(formats) > 1:
            return None

        merged_format = formats.pop() if formats else None

        if self.allof_merge_mode != AllOfMergeMode.NoMerge:
            merged = self._merge_primitive_schemas(items)
            merged_dict = model_dump(merged, exclude_unset=True, by_alias=True)
            if merged_format:
                merged_dict["format"] = merged_format
            return model_validate(self.SCHEMA_OBJECT_TYPE, merged_dict)

        base_dict: dict[str, Any] = {}
        for item in items:
            if item.type:
                base_dict = model_dump(item, exclude_unset=True, by_alias=True)
                break

        for item in items:
            for constraint_field in JsonSchemaObject.__constraint_fields__:
                value = getattr(item, constraint_field, None)
                if value is None:
                    value = item.extras.get(constraint_field)
                if value is not None:
                    base_dict[constraint_field] = value

        if merged_format:
            base_dict["format"] = merged_format

        return model_validate(self.SCHEMA_OBJECT_TYPE, base_dict)

    @staticmethod
    def _intersect_constraint(field: str, val1: Any, val2: Any) -> Any:  # noqa: PLR0911
        """Compute the intersection of two constraint values."""
        v1: float | None = None
        v2: float | None = None
        with suppress(TypeError, ValueError):
            v1 = float(val1) if val1 is not None else None
            v2 = float(val2) if val2 is not None else None

        if field in {"minLength", "minimum", "exclusiveMinimum", "minItems"}:
            if v1 is not None and v2 is not None:
                return val1 if v1 >= v2 else val2
            return val1  # pragma: no cover
        if field in {"maxLength", "maximum", "exclusiveMaximum", "maxItems"}:
            if v1 is not None and v2 is not None:
                return val1 if v1 <= v2 else val2
            return val1  # pragma: no cover
        if field == "pattern":
            return f"(?={val1})(?={val2})" if val1 != val2 else val1
        if field == "uniqueItems":
            return val1 or val2
        return val1

    def _build_allof_type(  # noqa: PLR0911, PLR0912
        self,
        allof_items: list[JsonSchemaObject],
        depth: int,
        visited: frozenset[int],
        max_depth: int,
        max_union_elements: int,
    ) -> DataType | None:
        """Build a DataType from allOf schema items."""
        if len(allof_items) == 1:
            item = allof_items[0]
            if item.ref:
                return self.get_ref_data_type(item.ref)
            return self._build_lightweight_type(item, depth + 1, visited, max_depth, max_union_elements)

        ref_items: list[JsonSchemaObject] = []
        primitive_items: list[JsonSchemaObject] = []
        constraint_only_items: list[JsonSchemaObject] = []
        object_items: list[JsonSchemaObject] = []

        for item in allof_items:
            if item.ref:
                ref_items.append(item)
            elif item.type and item.type != "object" and not isinstance(item.type, list):
                primitive_items.append(item)
            elif item.properties or item.additionalProperties or item.type == "object":
                object_items.append(item)
            elif item.allOf or item.anyOf or item.oneOf:
                nested_type = self._build_lightweight_type(item, depth + 1, visited, max_depth, max_union_elements)
                if nested_type is None:  # pragma: no cover
                    return None
                if nested_type.reference:  # pragma: no cover
                    ref_items.append(item)
                else:
                    primitive_items.append(item)
            elif item.enum:  # pragma: no cover
                primitive_items.append(item)
            elif item.has_constraint:
                constraint_only_items.append(item)

        if ref_items and not primitive_items and not object_items:
            ref = ref_items[0].ref
            if ref:
                return self.get_ref_data_type(ref)
            return None  # pragma: no cover

        if ref_items and (primitive_items or object_items or constraint_only_items):
            ignored_count = len(primitive_items) + len(constraint_only_items)
            if ignored_count > 0:  # pragma: no branch
                warn(
                    f"allOf combines $ref with {ignored_count} constraint(s) that will be ignored "
                    f"in inherited field type resolution. Consider defining constraints in the referenced schema.",
                    stacklevel=4,
                )
            ref = ref_items[0].ref
            if ref:
                return self.get_ref_data_type(ref)
            return None  # pragma: no cover

        if primitive_items and not object_items:
            all_primitives = primitive_items + constraint_only_items
            merged_schema = self._merge_primitive_schemas(all_primitives)
            return self._build_lightweight_type(merged_schema, depth + 1, visited, max_depth, max_union_elements)

        if object_items:
            additional_props_types: list[DataType] = []

            for obj_item in object_items:
                if isinstance(obj_item.additionalProperties, JsonSchemaObject):
                    ap_type = self._build_lightweight_type(
                        obj_item.additionalProperties, depth + 1, visited, max_depth, max_union_elements
                    )
                    if ap_type:
                        additional_props_types.append(ap_type)

            if additional_props_types:
                best_type = additional_props_types[0]
                for ap_type in additional_props_types[1:]:  # pragma: no branch
                    is_better = best_type.type == ANY and ap_type.type != ANY
                    is_better = is_better or (ap_type.reference and not best_type.reference)
                    if is_better:  # pragma: no cover
                        best_type = ap_type
                return self.data_type(data_types=[best_type], is_dict=True)

            return self.data_type(data_types=[DataType(type=ANY, import_=IMPORT_ANY)], is_dict=True)

        return None

    def _build_lightweight_type(  # noqa: PLR0911, PLR0912
        self,
        schema: JsonSchemaObject,
        depth: int = 0,
        visited: frozenset[int] | None = None,
        max_depth: int = 3,
        max_union_elements: int = 5,
    ) -> DataType | None:
        """Build a DataType from schema without generating models."""
        if depth > max_depth:  # pragma: no cover
            return None
        if visited is None:
            visited = frozenset()

        schema_id = id(schema)
        if schema_id in visited:  # pragma: no cover
            return None
        visited |= {schema_id}

        if schema.ref:
            return self.get_ref_data_type(schema.ref)

        if schema.enum:  # pragma: no cover
            return self.get_data_type(schema)

        if schema.is_array and schema.items and isinstance(schema.items, JsonSchemaObject):
            if schema.items.ref:
                item_type = self.get_ref_data_type(schema.items.ref)
            else:
                item_type = self._build_lightweight_type(
                    schema.items, depth + 1, visited, max_depth, max_union_elements
                )
                if item_type is None:  # pragma: no cover
                    item_type = DataType(type=ANY, import_=IMPORT_ANY)
            return self.data_type(data_types=[item_type], is_list=True)

        if schema.type and not isinstance(schema.type, list) and schema.type != "object":
            return self.get_data_type(schema)
        if isinstance(schema.type, list):
            return self.get_data_type(schema)

        combined_items = schema.anyOf or schema.oneOf
        if combined_items:
            if len(combined_items) > max_union_elements:  # pragma: no cover
                return None
            data_types: list[DataType] = []
            for item in combined_items:
                if item.ref:  # pragma: no cover
                    data_types.append(self.get_ref_data_type(item.ref))
                else:
                    item_type = self._build_lightweight_type(item, depth + 1, visited, max_depth, max_union_elements)
                    if item_type is None:  # pragma: no cover
                        return None
                    data_types.append(item_type)
            if len(data_types) == 1:  # pragma: no cover
                return data_types[0]
            return self.data_type(data_types=data_types)

        if schema.allOf:  # pragma: no cover
            return self._build_allof_type(schema.allOf, depth, visited, max_depth, max_union_elements)

        if isinstance(schema.additionalProperties, JsonSchemaObject):  # pragma: no cover
            value_type = self._build_lightweight_type(
                schema.additionalProperties, depth + 1, visited, max_depth, max_union_elements
            )
            if value_type is None:
                value_type = DataType(type=ANY, import_=IMPORT_ANY)
            return self.data_type(data_types=[value_type], is_dict=True)

        if schema.properties or schema.type == "object":
            return self.data_type(data_types=[DataType(type=ANY, import_=IMPORT_ANY)], is_dict=True)

        return None

    def _is_list_with_any_item_type(self, data_type: DataType | None) -> bool:  # noqa: PLR6301
        """Return True when data_type represents List[Any] (including nested lists)."""
        if not data_type:  # pragma: no cover
            return False

        candidate = data_type
        if not candidate.is_list and len(candidate.data_types) == 1 and candidate.data_types[0].is_list:
            candidate = candidate.data_types[0]

        if not candidate.is_list or len(candidate.data_types) != 1:
            return False

        item_type = candidate.data_types[0]
        while len(item_type.data_types) == 1:
            inner = item_type.data_types[0]
            if (not item_type.is_list and inner.is_list) or item_type.is_list:
                item_type = inner
            else:
                break
        return item_type.type == ANY

    def _merge_property_schemas(self, parent_dict: dict[str, Any], child_dict: dict[str, Any]) -> dict[str, Any]:
        """Merge parent and child property schemas for allOf."""
        if self.allof_merge_mode == AllOfMergeMode.NoMerge:
            return child_dict.copy()

        non_merged_fields: set[str] = set()
        if self.allof_merge_mode == AllOfMergeMode.Constraints:
            non_merged_fields = {"default", "examples", "example"}

        result = {key: value for key, value in parent_dict.items() if key not in non_merged_fields}

        for key, value in child_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                if "$ref" in value:
                    result[key] = value
                else:
                    result[key] = self._merge_property_schemas(result[key], value)
            else:
                result[key] = value
        return result

    def _merge_properties_with_parent_constraints(
        self, child_obj: JsonSchemaObject, parent_refs: list[str]
    ) -> JsonSchemaObject:
        """Merge child properties with parent property constraints for allOf inheritance."""
        if not child_obj.properties:
            return child_obj

        parent_properties: dict[str, JsonSchemaObject] = {}
        for ref in parent_refs:
            try:
                parent_schema = self._load_ref_schema_object(ref)
            except Exception:  # pragma: no cover  # noqa: BLE001, S112
                continue
            if parent_schema.properties:
                for prop_name, prop_schema in parent_schema.properties.items():
                    if isinstance(prop_schema, JsonSchemaObject) and prop_name not in parent_properties:
                        parent_properties[prop_name] = prop_schema

        if not parent_properties:
            return child_obj

        merged_properties: dict[str, JsonSchemaObject | bool] = {}
        for prop_name, child_prop in child_obj.properties.items():
            if not isinstance(child_prop, JsonSchemaObject):
                merged_properties[prop_name] = child_prop
                continue

            parent_prop = parent_properties.get(prop_name)
            if parent_prop is None:
                merged_properties[prop_name] = child_prop
                continue

            parent_dict = model_dump(parent_prop, exclude_unset=True, by_alias=True)
            child_dict = model_dump(child_prop, exclude_unset=True, by_alias=True)
            merged_dict = self._merge_property_schemas(parent_dict, child_dict)
            merged_properties[prop_name] = model_validate(self.SCHEMA_OBJECT_TYPE, merged_dict)

        merged_obj_dict = model_dump(child_obj, exclude_unset=True, by_alias=True)
        merged_obj_dict["properties"] = {
            k: model_dump(v, exclude_unset=True, by_alias=True) if isinstance(v, JsonSchemaObject) else v
            for k, v in merged_properties.items()
        }
        return model_validate(self.SCHEMA_OBJECT_TYPE, merged_obj_dict)

    def _get_inherited_field_type(  # noqa: PLR0912
        self, prop_name: str, base_classes: list[Reference], visited: frozenset[str] | None = None
    ) -> DataType | None:
        """Get the data type for an inherited property from parent schemas.

        Recursively traverses the inheritance chain when a parent property
        doesn't have type information but the parent itself inherits from another schema.
        """
        if visited is None:
            visited = frozenset()

        for base in base_classes:
            if not base.path:  # pragma: no cover
                continue
            if base.path in visited:  # pragma: no cover
                continue
            visited |= {base.path}

            if "#" in base.path:
                file_part, fragment = base.path.split("#", 1)
                ref = f"{file_part}#{fragment}" if file_part else f"#{fragment}"
            else:  # pragma: no cover
                ref = f"#{base.path}"
            try:
                parent_schema = self._load_ref_schema_object(ref)
            except Exception:  # pragma: no cover  # noqa: BLE001, S112
                continue

            result: DataType | None = None
            if parent_schema.properties:
                prop_schema = parent_schema.properties.get(prop_name)
                if isinstance(prop_schema, JsonSchemaObject):
                    result = self._build_lightweight_type(prop_schema)
            # In case of a missing type, continue searching up the inheritance chain
            if result is not None and not (result.type == ANY or self._is_list_with_any_item_type(result)):
                return result

            parent_result: DataType | None = None
            if parent_schema.allOf:
                grandparent_refs = [self.model_resolver.add_ref(item.ref) for item in parent_schema.allOf if item.ref]
                if grandparent_refs:
                    parent_result = self._get_inherited_field_type(prop_name, grandparent_refs, visited)
                    if parent_result is not None:
                        return parent_result
                    return result

        return None

    def _schema_signature(self, prop_schema: JsonSchemaObject | bool) -> str | bool:  # noqa: FBT001, PLR6301
        """Normalize property schema for comparison across allOf items."""
        if isinstance(prop_schema, bool):
            return prop_schema
        return json.dumps(model_dump(prop_schema, exclude_unset=True, by_alias=True), sort_keys=True, default=repr)

    def _is_root_model_schema(self, obj: JsonSchemaObject) -> bool:  # noqa: PLR0911
        """Check if schema represents a root model (primitive type with constraints).

        Based on parse_raw_obj() else branch conditions. Returns True when
        the schema would be processed by parse_root_type().
        """
        if obj.is_array:
            return False
        if obj.allOf or obj.oneOf or obj.anyOf:
            return False
        if obj.properties:
            return False
        if obj.patternProperties:
            return False
        if obj.propertyNames:
            return False
        if obj.type == "object":
            return False
        return not obj.enum or self.ignore_enum_constraints

    def _handle_allof_root_model_with_constraints(  # noqa: PLR0911, PLR0912
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> DataType | None:
        """Handle allOf that combines a root model $ref with additional constraints.

        This handler is for generating a root model from a root model reference.
        Object inheritance (with properties) is handled by existing _parse_all_of_item() path.
        Only applies to named schema definitions, not inline properties.
        """
        for path_element in path:
            if SPECIAL_PATH_MARKER in path_element:
                return None  # pragma: no cover

        ref_items = [item for item in obj.allOf if item.ref]

        if len(ref_items) != 1:
            return None

        ref_item = ref_items[0]
        ref_value = ref_item.ref
        if ref_value is None:
            return None  # pragma: no cover

        if ref_item.has_ref_with_schema_keywords and not ref_item.is_ref_with_nullable_only:
            ref_schema = self._merge_ref_with_schema(ref_item)
        else:
            ref_schema = self._load_ref_schema_object(ref_value)

        if not self._is_root_model_schema(ref_schema):
            return None

        constraint_items: list[JsonSchemaObject] = []
        for item in obj.allOf:
            if item.ref:
                continue
            if item.properties or item.items:
                return None
            if item.has_constraint or item.type or item.format:
                if item.type and ref_schema.type:
                    compatible_type_pairs = {
                        ("integer", "number"),
                        ("number", "integer"),
                    }
                    if item.type != ref_schema.type and (item.type, ref_schema.type) not in compatible_type_pairs:
                        return None
                constraint_items.append(item)

        if not constraint_items:
            return None

        all_items = [ref_schema, *constraint_items]
        merged_schema = self._merge_primitive_schemas_for_allof(all_items)
        if merged_schema is None:
            return None

        if obj.description:
            merged_dict = model_dump(merged_schema, exclude_unset=True, by_alias=True)
            merged_dict["description"] = obj.description
            merged_schema = model_validate(self.SCHEMA_OBJECT_TYPE, merged_dict)

        return self.parse_root_type(name, merged_schema, path)

    def _merge_all_of_object(self, obj: JsonSchemaObject) -> JsonSchemaObject | None:
        """Merge allOf items when they share object properties to avoid duplicate models.

        Skip merging when there is exactly one $ref (inheritance with property overrides).
        Continue merging when multiple $refs have conflicting property definitions to avoid MRO issues.
        Child property overrides (obj.properties) are not considered conflicts.
        """
        if self.allof_class_hierarchy == AllOfClassHierarchy.Always:
            # Skip merging when always inherit from the base classes
            return None

        ref_count = sum(1 for item in obj.allOf if item.ref)
        if ref_count == 1:
            return None

        resolved_items: list[JsonSchemaObject] = []
        property_signatures: dict[str, set[str | bool]] = {}
        for item in obj.allOf:
            resolved_item = self._load_ref_schema_object(item.ref) if item.ref else item
            resolved_items.append(resolved_item)
            if resolved_item.properties:
                for prop_name, prop_schema in resolved_item.properties.items():
                    property_signatures.setdefault(prop_name, set()).add(self._schema_signature(prop_schema))

        if not any(len(signatures) > 1 for signatures in property_signatures.values()):
            return None

        merged_schema: dict[str, Any] = model_dump(obj, exclude={"allOf"}, exclude_unset=True, by_alias=True)
        for resolved_item in resolved_items:
            merged_schema = self._deep_merge(
                merged_schema, model_dump(resolved_item, exclude_unset=True, by_alias=True)
            )

        if "required" in merged_schema and isinstance(merged_schema["required"], list):
            merged_schema["required"] = list(dict.fromkeys(merged_schema["required"]))

        merged_schema.pop("allOf", None)
        return model_validate(self.SCHEMA_OBJECT_TYPE, merged_schema)

    def parse_combined_schema(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        target_attribute_name: str,
    ) -> list[DataType]:
        """Parse combined schema (anyOf, oneOf, allOf) into a list of data types."""
        base_object = model_dump(obj, exclude={target_attribute_name, "title"}, exclude_unset=True, by_alias=True)
        combined_schemas: list[JsonSchemaObject] = []
        refs = []
        for index, target_attribute in enumerate(getattr(obj, target_attribute_name, [])):
            if target_attribute.ref:
                if target_attribute.has_ref_with_schema_keywords and not target_attribute.is_ref_with_nullable_only:
                    merged_attr = self._merge_ref_with_schema(target_attribute)
                    combined_schemas.append(
                        model_validate(
                            self.SCHEMA_OBJECT_TYPE,
                            self._deep_merge(base_object, model_dump(merged_attr, exclude_unset=True, by_alias=True)),
                        )
                    )
                else:
                    combined_schemas.append(target_attribute)
                    refs.append(index)
            else:
                combined_schemas.append(
                    model_validate(
                        self.SCHEMA_OBJECT_TYPE,
                        self._deep_merge(
                            base_object,
                            model_dump(target_attribute, exclude_unset=True, by_alias=True),
                        ),
                    )
                )

        parsed_schemas = self.parse_list_item(
            name,
            combined_schemas,
            path,
            obj,
            singular_name=False,
        )
        common_path_keyword = f"{target_attribute_name}Common"
        return [
            self._parse_object_common_part(
                name,
                obj,
                [*get_special_path(common_path_keyword, path), str(i)],
                ignore_duplicate_model=True,
                fields=[],
                base_classes=[d.reference],
                required=[],
            )
            if i in refs and d.reference
            else d
            for i, d in enumerate(parsed_schemas)
        ]

    def parse_any_of(self, name: str, obj: JsonSchemaObject, path: list[str]) -> list[DataType]:
        """Parse anyOf schema into a list of data types."""
        return self.parse_combined_schema(name, obj, path, "anyOf")

    def parse_one_of(self, name: str, obj: JsonSchemaObject, path: list[str]) -> list[DataType]:
        """Parse oneOf schema into a list of data types."""
        return self.parse_combined_schema(name, obj, path, "oneOf")

    def _create_data_model(self, model_type: type[DataModel] | None = None, **kwargs: Any) -> DataModel:
        """Create data model instance with dataclass_arguments support for DataClass."""
        # Add class decorators if not already provided
        if "decorators" not in kwargs and self.class_decorators:
            kwargs["decorators"] = list(self.class_decorators)
        data_model_class = model_type or self.data_model_type
        if issubclass(data_model_class, (DataClass, PydanticV2DataClass)):
            # Use dataclass_arguments from kwargs, or fall back to self.dataclass_arguments
            # If both are None, construct from legacy frozen_dataclasses/keyword_only flags
            dataclass_arguments = kwargs.pop("dataclass_arguments", None)
            if dataclass_arguments is None:
                dataclass_arguments = self.dataclass_arguments
            if dataclass_arguments is None:
                # Construct from legacy flags for library API compatibility
                dataclass_arguments = {}
                if self.frozen_dataclasses:
                    dataclass_arguments["frozen"] = True
                if self.keyword_only:
                    dataclass_arguments["kw_only"] = True
            kwargs["dataclass_arguments"] = dataclass_arguments
            kwargs.pop("frozen", None)
            kwargs.pop("keyword_only", None)
        else:
            kwargs.pop("dataclass_arguments", None)
        return data_model_class(**kwargs)

    def _parse_object_common_part(  # noqa: PLR0912, PLR0913, PLR0915
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        *,
        ignore_duplicate_model: bool,
        fields: list[DataModelFieldBase],
        base_classes: list[Reference],
        required: list[str],
    ) -> DataType:
        if self.read_only_write_only_model_type is not None and obj.properties:
            for prop in obj.properties.values():
                if isinstance(prop, JsonSchemaObject) and prop.ref:
                    self._load_ref_schema_object(prop.ref)
        if obj.properties:
            fields.extend(
                self.parse_object_fields(
                    obj,
                    path,
                    get_module_name(name, None, treat_dot_as_module=self.treat_dot_as_module),
                    class_name=name,
                )
            )
        if base_classes:
            for field in fields:
                current_type = field.data_type
                field_name = field.original_name or field.name
                if current_type and current_type.type == ANY and field_name:
                    inherited_type = self._get_inherited_field_type(field_name, base_classes)
                    if inherited_type is not None:
                        new_type = model_copy(inherited_type, deep=True)
                        new_type.is_optional = new_type.is_optional or current_type.is_optional
                        new_type.is_dict = new_type.is_dict or current_type.is_dict
                        new_type.is_list = new_type.is_list or current_type.is_list
                        new_type.is_set = new_type.is_set or current_type.is_set
                        if new_type.kwargs is None and current_type.kwargs is not None:  # pragma: no cover
                            new_type.kwargs = current_type.kwargs
                        field.data_type = new_type
                # Handle List[Any] case: inherit item type from parent if items have Any type
                elif field_name and self._is_list_with_any_item_type(current_type):
                    inherited_type = self._get_inherited_field_type(field_name, base_classes)
                    if inherited_type is None or not inherited_type.is_list or not inherited_type.data_types:
                        continue

                    new_type = model_copy(inherited_type, deep=True)

                    # Preserve modifiers coming from the overriding schema.
                    if current_type is not None:  # pragma: no branch
                        new_type.is_optional = new_type.is_optional or current_type.is_optional
                        new_type.is_dict = new_type.is_dict or current_type.is_dict
                        new_type.is_list = new_type.is_list or current_type.is_list
                        new_type.is_set = new_type.is_set or current_type.is_set
                        if new_type.kwargs is None and current_type.kwargs is not None:  # pragma: no cover
                            new_type.kwargs = current_type.kwargs

                    # Some code paths represent the list type inside an outer container.
                    is_wrapped = (
                        current_type is not None
                        and not current_type.is_list
                        and len(current_type.data_types) == 1
                        and current_type.data_types[0].is_list
                    )
                    if is_wrapped:
                        wrapper = model_copy(current_type, deep=True)
                        wrapper.data_types[0] = new_type
                        field.data_type = wrapper
                        continue

                    field.data_type = new_type  # pragma: no cover
        # ignore an undetected object
        if ignore_duplicate_model and not fields and len(base_classes) == 1:
            with self.model_resolver.current_base_path_context(self.model_resolver._base_path):  # noqa: SLF001
                self.model_resolver.delete(path)
                return self.data_type(reference=base_classes[0])
        if required:
            for field in fields:
                if self.force_optional_for_required_fields or (  # pragma: no cover
                    self.apply_default_values_for_required_fields and field.has_default
                ):
                    continue  # pragma: no cover
                if (field.original_name or field.name) in required:
                    field.required = True
        if obj.required:
            field_name_to_field = {f.original_name or f.name: f for f in fields}
            for required_ in obj.required:
                if required_ in field_name_to_field:
                    field = field_name_to_field[required_]
                    if self.force_optional_for_required_fields or (
                        self.apply_default_values_for_required_fields and field.has_default
                    ):
                        continue
                    field.required = True
                else:
                    fields.append(
                        self.data_model_field_type(required=True, original_name=required_, data_type=DataType())
                    )
        name = self._apply_title_as_name(name, obj)  # pragma: no cover
        reference = self.model_resolver.add(path, name, class_name=True, loaded=True)
        self.set_additional_properties(reference.path, obj)
        self.set_unevaluated_properties(reference.path, obj)
        self.set_schema_id(reference.path, obj)
        self.set_schema_extensions(reference.path, obj)

        generates_separate = self._should_generate_separate_models(fields, base_classes)
        if generates_separate:
            self._create_request_response_models(
                name=reference.name,
                obj=obj,
                path=path,
                fields=fields,
                data_model_type_class=self.data_model_type,
                base_classes=base_classes,
            )

        # Generate base model if needed
        if self._should_generate_base_model(generates_separate_models=generates_separate):
            data_model_type = self._create_data_model(
                reference=reference,
                fields=fields,
                base_classes=base_classes,
                custom_base_class=self._resolve_base_class(reference.name, obj.custom_base_path),
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                path=self.current_source_path,
                description=obj.description if self.use_schema_description else None,
                keyword_only=self.keyword_only,
                treat_dot_as_module=self.treat_dot_as_module,
                dataclass_arguments=self.dataclass_arguments,
            )
            self.results.append(data_model_type)

        return self.data_type(reference=reference)

    def _parse_all_of_item(  # noqa: PLR0912, PLR0913, PLR0915, PLR0917
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        fields: list[DataModelFieldBase],
        base_classes: list[Reference],
        required: list[str],
        union_models: list[Reference],
    ) -> None:
        parent_refs = [item.ref for item in obj.allOf if item.ref]

        for all_of_item in obj.allOf:  # noqa: PLR1702
            if all_of_item.ref:  # $ref
                ref_schema = self._load_ref_schema_object(all_of_item.ref)

                if ref_schema.oneOf or ref_schema.anyOf:
                    self.model_resolver.add(path, name, class_name=True, loaded=True)
                    if ref_schema.anyOf:
                        union_models.extend(
                            d.reference for d in self.parse_any_of(name, ref_schema, path) if d.reference
                        )
                    if ref_schema.oneOf:
                        union_models.extend(
                            d.reference for d in self.parse_one_of(name, ref_schema, path) if d.reference
                        )
                else:
                    ref = self.model_resolver.add_ref(all_of_item.ref)
                    if ref.path not in {b.path for b in base_classes}:
                        base_classes.append(ref)
                        self.extra_template_data[ref.path]["is_base_class"] = True
            else:
                # Merge child properties with parent constraints before processing
                merged_item = self._merge_properties_with_parent_constraints(all_of_item, parent_refs)
                module_name = get_module_name(name, None, treat_dot_as_module=self.treat_dot_as_module)
                object_fields = self.parse_object_fields(
                    merged_item,
                    path,
                    module_name,
                    class_name=name,
                )

                if object_fields:
                    fields.extend(object_fields)
                    if all_of_item.required:
                        required.extend(all_of_item.required)
                        field_names: set[str] = set()
                        for f in object_fields:
                            if f.original_name:
                                field_names.add(f.original_name)
                            elif f.name:  # pragma: no cover
                                field_names.add(f.name)
                        existing_field_names: set[str] = set()
                        for f in fields:
                            if f.original_name:
                                existing_field_names.add(f.original_name)
                            elif f.name:  # pragma: no cover
                                existing_field_names.add(f.name)
                        for request in all_of_item.required:
                            if request in field_names or request in existing_field_names:
                                continue
                            if self.force_optional_for_required_fields:
                                continue
                            field_name, alias = self.model_resolver.get_valid_field_name_and_alias(
                                request,
                                excludes=existing_field_names,
                                model_type=self.field_name_model_type,
                                class_name=name,
                            )
                            data_type = self._get_inherited_field_type(request, base_classes)
                            if data_type is None:
                                data_type = DataType(type=ANY, import_=IMPORT_ANY)
                            # Handle multiple aliases (Pydantic v2 AliasChoices)
                            single_alias: str | None = None
                            validation_aliases: list[str] | None = None
                            if isinstance(alias, list):
                                validation_aliases = alias
                            else:
                                single_alias = alias
                            fields.append(
                                self.data_model_field_type(
                                    name=field_name,
                                    required=True,
                                    original_name=request,
                                    alias=single_alias,
                                    validation_aliases=validation_aliases,
                                    data_type=data_type,
                                    use_serialization_alias=self.use_serialization_alias,
                                )
                            )
                            existing_field_names.update({request, field_name})
                elif all_of_item.required:
                    required.extend(all_of_item.required)
                self._parse_all_of_item(
                    name,
                    all_of_item,
                    path,
                    fields,
                    base_classes,
                    required,
                    union_models,
                )
                if all_of_item.anyOf:
                    self.model_resolver.add(path, name, class_name=True, loaded=True)
                    union_models.extend(d.reference for d in self.parse_any_of(name, all_of_item, path) if d.reference)
                if all_of_item.oneOf:
                    self.model_resolver.add(path, name, class_name=True, loaded=True)
                    union_models.extend(d.reference for d in self.parse_one_of(name, all_of_item, path) if d.reference)

    def parse_all_of(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        ignore_duplicate_model: bool = False,  # noqa: FBT001, FBT002
    ) -> DataType:
        """Parse allOf schema into a single data type with combined properties."""
        if len(obj.allOf) == 1 and not obj.properties:
            single_obj = obj.allOf[0]
            if (
                single_obj.ref
                and single_obj.ref_type == JSONReference.LOCAL
                and get_model_by_path(self.raw_obj, single_obj.ref[2:].split("/")).get("enum")
            ):
                ref_data_type = self.get_ref_data_type(single_obj.ref)

                full_path = self.model_resolver.join_path(tuple(path))
                existing_ref = self.model_resolver.references.get(full_path)
                if existing_ref is not None and not existing_ref.loaded:
                    reference = self.model_resolver.add(path, name, class_name=True, loaded=True)
                    self.set_schema_extensions(reference.path, obj)
                    field = self.data_model_field_type(
                        name=None,
                        data_type=ref_data_type,
                        required=True,
                    )
                    data_model_root = self.data_model_root_type(
                        reference=reference,
                        fields=[field],
                        custom_base_class=self._resolve_base_class(name, obj.custom_base_path),
                        custom_template_dir=self.custom_template_dir,
                        extra_template_data=self.extra_template_data,
                        path=self.current_source_path,
                        description=obj.description if self.use_schema_description else None,
                        nullable=obj.type_has_null,
                        treat_dot_as_module=self.treat_dot_as_module,
                    )
                    self.results.append(data_model_root)
                    return self.data_type(reference=reference)

                return ref_data_type

        merged_all_of_obj = self._merge_all_of_object(obj)
        if merged_all_of_obj:
            return self._parse_object_common_part(
                name,
                merged_all_of_obj,
                path,
                ignore_duplicate_model=ignore_duplicate_model,
                fields=[],
                base_classes=[],
                required=[],
            )

        root_model_result = self._handle_allof_root_model_with_constraints(name, obj, path)
        if root_model_result is not None:
            return root_model_result

        fields: list[DataModelFieldBase] = []
        base_classes: list[Reference] = []
        required: list[str] = []
        union_models: list[Reference] = []
        self._parse_all_of_item(name, obj, path, fields, base_classes, required, union_models)
        if not union_models:
            return self._parse_object_common_part(
                name,
                obj,
                path,
                ignore_duplicate_model=ignore_duplicate_model,
                fields=fields,
                base_classes=base_classes,
                required=required,
            )
        reference = self.model_resolver.add(path, name, class_name=True, loaded=True)
        self.set_schema_extensions(reference.path, obj)
        all_of_data_type = self._parse_object_common_part(
            name,
            obj,
            get_special_path("allOf", path),
            ignore_duplicate_model=ignore_duplicate_model,
            fields=fields,
            base_classes=base_classes,
            required=required,
        )
        assert all_of_data_type.reference is not None
        data_type = self.data_type(
            data_types=[
                self._parse_object_common_part(
                    name,
                    obj,
                    get_special_path(f"union_model-{index}", path),
                    ignore_duplicate_model=ignore_duplicate_model,
                    fields=[],
                    base_classes=[union_model, all_of_data_type.reference],
                    required=[],
                )
                for index, union_model in enumerate(union_models)
            ]
        )
        field = self.get_object_field(
            field_name=None,
            field=obj,
            required=True,
            field_type=data_type,
            alias=None,
            original_field_name=None,
        )
        data_model_root = self.data_model_root_type(
            reference=reference,
            fields=[field],
            custom_base_class=self._resolve_base_class(name, obj.custom_base_path),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description if self.use_schema_description else None,
            nullable=obj.type_has_null,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.results.append(data_model_root)
        return self.data_type(reference=reference)

    def parse_object_fields(
        self,
        obj: JsonSchemaObject,
        path: list[str],
        module_name: Optional[str] = None,  # noqa: UP045
        class_name: Optional[str] = None,  # noqa: UP045
    ) -> list[DataModelFieldBase]:
        """Parse object properties into a list of data model fields."""
        properties: dict[str, JsonSchemaObject | bool] = {} if obj.properties is None else obj.properties
        requires: set[str] = {*()} if obj.required is None else {*obj.required}
        fields: list[DataModelFieldBase] = []

        exclude_field_names: set[str] = set()
        for original_field_name, field in properties.items():
            field_name, alias = self.model_resolver.get_valid_field_name_and_alias(
                original_field_name,
                excludes=exclude_field_names,
                model_type=self.field_name_model_type,
                class_name=class_name,
            )
            modular_name = f"{module_name}.{field_name}" if module_name else field_name

            exclude_field_names.add(field_name)

            if isinstance(field, bool):
                # Handle multiple aliases (Pydantic v2 AliasChoices)
                single_alias: str | None = None
                validation_aliases: list[str] | None = None
                if isinstance(alias, list):
                    validation_aliases = alias
                else:
                    single_alias = alias
                fields.append(
                    self.data_model_field_type(
                        name=field_name,
                        data_type=self.data_type_manager.get_data_type(
                            Types.any,
                        ),
                        required=False if self.force_optional_for_required_fields else original_field_name in requires,
                        alias=single_alias,
                        validation_aliases=validation_aliases,
                        strip_default_none=self.strip_default_none,
                        use_annotated=self.use_annotated,
                        use_field_description=self.use_field_description,
                        use_field_description_example=self.use_field_description_example,
                        use_inline_field_description=self.use_inline_field_description,
                        original_name=original_field_name,
                    )
                )
                continue

            field_type = self.parse_item(modular_name, field, [*path, field_name])

            effective_default, effective_has_default = self.model_resolver.resolve_default_value(
                original_field_name,
                field.default,
                field.has_default,
                class_name=class_name,
            )

            if self.force_optional_for_required_fields or (
                self.apply_default_values_for_required_fields and effective_has_default
            ):
                required: bool = False
            else:
                required = original_field_name in requires
            fields.append(
                self.get_object_field(
                    field_name=field_name,
                    field=field,
                    required=required,
                    field_type=field_type,
                    alias=alias,
                    original_field_name=original_field_name,
                    effective_default=effective_default,
                    effective_has_default=effective_has_default,
                )
            )
        return fields

    def parse_object(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        singular_name: bool = False,  # noqa: FBT001, FBT002
        unique: bool = True,  # noqa: FBT001, FBT002
    ) -> DataType:
        """Parse object schema into a data model."""
        if not unique:  # pragma: no cover
            warn(
                f"{self.__class__.__name__}.parse_object() ignore `unique` argument."
                f"An object name must be unique."
                f"This argument will be removed in a future version",
                stacklevel=2,
            )
        name = self._apply_title_as_name(name, obj)
        reference = self.model_resolver.add(
            path,
            name,
            class_name=True,
            singular_name=singular_name,
            loaded=True,
        )
        class_name = reference.name
        self.set_title(reference.path, obj)
        self.set_schema_id(reference.path, obj)
        if self.read_only_write_only_model_type is not None and obj.properties:
            for prop in obj.properties.values():
                if isinstance(prop, JsonSchemaObject) and prop.ref:
                    self._load_ref_schema_object(prop.ref)
        fields = self.parse_object_fields(
            obj,
            path,
            get_module_name(class_name, None, treat_dot_as_module=self.treat_dot_as_module),
            class_name=class_name,
        )
        if fields or not isinstance(obj.additionalProperties, JsonSchemaObject):
            data_model_type_class = self.data_model_type
        else:
            fields.append(
                self.get_object_field(
                    field_name=None,
                    field=obj.additionalProperties,
                    required=True,
                    original_field_name=None,
                    field_type=self.data_type(
                        data_types=[
                            self.parse_item(
                                # TODO: Improve naming for nested ClassName
                                name,
                                obj.additionalProperties,
                                [*path, "additionalProperties"],
                            )
                        ],
                        is_dict=True,
                    ),
                    alias=None,
                )
            )
            data_model_type_class = self.data_model_root_type

        self.set_additional_properties(reference.path, obj)
        self.set_unevaluated_properties(reference.path, obj)
        self.set_schema_extensions(reference.path, obj)

        generates_separate = self._should_generate_separate_models(fields, None)
        if generates_separate:
            self._create_request_response_models(
                name=class_name,
                obj=obj,
                path=path,
                fields=fields,
                data_model_type_class=data_model_type_class,
            )

        # Generate base model if needed
        if self._should_generate_base_model(generates_separate_models=generates_separate):
            data_model_type = self._create_data_model(
                model_type=data_model_type_class,
                reference=reference,
                fields=fields,
                custom_base_class=self._resolve_base_class(class_name, obj.custom_base_path),
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                path=self.current_source_path,
                description=obj.description if self.use_schema_description else None,
                nullable=obj.type_has_null,
                keyword_only=self.keyword_only,
                treat_dot_as_module=self.treat_dot_as_module,
                dataclass_arguments=self.dataclass_arguments,
            )
            self.results.append(data_model_type)

        return self.data_type(reference=reference)

    def parse_pattern_properties(
        self,
        name: str,
        pattern_properties: dict[str, JsonSchemaObject | bool],
        path: list[str],
    ) -> DataType:
        """Parse patternProperties into a dict data type with regex keys."""
        pattern_value_pairs: list[tuple[str, DataType]] = []
        for i, (pattern, schema) in enumerate(pattern_properties.items()):
            if schema is False:
                continue

            if schema is True:
                value_type = self.data_type_manager.get_data_type(Types.any)
            else:
                value_type = self.parse_item(
                    name,
                    schema,
                    get_special_path(f"patternProperties/{i}", path),
                )
            pattern_value_pairs.append((pattern, value_type))

        if not pattern_value_pairs:
            return self.data_type(data_types=[])

        groups: dict[str, tuple[list[str], DataType]] = {}
        for pattern, value_type in pattern_value_pairs:
            key = value_type.type_hint
            if key not in groups:
                groups[key] = ([], value_type)
            groups[key][0].append(pattern)

        data_types: list[DataType] = []
        for patterns, value_type in groups.values():
            merged_pattern = patterns[0] if len(patterns) == 1 else "|".join(patterns)
            data_types.append(
                self.data_type(
                    data_types=[value_type],
                    is_dict=True,
                    dict_key=self.data_type_manager.get_data_type(
                        Types.string,
                        pattern=merged_pattern if not self.field_constraints else None,
                    ),
                )
            )

        return self.data_type(data_types=data_types)

    def parse_property_names(  # noqa: PLR0912
        self,
        name: str,
        property_names: JsonSchemaObject,
        additional_properties: JsonSchemaObject | bool | None,  # noqa: FBT001
        path: list[str],
        parent_obj: JsonSchemaObject | None = None,
    ) -> DataType:
        """Parse propertyNames into a dict data type with constrained keys.

        Args:
            name: Name for the data type
            property_names: Schema constraining property names
            additional_properties: Schema for values (or bool/None)
            path: Current path in schema
            parent_obj: Parent schema object for x-python-type lookup

        Returns:
            DataType representing dict with constrained keys
        """
        # Determine value type from additionalProperties
        if isinstance(additional_properties, JsonSchemaObject):
            value_type = self.parse_item(
                name,
                additional_properties,
                get_special_path("propertyNames/value", path),
            )
        else:
            value_type = self.data_type_manager.get_data_type(Types.any)

        # Determine key type from propertyNames constraints
        # Case 1: $ref -> resolve reference directly (most common case for refs)
        if property_names.ref:
            key_type = self.get_ref_data_type(property_names.ref)
        # Case 2: composite types (anyOf/oneOf/allOf) -> delegate to parse_item
        elif property_names.anyOf or property_names.oneOf or property_names.allOf:
            key_type = self.parse_item(
                name,
                property_names,
                get_special_path("propertyNames/key", path),
            )
        # Case 3: enum constraint -> Literal type
        elif property_names.enum:
            # Filter to only string values (property names must be strings)
            string_enums = [e for e in property_names.enum if isinstance(e, str)]
            if string_enums:
                key_type = self.data_type(literals=string_enums)
            else:
                key_type = self.data_type_manager.get_data_type(Types.string)
        # Case 4: pattern/minLength/maxLength constraints -> constr type
        elif (
            property_names.pattern is not None
            or property_names.minLength is not None
            or property_names.maxLength is not None
        ):
            kwargs: dict[str, Any] = {}
            if property_names.pattern and not self.field_constraints:
                kwargs["pattern"] = property_names.pattern
            if property_names.minLength is not None:
                kwargs["minLength"] = property_names.minLength
            if property_names.maxLength is not None:
                kwargs["maxLength"] = property_names.maxLength

            key_type = self.data_type_manager.get_data_type(
                Types.string,
                **kwargs,
            )
        # Case 5: No specific constraints -> plain str
        else:
            key_type = self.data_type_manager.get_data_type(Types.string)

        dict_flags: dict[str, bool] = {"is_dict": True}
        if parent_obj:  # pragma: no branch
            python_type_flags = self._get_python_type_flags(parent_obj)
            if python_type_flags:  # pragma: no cover
                dict_flags = python_type_flags

        return self.data_type(
            data_types=[value_type],
            **dict_flags,
            dict_key=key_type,
        )

    def _should_create_type_alias_for_title(  # noqa: PLR0911
        self, item: JsonSchemaObject, name: str
    ) -> bool:
        """Check if a type alias should be created for an inline type with title.

        When use_title_as_name is enabled and the item has a title, certain inline types
        (array, dict, oneOf/anyOf unions, enum as literal, primitive types) should create
        a type alias instead of being inlined.
        """
        if not (self.use_title_as_name and item.title):
            return False

        if item.is_array:
            return True
        if item.anyOf or item.oneOf:
            combined_items = item.anyOf or item.oneOf
            const_enum_data = self._extract_const_enum_from_combined(combined_items, item.type)
            if const_enum_data is None:
                return True
            enum_values, varnames, enum_type, nullable = const_enum_data
            synthetic_obj = self._create_synthetic_enum_obj(item, enum_values, varnames, enum_type, nullable)
            if self.should_parse_enum_as_literal(synthetic_obj, property_name=name, property_obj=item):
                return True
        if (
            item.is_object
            and not item.properties
            and not item.patternProperties
            and not item.propertyNames
            and isinstance(item.additionalProperties, JsonSchemaObject)
        ):
            return True
        if item.patternProperties:
            return True
        if item.propertyNames:
            return True
        if (
            item.enum
            and not self.ignore_enum_constraints
            and self.should_parse_enum_as_literal(item, property_name=name)
        ):
            return True
        is_primitive = (
            item.type
            and not item.is_array
            and not item.is_object
            and not item.anyOf
            and not item.oneOf
            and not item.allOf
            and not item.ref
            and not (item.enum and not self.ignore_enum_constraints)
        )
        return bool(is_primitive)

    def parse_item(  # noqa: PLR0911, PLR0912, PLR0914, PLR0915
        self,
        name: str,
        item: JsonSchemaObject,
        path: list[str],
        singular_name: bool = False,  # noqa: FBT001, FBT002
        parent: JsonSchemaObject | None = None,
    ) -> DataType:
        """Parse a single JSON Schema item into a data type."""
        python_type_override = self._get_python_type_override(item)
        if python_type_override:
            return python_type_override
        if self.use_title_as_name and item.title:
            name = sanitize_module_name(item.title, treat_dot_as_module=self.treat_dot_as_module)
            singular_name = False
        if self._should_create_type_alias_for_title(item, name):
            return self.parse_root_type(name, item, path)
        if parent and not item.enum and item.has_constraint and (parent.has_constraint or self.field_constraints):
            root_type_path = get_special_path("array", path)
            return self.parse_root_type(
                self.model_resolver.add(
                    root_type_path,
                    name,
                    class_name=True,
                    singular_name=singular_name,
                ).name,
                item,
                root_type_path,
            )
        # Resolve $recursiveRef to $ref (JSON Schema 2019-09)
        if item.recursiveRef and not item.ref:
            return self.get_ref_data_type(self._resolve_recursive_ref(item, path) or "#")
        # Resolve $dynamicRef to $ref (JSON Schema 2020-12)
        if item.dynamicRef and not item.ref:
            return self.get_ref_data_type(self._resolve_dynamic_ref(item) or item.dynamicRef)
        if item.is_ref_with_nullable_only and item.ref:
            ref_data_type = self.get_ref_data_type(item.ref)
            if self.strict_nullable:
                return self.data_type(data_types=[ref_data_type], is_optional=True)
            return ref_data_type
        if item.has_ref_with_schema_keywords:
            item = self._merge_ref_with_schema(item)
        if item.ref:
            return self.get_ref_data_type(item.ref)
        if item.custom_type_path:  # pragma: no cover
            return self.data_type_manager.get_data_type_from_full_path(item.custom_type_path, is_custom_type=True)
        if item.is_array:
            return self.parse_array_fields(name, item, get_special_path("array", path)).data_type
        if item.discriminator and parent and parent.is_array and (item.oneOf or item.anyOf):
            return self.parse_root_type(name, item, path)
        if item.anyOf:
            const_enum_data = self._extract_const_enum_from_combined(item.anyOf, item.type)
            if const_enum_data is not None:
                enum_values, varnames, enum_type, nullable = const_enum_data
                synthetic_obj = self._create_synthetic_enum_obj(item, enum_values, varnames, enum_type, nullable)
                if self.should_parse_enum_as_literal(synthetic_obj, property_name=name, property_obj=item):
                    return self.parse_enum_as_literal(synthetic_obj)
                return self.parse_enum(name, synthetic_obj, get_special_path("enum", path), singular_name=singular_name)
            return self.data_type(data_types=self.parse_any_of(name, item, get_special_path("anyOf", path)))
        if item.oneOf:
            const_enum_data = self._extract_const_enum_from_combined(item.oneOf, item.type)
            if const_enum_data is not None:
                enum_values, varnames, enum_type, nullable = const_enum_data
                synthetic_obj = self._create_synthetic_enum_obj(item, enum_values, varnames, enum_type, nullable)
                if self.should_parse_enum_as_literal(synthetic_obj, property_name=name, property_obj=item):
                    return self.parse_enum_as_literal(synthetic_obj)
                return self.parse_enum(name, synthetic_obj, get_special_path("enum", path), singular_name=singular_name)
            return self.data_type(data_types=self.parse_one_of(name, item, get_special_path("oneOf", path)))
        if item.allOf:
            if len(item.allOf) == 1 and not item.properties:
                single_item = item.allOf[0]
                if single_item.ref:
                    return self.get_ref_data_type(single_item.ref)
            all_of_path = get_special_path("allOf", path)
            all_of_path = [self.model_resolver.resolve_ref(all_of_path)]
            return self.parse_all_of(
                self.model_resolver.add(all_of_path, name, singular_name=singular_name, class_name=True).name,
                item,
                all_of_path,
                ignore_duplicate_model=True,
            )
        if item.is_object or item.patternProperties or item.propertyNames:
            object_path = get_special_path("object", path)
            if item.properties:
                if item.has_multiple_types and isinstance(item.type, list):
                    data_types: list[DataType] = []
                    data_types.append(self.parse_object(name, item, object_path, singular_name=singular_name))
                    data_types.extend(
                        self.data_type_manager.get_data_type(
                            self._get_type_with_mappings(t, item.format or "default"),
                        )
                        for t in item.type
                        if t not in {"object", "null"}
                    )
                    return self.data_type(data_types=data_types)
                return self.parse_object(name, item, object_path, singular_name=singular_name)
            if item.patternProperties:
                # support only single key dict.
                return self.parse_pattern_properties(name, item.patternProperties, object_path)
            if item.propertyNames:
                return self.parse_property_names(
                    name, item.propertyNames, item.additionalProperties, object_path, parent_obj=item
                )
            if isinstance(item.additionalProperties, JsonSchemaObject):
                python_type_flags = self._get_python_type_flags(item)
                dict_flags = python_type_flags or {"is_dict": True}
                return self.data_type(
                    data_types=[
                        self.parse_item(
                            name, item.additionalProperties, get_special_path("additionalProperties", object_path)
                        )
                    ],
                    **dict_flags,
                )
            return self.data_type_manager.get_data_type(
                Types.object,
            )
        if item.enum and not self.ignore_enum_constraints:
            if self.should_parse_enum_as_literal(item, property_name=name):
                return self.parse_enum_as_literal(item)
            return self.parse_enum(name, item, get_special_path("enum", path), singular_name=singular_name)
        return self.get_data_type(item)

    def parse_list_item(
        self,
        name: str,
        target_items: list[JsonSchemaObject],
        path: list[str],
        parent: JsonSchemaObject,
        singular_name: bool = True,  # noqa: FBT001, FBT002
    ) -> list[DataType]:
        """Parse a list of items into data types."""
        return [
            self.parse_item(
                name,
                item,
                [*path, str(index)],
                singular_name=singular_name,
                parent=parent,
            )
            for index, item in enumerate(target_items)
        ]

    def parse_array_fields(  # noqa: PLR0912, PLR0915
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        singular_name: bool = True,  # noqa: FBT001, FBT002
    ) -> DataModelFieldBase:
        """Parse array schema into a data model field with list type."""
        # Strict mode: check for version-specific array features
        self._check_array_version_features(obj, path)

        if self.force_optional_for_required_fields:
            required: bool = False
            nullable: Optional[bool] = None  # noqa: UP045
        else:
            required = not obj.has_default
            if self.strict_nullable:
                nullable = obj.nullable if obj.has_default or required else True
            else:
                required = not obj.nullable and required
                if obj.nullable:
                    nullable = True
                elif obj.has_default:
                    nullable = False
                else:
                    nullable = None
        is_tuple = False
        suppress_item_constraints = False
        if isinstance(obj.items, JsonSchemaObject):
            items: list[JsonSchemaObject] = [obj.items]
        elif isinstance(obj.items, list):
            items = obj.items
            if self._is_fixed_length_tuple(obj):
                is_tuple = True
                suppress_item_constraints = True
        elif obj.prefixItems is not None and self._is_fixed_length_tuple(obj):
            suppress_item_constraints = True
            items = obj.prefixItems
            is_tuple = True
        else:
            items = []

        if items:
            item_data_types = self.parse_list_item(
                name,
                items,
                path,
                obj,
                singular_name=singular_name,
            )
        else:
            item_data_types = [self.data_type_manager.get_data_type(Types.any)]

        python_type_flags = self._get_python_type_flags(obj)
        container_flags: dict[str, bool] = {}
        if not is_tuple:
            container_flags = python_type_flags or {"is_list": True}

        data_types: list[DataType] = [
            self.data_type(
                data_types=item_data_types,
                is_tuple=is_tuple,
                **container_flags,
            )
        ]
        # TODO: decide special path word for a combined data model.
        if obj.allOf:
            data_types.append(self.parse_all_of(name, obj, get_special_path("allOf", path)))
        elif obj.is_object:
            data_types.append(self.parse_object(name, obj, get_special_path("object", path)))
        if obj.enum and not self.ignore_enum_constraints:
            data_types.append(self.parse_enum(name, obj, get_special_path("enum", path)))
        constraints = model_dump(obj, exclude_none=True)
        if suppress_item_constraints:
            constraints.pop("minItems", None)
            constraints.pop("maxItems", None)
        return self.data_model_field_type(
            data_type=self.data_type(data_types=data_types),
            default=obj.default,
            required=required,
            constraints=constraints,
            nullable=nullable,
            strip_default_none=self.strip_default_none,
            extras=self.get_field_extras(obj),
            use_annotated=self.use_annotated,
            use_serialize_as_any=self.use_serialize_as_any,
            use_field_description=self.use_field_description,
            use_field_description_example=self.use_field_description_example,
            use_inline_field_description=self.use_inline_field_description,
            original_name=None,
            has_default=obj.has_default,
        )

    def parse_array(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        original_name: str | None = None,
    ) -> DataType:
        """Parse array schema into a root model with array type."""
        name = self._apply_title_as_name(name, obj)
        reference = self.model_resolver.add(path, name, loaded=True, class_name=True)
        self.set_schema_extensions(reference.path, obj)
        field = self.parse_array_fields(original_name or name, obj, [*path, name])

        if any(d.reference == reference for d in field.data_type.all_data_types if d.reference):
            # self-reference
            field = self.data_model_field_type(
                data_type=self.data_type(
                    data_types=[
                        self.data_type(data_types=field.data_type.data_types[1:], is_list=True),
                        *field.data_type.data_types[1:],
                    ]
                ),
                default=field.default,
                required=field.required,
                constraints=field.constraints,
                nullable=field.nullable,
                strip_default_none=field.strip_default_none,
                extras=field.extras,
                use_annotated=self.use_annotated,
                use_field_description=self.use_field_description,
                use_field_description_example=self.use_field_description_example,
                use_inline_field_description=self.use_inline_field_description,
                original_name=None,
                has_default=field.has_default,
            )

        data_model_root = self.data_model_root_type(
            reference=reference,
            fields=[field],
            custom_base_class=self._resolve_base_class(name, obj.custom_base_path),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description if self.use_schema_description else None,
            nullable=obj.type_has_null,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.results.append(data_model_root)
        return self.data_type(reference=reference)

    def parse_root_type(  # noqa: PLR0912, PLR0914, PLR0915
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> DataType:
        """Parse a root-level type into a root model."""
        reference: Reference | None = None
        if obj.ref:
            data_type: DataType = self.get_ref_data_type(obj.ref)
        elif obj.custom_type_path:
            data_type = self.data_type_manager.get_data_type_from_full_path(
                obj.custom_type_path, is_custom_type=True
            )  # pragma: no cover
        elif obj.is_array:
            data_type = self.parse_array_fields(
                name, obj, get_special_path("array", path)
            ).data_type  # pragma: no cover
        elif obj.anyOf or obj.oneOf:
            combined_items = obj.anyOf or obj.oneOf
            const_enum_data = self._extract_const_enum_from_combined(combined_items, obj.type)
            if const_enum_data is not None:  # pragma: no cover
                enum_values, varnames, enum_type, nullable = const_enum_data
                synthetic_obj = self._create_synthetic_enum_obj(obj, enum_values, varnames, enum_type, nullable)
                if self.should_parse_enum_as_literal(synthetic_obj, property_name=name, property_obj=obj):
                    data_type = self.parse_enum_as_literal(synthetic_obj)
                else:
                    data_type = self.parse_enum(name, synthetic_obj, path)
            else:
                reference = self.model_resolver.add(path, name, loaded=True, class_name=True)
                if obj.anyOf:
                    data_types: list[DataType] = self.parse_any_of(name, obj, get_special_path("anyOf", path))
                else:
                    data_types = self.parse_one_of(name, obj, get_special_path("oneOf", path))

                if len(data_types) > 1:  # pragma: no cover
                    data_type = self.data_type(data_types=data_types)
                elif not data_types:  # pragma: no cover
                    return EmptyDataType()
                else:  # pragma: no cover
                    data_type = data_types[0]
        elif obj.patternProperties:
            data_type = self.parse_pattern_properties(name, obj.patternProperties, path)
        elif obj.propertyNames:
            data_type = self.parse_property_names(
                name, obj.propertyNames, obj.additionalProperties, path, parent_obj=obj
            )
        elif obj.is_object and not obj.properties and isinstance(obj.additionalProperties, JsonSchemaObject):
            python_type_flags = self._get_python_type_flags(obj)
            dict_flags = python_type_flags or {"is_dict": True}
            data_type = self.data_type(
                data_types=[
                    self.parse_item(name, obj.additionalProperties, get_special_path("additionalProperties", path))
                ],
                **dict_flags,
            )
        elif obj.enum and not self.ignore_enum_constraints:
            if self.should_parse_enum_as_literal(obj, property_name=name):
                data_type = self.parse_enum_as_literal(obj)
            else:  # pragma: no cover
                data_type = self.parse_enum(name, obj, path)
        elif obj.type:
            data_type = self.get_data_type(obj)
        else:
            data_type = self.data_type_manager.get_data_type(
                Types.any,
            )
        is_type_alias = self.data_model_root_type.IS_ALIAS
        if self.force_optional_for_required_fields:
            required = False
            nullable = None
            has_default_override = True
            default_value = obj.default if obj.has_default else None
        elif obj.nullable:
            required = False
            nullable = True
            has_default_override = True
            default_value = obj.default if obj.has_default else None
        elif obj.has_default and not is_type_alias:
            required = False
            nullable = False
            has_default_override = True
            default_value = obj.default
        else:
            required = True
            nullable = None
            has_default_override = obj.has_default
            default_value = obj.default if obj.has_default else UNDEFINED
        name = self._apply_title_as_name(name, obj)
        if not reference:
            reference = self.model_resolver.add(path, name, loaded=True, class_name=True)
        self._set_schema_metadata(reference.path, obj)
        self.set_schema_extensions(reference.path, obj)
        constraints = model_dump(obj, exclude_none=True) if self.field_constraints else {}
        if self.field_constraints and obj.format == "hostname":
            constraints["pattern"] = self.data_type_manager.HOSTNAME_REGEX
        data_model_root_type = self.data_model_root_type(
            reference=reference,
            fields=[
                self.data_model_field_type(
                    data_type=data_type,
                    default=default_value,
                    required=required,
                    constraints=constraints,
                    nullable=nullable,
                    strip_default_none=self.strip_default_none,
                    extras=self.get_field_extras(obj),
                    use_annotated=self.use_annotated,
                    use_field_description=self.use_field_description,
                    use_field_description_example=self.use_field_description_example,
                    use_inline_field_description=self.use_inline_field_description,
                    original_name=None,
                    has_default=has_default_override,
                )
            ],
            custom_base_class=self._resolve_base_class(name, obj.custom_base_path),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            nullable=obj.type_has_null,
            treat_dot_as_module=self.treat_dot_as_module,
            default=default_value if has_default_override else UNDEFINED,
        )
        self.results.append(data_model_root_type)
        return self.data_type(reference=reference)

    def _parse_multiple_types_with_properties(
        self,
        name: str,
        obj: JsonSchemaObject,
        type_list: list[str],
        path: list[str],
    ) -> None:
        """Parse a schema with multiple types including object with properties."""
        data_types: list[DataType] = []

        object_path = get_special_path("object", path)
        object_data_type = self.parse_object(name, obj, object_path)
        data_types.append(object_data_type)

        data_types.extend(
            self.data_type_manager.get_data_type(
                self._get_type_with_mappings(t, obj.format or "default"),
            )
            for t in type_list
            if t not in {"object", "null"}
        )

        is_nullable = obj.nullable or obj.type_has_null
        required = not (self.force_optional_for_required_fields or is_nullable)

        reference = self.model_resolver.add(path, name, loaded=True, class_name=True)
        self._set_schema_metadata(reference.path, obj)
        self.set_schema_extensions(reference.path, obj)

        constraints = model_dump(obj, exclude_none=True) if self.field_constraints else {}
        if self.field_constraints and obj.format == "hostname":
            constraints["pattern"] = self.data_type_manager.HOSTNAME_REGEX
        data_model_root_type = self.data_model_root_type(
            reference=reference,
            fields=[
                self.data_model_field_type(
                    data_type=self.data_type(data_types=data_types),
                    default=obj.default,
                    required=required,
                    constraints=constraints,
                    nullable=obj.type_has_null if self.strict_nullable else None,
                    strip_default_none=self.strip_default_none,
                    extras=self.get_field_extras(obj),
                    use_annotated=self.use_annotated,
                    use_field_description=self.use_field_description,
                    use_field_description_example=self.use_field_description_example,
                    use_inline_field_description=self.use_inline_field_description,
                    original_name=None,
                    has_default=obj.has_default,
                )
            ],
            custom_base_class=self._resolve_base_class(name, obj.custom_base_path),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            nullable=obj.type_has_null,
            treat_dot_as_module=self.treat_dot_as_module,
            default=obj.default if obj.has_default else UNDEFINED,
        )
        self.results.append(data_model_root_type)

    def parse_enum_as_literal(self, obj: JsonSchemaObject) -> DataType:
        """Parse enum values as a Literal type."""
        return self.data_type(literals=[i for i in obj.enum if i is not None])

    @classmethod
    def _get_field_name_from_dict_enum(cls, enum_part: dict[str, Any], index: int) -> str:
        """Extract field name from dict enum value using title, name, or const keys."""
        if enum_part.get("title"):
            return str(enum_part["title"])
        if enum_part.get("name"):
            return str(enum_part["name"])
        if "const" in enum_part:
            return str(enum_part["const"])
        return f"value_{index}"

    def parse_enum(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        singular_name: bool = False,  # noqa: FBT001, FBT002
        unique: bool = True,  # noqa: FBT001, FBT002
    ) -> DataType:
        """Parse enum schema into an Enum class."""
        if not unique:  # pragma: no cover
            warn(
                f"{self.__class__.__name__}.parse_enum() ignore `unique` argument."
                f"An object name must be unique."
                f"This argument will be removed in a future version",
                stacklevel=2,
            )
        enum_fields: list[DataModelFieldBase] = []

        if None in obj.enum and obj.type == "string":
            # Nullable is valid in only OpenAPI
            nullable: bool = True
            enum_times = [e for e in obj.enum if e is not None]
        else:
            enum_times = obj.enum
            nullable = False

        exclude_field_names: set[str] = set()

        enum_names = obj.x_enum_varnames or obj.x_enum_names

        for i, enum_part in enumerate(enum_times):
            if obj.type == "string" or isinstance(enum_part, str):
                default = f"'{enum_part.translate(escape_characters)}'" if isinstance(enum_part, str) else enum_part
                field_name = enum_names[i] if enum_names and i < len(enum_names) and enum_names[i] else str(enum_part)
            else:
                default = enum_part
                if enum_names and i < len(enum_names) and enum_names[i]:
                    field_name = enum_names[i]
                elif isinstance(enum_part, dict):
                    field_name = self._get_field_name_from_dict_enum(enum_part, i)
                else:
                    prefix = obj.type if isinstance(obj.type, str) else type(enum_part).__name__
                    field_name = f"{prefix}_{enum_part}"
            field_name = self.model_resolver.get_valid_field_name(
                field_name, excludes=exclude_field_names, model_type=ModelType.ENUM
            )
            exclude_field_names.add(field_name)
            enum_fields.append(
                self.data_model_field_type(
                    name=field_name,
                    default=default,
                    data_type=self.data_type_manager.get_data_type(
                        Types.any,
                    ),
                    required=True,
                    strip_default_none=self.strip_default_none,
                    has_default=obj.has_default,
                    use_field_description=self.use_field_description,
                    use_field_description_example=self.use_field_description_example,
                    use_inline_field_description=self.use_inline_field_description,
                    original_name=None,
                )
            )

        if not enum_fields:
            if not nullable:
                return self.data_type_manager.get_data_type(Types.null)
            name = self._apply_title_as_name(name, obj)
            reference = self.model_resolver.add(
                path,
                name,
                class_name=True,
                singular_name=singular_name,
                singular_name_suffix="Enum",
                loaded=True,
                model_type="enum",
            )
            self.set_schema_extensions(reference.path, obj)
            data_model_root_type = self.data_model_root_type(
                reference=reference,
                fields=[
                    self.data_model_field_type(
                        data_type=self.data_type_manager.get_data_type(Types.null),
                        default=obj.default,
                        required=False,
                        nullable=True,
                        strip_default_none=self.strip_default_none,
                        extras=self.get_field_extras(obj),
                        use_annotated=self.use_annotated,
                        has_default=obj.has_default,
                        use_field_description=self.use_field_description,
                        use_field_description_example=self.use_field_description_example,
                        use_inline_field_description=self.use_inline_field_description,
                        original_name=None,
                    )
                ],
                custom_base_class=self._resolve_base_class(name, obj.custom_base_path),
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                path=self.current_source_path,
                default=obj.default if obj.has_default else UNDEFINED,
                nullable=obj.type_has_null,
                treat_dot_as_module=self.treat_dot_as_module,
            )
            self.results.append(data_model_root_type)
            return self.data_type(reference=reference)

        def create_enum(reference_: Reference) -> DataType:
            type_: Types | None = (
                self._get_type_with_mappings(obj.type, obj.format) if isinstance(obj.type, str) else None
            )

            enum_cls: type[Enum] = Enum
            if (
                self.use_specialized_enum
                and type_
                and (specialized_type := SPECIALIZED_ENUM_TYPE_MATCH.get(type_))
                # StrEnum is available only in Python 3.11+
                and (specialized_type != StrEnum or self.target_python_version.has_strenum)
            ):
                # If specialized enum is available in the target Python version,
                # use it and ignore `self.use_subclass_enum` setting.
                type_ = None
                enum_cls = specialized_type

            enum = enum_cls(
                reference=reference_,
                fields=enum_fields,
                path=self.current_source_path,
                description=obj.description if self.use_schema_description else None,
                custom_template_dir=self.custom_template_dir,
                type_=type_ if self.use_subclass_enum else None,
                default=obj.default if obj.has_default else UNDEFINED,
                treat_dot_as_module=self.treat_dot_as_module,
            )
            self.results.append(enum)
            return self.data_type(reference=reference_)

        name = self._apply_title_as_name(name, obj)
        reference = self.model_resolver.add(
            path,
            name,
            class_name=True,
            singular_name=singular_name,
            singular_name_suffix="Enum",
            loaded=True,
            model_type="enum",
        )

        if not nullable:
            return create_enum(reference)

        self.set_schema_extensions(reference.path, obj)
        enum_reference = self.model_resolver.add(
            [*path, "Enum"],
            f"{reference.name}Enum",
            class_name=True,
            singular_name=singular_name,
            singular_name_suffix="Enum",
            loaded=True,
            model_type="enum",
        )

        data_model_root_type = self.data_model_root_type(
            reference=reference,
            fields=[
                self.data_model_field_type(
                    data_type=create_enum(enum_reference),
                    default=obj.default,
                    required=False,
                    nullable=True,
                    strip_default_none=self.strip_default_none,
                    extras=self.get_field_extras(obj),
                    use_annotated=self.use_annotated,
                    has_default=obj.has_default,
                    use_field_description=self.use_field_description,
                    use_field_description_example=self.use_field_description_example,
                    use_inline_field_description=self.use_inline_field_description,
                    original_name=None,
                )
            ],
            custom_base_class=self._resolve_base_class(reference.name, obj.custom_base_path),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            default=obj.default if obj.has_default else UNDEFINED,
            nullable=obj.type_has_null,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.results.append(data_model_root_type)
        return self.data_type(reference=reference)

    def _get_ref_body(self, resolved_ref: str) -> dict[str, YamlValue]:
        """Get the body of a reference from URL or remote file."""
        if is_url(resolved_ref):
            return self._get_ref_body_from_url(resolved_ref)
        return self._get_ref_body_from_remote(resolved_ref)

    def _get_ref_body_from_url(self, ref: str) -> dict[str, YamlValue]:
        """Get reference body from a URL (HTTP, HTTPS, or file scheme)."""
        if ref.startswith("file://"):
            from urllib.parse import urlparse  # noqa: PLC0415
            from urllib.request import url2pathname  # noqa: PLC0415

            parsed = urlparse(ref)
            # url2pathname handles percent-decoding and Windows drive letters
            path = url2pathname(parsed.path)
            # Handle UNC paths (file://server/share/path)
            if parsed.netloc:
                path = f"//{parsed.netloc}{path}"
            file_path = Path(path)
            return self.remote_object_cache.get_or_put(
                ref, default_factory=lambda _: load_data_from_path(file_path, self.encoding)
            )
        return self.remote_object_cache.get_or_put(
            ref, default_factory=lambda key: load_data(self._get_text_from_url(key))
        )

    def _get_ref_body_from_remote(self, resolved_ref: str) -> dict[str, YamlValue]:
        """Get reference body from a remote file path."""
        full_path = self.base_path / resolved_ref

        return self.remote_object_cache.get_or_put(
            str(full_path),
            default_factory=lambda _: load_data_from_path(full_path, self.encoding),
        )

    def resolve_ref(self, object_ref: str) -> Reference:
        """Resolve a reference by loading and parsing the referenced schema."""
        reference = self.model_resolver.add_ref(object_ref)
        if reference.loaded:
            return reference

        # https://swagger.io/docs/specification/using-ref/
        ref = self.model_resolver.resolve_ref(object_ref)
        if get_ref_type(object_ref) == JSONReference.LOCAL or get_ref_type(ref) == JSONReference.LOCAL:
            self.reserved_refs[tuple(self.model_resolver.current_root)].add(ref)
            return reference
        if self.model_resolver.is_after_load(ref):
            self.reserved_refs[tuple(ref.split("#")[0].split("/"))].add(ref)
            return reference

        if is_url(ref):
            relative_path, object_path = ref.split("#")
            relative_paths = [relative_path]
            base_path = None
        else:
            if self.model_resolver.is_external_root_ref(ref):
                relative_path, object_path = ref[:-1], ""
            else:
                relative_path, object_path = ref.split("#")
            relative_paths = relative_path.split("/")
            base_path = Path(*relative_paths).parent
        with (
            self.model_resolver.current_base_path_context(base_path),
            self.model_resolver.base_url_context(relative_path),
        ):
            self._parse_file(
                self._get_ref_body(relative_path),
                self.model_resolver.add_ref(ref, resolved=True).name,
                relative_paths,
                object_path.split("/") if object_path else None,
            )
        reference.loaded = True
        return reference

    def _traverse_schema_objects(  # noqa: PLR0912
        self,
        obj: JsonSchemaObject,
        path: list[str],
        callback: Callable[[JsonSchemaObject, list[str]], None],
        *,
        include_one_of: bool = True,
    ) -> None:
        """Traverse schema objects recursively and apply callback."""
        callback(obj, path)
        match obj.items:
            case JsonSchemaObject() as item:
                self._traverse_schema_objects(item, path, callback, include_one_of=include_one_of)
            case list() as items:
                for item in items:
                    self._traverse_schema_objects(item, path, callback, include_one_of=include_one_of)
        if obj.prefixItems:
            for item in obj.prefixItems:
                self._traverse_schema_objects(item, path, callback, include_one_of=include_one_of)
        if isinstance(obj.additionalProperties, JsonSchemaObject):
            self._traverse_schema_objects(obj.additionalProperties, path, callback, include_one_of=include_one_of)
        if isinstance(obj.unevaluatedProperties, JsonSchemaObject):
            self._traverse_schema_objects(obj.unevaluatedProperties, path, callback, include_one_of=include_one_of)
        if obj.patternProperties:
            for value in obj.patternProperties.values():
                if isinstance(value, JsonSchemaObject):
                    self._traverse_schema_objects(value, path, callback, include_one_of=include_one_of)
        if obj.propertyNames:
            self._traverse_schema_objects(obj.propertyNames, path, callback, include_one_of=include_one_of)
        for item in obj.anyOf:
            self._traverse_schema_objects(item, path, callback, include_one_of=include_one_of)
        for item in obj.allOf:
            self._traverse_schema_objects(item, path, callback, include_one_of=include_one_of)
        if include_one_of:
            for item in obj.oneOf:
                self._traverse_schema_objects(item, path, callback, include_one_of=include_one_of)
        if obj.properties:
            for value in obj.properties.values():
                if isinstance(value, JsonSchemaObject):
                    self._traverse_schema_objects(value, path, callback, include_one_of=include_one_of)

    def _resolve_ref_callback(self, obj: JsonSchemaObject, path: list[str]) -> None:  # noqa: ARG002
        """Resolve $ref in schema object."""
        if obj.ref:
            self.resolve_ref(obj.ref)

    def _add_id_callback(self, obj: JsonSchemaObject, path: list[str]) -> None:  # noqa: PLR0912
        """Add $id to model resolver."""
        if obj.id:
            self.model_resolver.add_id(obj.id, path)
        if obj.items:
            if isinstance(obj.items, JsonSchemaObject):
                self.parse_id(obj.items, path)
            elif isinstance(obj.items, list):
                for item in obj.items:
                    self.parse_id(item, path)
        if obj.prefixItems:
            for item in obj.prefixItems:
                self.parse_id(item, path)
        if isinstance(obj.additionalProperties, JsonSchemaObject):
            self.parse_id(obj.additionalProperties, path)
        if isinstance(obj.unevaluatedProperties, JsonSchemaObject):
            self.parse_id(obj.unevaluatedProperties, path)
        if obj.patternProperties:
            for value in obj.patternProperties.values():
                if isinstance(value, JsonSchemaObject):
                    self.parse_id(value, path)
        if obj.propertyNames:
            self.parse_id(obj.propertyNames, path)
        for item in obj.anyOf:
            self.parse_id(item, path)
        for item in obj.allOf:
            self.parse_id(item, path)
        if obj.properties:
            for property_value in obj.properties.values():
                if isinstance(property_value, JsonSchemaObject):
                    self.parse_id(property_value, path)

    def parse_ref(self, obj: JsonSchemaObject, path: list[str]) -> None:
        """Recursively parse all $ref references in a schema object."""
        self._traverse_schema_objects(obj, path, self._resolve_ref_callback)

    def parse_id(self, obj: JsonSchemaObject, path: list[str]) -> None:
        """Recursively parse all $id fields in a schema object."""
        self._traverse_schema_objects(obj, path, self._add_id_callback, include_one_of=False)

    @contextmanager
    def root_id_context(self, root_raw: dict[str, Any]) -> Generator[None, None, None]:
        """Context manager to temporarily set the root $id during parsing.

        Uses schema_features.id_field to support both "id" (Draft 4) and "$id" (Draft 6+).
        Falls back to checking both fields for lenient compatibility.
        """
        previous_root_id = self.root_id
        # Try version-specific field first, then fallback to alternative for compatibility
        id_field = self.schema_features.id_field
        self.root_id = root_raw.get(id_field) or root_raw.get("$id") or root_raw.get("id") or None
        yield
        self.root_id = previous_root_id

    def _validate_schema_object(
        self,
        raw: dict[str, YamlValue] | YamlValue,
        path: list[str],
    ) -> JsonSchemaObject:
        """Validate raw data as JsonSchemaObject with path context in errors."""
        try:
            return model_validate(self.SCHEMA_OBJECT_TYPE, raw)
        except SchemaParseError:
            raise
        except Exception as e:
            raise SchemaParseError(
                message=f"{type(e).__name__}: {e}",
                path=path,
                original_error=e,
            ) from e

    def parse_raw_obj(
        self,
        name: str,
        raw: dict[str, YamlValue] | YamlValue,
        path: list[str],
    ) -> None:
        """Parse a raw dictionary into a JsonSchemaObject and process it."""
        if isinstance(raw, dict) and "x-python-import" in raw:
            self._handle_python_import(name, path)
            return

        # Strict mode: check for version-specific features before validation
        self._check_version_specific_features(raw, path)

        obj = self._validate_schema_object(raw, path)
        # Build $recursiveAnchor / $dynamicAnchor indexes for this schema
        self._build_anchor_indexes(obj, path)
        self.parse_obj(name, obj, path)

    def _check_version_specific_features(  # noqa: PLR0912
        self,
        raw: dict[str, YamlValue] | YamlValue,
        path: list[str],
    ) -> None:
        """Check for version-specific features and warn in Strict mode.

        This method checks the raw schema data before Pydantic validation
        to detect features that may not be valid for the declared version.
        """
        if self.config.schema_version_mode != VersionMode.Strict:
            return

        # Check boolean schemas (Draft 6+)
        if isinstance(raw, bool):
            if not self.schema_features.boolean_schemas:
                version_name = "Draft 4" if self.schema_features.id_field == "id" else "this version"
                warn(
                    f"Boolean schemas are not supported in {version_name}. Schema path: {'/'.join(path)}",
                    stacklevel=3,
                )
            return

        # Check null in type array (Draft 2020-12 / OpenAPI 3.1+)
        type_value = raw.get("type")
        if isinstance(type_value, list) and "null" in type_value and not self.schema_features.null_in_type_array:
            warn(
                'null in type array (e.g., type: ["string", "null"]) is not supported '
                f"in this schema version. Use nullable: true instead. Schema path: {'/'.join(path)}",
                stacklevel=3,
            )

        # Check exclusive min/max format (Draft 4 uses boolean, Draft 6+ uses number)
        exclusive_min = raw.get("exclusiveMinimum")
        exclusive_max = raw.get("exclusiveMaximum")
        if self.schema_features.exclusive_as_number:
            # Draft 6+: should be numeric, not boolean
            if isinstance(exclusive_min, bool):
                warn(
                    f"exclusiveMinimum as boolean is Draft 4 style, but schema version uses numeric style. "
                    f"Schema path: {'/'.join(path)}",
                    stacklevel=3,
                )
            if isinstance(exclusive_max, bool):
                warn(
                    f"exclusiveMaximum as boolean is Draft 4 style, but schema version uses numeric style. "
                    f"Schema path: {'/'.join(path)}",
                    stacklevel=3,
                )
        else:
            # Draft 4: should be boolean, not numeric
            if exclusive_min is not None and not isinstance(exclusive_min, bool):
                warn(
                    f"exclusiveMinimum as number is Draft 6+ style, but schema version is Draft 4. "
                    f"Schema path: {'/'.join(path)}",
                    stacklevel=3,
                )
            if exclusive_max is not None and not isinstance(exclusive_max, bool):
                warn(
                    f"exclusiveMaximum as number is Draft 6+ style, but schema version is Draft 4. "
                    f"Schema path: {'/'.join(path)}",
                    stacklevel=3,
                )

        if not self.schema_features.read_only_write_only:
            if raw.get("readOnly") is True:
                warn(
                    f"readOnly is not supported in this schema version (Draft 7+ only). Schema path: {'/'.join(path)}",
                    stacklevel=3,
                )
            if raw.get("writeOnly") is True:
                warn(
                    f"writeOnly is not supported in this schema version (Draft 7+ only). Schema path: {'/'.join(path)}",
                    stacklevel=3,
                )

    def _check_array_version_features(
        self,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> None:
        """Check for version-specific array features and warn in Strict mode.

        Warns when prefixItems is used in versions that don't support it,
        or when items as array (tuple style) is used in Draft 2020-12+.
        """
        if self.config.schema_version_mode != VersionMode.Strict:
            return

        # Check prefixItems usage (Draft 2020-12+ only)
        if obj.prefixItems is not None and not self.schema_features.prefix_items:
            warn(
                f"prefixItems is not supported in this schema version. "
                f"Use items as array for tuple validation. Schema path: {'/'.join(path)}",
                stacklevel=4,
            )

        # Check items as array usage (deprecated in Draft 2020-12)
        if isinstance(obj.items, list) and self.schema_features.prefix_items:
            warn(
                f"items as array (tuple validation) is deprecated in Draft 2020-12. "
                f"Use prefixItems instead. Schema path: {'/'.join(path)}",
                stacklevel=4,
            )

    def _handle_python_import(
        self,
        name: str,
        path: list[str],
    ) -> None:
        """Mark x-python-import reference as loaded to skip model generation."""
        self.model_resolver.add(path, name, class_name=True, loaded=True)

    def parse_obj(  # noqa: PLR0912
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> None:
        """Parse a JsonSchemaObject by dispatching to appropriate parse methods."""
        if obj.has_ref_with_schema_keywords and not obj.is_ref_with_nullable_only:
            obj = self._merge_ref_with_schema(obj)

        if obj.is_array:
            self.parse_array(name, obj, path)
        elif obj.allOf:
            self.parse_all_of(name, obj, path)
        elif obj.oneOf or obj.anyOf:
            combined_items = obj.oneOf or obj.anyOf
            const_enum_data = self._extract_const_enum_from_combined(combined_items, obj.type)
            if const_enum_data is not None:
                enum_values, varnames, enum_type, nullable = const_enum_data
                synthetic_obj = self._create_synthetic_enum_obj(obj, enum_values, varnames, enum_type, nullable)
                if not self.should_parse_enum_as_literal(synthetic_obj, property_name=name, property_obj=obj):
                    self.parse_enum(name, synthetic_obj, path)
                else:
                    self.parse_root_type(name, synthetic_obj, path)
            else:
                data_type = self.parse_root_type(name, obj, path)
                if isinstance(data_type, EmptyDataType) and obj.properties:
                    self.parse_object(name, obj, path)  # pragma: no cover
        elif obj.properties:
            if obj.has_multiple_types and isinstance(obj.type, list):
                self._parse_multiple_types_with_properties(name, obj, obj.type, path)
            else:
                self.parse_object(name, obj, path)
        elif obj.patternProperties or obj.propertyNames:
            self.parse_root_type(name, obj, path)
        elif obj.type == "object":
            self.parse_object(name, obj, path)
        elif (
            obj.enum
            and not self.ignore_enum_constraints
            and not self.should_parse_enum_as_literal(obj, property_name=name)
        ):
            self.parse_enum(name, obj, path)
        else:
            self.parse_root_type(name, obj, path)
        self.parse_ref(obj, path)

    def _get_context_source_path_parts(self) -> Iterator[tuple[Source, list[str]]]:
        """Get source and path parts for each input file with context managers."""
        if isinstance(self.source, list) or (isinstance(self.source, Path) and self.source.is_dir()):
            self.current_source_path = Path()
            self.model_resolver.after_load_files = {
                self.base_path.joinpath(s.path).resolve().as_posix() for s in self.iter_source
            }

        for source in self.iter_source:
            if isinstance(self.source, ParseResult):
                path_parts = self.get_url_path_parts(self.source)
            else:
                path_parts = list(source.path.parts)
            if self.current_source_path is not None:
                self.current_source_path = source.path
            with (
                self.model_resolver.current_base_path_context(source.path.parent),
                self.model_resolver.current_root_context(path_parts),
            ):
                yield source, path_parts

    def parse_raw(self) -> None:
        """Parse all raw input sources into data models."""
        for source, path_parts in self._get_context_source_path_parts():
            if source.raw_data is not None:
                raw_obj = source.raw_data
                if not isinstance(raw_obj, dict):  # pragma: no cover
                    warn(f"{source.path} is empty or not a dict. Skipping this file", stacklevel=2)
                    continue
            else:
                try:
                    raw_obj = load_data(source.text)
                except TypeError:
                    warn(f"{source.path} is empty or not a dict. Skipping this file", stacklevel=2)
                    continue
            self.raw_obj = raw_obj
            title = self.raw_obj.get("title")
            title_str = str(title) if title is not None else "Model"
            if self.custom_class_name_generator:
                obj_name = title_str
            else:
                if self.class_name:
                    obj_name = self.class_name
                else:
                    # backward compatible
                    obj_name = title_str
                    if not self.model_resolver.validate_name(obj_name):
                        obj_name = title_to_class_name(obj_name)
                if not self.model_resolver.validate_name(obj_name):
                    raise InvalidClassNameError(obj_name)
            self._parse_file(self.raw_obj, obj_name, path_parts)

        self._resolve_unparsed_json_pointer()
        self._generate_forced_base_models()

    def _resolve_unparsed_json_pointer(self) -> None:
        """Resolve any remaining unparsed JSON pointer references recursively."""
        model_count: int = len(self.results)
        for source in self.iter_source:
            path_parts = list(source.path.parts)
            if not (reserved_refs := self.reserved_refs.get(tuple(path_parts))):
                continue
            if self.current_source_path is not None:
                self.current_source_path = source.path

            with (
                self.model_resolver.current_base_path_context(source.path.parent),
                self.model_resolver.current_root_context(path_parts),
            ):
                for reserved_ref in sorted(reserved_refs):
                    if self.model_resolver.add_ref(reserved_ref, resolved=True).loaded:
                        continue
                    self.raw_obj = dict(source.raw_data) if source.raw_data is not None else load_data(source.text)
                    self.parse_json_pointer(self.raw_obj, reserved_ref, path_parts)

        if model_count != len(self.results):
            # New model have been generated. It try to resolve json pointer again.
            self._resolve_unparsed_json_pointer()

    def parse_json_pointer(self, raw: dict[str, YamlValue], ref: str, path_parts: list[str]) -> None:
        """Parse a JSON pointer reference into a model."""
        path = ref.split("#", 1)[-1]
        if path[0] == "/":  # pragma: no cover
            path = path[1:]
        object_paths = path.split("/")
        models = get_model_by_path(raw, object_paths)
        model_name = object_paths[-1]

        self.parse_raw_obj(model_name, models, [*path_parts, f"#/{object_paths[0]}", *object_paths[1:]])

    def _parse_file(  # noqa: PLR0912, PLR0915
        self,
        raw: dict[str, Any],
        obj_name: str,
        path_parts: list[str],
        object_paths: list[str] | None = None,
    ) -> None:
        """Parse a file containing JSON Schema definitions and references."""
        object_paths = [o for o in object_paths or [] if o]
        path = [*path_parts, f"#/{object_paths[0]}", *object_paths[1:]] if object_paths else path_parts
        with self.model_resolver.current_root_context(path_parts):
            obj_name = self.model_resolver.add(path, obj_name, unique=False, class_name=True).name
            with self.root_id_context(raw):
                # Some jsonschema docs include attribute self to have include version details
                raw.pop("self", None)
                # parse $id before parsing $ref
                root_obj = self._validate_schema_object(raw, path_parts or ["#"])
                self.parse_id(root_obj, path_parts)
                # Build $recursiveAnchor index for root object
                if root_obj.recursiveAnchor:
                    root_key = tuple(path_parts)
                    self._recursive_anchor_index.setdefault(root_key, []).append("#")
                # Build $dynamicAnchor index for root object
                if root_obj.dynamicAnchor:
                    root_key = tuple(path_parts)
                    self._dynamic_anchor_index.setdefault(root_key, {}).setdefault(root_obj.dynamicAnchor, "#")
                definitions: dict[str, YamlValue] = {}
                schema_path = ""
                for schema_path_candidate, split_schema_path in self.schema_paths:
                    try:
                        if definitions := get_model_by_path(raw, split_schema_path):
                            schema_path = schema_path_candidate
                            break
                    except KeyError:  # pragma: no cover
                        continue

                for key, model in definitions.items():
                    definition_path = [*path_parts, schema_path, key]
                    obj = self._validate_schema_object(model, definition_path)
                    self.parse_id(obj, definition_path)
                    # Build $recursiveAnchor index for definitions
                    if obj.recursiveAnchor:
                        root_key = tuple(path_parts)
                        ref_path = "#/" + schema_path.lstrip("#/") + "/" + key
                        self._recursive_anchor_index.setdefault(root_key, []).append(ref_path)
                    # Build $dynamicAnchor index for definitions
                    if obj.dynamicAnchor:
                        root_key = tuple(path_parts)
                        ref_path = "#/" + schema_path.lstrip("#/") + "/" + key
                        self._dynamic_anchor_index.setdefault(root_key, {}).setdefault(obj.dynamicAnchor, ref_path)

                if object_paths:
                    models = get_model_by_path(raw, object_paths)
                    model_name = object_paths[-1]
                    self.parse_obj(model_name, self._validate_schema_object(models, path), path)
                elif not self.skip_root_model:
                    self.parse_obj(obj_name, root_obj, path_parts or ["#"])
                for key, model in definitions.items():
                    path = [*path_parts, schema_path, key]
                    reference = self.model_resolver.get(path)
                    if not reference or not reference.loaded:
                        self.parse_raw_obj(key, model, path)

                key = tuple(path_parts)
                reserved_refs = set(self.reserved_refs.get(key) or [])
                while reserved_refs:
                    for reserved_path in sorted(reserved_refs):
                        reference = self.model_resolver.references.get(reserved_path)
                        if not reference or reference.loaded:
                            continue
                        object_paths = reserved_path.split("#/", 1)[-1].split("/")
                        path = reserved_path.split("/")
                        models = get_model_by_path(raw, object_paths)
                        model_name = object_paths[-1]
                        self.parse_obj(model_name, self._validate_schema_object(models, path), path)
                    previous_reserved_refs = reserved_refs
                    reserved_refs = set(self.reserved_refs.get(key) or [])
                    if previous_reserved_refs == reserved_refs:
                        break
