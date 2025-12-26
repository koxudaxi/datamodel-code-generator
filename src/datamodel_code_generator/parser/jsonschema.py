"""JSON Schema parser implementation.

Handles parsing of JSON Schema, JSON, YAML, Dict, and CSV inputs to generate
Python data models. Supports draft-04 through draft-2020-12 schemas.
"""

from __future__ import annotations

import enum as _enum
import json
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

from datamodel_code_generator import (
    DEFAULT_SHARED_MODULE_NAME,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    FieldTypeCollisionStrategy,
    InvalidClassNameError,
    NamingStrategy,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    SchemaParseError,
    TargetPydanticVersion,
    YamlValue,
    load_data,
    load_data_from_path,
    snooper_to_methods,
)
from datamodel_code_generator.format import (
    DEFAULT_FORMATTERS,
    DateClassType,
    DatetimeClassType,
    Formatter,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.imports import IMPORT_ANY
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
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
    DataTypeManager,
    EmptyDataType,
    StrictTypes,
    Types,
    UnionIntFloat,
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
    from collections.abc import Callable, Generator, Iterable, Iterator, Mapping, Sequence


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
    """Represent OpenAPI discriminator object."""

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
        if isinstance(value, list):  # noqa: PLR1702
            # Filter to only include valid strings, excluding invalid objects
            required_fields: list[str] = []
            for item in value:
                if isinstance(item, str):
                    required_fields.append(item)

                # In some cases, the required field can include "anyOf", "oneOf", or "allOf" as a dict (#2297)
                elif isinstance(item, dict):
                    for key, val in item.items():
                        if isinstance(val, list):
                            # If 'anyOf' or "oneOf" is present, we won't include it in required fields
                            if key in {"anyOf", "oneOf"}:
                                continue

                            if key == "allOf":
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
    oneOf: list[JsonSchemaObject] = []  # noqa: N815, RUF012
    anyOf: list[JsonSchemaObject] = []  # noqa: N815, RUF012
    allOf: list[JsonSchemaObject] = []  # noqa: N815, RUF012
    enum: list[Any] = []  # noqa: RUF012
    writeOnly: Optional[bool] = None  # noqa: N815, UP045
    readOnly: Optional[bool] = None  # noqa: N815, UP045
    properties: Optional[dict[str, Union[JsonSchemaObject, bool]]] = None  # noqa: UP007, UP045
    required: list[str] = []  # noqa: RUF012
    ref: Optional[str] = Field(default=None, alias="$ref")  # noqa: UP045
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
    custom_base_path: Optional[str] = Field(default=None, alias="customBasePath")  # noqa: UP045
    extras: dict[str, Any] = Field(alias=__extra_key__, default_factory=dict)
    discriminator: Optional[Union[Discriminator, str]] = None  # noqa: UP007, UP045
    if is_pydantic_v2():
        model_config = ConfigDict(  # pyright: ignore[reportPossiblyUnboundVariable]
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
        as they don't affect the schema structure.
        """
        if not self.ref:
            return False
        other_fields = get_fields_set(self) - {"ref"}
        schema_affecting_fields = other_fields - self.__metadata_only_fields__ - {"extras"}
        if self.extras:
            schema_affecting_extras = {k for k in self.extras if k not in self.__metadata_only_fields__}
            if schema_affecting_extras:
                schema_affecting_fields |= {"extras"}
        return bool(schema_affecting_fields)


@lru_cache
def get_ref_type(ref: str) -> JSONReference:
    """Determine the type of reference (LOCAL, REMOTE, or URL)."""
    if ref[0] == "#":
        return JSONReference.LOCAL
    if is_url(ref):
        return JSONReference.URL
    return JSONReference.REMOTE


def _get_type(type_: str, format__: str | None = None) -> Types:
    """Get the appropriate Types enum for a given JSON Schema type and format."""
    if type_ not in json_schema_data_formats:
        return Types.any
    if (data_formats := json_schema_data_formats[type_].get("default" if format__ is None else format__)) is not None:
        return data_formats

    warn(f"format of {format__!r} not understood for {type_!r} - using default", stacklevel=2)
    return json_schema_data_formats[type_]["default"]


JsonSchemaObject.model_rebuild()

DEFAULT_FIELD_KEYS: set[str] = {
    "example",
    "examples",
    "description",
    "discriminator",
    "title",
    "const",
    "default_factory",
}

EXCLUDE_FIELD_KEYS_IN_JSON_SCHEMA: set[str] = {
    "readOnly",
    "writeOnly",
}

EXCLUDE_FIELD_KEYS = (
    set(JsonSchemaObject.get_fields())  # pyright: ignore[reportAttributeAccessIssue]
    - DEFAULT_FIELD_KEYS
    - EXCLUDE_FIELD_KEYS_IN_JSON_SCHEMA
) | {
    "$id",
    "$ref",
    JsonSchemaObject.__extra_key__,
}


@snooper_to_methods()  # noqa: PLR0904
class JsonSchemaParser(Parser):
    """Parser for JSON Schema, JSON, YAML, Dict, and CSV formats."""

    SCHEMA_PATHS: ClassVar[list[str]] = ["#/definitions", "#/$defs"]
    SCHEMA_OBJECT_TYPE: ClassVar[type[JsonSchemaObject]] = JsonSchemaObject

    def __init__(  # noqa: PLR0913
        self,
        source: str | Path | list[Path] | ParseResult,
        *,
        data_model_type: type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: type[DataModel] = pydantic_model.CustomRootType,
        data_type_manager_type: type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: str | None = None,
        base_class_map: dict[str, str] | None = None,
        additional_imports: list[str] | None = None,
        class_decorators: list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        target_python_version: PythonVersion = PythonVersionMin,
        dump_resolve_reference_action: Callable[[Iterable[str]], str] | None = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Mapping[str, str] | None = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        allow_extra_fields: bool = False,
        extra_fields: str | None = None,
        use_generic_base_class: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: str | None = None,
        use_standard_collections: bool = False,
        base_path: Path | None = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_field_description_example: bool = False,
        use_attribute_docstrings: bool = False,
        use_inline_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        reuse_scope: ReuseScope | None = None,
        shared_module_name: str = DEFAULT_SHARED_MODULE_NAME,
        encoding: str = "utf-8",
        enum_field_as_literal: LiteralType | None = None,
        enum_field_as_literal_map: dict[str, str] | None = None,
        ignore_enum_constraints: bool = False,
        use_one_literal_as_default: bool = False,
        use_enum_values_in_discriminator: bool = False,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
        use_specialized_enum: bool = True,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: DefaultPutDict[str, str] | None = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Sequence[StrictTypes] | None = None,
        empty_enum_field_name: str | None = None,
        custom_class_name_generator: Callable[[str], str] | None = None,
        field_extra_keys: set[str] | None = None,
        field_include_all_keys: bool = False,
        field_extra_keys_without_x_prefix: set[str] | None = None,
        model_extra_keys: set[str] | None = None,
        model_extra_keys_without_x_prefix: set[str] | None = None,
        wrap_string_literal: bool | None = None,
        use_title_as_name: bool = False,
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
        use_tuple_for_fixed_items: bool = False,
        allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints,
        http_headers: Sequence[tuple[str, str]] | None = None,
        http_ignore_tls: bool = False,
        http_timeout: float | None = None,
        use_annotated: bool = False,
        use_serialize_as_any: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        use_decimal_for_multiple_of: bool = False,
        original_field_name_delimiter: str | None = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None = None,
        collapse_reuse_models: bool = False,
        skip_root_model: bool = False,
        use_type_alias: bool = False,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
        known_third_party: list[str] | None = None,
        custom_formatters: list[str] | None = None,
        custom_formatters_kwargs: dict[str, Any] | None = None,
        use_pendulum: bool = False,
        use_standard_primitive_types: bool = False,
        http_query_parameters: Sequence[tuple[str, str]] | None = None,
        treat_dot_as_module: bool | None = None,
        use_exact_imports: bool = False,
        default_field_extras: dict[str, Any] | None = None,
        target_datetime_class: DatetimeClassType | None = None,
        target_date_class: DateClassType | None = None,
        keyword_only: bool = False,
        frozen_dataclasses: bool = False,
        no_alias: bool = False,
        use_frozen_field: bool = False,
        use_default_factory_for_optional_nested_models: bool = False,
        formatters: list[Formatter] = DEFAULT_FORMATTERS,
        defer_formatting: bool = False,
        parent_scoped_naming: bool = False,
        naming_strategy: NamingStrategy | None = None,
        duplicate_name_suffix: dict[str, str] | None = None,
        dataclass_arguments: DataclassArguments | None = None,
        type_mappings: list[str] | None = None,
        type_overrides: dict[str, str] | None = None,
        read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None,
        field_type_collision_strategy: FieldTypeCollisionStrategy | None = None,
        target_pydantic_version: TargetPydanticVersion | None = None,
    ) -> None:
        """Initialize the JSON Schema parser with configuration options."""
        target_datetime_class = target_datetime_class or DatetimeClassType.Awaredatetime
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_type_manager_type=data_type_manager_type,
            data_model_field_type=data_model_field_type,
            base_class=base_class,
            base_class_map=base_class_map,
            additional_imports=additional_imports,
            class_decorators=class_decorators,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            target_python_version=target_python_version,
            dump_resolve_reference_action=dump_resolve_reference_action,
            validation=validation,
            field_constraints=field_constraints,
            snake_case_field=snake_case_field,
            strip_default_none=strip_default_none,
            aliases=aliases,
            allow_population_by_field_name=allow_population_by_field_name,
            allow_extra_fields=allow_extra_fields,
            extra_fields=extra_fields,
            use_generic_base_class=use_generic_base_class,
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            force_optional_for_required_fields=force_optional_for_required_fields,
            class_name=class_name,
            use_standard_collections=use_standard_collections,
            base_path=base_path,
            use_schema_description=use_schema_description,
            use_field_description=use_field_description,
            use_field_description_example=use_field_description_example,
            use_attribute_docstrings=use_attribute_docstrings,
            use_inline_field_description=use_inline_field_description,
            use_default_kwarg=use_default_kwarg,
            reuse_model=reuse_model,
            reuse_scope=reuse_scope,
            shared_module_name=shared_module_name,
            encoding=encoding,
            enum_field_as_literal=enum_field_as_literal,
            enum_field_as_literal_map=enum_field_as_literal_map,
            ignore_enum_constraints=ignore_enum_constraints,
            use_one_literal_as_default=use_one_literal_as_default,
            use_enum_values_in_discriminator=use_enum_values_in_discriminator,
            set_default_enum_member=set_default_enum_member,
            use_subclass_enum=use_subclass_enum,
            use_specialized_enum=use_specialized_enum,
            strict_nullable=strict_nullable,
            use_generic_container_types=use_generic_container_types,
            enable_faux_immutability=enable_faux_immutability,
            remote_text_cache=remote_text_cache,
            disable_appending_item_suffix=disable_appending_item_suffix,
            strict_types=strict_types,
            empty_enum_field_name=empty_enum_field_name,
            custom_class_name_generator=custom_class_name_generator,
            field_extra_keys=field_extra_keys,
            field_include_all_keys=field_include_all_keys,
            field_extra_keys_without_x_prefix=field_extra_keys_without_x_prefix,
            model_extra_keys=model_extra_keys,
            model_extra_keys_without_x_prefix=model_extra_keys_without_x_prefix,
            wrap_string_literal=wrap_string_literal,
            use_title_as_name=use_title_as_name,
            use_operation_id_as_name=use_operation_id_as_name,
            use_unique_items_as_set=use_unique_items_as_set,
            use_tuple_for_fixed_items=use_tuple_for_fixed_items,
            allof_merge_mode=allof_merge_mode,
            http_headers=http_headers,
            http_ignore_tls=http_ignore_tls,
            http_timeout=http_timeout,
            use_annotated=use_annotated,
            use_serialize_as_any=use_serialize_as_any,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            use_decimal_for_multiple_of=use_decimal_for_multiple_of,
            original_field_name_delimiter=original_field_name_delimiter,
            use_double_quotes=use_double_quotes,
            use_union_operator=use_union_operator,
            allow_responses_without_content=allow_responses_without_content,
            collapse_root_models=collapse_root_models,
            collapse_root_models_name_strategy=collapse_root_models_name_strategy,
            collapse_reuse_models=collapse_reuse_models,
            skip_root_model=skip_root_model,
            use_type_alias=use_type_alias,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
            keep_model_order=keep_model_order,
            known_third_party=known_third_party,
            custom_formatters=custom_formatters,
            custom_formatters_kwargs=custom_formatters_kwargs,
            use_pendulum=use_pendulum,
            use_standard_primitive_types=use_standard_primitive_types,
            http_query_parameters=http_query_parameters,
            treat_dot_as_module=treat_dot_as_module,
            use_exact_imports=use_exact_imports,
            default_field_extras=default_field_extras,
            target_datetime_class=target_datetime_class,
            target_date_class=target_date_class,
            keyword_only=keyword_only,
            frozen_dataclasses=frozen_dataclasses,
            no_alias=no_alias,
            use_frozen_field=use_frozen_field,
            use_default_factory_for_optional_nested_models=use_default_factory_for_optional_nested_models,
            formatters=formatters,
            defer_formatting=defer_formatting,
            parent_scoped_naming=parent_scoped_naming,
            naming_strategy=naming_strategy,
            duplicate_name_suffix=duplicate_name_suffix,
            dataclass_arguments=dataclass_arguments,
            type_mappings=type_mappings,
            type_overrides=type_overrides,
            read_only_write_only_model_type=read_only_write_only_model_type,
            field_type_collision_strategy=field_type_collision_strategy,
            target_pydantic_version=target_pydantic_version,
        )

        self.remote_object_cache: DefaultPutDict[str, dict[str, YamlValue]] = DefaultPutDict()
        self.raw_obj: dict[str, YamlValue] = {}
        self._root_id: Optional[str] = None  # noqa: UP045
        self._root_id_base_path: Optional[str] = None  # noqa: UP045
        self.reserved_refs: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
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

    def _get_type_with_mappings(self, type_: str, format_: str | None = None) -> Types:
        """Get the Types enum for a given type and format, applying custom type mappings.

        Custom mappings from --type-mappings are checked first, then falls back to
        the default json_schema_data_formats mappings.
        """
        if self.type_mappings and format_ is not None and (type_, format_) in self.type_mappings:
            target_format = self.type_mappings[type_, format_]
            for type_formats in json_schema_data_formats.values():
                if target_format in type_formats:
                    return type_formats[target_format]
            if target_format in json_schema_data_formats:
                return json_schema_data_formats[target_format]["default"]

        return _get_type(type_, format_)

    @cached_property
    def schema_paths(self) -> list[tuple[str, list[str]]]:
        """Get schema paths for definitions and defs."""
        return [(s, s.lstrip("#/").split("/")) for s in self.SCHEMA_PATHS]

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
            else:
                varnames.append(str(const_value))

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
            x_enum_varnames=final_varnames,
            default=original.default if original.has_default else None,
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
        if self.read_only_write_only_model_type is None:
            return True
        if self.read_only_write_only_model_type == ReadOnlyWriteOnlyModelType.All:
            return True
        return not generates_separate_models

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
        alias: str | None,
        original_field_name: str | None,
    ) -> DataModelFieldBase:
        """Create a data model field from a JSON Schema object field."""
        constraints = model_dump(field, exclude_none=True) if self.is_constraints_field(field) else None
        if constraints is not None and self.field_constraints and field.format == "hostname":
            constraints["pattern"] = self.data_type_manager.HOSTNAME_REGEX
        # Suppress minItems/maxItems for fixed-length tuples
        if constraints and self._is_fixed_length_tuple(field):
            constraints.pop("minItems", None)
            constraints.pop("maxItems", None)
        return self.data_model_field_type(
            name=field_name,
            default=field.default,
            data_type=field_type,
            required=required,
            alias=alias,
            constraints=constraints,
            nullable=field.nullable
            if self.strict_nullable and field.nullable is not None
            else (False if self.strict_nullable and (field.has_default or required) else None),
            strip_default_none=self.strip_default_none,
            extras=self.get_field_extras(field),
            use_annotated=self.use_annotated,
            use_serialize_as_any=self.use_serialize_as_any,
            use_field_description=self.use_field_description,
            use_field_description_example=self.use_field_description_example,
            use_inline_field_description=self.use_inline_field_description,
            use_default_kwarg=self.use_default_kwarg,
            original_name=original_field_name,
            has_default=field.has_default,
            type_has_null=field.type_has_null,
            read_only=self._resolve_field_flag(field, "readOnly"),
            write_only=self._resolve_field_flag(field, "writeOnly"),
            use_frozen_field=self.use_frozen_field,
            use_default_factory_for_optional_nested_models=self.use_default_factory_for_optional_nested_models,
        )

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        """Get the data type for a JSON Schema object."""
        if obj.type is None:
            if "const" in obj.extras:
                return self.data_type_manager.get_data_type_from_value(obj.extras["const"])
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
        reference = self.model_resolver.add_ref(ref)
        ref_schema = self._load_ref_schema_object(ref)
        is_optional = ref_schema.type == "null" or (self.strict_nullable and ref_schema.nullable is True)
        return self.data_type(reference=reference, is_optional=is_optional)

    def set_additional_properties(self, path: str, obj: JsonSchemaObject) -> None:
        """Set additional properties flag in extra template data."""
        if isinstance(obj.additionalProperties, bool):
            self.extra_template_data[path]["additionalProperties"] = obj.additionalProperties

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

    def _apply_title_as_name(self, name: str, obj: JsonSchemaObject) -> str:
        """Apply title as name if use_title_as_name is enabled."""
        if self.use_title_as_name and obj.title:
            return sanitize_module_name(obj.title, treat_dot_as_module=self.treat_dot_as_module)
        return name

    def _should_field_be_required(
        self,
        *,
        in_required_list: bool = True,
        has_default: bool = False,
        is_nullable: bool = False,
    ) -> bool:
        """Determine if a field should be marked as required."""
        if self.force_optional_for_required_fields:
            return False
        if self.apply_default_values_for_required_fields and has_default:  # pragma: no cover
            return False
        if is_nullable:
            return False
        return in_required_list

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

    def _get_inherited_field_type(self, prop_name: str, base_classes: list[Reference]) -> DataType | None:
        """Get the data type for an inherited property from parent schemas."""
        for base in base_classes:
            if not base.path:  # pragma: no cover
                continue
            if "#" in base.path:
                file_part, fragment = base.path.split("#", 1)
                ref = f"{file_part}#{fragment}" if file_part else f"#{fragment}"
            else:  # pragma: no cover
                ref = f"#{base.path}"
            try:
                parent_schema = self._load_ref_schema_object(ref)
            except Exception:  # pragma: no cover  # noqa: BLE001, S112
                continue
            if not parent_schema.properties:  # pragma: no cover
                continue
            prop_schema = parent_schema.properties.get(prop_name)
            if not isinstance(prop_schema, JsonSchemaObject):  # pragma: no cover
                continue
            result = self._build_lightweight_type(prop_schema)
            if result is not None:
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

        if ref_item.has_ref_with_schema_keywords:
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
        Continue merging when multiple $refs share properties to avoid duplicate fields.
        """
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

        if obj.properties:
            for prop_name, prop_schema in obj.properties.items():
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
        base_object = model_dump(obj, exclude={target_attribute_name}, exclude_unset=True, by_alias=True)
        combined_schemas: list[JsonSchemaObject] = []
        refs = []
        for index, target_attribute in enumerate(getattr(obj, target_attribute_name, [])):
            if target_attribute.ref:
                if target_attribute.has_ref_with_schema_keywords:
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

    def _parse_all_of_item(  # noqa: PLR0912, PLR0913, PLR0917
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
                            fields.append(
                                self.data_model_field_type(
                                    name=field_name,
                                    required=True,
                                    original_name=request,
                                    alias=alias,
                                    data_type=data_type,
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
                fields.append(
                    self.data_model_field_type(
                        name=field_name,
                        data_type=self.data_type_manager.get_data_type(
                            Types.any,
                        ),
                        required=False if self.force_optional_for_required_fields else original_field_name in requires,
                        alias=alias,
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

            if self.force_optional_for_required_fields or (
                self.apply_default_values_for_required_fields and field.has_default
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

    def parse_property_names(
        self,
        name: str,
        property_names: JsonSchemaObject,
        additional_properties: JsonSchemaObject | bool | None,  # noqa: FBT001
        path: list[str],
    ) -> DataType:
        """Parse propertyNames into a dict data type with constrained keys.

        Args:
            name: Name for the data type
            property_names: Schema constraining property names
            additional_properties: Schema for values (or bool/None)
            path: Current path in schema

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

        return self.data_type(
            data_types=[value_type],
            is_dict=True,
            dict_key=key_type,
        )

    def parse_item(  # noqa: PLR0911, PLR0912
        self,
        name: str,
        item: JsonSchemaObject,
        path: list[str],
        singular_name: bool = False,  # noqa: FBT001, FBT002
        parent: JsonSchemaObject | None = None,
    ) -> DataType:
        """Parse a single JSON Schema item into a data type."""
        if self.use_title_as_name and item.title:
            name = sanitize_module_name(item.title, treat_dot_as_module=self.treat_dot_as_module)
            singular_name = False
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
                return self.parse_property_names(name, item.propertyNames, item.additionalProperties, object_path)
            if isinstance(item.additionalProperties, JsonSchemaObject):
                return self.data_type(
                    data_types=[self.parse_item(name, item.additionalProperties, object_path)],
                    is_dict=True,
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

    def parse_array_fields(  # noqa: PLR0912
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
        singular_name: bool = True,  # noqa: FBT001, FBT002
    ) -> DataModelFieldBase:
        """Parse array schema into a data model field with list type."""
        if self.force_optional_for_required_fields:
            required: bool = False
            nullable: Optional[bool] = None  # noqa: UP045
        else:
            required = not (obj.has_default and self.apply_default_values_for_required_fields)
            if self.strict_nullable:
                nullable = obj.nullable if obj.has_default or required else True
            else:
                required = not obj.nullable and required
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

        data_types: list[DataType] = [
            self.data_type(
                data_types=item_data_types,
                is_tuple=is_tuple,
                is_list=not is_tuple,
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
            data_type = self.parse_property_names(name, obj.propertyNames, obj.additionalProperties, path)
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
        required = self._should_field_be_required(
            has_default=obj.has_default,
            is_nullable=bool(obj.nullable),
        )
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
                    default=obj.default,
                    required=required,
                    constraints=constraints,
                    nullable=obj.nullable
                    if self.strict_nullable and obj.nullable is not None
                    else (False if self.strict_nullable and obj.has_default else None),
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
        required = self._should_field_be_required(
            has_default=obj.has_default,
            is_nullable=bool(is_nullable),
        )

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
        """Context manager to temporarily set the root $id during parsing."""
        previous_root_id = self.root_id
        self.root_id = root_raw.get("$id") or None
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
        obj = self._validate_schema_object(raw, path)
        self.parse_obj(name, obj, path)

    def parse_obj(  # noqa: PLR0912
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> None:
        """Parse a JsonSchemaObject by dispatching to appropriate parse methods."""
        if obj.has_ref_with_schema_keywords:
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

    def _parse_file(
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
