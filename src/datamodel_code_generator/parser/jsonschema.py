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
from contextlib import contextmanager, suppress
from fractions import Fraction
from functools import cached_property, lru_cache
from math import gcd, lcm
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Optional, Union
from urllib.parse import ParseResult, unquote, urlparse
from warnings import warn

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from typing_extensions import Unpack

from datamodel_code_generator import (
    AllOfClassHierarchy,
    AllOfMergeMode,
    Error,
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
from datamodel_code_generator.deprecations import warn_deprecated
from datamodel_code_generator.format import (
    DatetimeClassType,
)
from datamodel_code_generator.imports import IMPORT_ANY, Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED, get_module_name, sanitize_module_name
from datamodel_code_generator.model.enum import (
    SPECIALIZED_ENUM_TYPE_MATCH,
    Enum,
    StrEnum,
)
from datamodel_code_generator.model.typed_dict import TypedDict as TypedDictModel
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.parser.base import (
    SPECIAL_PATH_FORMAT,
    Parser,
    Source,
    escape_characters,
    get_special_path,
    title_to_class_name,
)
from datamodel_code_generator.parser.schema_version import get_data_formats
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
    is_python_type_annotation,
)
from datamodel_code_generator.util import BaseModel
from datamodel_code_generator.validators import _validate_dotted_python_identifier_path

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Iterator, Sequence

    from datamodel_code_generator._types import JSONSchemaParserConfigDict
    from datamodel_code_generator.config import JSONSchemaParserConfig
    from datamodel_code_generator.parser.schema_version import JsonSchemaFeatures

JsonSchemaLiteral = Union[bool, int, str]  # noqa: UP007


def unescape_json_pointer_segment(segment: str) -> str:
    """Unescape JSON pointer segment by converting escape sequences and percent-encoding."""
    # Unescape ~1, ~0, and percent-encoding
    return unquote(segment.replace("~1", "/").replace("~0", "~"))


def get_model_by_path(schema: dict[str, YamlValue] | list[YamlValue], keys: list[str] | list[int]) -> YamlValue:
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
        return value
    if isinstance(value, (dict, list)):
        return get_model_by_path(value, keys[1:])
    msg = f"Cannot traverse non-container value. schema={schema}, key={keys}"  # pragma: no cover
    raise NotImplementedError(msg)  # pragma: no cover


def split_json_pointer(schema: dict[str, YamlValue] | list[YamlValue], pointer: str) -> list[str]:
    """Split a JSON pointer into path parts, preserving slash-containing dict keys."""
    return _split_json_pointer(schema, pointer)[0]


def _split_json_pointer(schema: dict[str, YamlValue] | list[YamlValue], pointer: str) -> tuple[list[str], list[str]]:
    """Split a JSON pointer into lookup and reference path parts."""
    raw_parts = pointer.lstrip("/").split("/") if pointer else []
    if "://" not in pointer and "~1" not in pointer:
        return raw_parts, raw_parts

    parts: list[str] = []
    reference_parts: list[str] = []
    current: YamlValue = schema
    index = 0
    while index < len(raw_parts):
        if isinstance(current, dict):
            direct_key = unescape_json_pointer_segment(raw_parts[index])
            if direct_key in current:
                parts.append(direct_key)
                reference_parts.append(raw_parts[index])
                current = current.get(direct_key, {})
                index += 1
                continue

            matched_key: str | None = None
            matched_end = index
            for end in range(len(raw_parts), index, -1):
                key = unescape_json_pointer_segment("/".join(raw_parts[index:end]))
                if key in current:
                    matched_key = key
                    matched_end = end
                    break
            if matched_key is None:  # pragma: no cover
                matched_key = unescape_json_pointer_segment(raw_parts[index])
                matched_end = index + 1
            parts.append(matched_key)
            reference_parts.append("/".join(raw_parts[index:matched_end]))
            current = current.get(matched_key, {})
            index = matched_end
            continue
        part = unescape_json_pointer_segment(raw_parts[index])
        parts.append(part)
        reference_parts.append(raw_parts[index])
        if isinstance(current, list):  # pragma: no branch
            current = current[int(part)]
        index += 1
    return parts, reference_parts


json_schema_data_formats: dict[str, dict[str, Types]] = get_data_formats(is_openapi=True)


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

        @classmethod
        def get_fields(cls) -> dict[str, Any]:
            """Get fields for Pydantic v2 models."""
            return cls.model_fields

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
    __constraint_field_order__: ClassVar[tuple[str, ...]] = (
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
    )
    __extra_key__: str = SPECIAL_PATH_FORMAT.format("extras")
    __metadata_only_fields__: set[str] = {  # noqa: RUF012
        "title",
        "description",
        "id",
        "$id",
        "$anchor",
        "$schema",
        "$comment",
        "examples",
        "example",
        "x_enum_varnames",
        "x_enum_descriptions",
        "x_enum_field_as_literal",
        "definitions",
        "$defs",
        "default",
        "readOnly",
        "writeOnly",
        "deprecated",
        "contentEncoding",
        "contentMediaType",
        "contentSchema",
        "externalDocs",
        "xml",
        "$recursiveRef",
        "recursiveRef",
        "$recursiveAnchor",
        "recursiveAnchor",
        "$dynamicRef",
        "dynamicRef",
        "$dynamicAnchor",
        "dynamicAnchor",
    }

    __schema_affecting_extras__: set[str] = {  # noqa: RUF012
        "const",
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

    items: Optional[Union[list[Union[JsonSchemaObject, bool]], JsonSchemaObject, bool]] = None  # noqa: UP007, UP045
    additionalItems: Optional[Union[JsonSchemaObject, bool]] = None  # noqa: N815, UP007, UP045
    prefixItems: Optional[list[Union[JsonSchemaObject, bool]]] = None  # noqa: N815, UP007, UP045
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
    minProperties: Optional[int] = None  # noqa: N815, UP045
    maxProperties: Optional[int] = None  # noqa: N815, UP045
    multipleOf: Optional[float] = None  # noqa: N815, UP045
    exclusiveMaximum: Optional[Union[float, bool]] = None  # noqa: N815, UP007, UP045
    exclusiveMinimum: Optional[Union[float, bool]] = None  # noqa: N815, UP007, UP045
    additionalProperties: Optional[Union[JsonSchemaObject, bool]] = None  # noqa: N815, UP007, UP045
    unevaluatedProperties: Optional[Union[JsonSchemaObject, bool]] = None  # noqa: N815, UP007, UP045
    unevaluatedItems: Optional[Union[JsonSchemaObject, bool]] = None  # noqa: N815, UP007, UP045
    patternProperties: Optional[dict[str, Union[JsonSchemaObject, bool]]] = None  # noqa: N815, UP007, UP045
    propertyNames: Optional[Union[JsonSchemaObject, bool]] = None  # noqa: N815, UP007, UP045
    oneOf: list[Union[JsonSchemaObject, bool]] = Field(default_factory=list)  # noqa: N815, UP007
    anyOf: list[Union[JsonSchemaObject, bool]] = Field(default_factory=list)  # noqa: N815, UP007
    allOf: list[Union[JsonSchemaObject, bool]] = Field(default_factory=list)  # noqa: N815, UP007
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
    x_enum_descriptions: list[str] = Field(default_factory=list, alias="x-enum-descriptions")
    x_enum_names: list[str] = Field(default_factory=list, alias="x-enumNames")
    x_enum_field_as_literal: Optional[bool] = Field(default=None, alias="x-enum-field-as-literal")  # noqa: UP045
    description: Optional[str] = None  # noqa: UP045
    title: Optional[str] = None  # noqa: UP045
    example: Any = None
    examples: Any = None
    default: Any = None
    id: Optional[str] = Field(default=None, alias="$id")  # noqa: UP045
    anchor: Optional[str] = Field(default=None, alias="$anchor")  # noqa: UP045
    custom_type_path: Optional[str] = Field(default=None, alias="customTypePath")  # noqa: UP045
    custom_base_path: str | list[str] | None = Field(default=None, alias="customBasePath")
    is_boolean_schema_false: bool = Field(default=False, exclude=True)
    extras: dict[str, Any] = Field(alias=__extra_key__, default_factory=dict)
    discriminator: Optional[Union[Discriminator, str]] = None  # noqa: UP007, UP045
    model_config = ConfigDict(  # ty: ignore
        arbitrary_types_allowed=True,
        ignored_types=(cached_property,),
    )

    def __init__(self, **data: Any) -> None:
        """Initialize JsonSchemaObject with extra fields handling."""
        super().__init__(**data)
        items = data.get("items")
        if items is False:
            self.items = False
        elif items == []:
            self.items = []
        # Restore extras from alias key (for dict -> parse_obj round-trip)
        alias_extras = data.get(self.__extra_key__, {})
        # Collect custom keys from raw data
        raw_extras = {k: v for k, v in data.items() if k not in EXCLUDE_FIELD_KEYS}
        if alias_extras or raw_extras:
            # Merge: raw_extras takes precedence (original data is the source of truth)
            self.extras = {**alias_extras, **raw_extras}
            if "const" in alias_extras:  # pragma: no cover
                self.extras["const"] = alias_extras["const"]
        # Support x-propertyNames extension for OpenAPI 3.0
        if "x-propertyNames" in self.extras and self.propertyNames is None:
            x_prop_names = self.extras.pop("x-propertyNames")
            if isinstance(x_prop_names, bool):
                self.propertyNames = x_prop_names
            elif isinstance(x_prop_names, dict):
                self.propertyNames = JsonSchemaObject.model_validate(x_prop_names)

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
        return "default" in self.model_fields_set or "default_factory" in self.extras

    @cached_property
    def has_constraint(self) -> bool:
        """Check if the schema has any constraint fields set."""
        return bool(self.__constraint_fields__ & self.model_fields_set)

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
            if not isinstance(item, JsonSchemaObject):
                continue
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
        other_fields = self.model_fields_set - {"ref"}
        schema_affecting_fields = other_fields - self.__metadata_only_fields__ - {"extras"}
        if self.extras:
            schema_affecting_extras = {k for k in self.extras if k in self.__schema_affecting_extras__}
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
        other_fields = self.model_fields_set - {"ref", "nullable"} - self.__metadata_only_fields__ - {"extras"}
        if other_fields:
            return False
        if self.extras:
            schema_affecting_extras = {k for k in self.extras if k in self.__schema_affecting_extras__}
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
    "contentEncoding",
    "contentMediaType",
    "contentSchema",
    "externalDocs",
    "xml",
}

ALLOWED_DEFAULT_FACTORIES: frozenset[str] = frozenset({"dict", "list", "set"})


def _validate_default_factory(default_factory: Any) -> str:
    if isinstance(default_factory, str) and default_factory in ALLOWED_DEFAULT_FACTORIES:
        return default_factory
    allowed_values = ", ".join(sorted(ALLOWED_DEFAULT_FACTORIES))
    msg = f"default_factory must be one of: {allowed_values}"
    raise Error(msg)


def _validate_schema_python_import_path(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        msg = f"{field_name} must be a dotted Python identifier path: {value!r}"
        raise Error(msg)
    try:
        return _validate_dotted_python_identifier_path(value)
    except ValueError as exc:
        msg = f"{field_name} {exc}"
        raise Error(msg) from None


DEFAULT_MODEL_EXTRA_KEYS: set[str] = {
    "contentEncoding",
    "contentMediaType",
    "contentSchema",
    "externalDocs",
    "xml",
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


_DEFAULT_SCHEMA_PATHS = ("#/definitions", "#/$defs")


@snooper_to_methods()  # noqa: PLR0904
class JsonSchemaParser(Parser["JSONSchemaParserConfig", "JsonSchemaFeatures"]):
    """Parser for JSON Schema, JSON, YAML, Dict, and CSV formats."""

    SCHEMA_PATHS: ClassVar[list[str]] = list(_DEFAULT_SCHEMA_PATHS)
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

        # Normalize external ref mapping paths to absolute for reliable matching
        raw_mapping = self.config.external_ref_mapping
        self._external_ref_mapping: dict[str, str] = {}
        if raw_mapping:
            for file_path, python_package in raw_mapping.items():
                if is_url(file_path):
                    self._external_ref_mapping[file_path] = python_package
                else:
                    abs_path = str((self.base_path / file_path).resolve())
                    self._external_ref_mapping[abs_path] = python_package
        self.reserved_refs: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
        self._dynamic_anchor_index: dict[tuple[str, ...], dict[str, str]] = {}
        self._recursive_anchor_index: dict[tuple[str, ...], list[str]] = {}
        self._ref_data_type_facts: dict[str, tuple[Any, bool]] = {}
        self._force_base_model_refs: set[str] = set()
        self._force_base_model_generation = False
        self.field_keys: set[str] = {
            *DEFAULT_FIELD_KEYS,
            *self.field_extra_keys,
            *self.field_extra_keys_without_x_prefix,
        }
        self._circular_ref_cache: dict[str, bool] = {}

        if self.data_model_field_type.can_have_extra_keys:
            self.get_field_extra_key: Callable[[str], str] = lambda key: (
                self.model_resolver.get_valid_field_name_and_alias(key, model_type=self.field_name_model_type)[0]
            )

        else:
            self.get_field_extra_key = lambda key: key

    def get_field_extras(self, obj: JsonSchemaObject) -> dict[str, Any]:
        """Extract extra field metadata from a JSON Schema object."""
        extras = {
            self.get_field_extra_key(k.removeprefix("x-") if k in self.field_extra_keys_without_x_prefix else k): v
            for k, v in obj.extras.items()
            if self.field_include_all_keys or k in self.field_keys
        }
        if self.default_field_extras:
            extras.update(self.default_field_extras)
        if (default_factory := extras.get("default_factory", UNDEFINED)) is not UNDEFINED:
            extras["default_factory"] = _validate_default_factory(default_factory)
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

    def _is_base64_encoded_binary_mapping(self, type_: str, format_: str) -> bool:
        if type_ != "string" or format_ != "byte" or not self.type_mappings:
            return False
        return self.type_mappings.get((type_, format_)) == "binary"

    @cached_property
    def schema_paths(self) -> list[tuple[str, list[str]]]:
        """Get schema paths for definitions and defs.

        For JsonSchema, uses schema_features.definitions_key to determine
        the primary path, with fallback to the alternative in Lenient mode.
        OpenAPI subclass uses its own SCHEMA_PATHS (#/components/schemas).
        """
        # OpenAPI and other subclasses use their own SCHEMA_PATHS
        if list(_DEFAULT_SCHEMA_PATHS) != self.SCHEMA_PATHS:
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
        cls, items: list[JsonSchemaObject | bool], parent_type: str | list[str] | None
    ) -> tuple[list[Any], list[str], list[str], str | None, bool] | None:
        """Extract enum values from oneOf/anyOf const pattern."""
        enum_values: list[Any] = []
        varnames: list[str] = []
        descriptions: list[str] = []
        nullable = False
        inferred_type: str | None = None

        for item in items:
            if item is False:
                continue
            if item is True:
                return None
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
            descriptions.append(item.description or "")

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

        return (enum_values, varnames, descriptions, final_type, nullable)

    def _create_synthetic_enum_obj(  # noqa: PLR0913, PLR0917
        self,
        original: JsonSchemaObject,
        enum_values: list[Any],
        varnames: list[str],
        descriptions: list[str],
        enum_type: str | None,
        nullable: bool,  # noqa: FBT001
    ) -> JsonSchemaObject:
        """Create a synthetic JsonSchemaObject for enum parsing."""
        final_enum = [*enum_values, None] if nullable else enum_values
        final_varnames = varnames if len(varnames) == len(enum_values) else []
        enum_metadata = {"x-enum-varnames": final_varnames}
        if any(descriptions):
            enum_metadata["x-enum-descriptions"] = descriptions

        return self.SCHEMA_OBJECT_TYPE(
            type=enum_type,
            enum=final_enum,
            nullable=nullable,
            title=original.title,
            description=original.description,
            **(enum_metadata | ({"default": original.default} if original.has_default else {})),
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

    def _get_constraint_values(self, obj: JsonSchemaObject) -> dict[str, Any]:  # noqa: PLR6301
        """Return JSON Schema constraint values without serializing nested schemas."""
        return {
            constraint: value
            for constraint in obj.__constraint_field_order__
            if (value := getattr(obj, constraint)) is not None
        }

    def _is_fixed_length_tuple(self, obj: JsonSchemaObject) -> bool:
        """Check if an array field represents a fixed-length tuple."""
        if obj.prefixItems is not None and (obj.items is None or obj.items is False):
            if any(item is False for item in obj.prefixItems):
                return False
            return obj.minItems == obj.maxItems == len(obj.prefixItems)
        if self.use_tuple_for_fixed_items and isinstance(obj.items, list) and obj.prefixItems is None:
            if any(item is False for item in obj.items):
                return False
            return obj.minItems == obj.maxItems == len(obj.items)
        return False

    @classmethod
    def _get_fixed_length_prefix_tuple_items(cls, obj: JsonSchemaObject) -> list[JsonSchemaObject | bool] | None:
        """Return positional item schemas for fixed-length prefixItems arrays."""
        if (
            obj.prefixItems is None
            or obj.minItems is None
            or obj.maxItems is None
            or obj.minItems != obj.maxItems
            or obj.minItems < 0
        ):  # pragma: no cover
            return None

        tuple_length = obj.minItems
        prefix_items = obj.prefixItems
        if any(item is False for item in prefix_items[:tuple_length]):  # pragma: no cover
            return None

        items = [*prefix_items[:tuple_length]]
        if len(items) == tuple_length:
            return items

        if isinstance(obj.items, (JsonSchemaObject, bool)):
            tail_item: JsonSchemaObject | bool = obj.items
        elif isinstance(obj.unevaluatedItems, (JsonSchemaObject, bool)):
            tail_item = obj.unevaluatedItems
        else:
            tail_item = True
        if tail_item is False:  # pragma: no cover
            return None

        items.extend(tail_item for _ in range(tuple_length - len(items)))
        return items

    @classmethod
    def _get_schemas_before_false(
        cls, items: Sequence[JsonSchemaObject | bool] | None
    ) -> tuple[list[JsonSchemaObject | bool], bool]:
        """Return schemas before the first false schema and whether one was found."""
        schema_items = [*(items or [])]
        if (false_index := cls._get_first_false_schema_index(schema_items)) is not None:
            return schema_items[:false_index], True
        return schema_items, False

    @staticmethod
    def _tail_schema(
        *tail_candidates: JsonSchemaObject | bool | list[JsonSchemaObject | bool] | None,
        include_true_schema: bool = False,
    ) -> JsonSchemaObject | bool | None:
        for tail_candidate in tail_candidates:
            match tail_candidate:
                case JsonSchemaObject() as tail_schema:
                    return tail_schema
                case True if include_true_schema:
                    return True
        return None

    def _get_array_item_schemas(  # noqa: PLR0911
        self,
        obj: JsonSchemaObject,
        *,
        include_true_tail_schema: bool = False,
        force_prefix_items: bool = False,
    ) -> tuple[list[JsonSchemaObject | bool], bool, bool]:
        """Return item schemas plus tuple/constraint flags for array-like schemas."""
        if (
            obj.prefixItems is not None
            and obj.minItems is not None
            and obj.minItems == obj.maxItems
            and (fixed_items := self._get_fixed_length_prefix_tuple_items(obj)) is not None
        ):
            return fixed_items, True, True

        if obj.prefixItems is not None and (force_prefix_items or self._has_prefix_items_tail_schema_or_boolean(obj)):
            items, has_false_schema = self._get_schemas_before_false(obj.prefixItems)
            if (
                not has_false_schema
                and (
                    tail_schema := self._tail_schema(
                        obj.items,
                        obj.unevaluatedItems,
                        include_true_schema=include_true_tail_schema,
                    )
                )
                is not None
            ):
                items.append(tail_schema)
            return items, False, False

        match obj.items:
            case JsonSchemaObject() as item_schema:
                return [item_schema], False, False
            case list() as item_schemas:
                items, has_false_schema = self._get_schemas_before_false(item_schemas)
                if self._is_fixed_length_tuple(obj):
                    return items, True, True
                if (
                    not has_false_schema
                    and (
                        tail_schema := self._tail_schema(
                            obj.additionalItems,
                            include_true_schema=include_true_tail_schema,
                        )
                    )
                    is not None
                ):
                    items.append(tail_schema)
                return items, False, False

        match obj.unevaluatedItems:
            case JsonSchemaObject() as item_schema:
                return [item_schema], False, False
            case True if include_true_tail_schema:
                return [True], False, False

        return [], False, False

    @classmethod
    def _get_property_count_constraints(cls, obj: JsonSchemaObject) -> dict[str, int]:
        """Return dict length constraints derived from object property-count keywords."""
        constraints: dict[str, int] = {}
        if obj.minProperties is not None:
            constraints["minItems"] = obj.minProperties
        if obj.maxProperties is not None:
            constraints["maxItems"] = obj.maxProperties
        if cls._property_names_forbids_all_keys(obj.propertyNames):
            constraints["maxItems"] = 0
        if obj.additionalProperties is False and not obj.properties and not obj.patternProperties:
            constraints["maxItems"] = 0
        if (
            obj.additionalProperties is False
            and obj.patternProperties
            and all(value is False for value in obj.patternProperties.values())
            and not obj.properties
        ):
            constraints["maxItems"] = 0
        return constraints

    def _should_parse_empty_object_as_dict(self, obj: JsonSchemaObject) -> bool:  # noqa: PLR6301
        return bool(obj.minProperties is not None or obj.maxProperties is not None or obj.propertyNames is not None)

    @staticmethod
    def _property_names_forbids_all_keys(property_names: JsonSchemaObject | bool | None) -> bool:  # noqa: FBT001
        """Return whether a propertyNames schema rejects every JSON object key."""
        if property_names is False:
            return True
        if not isinstance(property_names, JsonSchemaObject):
            return False
        forbids_all_keys = bool(
            property_names.enum and not any(isinstance(value, str) for value in property_names.enum)
        )
        forbids_all_keys = forbids_all_keys or (
            "const" in property_names.extras and not isinstance(property_names.extras["const"], str)
        )
        if isinstance(property_names.type, str):
            forbids_all_keys = forbids_all_keys or property_names.type != "string"
        elif isinstance(property_names.type, list):
            forbids_all_keys = forbids_all_keys or "string" not in property_names.type
        return forbids_all_keys

    @classmethod
    def _get_array_max_items_constraints(cls, obj: JsonSchemaObject) -> list[int]:
        max_items: list[int] = []
        false_prefix_index = cls._get_first_false_schema_index(obj.prefixItems)
        if false_prefix_index is not None:
            max_items.append(false_prefix_index)
        if isinstance(obj.items, list):
            false_item_index = cls._get_first_false_schema_index(obj.items)
            if false_item_index is not None:
                max_items.append(false_item_index)
        if obj.items is False and obj.prefixItems is None:
            max_items.append(0)
        if obj.items is False and obj.prefixItems is not None:
            max_items.append(len(obj.prefixItems))
        if obj.additionalItems is False and isinstance(obj.items, list):
            max_items.append(len(obj.items))
        if obj.unevaluatedItems is False and obj.items is None:
            max_items.append(len(obj.prefixItems or []))
        return max_items

    @staticmethod
    def _contains_matches_every_item(obj: JsonSchemaObject) -> bool:
        contains = obj.extras.get("contains")
        return contains is True or contains == {}

    @classmethod
    def _get_contains_count_constraints(cls, obj: JsonSchemaObject) -> tuple[int | None, int | None]:
        if not cls._contains_matches_every_item(obj):
            return None, None

        min_contains = obj.extras.get("minContains")
        max_contains = obj.extras.get("maxContains")
        min_items = (
            min_contains
            if isinstance(min_contains, int) and not isinstance(min_contains, bool) and min_contains > 0
            else 1
            if "minContains" not in obj.extras
            else None
        )
        max_items = max_contains if isinstance(max_contains, int) and not isinstance(max_contains, bool) else None
        return min_items, max_items

    @staticmethod
    def _contains_false_requires_match(obj: JsonSchemaObject) -> bool:
        if obj.extras.get("contains") is not False:
            return False
        if "minContains" not in obj.extras:
            return True
        min_contains = obj.extras["minContains"]
        return isinstance(min_contains, int) and not isinstance(min_contains, bool) and min_contains > 0

    @classmethod
    def _get_array_items_constraints(cls, obj: JsonSchemaObject) -> dict[str, int]:
        """Return array length constraints derived from boolean items."""
        min_items: list[int] = []
        max_items = cls._get_array_max_items_constraints(obj)
        if cls._contains_matches_every_item(obj):
            contains_min_items, contains_max_items = cls._get_contains_count_constraints(obj)
            if contains_min_items is not None:
                min_items.append(contains_min_items)
            if contains_max_items is not None:
                max_items.append(contains_max_items)
        elif cls._contains_false_requires_match(obj):
            min_items.append(1)
            max_items.append(0)

        constraints: dict[str, int] = {}
        if min_items:
            if obj.minItems is not None:
                min_items.append(obj.minItems)
            constraints["minItems"] = max(min_items)
        if max_items:
            if obj.maxItems is not None:
                max_items.append(obj.maxItems)
            constraints["maxItems"] = min(max_items)
        return constraints

    @classmethod
    def _get_first_false_schema_index(cls, items: Sequence[JsonSchemaObject | bool] | None) -> int | None:
        """Return the first tuple/prefix item index that rejects every value."""
        if items is None:
            return None
        return next((index for index, item in enumerate(items) if item is False), None)

    def _has_prefix_items_tail_schema_or_boolean(self, obj: JsonSchemaObject) -> bool:  # noqa: PLR6301
        return bool(
            obj.prefixItems is not None
            and (
                obj.items is False
                or isinstance(obj.items, JsonSchemaObject)
                or obj.unevaluatedItems is False
                or isinstance(obj.unevaluatedItems, JsonSchemaObject)
                or any(isinstance(item, bool) for item in obj.prefixItems)
            )
        )

    def _suppress_array_length_constraints(self, constraints: dict[str, Any] | None, obj: JsonSchemaObject) -> None:
        if not constraints:
            return
        fixed_prefix_tuple_items = (
            self._get_fixed_length_prefix_tuple_items(obj)
            if obj.prefixItems is not None and obj.minItems is not None and obj.minItems == obj.maxItems
            else None
        )
        if self._is_fixed_length_tuple(obj) or fixed_prefix_tuple_items is not None:
            constraints.pop("minItems", None)
            constraints.pop("maxItems", None)

    def _resolve_array_field_required_nullable(self, obj: JsonSchemaObject) -> tuple[bool, bool | None]:
        if self.force_optional_for_required_fields:
            return False, None

        required = not obj.has_default
        if self.strict_nullable:
            return required, obj.nullable if obj.has_default or required else True

        required = not obj.nullable and required
        if obj.nullable:
            return required, True
        if obj.has_default:
            return required, False
        return required, None

    def _fallback_array_item_data_types(self) -> list[DataType]:
        return [
            self.data_type_manager.data_type(type="object")
            if self.data_type_manager.use_object_type
            else self.data_type_manager.get_data_type(Types.any)
        ]

    def _get_scalar_data_type_from_json_value(self, value: object) -> DataType | None:
        """Infer a normal Python type from a scalar JSON value."""
        if value is None:
            return self.data_type_manager.get_data_type(Types.null)
        if isinstance(value, bool):
            return self.data_type_manager.get_data_type(Types.boolean)
        if isinstance(value, int):
            return self.data_type_manager.get_data_type(Types.integer)
        if isinstance(value, float):
            return self.data_type_manager.get_data_type(Types.float)
        if isinstance(value, str):
            return self.data_type_manager.get_data_type(Types.string)
        return None

    def _get_data_type_from_json_value(self, value: object) -> DataType:
        """Infer a normal Python type from a JSON value."""
        scalar_type = self._get_scalar_data_type_from_json_value(value)
        if scalar_type is not None:
            return scalar_type
        if isinstance(value, list):
            item_types = [self._get_data_type_from_json_value(item) for item in value]
            return self.data_type(
                data_types=item_types or [self.data_type(type=ANY, import_=IMPORT_ANY)],
                is_list=True,
            )
        if isinstance(value, dict):
            value_types = [self._get_data_type_from_json_value(item) for item in value.values()]
            return self.data_type(
                data_types=value_types or [self.data_type(type=ANY, import_=IMPORT_ANY)],
                is_dict=True,
            )
        return self.data_type_manager.get_data_type(Types.any)

    def _get_const_data_type(self, const: object) -> DataType:
        """Return a DataType for a JSON Schema const value."""
        if isinstance(const, (bool, int, str)):
            return self.data_type(literals=[const])
        return self._get_data_type_from_json_value(const)

    def _partition_enum_values(  # noqa: PLR6301
        self, enum_values: list[Any]
    ) -> tuple[list[JsonSchemaLiteral], list[object], bool]:
        """Split enum values into literal and non-literal values."""
        literal_values: list[JsonSchemaLiteral] = []
        non_literal_values: list[object] = []
        has_null = False
        for enum_value in enum_values:
            if enum_value is None:
                has_null = True
                non_literal_values.append(enum_value)
            elif isinstance(enum_value, (bool, int, str)):
                literal_values.append(enum_value)
            else:
                non_literal_values.append(enum_value)
        return literal_values, non_literal_values, has_null

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
        return any(
            self._resolve_field_flag(sub, flag)
            for sub in obj.allOf + obj.anyOf + obj.oneOf
            if isinstance(sub, JsonSchemaObject)
        )

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
                if not isinstance(item, JsonSchemaObject):  # pragma: no cover
                    continue
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
        if self._force_base_model_generation:
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

    def _preload_property_refs_for_rw_models(self, obj: JsonSchemaObject) -> None:
        """Preload property refs needed for readOnly/writeOnly model splitting."""
        if self.read_only_write_only_model_type is None or not obj.properties:
            return
        for prop in obj.properties.values():
            if isinstance(prop, JsonSchemaObject) and prop.ref and self._resolve_external_ref_mapping(prop.ref) is None:
                self._load_ref_schema_object(prop.ref)

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
                self.generation_store.replace_data_type_ref(data_type, variant_ref)
            elif not self._ref_schema_has_model(ref_path):  # pragma: no branch
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
        with self.generation_store.defer_refresh():
            for field in model_fields:
                if field.data_type:  # pragma: no branch
                    self._update_data_type_ref_for_variant(field.data_type, suffix)
        return model_fields

    def _generate_forced_base_models(self) -> None:
        """Generate base models for schemas that are referenced as property types but lack models."""
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
        self._set_schema_metadata(reference.path, obj)
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
        self.generation_store.register_model(model)

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
        use_default_with_required: bool = False,
        class_name: str | None = None,
    ) -> DataModelFieldBase:
        """Create a data model field from a JSON Schema object field."""
        default_value = effective_default if effective_has_default is not None else field.default
        has_default = effective_has_default if effective_has_default is not None else field.has_default

        constraints = self._get_constraint_values(field) if self.is_constraints_field(field) else None
        consumed = self.data_type_manager.CONSTRAINED_TYPE_CONSUMED_KEYS
        if constraints is not None and field_type.type in consumed:
            for key in consumed[field_type.type]:
                constraints.pop(key, None)
        if constraints is not None and self.field_constraints and field.format == "hostname":
            constraints["pattern"] = self.data_type_manager.HOSTNAME_REGEX
        if field_type.is_dict or field_type.is_mapping:
            property_count_constraints = self._get_property_count_constraints(field)
            if property_count_constraints:
                constraints = constraints or {}
                constraints.update(property_count_constraints)
        array_items_constraints = self._get_array_items_constraints(field)
        if array_items_constraints:
            constraints = constraints or {}
            constraints.update(array_items_constraints)
        self._suppress_array_length_constraints(constraints, field)
        single_alias, validation_aliases = self._split_alias(alias)
        serialization_alias = (
            self.get_serialization_alias(original_field_name, field_name, class_name)
            if original_field_name and field_name
            else None
        )
        return self.data_model_field_type(
            name=field_name,
            default=default_value,
            data_type=field_type,
            required=required,
            alias=single_alias,
            validation_aliases=validation_aliases,
            serialization_alias=serialization_alias,
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
            use_default_with_required=use_default_with_required,
        )

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        """Get the data type for a JSON Schema object."""
        python_type_override = self._get_python_type_override(obj)
        if python_type_override:  # pragma: no cover
            return python_type_override

        if "const" in obj.extras:
            return self._get_const_data_type(obj.extras["const"])

        if obj.type is None:
            return self.data_type_manager.get_data_type(
                Types.any,
            )

        def _get_data_type(type_: str, format__: str) -> DataType:
            if self.field_constraints:
                # To prevent type manager from generating conint/confloat,
                # we only pass constraints that perfectly match specialized types
                # (like NonNegativeInt -> minimum: 0).
                # Other constraints should remain on Field(), so we pass {}
                kwargs_to_pass = {}
                number_keys = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")
                number_kwargs: dict[str, int | float | bool] = {}
                for key in number_keys:
                    value = getattr(obj, key)
                    if value is not None:
                        number_kwargs[key] = value.value if isinstance(value, UnionIntFloat) else value

                if self.data_type_manager.use_non_positive_negative_number_constrained_types:
                    zero_bound_keys = [k for k, v in number_kwargs.items() if v == 0]
                    if len(zero_bound_keys) == 1:
                        key = zero_bound_keys[0]
                        kwargs_to_pass = {key: number_kwargs[key]}
            else:
                kwargs_to_pass = obj.model_dump()

            types = self._get_type_with_mappings(type_, format__)
            if types == Types.binary and self._is_base64_encoded_binary_mapping(type_, format__):
                kwargs_to_pass["base64_encoded"] = True

            return self.data_type_manager.get_data_type(
                types,
                field_constraints=self.field_constraints,
                **kwargs_to_pass,
            )

        if isinstance(obj.type, list):
            data_types = [_get_data_type(t, obj.format or "default") for t in obj.type if t != "null"]
            return (
                self.data_type(
                    data_types=data_types,
                    is_optional=len(data_types) != len(obj.type),
                )
                if data_types
                else self.data_type_manager.get_data_type(Types.null)
            )
        data_type = _get_data_type(obj.type, obj.format or "default")
        if self.strict_nullable and obj.nullable:
            return self.data_type(data_types=[data_type], is_optional=True)
        return data_type

    def _resolve_external_ref_mapping(self, ref: str) -> tuple[str, str] | None:
        """Resolve a ref and return mapped package + fragment if configured."""
        if not self._external_ref_mapping:
            return None

        def _resolve_lookup_key(file_part: str) -> str:
            if is_url(file_part):
                return file_part
            path = Path(file_part)
            if path.is_absolute():
                return str(path.resolve())
            base_path = self.model_resolver.current_base_path or self.base_path
            return str((base_path / path).resolve())

        candidate_refs = [ref]
        resolved_ref = self.model_resolver.resolve_ref(ref)
        if resolved_ref not in candidate_refs:
            candidate_refs.append(resolved_ref)

        for candidate_ref in candidate_refs:
            if "#" not in candidate_ref:
                continue
            file_part, fragment = candidate_ref.split("#", maxsplit=1)
            if not file_part:
                continue
            lookup_key = _resolve_lookup_key(file_part)
            if python_package := self._external_ref_mapping.get(lookup_key):
                return python_package, fragment

        return None

    def _check_external_ref_mapping(self, ref: str) -> DataType | None:
        """Check if a $ref matches an external ref mapping and return an import-based DataType.

        Splits the ref into file path + JSON pointer fragment, resolves the file path
        to absolute, and checks against the normalized mapping. If matched, constructs
        an import from the mapped package and the class name extracted from the fragment.

        Returns None if no mapping matches, allowing the caller to fall through
        to normal ref resolution.
        """
        mapped = self._resolve_external_ref_mapping(ref)
        if mapped is None:
            return None
        python_package, fragment = mapped

        # Extract and normalize class name from fragment to match generated model naming.
        raw_name = unescape_json_pointer_segment(fragment.rstrip("/").rsplit("/", maxsplit=1)[-1])
        if not raw_name:
            return None
        class_name = self.model_resolver.get_class_name(raw_name, unique=False).name

        # Construct import — same pattern as x-python-import
        full_path = f"{python_package}.{class_name}"
        import_ = Import.from_full_path(full_path)
        self.imports.append(import_)
        return self.data_type.from_import(import_)

    def _get_x_python_import_path(self, x_python_import: dict[str, Any]) -> str | None:  # noqa: PLR6301
        module = x_python_import.get("module")
        type_name = x_python_import.get("name")
        if not module and not type_name:
            return None
        if not module or not type_name:
            msg = "x-python-import requires both module and name"
            raise Error(msg)
        return _validate_schema_python_import_path(f"{module}.{type_name}", "x-python-import")

    def get_ref_data_type(self, ref: str) -> DataType:
        """Get a data type from a reference string.

        The referenced schema only contributes its x-python-import extra and
        null/nullable flags here, so those facts are cached per resolved ref to
        avoid re-validating the same schema for every occurrence of the ref.
        """
        # Check external ref mapping before loading the schema
        mapped = self._check_external_ref_mapping(ref)
        if mapped is not None:
            return mapped

        resolved_ref = self.model_resolver.resolve_ref(ref)
        if (facts := self._ref_data_type_facts.get(resolved_ref)) is None:
            ref_schema = self._load_ref_schema_object(ref)
            facts = (
                ref_schema.extras.get("x-python-import"),
                ref_schema.type == "null" or (self.strict_nullable and ref_schema.nullable is True),
            )
            self._ref_data_type_facts[resolved_ref] = facts
        x_python_import, is_optional = facts
        if isinstance(x_python_import, dict) and (full_path := self._get_x_python_import_path(x_python_import)):
            import_ = Import.from_full_path(full_path)
            self.imports.append(import_)
            return self.data_type.from_import(import_)
        reference = self.model_resolver.add_ref(ref)
        return self.data_type(reference=reference, is_optional=is_optional)

    def set_additional_properties(self, path: str, obj: JsonSchemaObject) -> None:
        """Set additional properties flag in extra template data.

        For TypedDict with PEP 728 support:
        - additionalProperties: false -> closed=True
        - additionalProperties: { type: X } -> extra_items=X

        This is controlled by use_closed_typed_dict option. When disabled,
        the additionalProperties constraint is not converted to PEP 728 syntax.
        """
        if isinstance(obj.additionalProperties, bool):
            if not self.use_closed_typed_dict:
                return
            self.extra_template_data[path]["additionalProperties"] = obj.additionalProperties
            if obj.additionalProperties is False and not self.target_python_version.has_typed_dict_closed:
                self.extra_template_data[path]["use_typeddict_backport"] = True
        elif isinstance(obj.additionalProperties, JsonSchemaObject):
            # A schema-valued additionalProperties still means extra keys are accepted.
            # Keep typed extra validation out of this bugfix; PEP 728 TypedDict uses
            # additionalPropertiesType below when explicitly enabled.
            self.extra_template_data[path]["additionalProperties"] = True
            if not self.use_closed_typed_dict:
                return
            additional_props_type = self._build_lightweight_type(obj.additionalProperties)
            if additional_props_type:  # pragma: no branch
                self.extra_template_data[path]["additionalPropertiesType"] = additional_props_type.type_hint
                if issubclass(self.data_model_type, TypedDictModel) and (
                    reference_classes := {
                        data_type.reference.path
                        for data_type in additional_props_type.all_data_types
                        if data_type.reference
                    }
                ):
                    self.extra_template_data[path]["additionalPropertiesReferenceClasses"] = reference_classes
                if not self.target_python_version.has_typed_dict_closed:  # pragma: no branch
                    self.extra_template_data[path]["use_typeddict_backport"] = True

    def set_unevaluated_properties(self, path: str, obj: JsonSchemaObject) -> None:
        """Set unevaluated properties flag in extra template data."""
        if isinstance(obj.unevaluatedProperties, bool):
            self.extra_template_data[path]["unevaluatedProperties"] = obj.unevaluatedProperties
        elif isinstance(obj.unevaluatedProperties, JsonSchemaObject) and obj.additionalProperties is None:
            # Schema-valued unevaluatedProperties allows extra keys. Its value
            # schema would require generated typed-extra validation, which is out
            # of scope for this bugfix.
            self.extra_template_data[path]["unevaluatedProperties"] = True

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
        self.set_deprecated(path, obj)

    def set_deprecated(self, path: str, obj: JsonSchemaObject) -> None:
        """Set deprecated flag in extra template data."""
        if obj.extras.get("deprecated") is True:
            self.extra_template_data[path]["deprecated"] = True

    def set_schema_extensions(self, path: str, obj: JsonSchemaObject) -> None:
        """Set schema extensions (x-* fields) in extra template data."""
        extensions = {k: v for k, v in obj.extras.items() if k.startswith("x-")}
        if extensions:
            self.extra_template_data[path]["extensions"] = extensions

        if obj.extras.get("x-is-base-class"):
            self.extra_template_data[path]["is_base_class"] = True

        # Process model-level metadata and model_extra_keys for json_schema_extra in ConfigDict
        model_extras: dict[str, Any] = {k: v for k, v in obj.extras.items() if k in DEFAULT_MODEL_EXTRA_KEYS}
        if self.model_extra_keys or self.model_extra_keys_without_x_prefix:
            for k, v in obj.extras.items():
                if self.model_extra_keys and k in self.model_extra_keys:
                    model_extras[k] = v
                elif self.model_extra_keys_without_x_prefix and k in self.model_extra_keys_without_x_prefix:
                    # Strip the x- prefix
                    model_extras[k.lstrip("x-")] = v
        if model_extras:
            self.extra_template_data[path]["model_extras"] = model_extras

    def _get_python_type_flags(self, obj: JsonSchemaObject) -> dict[str, bool]:
        """Get container type flags from x-python-type extension.

        Returns a dict with flags like is_set, is_frozen_set, is_mapping, is_sequence
        that can be passed to data_type() to override the default container type.

        Note: This is an instance method (not static) due to the snooper_to_methods
        class decorator which does not preserve staticmethod descriptors.
        """
        if (x_python_type := self._get_x_python_type(obj)) is None:
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

    def _get_x_python_type(self, obj: JsonSchemaObject) -> str | None:  # noqa: PLR6301
        """Return a validated x-python-type value."""
        x_python_type = obj.extras.get("x-python-type")
        if not x_python_type or not isinstance(x_python_type, str):
            return None
        if is_python_type_annotation(x_python_type):
            return x_python_type
        msg = "x-python-type must be a valid Python type annotation"
        raise Error(msg)

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
        return type(self)._resolve_type_import_dynamic(type_name)  # noqa: SLF001

    def _resolve_type_import_from_defs(self, type_name: str) -> Import | None:
        """Resolve import for a type name from $defs with x-python-import."""
        try:
            ref_schema = self._load_ref_schema_object(f"#/$defs/{type_name}")
            x_python_import = ref_schema.extras.get("x-python-import")
            if isinstance(x_python_import, dict) and (full_path := self._get_x_python_import_path(x_python_import)):
                return Import.from_full_path(full_path)
        except Error:
            raise
        except Exception:  # noqa: BLE001, S110
            pass
        return None

    def _get_python_type_override(self, obj: JsonSchemaObject) -> DataType | None:
        """Get DataType from x-python-type if it's incompatible with schema type."""
        if (x_python_type := self._get_x_python_type(obj)) is None:
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
            pointer = split_json_pointer(raw_doc, fragment)
            target_schema = get_model_by_path(raw_doc, pointer)

        return self._validate_schema_object(target_schema, [resolved_ref])

    def _anchor_ref_path(self, root_key: tuple[str, ...], path: list[str]) -> str:  # noqa: PLR6301
        """Return the local ref path for an anchor under the current root."""
        root_len = len(root_key)
        if root_len >= len(path):
            return "#"
        suffix_parts = path[root_len:]
        first = suffix_parts[0]
        if first.startswith("#"):
            suffix_parts = [first[1:].lstrip("/"), *suffix_parts[1:]]
        return "#/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in suffix_parts if part)

    def _build_anchor_indexes(self, obj: JsonSchemaObject, path: list[str]) -> None:
        """Build $recursiveAnchor and $dynamicAnchor indexes for a schema object."""
        root_key = tuple(self.model_resolver.current_root)
        ref_path = self._anchor_ref_path(root_key, path)
        if obj.recursiveAnchor:
            anchors = self._recursive_anchor_index.setdefault(root_key, [])
            if ref_path not in anchors:
                anchors.append(ref_path)
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
        current_ref = self._anchor_ref_path(root_key, path)
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

        resolved_ref = self.model_resolver.resolve_ref(obj.ref)
        if self._is_ref_circular(resolved_ref):
            return obj

        ref_schema = self._load_ref_schema_object(obj.ref)
        ref_dict = ref_schema.model_dump(exclude_unset=True, by_alias=True)
        current_dict = obj.model_dump(exclude={"ref"}, exclude_unset=True, by_alias=True)
        merged = self._deep_merge(ref_dict, current_dict)
        merged.pop("$ref", None)

        return self.SCHEMA_OBJECT_TYPE.model_validate(merged)

    def _is_ref_circular(self, resolved_ref: str) -> bool:
        """Check if a resolved $ref target contains a circular reference (cached)."""
        if resolved_ref in self._circular_ref_cache:
            return self._circular_ref_cache[resolved_ref]
        try:
            result = self._has_ref_cycle(resolved_ref, resolved_ref, set())
        except Exception:  # noqa: BLE001  # pragma: no cover
            result = True
        self._circular_ref_cache[resolved_ref] = result
        return result

    def _has_ref_cycle(self, ref_to_check: str, target: str, visited: set[str]) -> bool:
        """Check if the schema at ref_to_check contains a reference back to target."""
        visited.add(ref_to_check)
        file_part, _, fragment = ref_to_check.partition("#")
        if file_part and is_url(file_part):
            base_path = None
            root_path = [file_part]
        else:
            base_path = Path(file_part).parent if file_part else self.model_resolver.current_base_path
            root_path = file_part.split("/") if file_part else self.model_resolver.current_root
        base_url = file_part or self.model_resolver.base_url
        with (
            self.model_resolver.current_base_path_context(base_path),
            self.model_resolver.base_url_context(base_url),
            self.model_resolver.current_root_context(root_path),
        ):
            raw_doc = self._get_ref_body(file_part) if file_part else self.raw_obj
            raw_obj: Any = raw_doc
            if fragment:
                pointer = [p for p in fragment.split("/") if p]
                raw_obj = get_model_by_path(raw_doc, pointer)
            return self._walk_for_ref(raw_obj, target, visited)

    def _walk_for_ref(self, data: dict[str, Any] | list[Any], target: str, visited: set[str]) -> bool:
        """Recursively walk raw dict/list data looking for a $ref that resolves to target."""
        if isinstance(data, dict):
            ref_value = data.get("$ref")
            if isinstance(ref_value, str):
                try:
                    resolved = self.model_resolver.resolve_ref(ref_value)
                except Exception:  # noqa: BLE001
                    resolved = ref_value
                if resolved == target:
                    return True
                if resolved not in visited and self._has_ref_cycle(resolved, target, visited):
                    return True
            for value in data.values():
                if isinstance(value, (dict, list)) and self._walk_for_ref(value, target, visited):
                    return True
            return False
        return any(isinstance(item, (dict, list)) and self._walk_for_ref(item, target, visited) for item in data)

    def _merge_primitive_schemas(self, items: list[JsonSchemaObject]) -> JsonSchemaObject:
        """Merge multiple primitive schemas by computing the intersection of their constraints."""
        if len(items) == 1:
            return items[0]

        base_dict = JsonSchemaParser._first_typed_schema_dict(items)
        self._merge_schema_constraints(base_dict, items, intersect=True)

        return self.SCHEMA_OBJECT_TYPE.model_validate(base_dict)

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
            merged_dict = merged.model_dump(exclude_unset=True, by_alias=True)
            if merged_format:
                merged_dict["format"] = merged_format
            return self.SCHEMA_OBJECT_TYPE.model_validate(merged_dict)

        base_dict = JsonSchemaParser._first_typed_schema_dict(items)
        self._merge_schema_constraints(base_dict, items, intersect=False)

        if merged_format:
            base_dict["format"] = merged_format

        return self.SCHEMA_OBJECT_TYPE.model_validate(base_dict)

    @staticmethod
    def _first_typed_schema_dict(items: list[JsonSchemaObject]) -> dict[str, Any]:
        return next(
            (item.model_dump(exclude_unset=True, by_alias=True) for item in items if item.type),
            {},
        )

    @staticmethod
    def _schema_constraint_value(item: JsonSchemaObject, field: str) -> Any:
        return value if (value := getattr(item, field, None)) is not None else item.extras.get(field)

    @classmethod
    def _merge_schema_constraints(
        cls,
        base_dict: dict[str, Any],
        items: list[JsonSchemaObject],
        *,
        intersect: bool,
    ) -> None:
        for item in items:
            for field in JsonSchemaObject.__constraint_fields__:
                if (value := cls._schema_constraint_value(item, field)) is None:
                    continue
                if intersect and field in base_dict and base_dict[field] is not None:
                    base_dict[field] = cls._intersect_constraint(field, base_dict[field], value)
                else:
                    base_dict[field] = value

    @staticmethod
    def _intersect_multiple_of(val1: object, val2: object) -> object:
        """Return the least common multiple for JSON Schema multipleOf values."""
        with suppress(TypeError, ValueError, ZeroDivisionError):
            multiple_1 = Fraction(str(val1))
            multiple_2 = Fraction(str(val2))
            merged = Fraction(
                lcm(multiple_1.numerator, multiple_2.numerator),
                gcd(multiple_1.denominator, multiple_2.denominator),
            )
            return merged.numerator if merged.denominator == 1 else float(merged)
        return val1  # pragma: no cover

    @staticmethod
    def _intersect_constraint(field: str, val1: Any, val2: Any) -> Any:  # noqa: PLR0911
        """Compute the intersection of two constraint values."""
        v1: float | None = None
        v2: float | None = None
        with suppress(TypeError, ValueError):
            v1 = float(val1) if val1 is not None else None
            v2 = float(val2) if val2 is not None else None

        match field:
            case "minLength" | "minimum" | "exclusiveMinimum" | "minItems":
                if v1 is not None and v2 is not None:
                    return val1 if v1 >= v2 else val2
                return val1  # pragma: no cover
            case "maxLength" | "maximum" | "exclusiveMaximum" | "maxItems":
                if v1 is not None and v2 is not None:
                    return val1 if v1 <= v2 else val2
                return val1  # pragma: no cover
            case "pattern":
                return f"(?={val1})(?={val2})" if val1 != val2 else val1
            case "uniqueItems":
                return val1 or val2
            case "multipleOf":
                return JsonSchemaParser._intersect_multiple_of(val1, val2)
        return val1  # pragma: no cover

    def _build_allof_type(  # noqa: PLR0911, PLR0912, PLR0913, PLR0915, PLR0917
        self,
        allof_items: Sequence[JsonSchemaObject | bool],
        depth: int,
        visited: frozenset[int],
        max_depth: int,
        max_union_elements: int,
        warn_on_ref_constraints: bool = True,  # noqa: FBT001, FBT002
    ) -> DataType | None:
        """Build a DataType from allOf schema items."""
        if any(self._is_false_schema_item(item) for item in allof_items):
            return None
        allof_effective_items = [item for item in allof_items if isinstance(item, JsonSchemaObject)]
        if not allof_effective_items:
            return DataType(type=ANY, import_=IMPORT_ANY)
        if len(allof_effective_items) == 1:
            item = allof_effective_items[0]
            if item.ref:
                return self.get_ref_data_type(item.ref)
            return self._build_lightweight_type(item, depth + 1, visited, max_depth, max_union_elements)

        ref_items: list[JsonSchemaObject] = []
        ref_data_types: list[DataType] = []
        primitive_items: list[JsonSchemaObject] = []
        constraint_only_items: list[JsonSchemaObject] = []
        object_items: list[JsonSchemaObject] = []

        for item in allof_effective_items:
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
                    ref_data_types.append(nested_type)
                else:
                    primitive_items.append(item)
            elif item.enum:  # pragma: no cover
                primitive_items.append(item)
            elif item.has_constraint:
                constraint_only_items.append(item)

        if (ref_items or ref_data_types) and not primitive_items and not object_items:
            if ref_data_types:
                return ref_data_types[0]
            ref = ref_items[0].ref
            if ref:
                return self.get_ref_data_type(ref)
            return None  # pragma: no cover

        if (ref_items or ref_data_types) and (primitive_items or object_items or constraint_only_items):
            ignored_count = len(primitive_items) + len(constraint_only_items)
            if warn_on_ref_constraints and ignored_count > 0:
                warn(
                    f"allOf combines $ref with {ignored_count} constraint(s) that will be ignored "
                    f"in inherited field type resolution. Consider defining constraints in the referenced schema.",
                    stacklevel=4,
                )
            if ref_data_types:
                return ref_data_types[0]
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

    def _build_lightweight_array_type(
        self,
        schema: JsonSchemaObject,
        depth: int,
        visited: frozenset[int],
        max_depth: int,
        max_union_elements: int,
    ) -> DataType:
        """Build a lightweight list type from array item schemas."""
        item_schemas, _, _ = self._get_array_item_schemas(
            schema,
            include_true_tail_schema=True,
            force_prefix_items=True,
        )
        item_types = [
            item_type
            for item_schema in item_schemas
            if (
                item_type := self._build_lightweight_item_type(
                    item_schema, depth, visited, max_depth, max_union_elements
                )
            )
            is not None
        ]
        return self.data_type(
            data_types=item_types or [DataType(type=ANY, import_=IMPORT_ANY)],
            is_list=True,
        )

    def _build_lightweight_item_type(
        self,
        item_schema: JsonSchemaObject | bool,  # noqa: FBT001
        depth: int,
        visited: frozenset[int],
        max_depth: int,
        max_union_elements: int,
    ) -> DataType | None:
        if item_schema is False:
            return None  # pragma: no cover
        if item_schema is True:
            return DataType(type=ANY, import_=IMPORT_ANY)
        if item_schema.ref:
            return self.get_ref_data_type(item_schema.ref)
        return self._build_lightweight_type(item_schema, depth + 1, visited, max_depth, max_union_elements) or DataType(
            type=ANY, import_=IMPORT_ANY
        )

    def _is_false_schema_item(self, item: JsonSchemaObject | bool) -> bool:  # noqa: FBT001, PLR6301
        return item is False or (isinstance(item, JsonSchemaObject) and item.is_boolean_schema_false)

    def _contains_false_schema(self, items: Iterable[JsonSchemaObject | bool]) -> bool:
        return any(self._is_false_schema_item(item) for item in items)

    def _schema_requires_model_type(
        self,
        item: JsonSchemaObject,
        *,
        resolve_ref: bool = False,
        visited_refs: frozenset[str] | None = None,
    ) -> bool:
        """Return whether a schema describes a model-shaped object."""
        if item.ref:
            if not resolve_ref:
                return True
            if visited_refs is None:
                visited_refs = frozenset()
            if item.ref in visited_refs:
                return True
            return self._schema_requires_model_type(
                self._load_ref_schema_object(item.ref),
                resolve_ref=True,
                visited_refs=visited_refs | {item.ref},
            )
        return bool(
            item.properties is not None
            or item.patternProperties is not None
            or item.propertyNames is not None
            or item.additionalProperties is not None
            or item.unevaluatedProperties is not None
            or item.required
            or item.minProperties is not None
            or item.maxProperties is not None
            or item.type == "object"
            or (isinstance(item.type, list) and "object" in item.type)
        )

    def _allof_requires_model_type(
        self,
        items: Iterable[JsonSchemaObject | bool],
        *,
        resolve_ref: bool = False,
        visited_refs: frozenset[str] | None = None,
    ) -> bool:
        """Return whether allOf members describe a model-shaped schema."""
        for item in items:
            if not isinstance(item, JsonSchemaObject):
                continue
            if self._schema_requires_model_type(item, resolve_ref=resolve_ref, visited_refs=visited_refs):
                return True
            if item.allOf and self._allof_requires_model_type(item.allOf, resolve_ref=True, visited_refs=visited_refs):
                return True
            if item.anyOf and self._allof_requires_model_type(item.anyOf, resolve_ref=True, visited_refs=visited_refs):
                return True
            if item.oneOf and self._allof_requires_model_type(item.oneOf, resolve_ref=True, visited_refs=visited_refs):
                return True
        return False

    def _schema_has_own_value_keywords(self, schema: JsonSchemaObject) -> bool:  # noqa: PLR6301
        return bool(schema.type or schema.format or schema.enum or schema.has_constraint or "const" in schema.extras)

    def _without_allof_keywords(self, schema: JsonSchemaObject) -> JsonSchemaObject:
        schema_dict = schema.model_dump(exclude_unset=True, by_alias=True)
        schema_dict.pop("allOf", None)
        return self.SCHEMA_OBJECT_TYPE.model_validate(schema_dict)

    def _build_lightweight_allof_type(
        self,
        schema: JsonSchemaObject,
        depth: int,
        visited: frozenset[int],
        max_depth: int,
        max_union_elements: int,
    ) -> DataType | None:
        allof_items: Sequence[JsonSchemaObject | bool] = schema.allOf or []
        if self._schema_has_own_value_keywords(schema):
            allof_items = [self._without_allof_keywords(schema), *allof_items]
        return self._build_allof_type(
            allof_items,
            depth,
            visited,
            max_depth,
            max_union_elements,
        )

    def _raise_unsatisfiable_schema(self, path: list[str], keyword: str) -> None:  # noqa: PLR6301
        raise SchemaParseError(
            message=f"{keyword} contains a boolean false schema that makes the schema unsatisfiable",
            path=path,
        )

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

        if "const" in schema.extras:
            return self._get_const_data_type(schema.extras["const"])

        if schema.enum:
            literal_values, non_literal_values, has_null = self._partition_enum_values(schema.enum)
            if not non_literal_values:
                return self.data_type(literals=literal_values, is_optional=has_null)
            data_types = [self.data_type(literals=literal_values)] if literal_values else []
            data_types.extend(self._get_data_type_from_json_value(value) for value in non_literal_values)
            return self.data_type(data_types=data_types, is_optional=has_null)

        if schema.is_array:
            return self._build_lightweight_array_type(schema, depth, visited, max_depth, max_union_elements)

        if schema.allOf:
            return self._build_lightweight_allof_type(schema, depth, visited, max_depth, max_union_elements)

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
                if self._is_false_schema_item(item):
                    continue
                if item is True:
                    data_types.append(DataType(type=ANY, import_=IMPORT_ANY))
                    continue
                if not isinstance(item, JsonSchemaObject):  # pragma: no cover
                    continue
                if item.ref:  # pragma: no cover
                    data_types.append(self.get_ref_data_type(item.ref))
                else:
                    item_type = self._build_lightweight_type(item, depth + 1, visited, max_depth, max_union_elements)
                    if item_type is None:  # pragma: no cover
                        return None
                    data_types.append(item_type)
            if not data_types:
                return None
            if len(data_types) == 1:  # pragma: no cover
                return data_types[0]
            return self.data_type(data_types=data_types)

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

            parent_dict = parent_prop.model_dump(exclude_unset=True, by_alias=True)
            child_dict = child_prop.model_dump(exclude_unset=True, by_alias=True)
            merged_dict = self._merge_property_schemas(parent_dict, child_dict)
            merged_properties[prop_name] = self.SCHEMA_OBJECT_TYPE.model_validate(merged_dict)

        merged_obj_dict = child_obj.model_dump(exclude_unset=True, by_alias=True)
        merged_obj_dict["properties"] = {
            k: v.model_dump(exclude_unset=True, by_alias=True) if isinstance(v, JsonSchemaObject) else v
            for k, v in merged_properties.items()
        }
        return self.SCHEMA_OBJECT_TYPE.model_validate(merged_obj_dict)

    def _iter_inherited_schema_objects(
        self, base_classes: list[Reference], visited: frozenset[str]
    ) -> Iterator[tuple[JsonSchemaObject, frozenset[str]]]:
        """Yield inherited schema objects with updated visited paths."""
        for base in base_classes:
            if not base.path:  # pragma: no cover
                continue
            if base.path in visited:  # pragma: no cover
                continue
            next_visited = visited | {base.path}

            try:
                parent_schema = self._load_ref_schema_object(base.path)
            except Exception:  # pragma: no cover  # noqa: BLE001, S112
                continue
            yield parent_schema, next_visited

    def _get_inherited_field_type(
        self, prop_name: str, base_classes: list[Reference], visited: frozenset[str] | None = None
    ) -> DataType | None:
        """Get the data type for an inherited property from parent schemas.

        Recursively traverses the inheritance chain when a parent property
        doesn't have type information but the parent itself inherits from another schema.
        """
        if visited is None:
            visited = frozenset()

        for parent_schema, next_visited in self._iter_inherited_schema_objects(base_classes, visited):
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
                grandparent_refs = [
                    self.model_resolver.add_ref(item.ref)
                    for item in parent_schema.allOf
                    if isinstance(item, JsonSchemaObject) and item.ref
                ]
                if grandparent_refs:
                    parent_result = self._get_inherited_field_type(prop_name, grandparent_refs, next_visited)
                    if parent_result is not None:
                        return parent_result
                    return result

        return None

    def _split_alias(self, alias: str | list[str] | None) -> tuple[str | None, list[str] | None]:  # noqa: PLR6301
        """Split a resolver alias result into single and validation aliases."""
        if isinstance(alias, list):
            return None, alias
        return alias, None

    def _effective_default_state(
        self,
        field_name: str,
        default: Any,
        *,
        has_default: bool,
        required: bool,
        class_name: str | None,
    ) -> tuple[Any, bool, bool]:
        effective_default, effective_has_default = self.model_resolver.resolve_default_value(
            field_name,
            default,
            has_default,
            class_name=class_name,
        )
        return (
            effective_default,
            effective_has_default,
            required and self.apply_default_values_for_required_fields and effective_has_default,
        )

    def _get_inherited_field(self, prop_name: str, base_classes: list[Reference]) -> DataModelFieldBase | None:
        """Get an inherited generated field from parsed base models."""
        for base in base_classes:
            data_model = base.source if isinstance(base.source, DataModel) else None
            if data_model is None:
                data_model = next((result for result in self.results if result.reference.path == base.path), None)
            if data_model is not None:
                for field in data_model.iter_all_fields():
                    if prop_name in {field.original_name, field.name}:
                        return field
        return None

    def _get_inherited_field_schema(
        self, prop_name: str, base_classes: list[Reference], visited: frozenset[str] | None = None
    ) -> JsonSchemaObject | None:
        """Get the schema for an inherited property from parent schemas."""
        if visited is None:
            visited = frozenset()

        for parent_schema, next_visited in self._iter_inherited_schema_objects(base_classes, visited):
            if parent_schema.properties:
                prop_schema = parent_schema.properties.get(prop_name)
                if isinstance(prop_schema, JsonSchemaObject):
                    return prop_schema

            if parent_schema.allOf:
                grandparent_refs = [
                    self.model_resolver.add_ref(item.ref)
                    for item in parent_schema.allOf
                    if isinstance(item, JsonSchemaObject) and item.ref
                ]
                if grandparent_refs:
                    parent_schema_result = self._get_inherited_field_schema(prop_name, grandparent_refs, next_visited)
                    if parent_schema_result is not None:
                        return parent_schema_result

        return None

    def _build_missing_required_field(
        self,
        required_field_name: str,
        excludes: set[str],
        base_classes: list[Reference],
        class_name: str,
    ) -> DataModelFieldBase:
        """Build a field for a required name that is not declared in properties."""
        field_name, alias = self.model_resolver.get_valid_field_name_and_alias(
            required_field_name,
            excludes=excludes,
            model_type=self.field_name_model_type,
            class_name=class_name,
        )
        inherited_field = self._get_inherited_field(required_field_name, base_classes)
        if inherited_field is not None and inherited_field.name:
            field_name = inherited_field.name
        single_alias, validation_aliases = self._split_alias(alias)
        serialization_alias = self.get_serialization_alias(required_field_name, field_name, class_name)
        inherited_schema = self._get_inherited_field_schema(required_field_name, base_classes)
        if inherited_schema is not None:
            data_type = (
                inherited_field.data_type.model_copy(deep=True)
                if inherited_schema.enum and inherited_field is not None
                else self._get_inherited_field_type(required_field_name, base_classes)
                or self._build_lightweight_type(inherited_schema)
            )
            return self.get_object_field(
                field_name=field_name,
                field=inherited_schema,
                required=True,
                field_type=data_type or DataType(type=ANY, import_=IMPORT_ANY),
                alias=alias,
                original_field_name=required_field_name,
                use_default_with_required=self.apply_default_values_for_required_fields
                and inherited_schema.has_default,
                class_name=class_name,
            )

        return self.data_model_field_type(
            name=field_name,
            required=True,
            original_name=required_field_name,
            alias=single_alias,
            validation_aliases=validation_aliases,
            serialization_alias=serialization_alias,
            data_type=self._get_inherited_field_type(required_field_name, base_classes)
            or DataType(type=ANY, import_=IMPORT_ANY),
            use_serialization_alias=self.use_serialization_alias,
        )

    def _schema_signature(self, prop_schema: JsonSchemaObject | bool) -> str | bool:  # noqa: FBT001, PLR6301
        """Normalize property schema for comparison across allOf items."""
        if isinstance(prop_schema, bool):
            return prop_schema
        return json.dumps(prop_schema.model_dump(exclude_unset=True, by_alias=True), sort_keys=True, default=repr)

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
        if obj.propertyNames is not None:
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

        ref_items = [item for item in obj.allOf if isinstance(item, JsonSchemaObject) and item.ref]

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
            if not isinstance(item, JsonSchemaObject):  # pragma: no cover
                continue
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
            merged_dict = merged_schema.model_dump(exclude_unset=True, by_alias=True)
            merged_dict["description"] = obj.description
            merged_schema = self.SCHEMA_OBJECT_TYPE.model_validate(merged_dict)

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

        ref_count = sum(1 for item in obj.allOf if isinstance(item, JsonSchemaObject) and item.ref)
        if ref_count == 1:
            return None

        resolved_items: list[JsonSchemaObject] = []
        property_signatures: dict[str, set[str | bool]] = {}
        for item in obj.allOf:
            if not isinstance(item, JsonSchemaObject):  # pragma: no cover
                continue
            resolved_item = self._load_ref_schema_object(item.ref) if item.ref else item
            if resolved_item.is_boolean_schema_false:
                self._raise_unsatisfiable_schema([], "allOf")
            resolved_items.append(resolved_item)
            if resolved_item.properties:
                for prop_name, prop_schema in resolved_item.properties.items():
                    property_signatures.setdefault(prop_name, set()).add(self._schema_signature(prop_schema))

        if not any(len(signatures) > 1 for signatures in property_signatures.values()):
            return None

        merged_schema: dict[str, Any] = obj.model_dump(exclude={"allOf"}, exclude_unset=True, by_alias=True)
        for resolved_item in resolved_items:
            merged_schema = self._deep_merge(merged_schema, resolved_item.model_dump(exclude_unset=True, by_alias=True))

        if "required" in merged_schema and isinstance(merged_schema["required"], list):
            merged_schema["required"] = list(dict.fromkeys(merged_schema["required"]))

        merged_schema.pop("allOf", None)
        return self.SCHEMA_OBJECT_TYPE.model_validate(merged_schema)

    def parse_combined_schema(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        target_attribute_name: str,
    ) -> list[DataType]:
        """Parse combined schema (anyOf, oneOf, allOf) into a list of data types."""
        base_object = obj.model_dump(exclude={target_attribute_name, "title"}, exclude_unset=True, by_alias=True)
        combined_schemas: list[JsonSchemaObject] = []
        refs = []
        for index, target_attribute in enumerate(getattr(obj, target_attribute_name, [])):
            if self._is_false_schema_item(target_attribute):
                continue
            if target_attribute is True:
                combined_schemas.append(self.SCHEMA_OBJECT_TYPE.model_validate(base_object))
                continue
            if target_attribute.ref:
                if target_attribute.ref_type == JSONReference.LOCAL:
                    ref_schema = self._load_ref_schema_object(target_attribute.ref)
                    if ref_schema.is_boolean_schema_false:
                        continue
                if target_attribute.has_ref_with_schema_keywords and not target_attribute.is_ref_with_nullable_only:
                    merged_attr = self._merge_ref_with_schema(target_attribute)
                    if merged_attr.ref:
                        combined_schemas.append(merged_attr)
                        refs.append(index)
                    else:
                        combined_schemas.append(
                            self.SCHEMA_OBJECT_TYPE.model_validate(
                                self._deep_merge(
                                    base_object, merged_attr.model_dump(exclude_unset=True, by_alias=True)
                                ),
                            )
                        )
                else:
                    combined_schemas.append(target_attribute)
                    refs.append(index)
            else:
                combined_schemas.append(
                    self.SCHEMA_OBJECT_TYPE.model_validate(
                        self._deep_merge(
                            base_object,
                            target_attribute.model_dump(exclude_unset=True, by_alias=True),
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
        if not parsed_schemas:
            self._raise_unsatisfiable_schema(path, target_attribute_name)
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

    def _merge_type_modifiers(self, new_type: DataType, current_type: DataType) -> None:  # noqa: PLR6301
        """Merge container modifiers from an overriding field type into an inherited type."""
        new_type.is_optional = new_type.is_optional or current_type.is_optional
        new_type.is_dict = new_type.is_dict or current_type.is_dict
        new_type.is_list = new_type.is_list or current_type.is_list
        new_type.is_set = new_type.is_set or current_type.is_set
        new_type.is_frozen_set = new_type.is_frozen_set or current_type.is_frozen_set
        new_type.is_mapping = new_type.is_mapping or current_type.is_mapping
        new_type.is_sequence = new_type.is_sequence or current_type.is_sequence
        if new_type.kwargs is None and current_type.kwargs is not None:  # pragma: no cover
            new_type.kwargs = current_type.kwargs

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
        self._preload_property_refs_for_rw_models(obj)
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
                        new_type = inherited_type.model_copy(deep=True)
                        self._merge_type_modifiers(new_type, current_type)
                        self.generation_store.replace_field_type(field, new_type)
                # Handle List[Any] case: inherit item type from parent if items have Any type
                elif field_name and self._is_list_with_any_item_type(current_type):
                    inherited_type = self._get_inherited_field_type(field_name, base_classes)
                    if inherited_type is None or not inherited_type.is_list or not inherited_type.data_types:
                        continue

                    new_type = inherited_type.model_copy(deep=True)

                    # Preserve modifiers coming from the overriding schema.
                    if current_type is not None:  # pragma: no branch
                        self._merge_type_modifiers(new_type, current_type)

                    # Some code paths represent the list type inside an outer container.
                    is_wrapped = (
                        current_type is not None
                        and not current_type.is_list
                        and len(current_type.data_types) == 1
                        and current_type.data_types[0].is_list
                    )
                    if is_wrapped:
                        wrapper = current_type.model_copy(deep=True)
                        wrapper.data_types[0] = new_type
                        self.generation_store.replace_field_type(field, wrapper)
                        continue

                    self.generation_store.replace_field_type(field, new_type)  # pragma: no cover
        name = self._apply_title_as_name(name, obj)  # pragma: no cover
        reference = self.model_resolver.add(path, name, class_name=True, loaded=True)
        extra_field = self._get_typed_additional_properties_field(reference.name, obj, path)
        # ignore an undetected object
        if ignore_duplicate_model and not fields and extra_field is None and len(base_classes) == 1:
            with self.model_resolver.current_base_path_context(self.model_resolver._base_path):  # noqa: SLF001
                self.model_resolver.delete(path)
                return self.data_type(reference=base_classes[0])
        if required:
            for field in fields:
                if self.force_optional_for_required_fields:  # pragma: no cover
                    continue  # pragma: no cover
                if (field.original_name or field.name) in required:
                    field.required = True
                    if self.apply_default_values_for_required_fields and field.has_default:
                        field.use_default_with_required = True
        if obj.required:
            field_name_to_field = {f.original_name or f.name: f for f in fields}
            for required_ in obj.required:
                if required_ in field_name_to_field:
                    field = field_name_to_field[required_]
                    if self.force_optional_for_required_fields:
                        continue
                    field.required = True
                    if self.apply_default_values_for_required_fields and field.has_default:
                        field.use_default_with_required = True
                else:
                    fields.append(
                        self._build_missing_required_field(
                            required_,
                            excludes={field.name for field in fields if field.name},
                            base_classes=base_classes,
                            class_name=name,
                        )
                    )
        if extra_field is not None:
            fields.insert(0, extra_field)
        self._set_schema_metadata(reference.path, obj)
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
            self.generation_store.register_model(data_model_type)

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
        parent_refs = [item.ref for item in obj.allOf if isinstance(item, JsonSchemaObject) and item.ref]

        for all_of_item in obj.allOf:  # noqa: PLR1702
            if self._is_false_schema_item(all_of_item):
                self._raise_unsatisfiable_schema(path, "allOf")
            if not isinstance(all_of_item, JsonSchemaObject):  # pragma: no cover
                continue
            if all_of_item.ref:  # $ref
                ref_schema = self._load_ref_schema_object(all_of_item.ref)
                if ref_schema.is_boolean_schema_false:
                    self._raise_unsatisfiable_schema(path, "allOf")

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
                        for required_field_name in all_of_item.required:
                            if required_field_name in field_names or required_field_name in existing_field_names:
                                continue
                            if self.force_optional_for_required_fields:
                                continue
                            field = self._build_missing_required_field(
                                required_field_name,
                                excludes=existing_field_names,
                                base_classes=base_classes,
                                class_name=name,
                            )
                            fields.append(field)
                            existing_field_names.update({required_field_name, field.name or required_field_name})
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

    def _build_all_of_ref_root_model(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        ref_data_type: DataType,
    ) -> DataType:
        reference = self.model_resolver.add(path, name, class_name=True, loaded=True)
        self._set_schema_metadata(reference.path, obj)
        self.set_schema_extensions(reference.path, obj)
        field = self.data_model_field_type(
            name=None,
            data_type=ref_data_type,
            required=True,
        )
        self._register_root_model(
            reference=reference,
            fields=[field],
            obj=obj,
            custom_base_class_name=name,
            description=obj.description if self.use_schema_description else None,
        )
        return self.data_type(reference=reference)

    def _register_root_model(  # noqa: PLR0913
        self,
        *,
        reference: Reference,
        fields: list[DataModelFieldBase],
        obj: JsonSchemaObject,
        custom_base_class_name: str,
        description: str | None = None,
        default: Any = UNDEFINED,
    ) -> DataModel:
        data_model_root = self.data_model_root_type(
            reference=reference,
            fields=fields,
            custom_base_class=self._resolve_base_class(custom_base_class_name, obj.custom_base_path),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=description,
            default=default,
            nullable=obj.type_has_null,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.generation_store.register_model(data_model_root)
        return data_model_root

    def _parse_all_of_single_ref(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> DataType | None:
        if len(obj.allOf) != 1 or obj.properties:
            return None

        single_obj = obj.allOf[0]
        if not (
            isinstance(single_obj, JsonSchemaObject) and single_obj.ref and single_obj.ref_type == JSONReference.LOCAL
        ):
            return None

        referenced_schema = get_model_by_path(self.raw_obj, single_obj.ref[2:].split("/"))
        ref_data_type = self.get_ref_data_type(single_obj.ref)
        if referenced_schema is True:
            return self._build_all_of_ref_root_model(name, obj, path, ref_data_type)
        if referenced_schema is False:
            self._raise_unsatisfiable_schema(path, "allOf")

        if not (isinstance(referenced_schema, dict) and referenced_schema.get("enum")):
            return None

        full_path = self.model_resolver.join_path(tuple(path))
        existing_ref = self.model_resolver.references.get(full_path)
        if existing_ref is not None and not existing_ref.loaded:
            return self._build_all_of_ref_root_model(name, obj, path, ref_data_type)

        return ref_data_type

    def parse_all_of(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        ignore_duplicate_model: bool = False,  # noqa: FBT001, FBT002
    ) -> DataType:
        """Parse allOf schema into a single data type with combined properties."""
        if self._contains_false_schema(obj.allOf):
            self._raise_unsatisfiable_schema(path, "allOf")

        single_ref_result = self._parse_all_of_single_ref(name, obj, path)
        if single_ref_result is not None:
            return single_ref_result

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
        self._set_schema_metadata(reference.path, obj)
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
        self._register_root_model(
            reference=reference,
            fields=[field],
            obj=obj,
            custom_base_class_name=name,
            description=obj.description if self.use_schema_description else None,
        )
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
                single_alias, validation_aliases = self._split_alias(alias)
                fields.append(
                    self.data_model_field_type(
                        name=field_name,
                        data_type=self.data_type_manager.get_data_type(
                            Types.any,
                        ),
                        required=False if self.force_optional_for_required_fields else original_field_name in requires,
                        alias=single_alias,
                        validation_aliases=validation_aliases,
                        serialization_alias=self.get_serialization_alias(original_field_name, field_name, class_name),
                        strip_default_none=self.strip_default_none,
                        use_annotated=self.use_annotated,
                        use_field_description=self.use_field_description,
                        use_field_description_example=self.use_field_description_example,
                        use_inline_field_description=self.use_inline_field_description,
                        original_name=original_field_name,
                        use_serialization_alias=self.use_serialization_alias,
                    )
                )
                continue

            if field.has_ref_with_schema_keywords and not field.is_ref_with_nullable_only:
                field = self._merge_ref_with_schema(field)  # noqa: PLW2901

            field_type = self.parse_item(modular_name, field, [*path, field_name])

            if self.force_optional_for_required_fields:
                required: bool = False
            else:
                required = original_field_name in requires
            effective_default, effective_has_default, use_default_with_required = self._effective_default_state(
                original_field_name,
                field.default,
                has_default=field.has_default,
                required=required,
                class_name=class_name,
            )
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
                    use_default_with_required=use_default_with_required,
                    class_name=class_name,
                )
            )
        return fields

    def _get_typed_additional_properties_field(
        self,
        class_name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> DataModelFieldBase | None:
        """Build the output model's typed extra field for schema-valued extras."""
        if self.data_model_type.TYPED_EXTRA_FIELD_NAME is None or not isinstance(
            obj.additionalProperties, JsonSchemaObject
        ):
            return None

        additional_props = obj.additionalProperties
        if additional_props.has_ref_with_schema_keywords and not additional_props.is_ref_with_nullable_only:
            additional_props = self._merge_ref_with_schema(additional_props)
        if additional_props.allOf and self._contains_false_schema(additional_props.allOf):
            return None
        additional_props = self._add_nullable_combined_schema_branches(additional_props)
        extra_value_type = self.parse_item(
            f"{class_name}AdditionalProperty",
            additional_props,
            [*path, "additionalProperties"],
        )

        return self.data_model_type.create_typed_extra_field(
            field_model=self.data_model_field_type,
            data_type=self.data_type(
                data_types=[extra_value_type],
                is_dict=True,
            ),
        )

    def _add_nullable_combined_schema_branches(self, obj: JsonSchemaObject) -> JsonSchemaObject:
        updates: dict[str, list[JsonSchemaObject | bool]] = {}
        for field_name in ("anyOf", "oneOf"):
            combined_items = getattr(obj, field_name)
            if not combined_items:
                continue

            updated_items: list[JsonSchemaObject | bool] = []
            for item in combined_items:
                updated_items.append(item)
                if isinstance(item, JsonSchemaObject) and item.nullable and not item.type_has_null:
                    updated_items.append(self.SCHEMA_OBJECT_TYPE.model_validate({"type": "null"}))

            if len(updated_items) != len(combined_items):
                updates[field_name] = updated_items

        return obj.model_copy(update=updates) if updates else obj

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
        self._preload_property_refs_for_rw_models(obj)
        fields = self.parse_object_fields(
            obj,
            path,
            get_module_name(class_name, None, treat_dot_as_module=self.treat_dot_as_module),
            class_name=class_name,
        )
        has_declared_fields = bool(fields)
        if has_declared_fields and (extra_field := self._get_typed_additional_properties_field(class_name, obj, path)):
            fields.insert(0, extra_field)
        should_parse_dict_root = not has_declared_fields and (
            isinstance(obj.additionalProperties, JsonSchemaObject) or self._should_parse_empty_object_as_dict(obj)
        )
        if not should_parse_dict_root:
            data_model_type_class = self.data_model_type
        else:
            additional_props = (
                obj.additionalProperties
                if isinstance(obj.additionalProperties, JsonSchemaObject)
                else self.SCHEMA_OBJECT_TYPE.model_validate({})
            )
            if additional_props.has_ref_with_schema_keywords and not additional_props.is_ref_with_nullable_only:
                additional_props = self._merge_ref_with_schema(additional_props)
            additional_props_update = {
                "minProperties": obj.minProperties,
                "maxProperties": obj.maxProperties,
                "propertyNames": obj.propertyNames,
                "additionalProperties": obj.additionalProperties,
            }
            if (
                isinstance(obj.additionalProperties, JsonSchemaObject)
                and obj.additionalProperties.has_ref_with_schema_keywords
                and not obj.additionalProperties.is_ref_with_nullable_only
            ):
                additional_props_field = self.SCHEMA_OBJECT_TYPE.model_validate(additional_props_update)
            else:
                additional_props_field = additional_props.model_copy(update=additional_props_update)
            fields.append(
                self.get_object_field(
                    field_name=None,
                    field=additional_props_field,
                    required=True,
                    original_field_name=None,
                    field_type=self.data_type(
                        data_types=[
                            self.parse_item(
                                # TODO: Improve naming for nested ClassName
                                name,
                                additional_props,
                                [*path, "additionalProperties"],
                            )
                            if isinstance(obj.additionalProperties, JsonSchemaObject)
                            else self.data_type_manager.get_data_type(Types.any)
                        ],
                        is_dict=True,
                    ),
                    alias=None,
                )
            )
            data_model_type_class = self.data_model_root_type

        self._set_schema_metadata(reference.path, obj)
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
            self.generation_store.register_model(data_model_type)

        return self.data_type(reference=reference)

    def parse_pattern_properties(
        self,
        name: str,
        pattern_properties: dict[str, JsonSchemaObject | bool],
        path: list[str],
        *,
        property_names: JsonSchemaObject | bool | None = None,
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
            return self.data_type(
                data_types=[self.data_type_manager.get_data_type(Types.any)],
                is_dict=True,
            )

        groups: dict[str, tuple[list[str], DataType]] = {}
        for pattern, value_type in pattern_value_pairs:
            key = value_type.type_hint
            if key not in groups:
                groups[key] = ([], value_type)
            groups[key][0].append(pattern)

        data_types: list[DataType] = []
        for patterns, value_type in groups.values():
            merged_pattern = patterns[0] if len(patterns) == 1 else "|".join(patterns)
            key_type = self.data_type_manager.get_data_type(
                Types.string,
                pattern=merged_pattern,
            )
            if isinstance(property_names, JsonSchemaObject):
                merged_property_names = property_names.model_copy(deep=True)
                merged_property_names.type = "string"
                merged_property_names.pattern = (
                    merged_pattern
                    if merged_property_names.pattern is None
                    else self._intersect_constraint("pattern", merged_property_names.pattern, merged_pattern)
                )
                if merged_property_names.ref:
                    merged_property_names = self._merge_ref_with_schema(merged_property_names)
                key_type = self._parse_property_name_key_schema(merged_property_names)
            data_types.append(
                self.data_type(
                    data_types=[value_type],
                    is_dict=True,
                    dict_key=key_type,
                )
            )

        return self.data_type(data_types=data_types)

    def _parse_property_name_key_schema(  # noqa: PLR0911
        self,
        property_names: JsonSchemaObject | bool,  # noqa: FBT001
    ) -> DataType:
        if isinstance(property_names, bool):
            return self.data_type_manager.get_data_type(Types.string)
        if property_names.extras.get("x-python-type") == "int":
            return self.data_type_manager.get_data_type(Types.integer)
        if property_names.extras.get("x-python-type") == "bool":
            return self.data_type_manager.get_data_type(Types.boolean)
        if property_names.extras.get("x-python-type") == "str":
            return self.data_type_manager.get_data_type(Types.string)
        if property_names.ref:
            return self.get_ref_data_type(property_names.ref)
        if property_names.enum:
            string_enums = [value for value in property_names.enum if isinstance(value, str)]
            if string_enums:
                return self.data_type(literals=string_enums)
            return self.data_type_manager.get_data_type(Types.string)
        if isinstance(property_names.extras.get("const"), str):
            return self.data_type(literals=[property_names.extras["const"]])
        if (
            property_names.pattern is not None
            or property_names.minLength is not None
            or property_names.maxLength is not None
        ):
            kwargs: dict[str, Any] = {}
            if property_names.pattern:
                kwargs["pattern"] = property_names.pattern
            if property_names.minLength is not None:
                kwargs["minLength"] = property_names.minLength
            if property_names.maxLength is not None:
                kwargs["maxLength"] = property_names.maxLength
            return self.data_type_manager.get_data_type(Types.string, **kwargs)
        return self.data_type_manager.get_data_type(Types.string)

    def parse_property_names(
        self,
        name: str,
        property_names: JsonSchemaObject | bool,  # noqa: FBT001
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
        if (
            isinstance(property_names, JsonSchemaObject)
            and property_names.has_ref_with_schema_keywords
            and not property_names.is_ref_with_nullable_only
        ):
            property_names = self._merge_ref_with_schema(property_names)

        # Determine value type from additionalProperties
        if isinstance(additional_properties, JsonSchemaObject):
            value_type = self.parse_item(
                name,
                additional_properties,
                get_special_path("propertyNames/value", path),
            )
        else:
            value_type = self.data_type_manager.get_data_type(Types.any)

        if isinstance(property_names, JsonSchemaObject) and (
            property_names.anyOf or property_names.oneOf or property_names.allOf
        ):
            key_type = self.parse_item(
                name,
                property_names,
                get_special_path("propertyNames/key", path),
            )
        else:
            key_type = self._parse_property_name_key_schema(property_names)

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
            enum_values, varnames, descriptions, enum_type, nullable = const_enum_data
            synthetic_obj = self._create_synthetic_enum_obj(
                item, enum_values, varnames, descriptions, enum_type, nullable
            )
            if self.should_parse_enum_as_literal(synthetic_obj, property_name=name, property_obj=item):
                return True
        if (
            item.is_object
            and not item.properties
            and not item.patternProperties
            and item.propertyNames is None
            and isinstance(item.additionalProperties, JsonSchemaObject)
        ):
            return True
        if item.patternProperties:
            return True
        if item.propertyNames is not None:
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

    def _parse_combined_const_enum(
        self,
        name: str,
        obj: JsonSchemaObject,
        combined_items: list[JsonSchemaObject | bool],
        enum_path: list[str],
        *,
        singular_name: bool = False,
    ) -> DataType | None:
        const_enum_data = self._extract_const_enum_from_combined(combined_items, obj.type)
        if const_enum_data is None:
            return None

        enum_values, varnames, descriptions, enum_type, nullable = const_enum_data
        synthetic_obj = self._create_synthetic_enum_obj(obj, enum_values, varnames, descriptions, enum_type, nullable)
        if self.should_parse_enum_as_literal(synthetic_obj, property_name=name, property_obj=obj):
            return self.parse_enum_as_literal(synthetic_obj)
        return self.parse_enum(name, synthetic_obj, enum_path, singular_name=singular_name)

    def parse_item(  # noqa: PLR0911, PLR0912, PLR0915
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
        if item.recursiveRef and not item.ref:
            return self.get_ref_data_type(self._resolve_recursive_ref(item, path) or "#")
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
            return self.data_type_manager.get_data_type_from_full_path(
                _validate_schema_python_import_path(item.custom_type_path, "customTypePath"),
                is_custom_type=True,
            )
        if item.is_array:
            return self.parse_array_fields(name, item, get_special_path("array", path)).data_type
        if item.discriminator and parent and parent.is_array and (item.oneOf or item.anyOf):
            return self.parse_root_type(name, item, path)
        if item.anyOf:
            if combined_const_enum := self._parse_combined_const_enum(
                name,
                item,
                item.anyOf,
                get_special_path("enum", path),
                singular_name=singular_name,
            ):
                return combined_const_enum
            return self.data_type(data_types=self.parse_any_of(name, item, get_special_path("anyOf", path)))
        if item.oneOf:
            if combined_const_enum := self._parse_combined_const_enum(
                name,
                item,
                item.oneOf,
                get_special_path("enum", path),
                singular_name=singular_name,
            ):
                return combined_const_enum
            return self.data_type(data_types=self.parse_one_of(name, item, get_special_path("oneOf", path)))
        if item.allOf:
            if self._contains_false_schema(item.allOf):
                self._raise_unsatisfiable_schema(get_special_path("allOf", path), "allOf")
            all_of_items = [sub_item for sub_item in item.allOf if isinstance(sub_item, JsonSchemaObject)]
            if len(all_of_items) == 1 and len(all_of_items) != len(item.allOf) and not item.properties:
                return self.parse_item(name, all_of_items[0], path, singular_name=singular_name, parent=parent)
            if not self._schema_requires_model_type(item) and not self._allof_requires_model_type(item.allOf):
                all_of_path = get_special_path("allOf", path)
                all_of_path = [self.model_resolver.resolve_ref(all_of_path)]
                root_model_name = self.model_resolver.add(
                    all_of_path, name, singular_name=singular_name, class_name=True
                ).name
                return self.parse_root_type(root_model_name, item, all_of_path)
            if len(item.allOf) == 1 and not item.properties:
                single_item = item.allOf[0]
                if isinstance(single_item, JsonSchemaObject) and single_item.ref:
                    return self.get_ref_data_type(single_item.ref)
            all_of_path = get_special_path("allOf", path)
            all_of_path = [self.model_resolver.resolve_ref(all_of_path)]
            return self.parse_all_of(
                self.model_resolver.add(all_of_path, name, singular_name=singular_name, class_name=True).name,
                item,
                all_of_path,
                ignore_duplicate_model=True,
            )
        if item.is_object or item.patternProperties or item.propertyNames is not None:
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
                return self.parse_pattern_properties(
                    name, item.patternProperties, object_path, property_names=item.propertyNames
                )
            if item.propertyNames is not None:
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
        target_items: Sequence[JsonSchemaObject | bool],
        path: list[str],
        parent: JsonSchemaObject,
        singular_name: bool = True,  # noqa: FBT001, FBT002
    ) -> list[DataType]:
        """Parse a list of items into data types."""
        return [
            self.data_type_manager.get_data_type(Types.any)
            if item is True
            else self.parse_item(
                name,
                item,
                [*path, str(index)],
                singular_name=singular_name,
                parent=parent,
            )
            for index, item in enumerate(target_items)
            if item is not False
        ]

    def parse_array_fields(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        singular_name: bool = True,  # noqa: FBT001, FBT002
    ) -> DataModelFieldBase:
        """Parse array schema into a data model field with list type."""
        # Strict mode: check for version-specific array features
        self._check_array_version_features(obj, path)

        required, nullable = self._resolve_array_field_required_nullable(obj)
        items, is_tuple, suppress_item_constraints = self._get_array_item_schemas(obj)

        if items:
            item_data_types = self.parse_list_item(
                name,
                items,
                path,
                obj,
                singular_name=singular_name,
            )
        else:
            item_data_types = self._fallback_array_item_data_types()

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
        constraints = self._get_constraint_values(obj)
        constraints.update(self._get_array_items_constraints(obj))
        if suppress_item_constraints:
            self._suppress_array_length_constraints(constraints, obj)
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
        self._set_schema_metadata(reference.path, obj)
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

        self._register_root_model(
            reference=reference,
            fields=[field],
            obj=obj,
            custom_base_class_name=name,
            description=obj.description if self.use_schema_description else None,
        )
        return self.data_type(reference=reference)

    def parse_root_type(  # noqa: PLR0912, PLR0915
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
                _validate_schema_python_import_path(obj.custom_type_path, "customTypePath"),
                is_custom_type=True,
            )  # pragma: no cover
        elif obj.is_array:
            data_type = self.parse_array_fields(
                name, obj, get_special_path("array", path)
            ).data_type  # pragma: no cover
        elif obj.anyOf or obj.oneOf:
            combined_items = obj.anyOf or obj.oneOf
            if const_enum_type := self._parse_combined_const_enum(name, obj, combined_items, path):
                data_type = const_enum_type  # pragma: no cover
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
        elif obj.allOf:
            data_type = self._build_lightweight_type(obj)
            if data_type is None:  # pragma: no cover
                data_type = self.data_type_manager.get_data_type(Types.any)
        elif obj.patternProperties:
            data_type = self.parse_pattern_properties(
                name, obj.patternProperties, path, property_names=obj.propertyNames
            )
        elif obj.propertyNames is not None:
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
        constraints = self._get_constraint_values(obj) if self.field_constraints else {}
        if self._should_skip_root_field_constraints_for_multiple_types(obj):
            constraints = {}
        elif self.field_constraints and obj.format == "hostname":
            constraints["pattern"] = self.data_type_manager.HOSTNAME_REGEX
        if data_type.is_dict or data_type.is_mapping:
            constraints.update(self._get_property_count_constraints(obj))
        self._register_root_model(
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
            obj=obj,
            custom_base_class_name=name,
            default=default_value if has_default_override else UNDEFINED,
        )
        return self.data_type(reference=reference)

    def _should_skip_root_field_constraints_for_multiple_types(self, obj: JsonSchemaObject) -> bool:
        """Avoid applying type-specific Field constraints to heterogeneous root unions."""
        if not self.field_constraints or not obj.has_multiple_types or not isinstance(obj.type, list):
            return False
        return len({type_ for type_ in obj.type if type_ != "null"}) > 1

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

        constraints = self._get_constraint_values(obj) if self.field_constraints else {}
        if self._should_skip_root_field_constraints_for_multiple_types(obj):
            constraints = {}
        self._register_root_model(
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
            obj=obj,
            custom_base_class_name=name,
            default=obj.default if obj.has_default else UNDEFINED,
        )

    def parse_enum_as_literal(self, obj: JsonSchemaObject) -> DataType:
        """Parse enum values as a Literal type."""
        literal_values, non_literal_values, has_null = self._partition_enum_values(obj.enum)
        if not non_literal_values:
            return self.data_type(
                literals=literal_values,
                is_optional=has_null,
            )

        data_types: list[DataType] = []
        if literal_values:
            data_types.append(self.data_type(literals=literal_values))
        data_types.extend(self._get_data_type_from_json_value(i) for i in non_literal_values)
        if not data_types:  # pragma: no cover
            data_types.append(self.data_type_manager.get_data_type(Types.null))
        return self.data_type(
            data_types=data_types,
            is_optional=has_null,
        )

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

    def parse_enum(  # noqa: PLR0912, PLR0915
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

        if None in obj.enum and (obj.type == "string" or obj.nullable):
            nullable: bool = True
            enum_times = [e for e in obj.enum if e is not None]
        else:
            enum_times = obj.enum
            nullable = False

        exclude_field_names: set[str] = set()

        enum_names = obj.x_enum_varnames or obj.x_enum_names
        enum_descriptions = obj.x_enum_descriptions

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
            field_extras: dict[str, Any] = {}
            if enum_descriptions and i < len(enum_descriptions) and enum_descriptions[i]:
                field_extras["description"] = enum_descriptions[i]
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
                    extras=field_extras,
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
            self._set_schema_metadata(reference.path, obj)
            self.set_schema_extensions(reference.path, obj)
            self._register_root_model(
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
                obj=obj,
                custom_base_class_name=name,
                default=obj.default if obj.has_default else UNDEFINED,
            )
            return self.data_type(reference=reference)

        def create_enum(reference_: Reference) -> DataType:
            type_: Types | None = (
                self._get_type_with_mappings(obj.type, obj.format) if isinstance(obj.type, str) else None
            )

            enum_cls: type[Enum] = Enum
            specialized_type = SPECIALIZED_ENUM_TYPE_MATCH.get(type_) if self.use_specialized_enum and type_ else None
            if specialized_type == StrEnum:
                # StrEnum is available only in Python 3.11+ and supports string values only.
                can_use_specialized_type = self.target_python_version.has_strenum and all(
                    isinstance(enum_part, str) for enum_part in enum_times
                )
            else:
                can_use_specialized_type = specialized_type is not None
            if can_use_specialized_type and specialized_type is not None:
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
            self.generation_store.register_model(enum)
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
        self._set_schema_metadata(reference.path, obj)
        self.set_schema_extensions(reference.path, obj)

        if not nullable:
            return create_enum(reference)

        enum_reference = self.model_resolver.add(
            [*path, "Enum"],
            f"{reference.name}Enum",
            class_name=True,
            singular_name=singular_name,
            singular_name_suffix="Enum",
            loaded=True,
            model_type="enum",
        )

        self._register_root_model(
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
            obj=obj,
            custom_base_class_name=reference.name,
            default=obj.default if obj.has_default else UNDEFINED,
        )
        return self.data_type(reference=reference)

    def _get_ref_body(self, resolved_ref: str) -> dict[str, YamlValue]:
        """Get the body of a reference from URL or remote file."""
        if is_url(resolved_ref):
            url_scheme = urlparse(resolved_ref).scheme
            uses_local_http_path = url_scheme in {"http", "https"} and self.http_local_ref_path is not None
            if not uses_local_http_path:
                if self.allow_remote_refs is False:
                    msg = (
                        f"Fetching remote $ref is disabled: {resolved_ref}\n"
                        "Reason: --no-allow-remote-refs was set, so external $ref targets are not fetched.\n"
                        "If this schema and all of its remote references are trusted, pass --allow-remote-refs. "
                        "If a trusted remote reference points to an internal schema registry, also pass "
                        "--allow-private-network."
                    )
                    raise Error(msg)
                if self.allow_remote_refs is None and url_scheme in {"http", "https"}:
                    warn_deprecated(
                        "behavior.remote-ref-default",
                        details=(
                            f"Reference: {resolved_ref}. Pass --allow-remote-refs for trusted remote schemas, "
                            "or --no-allow-remote-refs to block HTTP(S) $ref fetching. Internal network targets "
                            "also require --allow-private-network."
                        ),
                        stacklevel=2,
                    )
            return self._get_ref_body_from_url(resolved_ref)
        return self._get_ref_body_from_remote(resolved_ref)

    def _resolve_local_ref_path(self, path: Path, ref: str) -> Path:
        base_path = self.base_path.resolve()
        resolved_path = path.resolve()
        if resolved_path.is_relative_to(base_path) or self.allow_remote_refs is True:
            return resolved_path

        details = (
            f"Reference: {ref}. Reason: the resolved file is outside the input base path. "
            f"Base path: {base_path}. Resolved path: {resolved_path}. "
            "Move trusted referenced schemas under the input directory, pass --allow-remote-refs to allow this "
            "external local file reference without a warning, or pass --no-allow-remote-refs to block it."
        )
        if self.allow_remote_refs is None:
            warn_deprecated("behavior.remote-ref-default", details=details, stacklevel=3)
            return resolved_path

        msg = (
            f"Blocked unsafe local $ref: {ref}\n"
            "Reason: --no-allow-remote-refs was set and the resolved file is outside the input base path.\n"
            f"Base path: {base_path}\n"
            f"Resolved path: {resolved_path}\n"
            "Move trusted referenced schemas under the input directory, or pass --allow-remote-refs only when the "
            "schema and referenced files are trusted."
        )
        raise Error(msg)

    def _get_ref_body_from_local_http_path(self, ref: str) -> dict[str, YamlValue]:
        assert self.http_local_ref_path is not None
        parsed = urlparse(ref)
        if parsed.scheme not in {"http", "https"}:  # pragma: no cover
            msg = f"Unsupported local HTTP $ref URL: {ref}"
            raise Error(msg)

        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if not parsed.netloc or any(part in {".", ".."} or "/" in part or "\\" in part for part in parts):
            msg = f"Unsupported local HTTP $ref URL path: {ref}"
            raise Error(msg)

        base_path = self.http_local_ref_path.resolve()
        relative_path = Path(parsed.netloc, *parts)
        file_paths = [(base_path / relative_path).resolve()]
        if not parts or not Path(parts[-1]).suffix:
            file_paths.append((base_path / relative_path.with_name(f"{relative_path.name}.json")).resolve())

        if any(not file_path.is_relative_to(base_path) for file_path in file_paths):
            msg = f"Unsupported local HTTP $ref URL path: {ref}"
            raise Error(msg)

        for file_path in file_paths:
            if file_path.is_file():
                return self.remote_object_cache.get_or_put(
                    str(file_path),
                    default_factory=lambda _, file_path=file_path: load_data_from_path(file_path, self.encoding),
                )

        msg = f"$ref local file not found for {ref}: tried {', '.join(str(path) for path in file_paths)}"
        raise Error(msg)

    def _get_ref_body_from_url(self, ref: str) -> dict[str, YamlValue]:
        """Get reference body from a URL (HTTP, HTTPS, or file scheme)."""
        if ref.startswith("file://"):
            from urllib.request import url2pathname  # noqa: PLC0415

            parsed = urlparse(ref)
            # url2pathname handles percent-decoding and Windows drive letters
            path = url2pathname(parsed.path)
            # Handle UNC paths (file://server/share/path)
            if parsed.netloc:
                path = f"//{parsed.netloc}{path}"
            file_path = self._resolve_local_ref_path(Path(path), ref)
            return self.remote_object_cache.get_or_put(
                str(file_path), default_factory=lambda _: load_data_from_path(file_path, self.encoding)
            )
        if self.http_local_ref_path is not None and urlparse(ref).scheme in {"http", "https"}:
            return self._get_ref_body_from_local_http_path(ref)
        return self.remote_object_cache.get_or_put(
            ref, default_factory=lambda key: load_data(self._get_text_from_url(key))
        )

    def _get_ref_body_from_remote(self, resolved_ref: str) -> dict[str, YamlValue]:
        """Get reference body from a remote file path."""
        full_path = self._resolve_local_ref_path(self.base_path / resolved_ref, resolved_ref)

        try:
            return self.remote_object_cache.get_or_put(
                str(full_path),
                default_factory=lambda _: load_data_from_path(full_path, self.encoding),
            )
        except FileNotFoundError:
            msg = f"$ref file not found: {full_path}"
            raise Error(msg) from None

    def resolve_ref(self, object_ref: str) -> Reference:
        """Resolve a reference by loading and parsing the referenced schema."""
        # If the ref is mapped to an external package, mark as loaded and skip parsing
        if self._resolve_external_ref_mapping(object_ref) is not None:
            reference = self.model_resolver.add_ref(object_ref)
            reference.loaded = True
            return reference

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
            ref_body = self._get_ref_body(relative_path)
            object_paths: list[str] | None = None
            reference_paths: list[str] | None = None
            if object_path:
                object_paths, reference_paths = _split_json_pointer(ref_body, object_path)
            self._parse_file(
                ref_body,
                self.model_resolver.add_ref(ref, resolved=True).name,
                relative_paths,
                object_paths,
                reference_paths=reference_paths,
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
                self._traverse_schema_objects(item, [*path, "items"], callback, include_one_of=include_one_of)
            case list() as items:
                for index, item in enumerate(items):
                    if isinstance(item, JsonSchemaObject):
                        self._traverse_schema_objects(
                            item,
                            [*path, "items", str(index)],
                            callback,
                            include_one_of=include_one_of,
                        )
        if obj.prefixItems:
            for index, item in enumerate(obj.prefixItems):
                if isinstance(item, JsonSchemaObject):
                    self._traverse_schema_objects(
                        item,
                        [*path, "prefixItems", str(index)],
                        callback,
                        include_one_of=include_one_of,
                    )
        if isinstance(obj.additionalProperties, JsonSchemaObject):
            self._traverse_schema_objects(
                obj.additionalProperties,
                [*path, "additionalProperties"],
                callback,
                include_one_of=include_one_of,
            )
        if isinstance(obj.unevaluatedProperties, JsonSchemaObject):
            self._traverse_schema_objects(
                obj.unevaluatedProperties,
                [*path, "unevaluatedProperties"],
                callback,
                include_one_of=include_one_of,
            )
        if isinstance(obj.unevaluatedItems, JsonSchemaObject):
            self._traverse_schema_objects(
                obj.unevaluatedItems,
                [*path, "unevaluatedItems"],
                callback,
                include_one_of=include_one_of,
            )
        if obj.patternProperties:
            for key, value in obj.patternProperties.items():
                if isinstance(value, JsonSchemaObject):
                    self._traverse_schema_objects(
                        value,
                        [*path, "patternProperties", key],
                        callback,
                        include_one_of=include_one_of,
                    )
        if isinstance(obj.propertyNames, JsonSchemaObject):
            self._traverse_schema_objects(
                obj.propertyNames,
                [*path, "propertyNames"],
                callback,
                include_one_of=include_one_of,
            )
        for index, item in enumerate(obj.anyOf):
            if isinstance(item, JsonSchemaObject):
                self._traverse_schema_objects(
                    item,
                    [*path, "anyOf", str(index)],
                    callback,
                    include_one_of=include_one_of,
                )
        for index, item in enumerate(obj.allOf):
            if isinstance(item, JsonSchemaObject):
                self._traverse_schema_objects(
                    item,
                    [*path, "allOf", str(index)],
                    callback,
                    include_one_of=include_one_of,
                )
        if include_one_of:
            for index, item in enumerate(obj.oneOf):
                if isinstance(item, JsonSchemaObject):
                    self._traverse_schema_objects(
                        item,
                        [*path, "oneOf", str(index)],
                        callback,
                        include_one_of=include_one_of,
                    )
        if obj.properties:
            for key, value in obj.properties.items():
                if isinstance(value, JsonSchemaObject):
                    self._traverse_schema_objects(
                        value,
                        [*path, "properties", key],
                        callback,
                        include_one_of=include_one_of,
                    )

    def _resolve_ref_callback(self, obj: JsonSchemaObject, path: list[str]) -> None:  # noqa: ARG002
        """Resolve $ref in schema object."""
        if obj.ref:
            self.resolve_ref(obj.ref)

    def _add_id_callback(self, obj: JsonSchemaObject, path: list[str]) -> None:
        """Add $id and $anchor to model resolver."""
        if obj.id:
            self.model_resolver.add_id(obj.id, path)
        if obj.anchor:
            self.model_resolver.add_id(f"#{obj.anchor}", path)

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
        if raw is True:
            return self.SCHEMA_OBJECT_TYPE()
        if raw is False:
            return self.SCHEMA_OBJECT_TYPE(is_boolean_schema_false=True)
        try:
            return self.SCHEMA_OBJECT_TYPE.model_validate(raw)
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
            warn_deprecated(
                "schema.jsonschema-items-array",
                details=f"Schema path: {'/'.join(path)}",
                stacklevel=4,
            )

    def _handle_python_import(
        self,
        name: str,
        path: list[str],
    ) -> None:
        """Mark x-python-import reference as loaded to skip model generation."""
        self.model_resolver.add(path, name, class_name=True, loaded=True)

    def _is_named_schema_definition_path(self, path: list[str]) -> bool:
        """Check if path points to a named schema entry under definitions/$defs."""
        current_root = list(self.model_resolver.current_root)
        expected_path_length = len(current_root) + 2
        if len(path) != expected_path_length:
            return False

        schema_container_path = path[len(current_root)]
        return path[: len(current_root)] == current_root and any(
            schema_container_path == schema_path for schema_path, _ in self.schema_paths
        )

    def parse_obj(  # noqa: PLR0912
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> None:
        """Parse a JsonSchemaObject by dispatching to appropriate parse methods."""
        if obj.has_ref_with_schema_keywords and not obj.is_ref_with_nullable_only:
            obj = self._merge_ref_with_schema(obj)
            if obj.ref:
                if self._is_named_schema_definition_path(path):
                    self.parse_root_type(name, obj, path)
                self.parse_ref(obj, path)
                return

        if obj.is_array:
            self.parse_array(name, obj, path)
        elif obj.allOf and (obj.oneOf or obj.anyOf):
            self.parse_root_type(name, obj, path)
        elif obj.allOf:
            self.parse_all_of(name, obj, path)
        elif obj.oneOf or obj.anyOf:
            combined_items = obj.oneOf or obj.anyOf
            const_enum_data = self._extract_const_enum_from_combined(combined_items, obj.type)
            if const_enum_data is not None:
                enum_values, varnames, descriptions, enum_type, nullable = const_enum_data
                synthetic_obj = self._create_synthetic_enum_obj(
                    obj, enum_values, varnames, descriptions, enum_type, nullable
                )
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
        elif obj.patternProperties or (obj.propertyNames is not None and obj.propertyNames is not False):
            self.parse_root_type(name, obj, path)
        elif obj.type == "object":
            self.parse_object(name, obj, path)
        elif obj.propertyNames is False:
            self.parse_root_type(name, obj, path)
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

    def _load_source_dict(self, source: Source) -> dict[str, Any]:  # noqa: PLR6301
        return dict(source.raw_data) if source.raw_data is not None else load_data(source.text)

    def _resolve_root_model_name(self, raw_obj: dict[str, Any]) -> tuple[str, bool]:
        title = raw_obj.get("title")
        title_str = str(title) if title is not None else "Model"
        if self.custom_class_name_generator:
            return title_str, False

        if class_name := self.class_name:
            if not self.model_resolver.validate_name(class_name):
                raise InvalidClassNameError(class_name)
            return class_name, self._should_preserve_explicit_root_class_name(class_name)

        obj_name = title_str
        if not self.model_resolver.validate_name(obj_name):
            obj_name = title_to_class_name(obj_name)
        if not self.model_resolver.validate_name(obj_name):
            raise InvalidClassNameError(obj_name)
        return obj_name, False

    def _parse_converted_sources(self, make_converter: Callable[[], Any]) -> None:
        for source, path_parts in self._get_context_source_path_parts():
            raw_obj = make_converter().convert(source)
            source.raw_data = raw_obj
            if source.path.parts:
                self.remote_object_cache[str((self.base_path / source.path).resolve())] = raw_obj
            self.raw_obj = raw_obj
            obj_name, preserve_root_class_name = self._resolve_root_model_name(raw_obj)
            self._parse_file(
                raw_obj,
                obj_name,
                path_parts,
                preserve_root_class_name=preserve_root_class_name,
            )

        self._resolve_unparsed_json_pointer()
        self._generate_forced_base_models()

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
            obj_name, preserve_root_class_name = self._resolve_root_model_name(self.raw_obj)
            self._parse_file(self.raw_obj, obj_name, path_parts, preserve_root_class_name=preserve_root_class_name)

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
                    self.raw_obj = self._load_source_dict(source)
                    self.parse_json_pointer(self.raw_obj, reserved_ref, path_parts)

        if model_count != len(self.results):
            # New model have been generated. It try to resolve json pointer again.
            self._resolve_unparsed_json_pointer()

    def parse_json_pointer(self, raw: dict[str, YamlValue], ref: str, path_parts: list[str]) -> None:
        """Parse a JSON pointer reference into a model."""
        path = ref.split("#", 1)[-1]
        path = path.removeprefix("/")
        object_paths, reference_paths = _split_json_pointer(raw, path)
        if not object_paths:  # pragma: no cover
            reference = self.model_resolver.add_ref(ref)
            self.parse_obj(reference.name, self._validate_schema_object(raw, [ref]), [ref])
            return
        models = get_model_by_path(raw, object_paths)
        model_name = reference_paths[-1]

        self.parse_raw_obj(model_name, models, [*path_parts, f"#/{reference_paths[0]}", *reference_paths[1:]])

    def _parse_file(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915
        self,
        raw: dict[str, Any],
        obj_name: str,
        path_parts: list[str],
        object_paths: list[str] | None = None,
        reference_paths: list[str] | None = None,
        *,
        preserve_root_class_name: bool = False,
    ) -> None:
        """Parse a file containing JSON Schema definitions and references."""
        object_paths = [o for o in object_paths or [] if o]
        reference_paths = [r for r in reference_paths or [] if r]
        path = (
            [*path_parts, f"#/{reference_paths[0]}", *reference_paths[1:]]
            if reference_paths
            else [*path_parts, f"#/{object_paths[0]}", *object_paths[1:]]
            if object_paths
            else path_parts
        )
        with self.model_resolver.current_root_context(path_parts):
            obj_name = self.model_resolver.add(
                path,
                obj_name,
                unique=False,
                class_name=True,
                preserve_class_name=preserve_root_class_name,
            ).name
            with self.root_id_context(raw):
                # Some jsonschema docs include attribute self to have include version details
                raw.pop("self", None)
                # parse $id before parsing $ref
                root_obj = self._validate_schema_object(raw, path_parts or ["#"])
                self.parse_id(root_obj, [*path_parts, "#"] if path_parts else ["#"])
                root_key = tuple(path_parts)
                if root_obj.recursiveAnchor:
                    self._recursive_anchor_index.setdefault(root_key, []).append(
                        self._anchor_ref_path(root_key, path_parts)
                    )
                if root_obj.dynamicAnchor:
                    self._dynamic_anchor_index.setdefault(root_key, {}).setdefault(
                        root_obj.dynamicAnchor, self._anchor_ref_path(root_key, path_parts)
                    )
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
                    if obj.recursiveAnchor:
                        ref_path = self._anchor_ref_path(root_key, definition_path)
                        self._recursive_anchor_index.setdefault(root_key, []).append(ref_path)
                    if obj.dynamicAnchor:
                        ref_path = self._anchor_ref_path(root_key, definition_path)
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
                        object_paths, reference_paths = _split_json_pointer(raw, reserved_path.split("#", 1)[-1])
                        if not object_paths:
                            self.parse_obj(
                                reference.name, self._validate_schema_object(raw, [reserved_path]), [reserved_path]
                            )
                            continue
                        models = get_model_by_path(raw, object_paths)
                        model_name = reference_paths[-1]
                        path = [*path_parts, f"#/{reference_paths[0]}", *reference_paths[1:]]
                        self.parse_obj(model_name, self._validate_schema_object(models, path), path)
                    previous_reserved_refs = reserved_refs
                    reserved_refs = set(self.reserved_refs.get(key) or [])
                    if previous_reserved_refs == reserved_refs:
                        break
