"""OpenAPI and Swagger specification parser.

Extends JsonSchemaParser to handle OpenAPI 2.0 (Swagger), 3.0, and 3.1
specifications, including paths, operations, parameters, and request/response bodies.
"""

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import nullcontext
from enum import Enum
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Any, ClassVar, Optional, TypeVar, Union
from warnings import warn

from pydantic import Field

from datamodel_code_generator import (
    DEFAULT_SHARED_MODULE_NAME,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    Error,
    FieldTypeCollisionStrategy,
    LiteralType,
    NamingStrategy,
    OpenAPIScope,
    PythonVersion,
    PythonVersionMin,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    TargetPydanticVersion,
    YamlValue,
    load_data,
    snooper_to_methods,
)
from datamodel_code_generator.format import DEFAULT_FORMATTERS, DateClassType, DatetimeClassType, Formatter
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.parser.base import get_special_path
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    get_model_by_path,
)
from datamodel_code_generator.reference import FieldNameResolver, is_url, snake_to_upper_camel
from datamodel_code_generator.types import (
    DataType,
    DataTypeManager,
    EmptyDataType,
    StrictTypes,
)
from datamodel_code_generator.util import BaseModel, model_dump, model_validate

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence
    from urllib.parse import ParseResult

    from datamodel_code_generator.parser import DefaultPutDict


RE_APPLICATION_JSON_PATTERN: Pattern[str] = re.compile(r"^application/.*json$")

OPERATION_NAMES: list[str] = [
    "get",
    "put",
    "post",
    "delete",
    "patch",
    "head",
    "options",
    "trace",
]


class ParameterLocation(Enum):
    """Represent OpenAPI parameter locations."""

    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"


BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class ReferenceObject(BaseModel):
    """Represent an OpenAPI reference object ($ref)."""

    ref: str = Field(..., alias="$ref")


class ExampleObject(BaseModel):
    """Represent an OpenAPI example object."""

    summary: Optional[str] = None  # noqa: UP045
    description: Optional[str] = None  # noqa: UP045
    value: YamlValue = None
    externalValue: Optional[str] = None  # noqa: N815, UP045


class MediaObject(BaseModel):
    """Represent an OpenAPI media type object."""

    schema_: Optional[Union[ReferenceObject, JsonSchemaObject]] = Field(None, alias="schema")  # noqa: UP007, UP045
    example: YamlValue = None
    examples: Optional[Union[str, ReferenceObject, ExampleObject]] = None  # noqa: UP007, UP045


class ParameterObject(BaseModel):
    """Represent an OpenAPI parameter object."""

    name: Optional[str] = None  # noqa: UP045
    in_: Optional[ParameterLocation] = Field(None, alias="in")  # noqa: UP045
    description: Optional[str] = None  # noqa: UP045
    required: bool = False
    deprecated: bool = False
    schema_: Optional[JsonSchemaObject] = Field(None, alias="schema")  # noqa: UP045
    example: YamlValue = None
    examples: Optional[Union[str, ReferenceObject, ExampleObject]] = None  # noqa: UP007, UP045
    content: dict[str, MediaObject] = {}  # noqa: RUF012


class HeaderObject(BaseModel):
    """Represent an OpenAPI header object."""

    description: Optional[str] = None  # noqa: UP045
    required: bool = False
    deprecated: bool = False
    schema_: Optional[JsonSchemaObject] = Field(None, alias="schema")  # noqa: UP045
    example: YamlValue = None
    examples: Optional[Union[str, ReferenceObject, ExampleObject]] = None  # noqa: UP007, UP045
    content: dict[str, MediaObject] = {}  # noqa: RUF012


class RequestBodyObject(BaseModel):
    """Represent an OpenAPI request body object."""

    description: Optional[str] = None  # noqa: UP045
    content: dict[str, MediaObject] = {}  # noqa: RUF012
    required: bool = False


class ResponseObject(BaseModel):
    """Represent an OpenAPI response object."""

    description: Optional[str] = None  # noqa: UP045
    headers: dict[str, ParameterObject] = {}  # noqa: RUF012
    content: dict[Union[str, int], MediaObject] = {}  # noqa: RUF012, UP007


class Operation(BaseModel):
    """Represent an OpenAPI operation object."""

    tags: list[str] = []  # noqa: RUF012
    summary: Optional[str] = None  # noqa: UP045
    description: Optional[str] = None  # noqa: UP045
    operationId: Optional[str] = None  # noqa: N815, UP045
    parameters: list[Union[ReferenceObject, ParameterObject]] = []  # noqa: RUF012, UP007
    requestBody: Optional[Union[ReferenceObject, RequestBodyObject]] = None  # noqa: N815, UP007, UP045
    responses: dict[Union[str, int], Union[ReferenceObject, ResponseObject]] = {}  # noqa: RUF012, UP007
    deprecated: bool = False


class ComponentsObject(BaseModel):
    """Represent an OpenAPI components object."""

    schemas: dict[str, Union[ReferenceObject, JsonSchemaObject]] = {}  # noqa: RUF012, UP007
    responses: dict[str, Union[ReferenceObject, ResponseObject]] = {}  # noqa: RUF012, UP007
    examples: dict[str, Union[ReferenceObject, ExampleObject]] = {}  # noqa: RUF012, UP007
    requestBodies: dict[str, Union[ReferenceObject, RequestBodyObject]] = {}  # noqa: N815, RUF012, UP007
    headers: dict[str, Union[ReferenceObject, HeaderObject]] = {}  # noqa: RUF012, UP007


@snooper_to_methods()
class OpenAPIParser(JsonSchemaParser):
    """Parser for OpenAPI 2.0/3.0/3.1 and Swagger specifications."""

    SCHEMA_PATHS: ClassVar[list[str]] = ["#/components/schemas"]

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
        allow_extra_fields: bool = False,
        extra_fields: str | None = None,
        use_generic_base_class: bool = False,
        apply_default_values_for_required_fields: bool = False,
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
        openapi_scopes: list[OpenAPIScope] | None = None,
        include_path_parameters: bool = False,
        wrap_string_literal: bool | None = False,
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
        formatters: list[Formatter] = DEFAULT_FORMATTERS,
        defer_formatting: bool = False,
        parent_scoped_naming: bool = False,
        naming_strategy: NamingStrategy | None = None,
        duplicate_name_suffix: dict[str, str] | None = None,
        dataclass_arguments: DataclassArguments | None = None,
        type_mappings: list[str] | None = None,
        type_overrides: dict[str, str] | None = None,
        read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None,
        use_frozen_field: bool = False,
        use_default_factory_for_optional_nested_models: bool = False,
        use_status_code_in_response_name: bool = False,
        field_type_collision_strategy: FieldTypeCollisionStrategy | None = None,
        target_pydantic_version: TargetPydanticVersion | None = None,
    ) -> None:
        """Initialize the OpenAPI parser with extensive configuration options."""
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
            formatters=formatters,
            defer_formatting=defer_formatting,
            parent_scoped_naming=parent_scoped_naming,
            naming_strategy=naming_strategy,
            duplicate_name_suffix=duplicate_name_suffix,
            dataclass_arguments=dataclass_arguments,
            type_mappings=type_mappings,
            type_overrides=type_overrides,
            read_only_write_only_model_type=read_only_write_only_model_type,
            use_frozen_field=use_frozen_field,
            use_default_factory_for_optional_nested_models=use_default_factory_for_optional_nested_models,
            field_type_collision_strategy=field_type_collision_strategy,
            target_pydantic_version=target_pydantic_version,
        )
        self.open_api_scopes: list[OpenAPIScope] = openapi_scopes or [OpenAPIScope.Schemas]
        self.include_path_parameters: bool = include_path_parameters
        self.use_status_code_in_response_name: bool = use_status_code_in_response_name
        self._discriminator_schemas: dict[str, dict[str, Any]] = {}
        self._discriminator_subtypes: dict[str, list[str]] = defaultdict(list)

    def get_ref_model(self, ref: str) -> dict[str, Any]:
        """Resolve a reference to its model definition."""
        ref_file, ref_path = self.model_resolver.resolve_ref(ref).split("#", 1)
        ref_body = self._get_ref_body(ref_file) if ref_file else self.raw_obj
        return get_model_by_path(ref_body, ref_path.split("/")[1:])

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        """Get data type from JSON schema object, handling OpenAPI nullable semantics."""
        # OpenAPI 3.0 doesn't allow `null` in the `type` field and list of types
        # https://swagger.io/docs/specification/data-models/data-types/#null
        # OpenAPI 3.1 does allow `null` in the `type` field and is equivalent to
        # a `nullable` flag on the property itself
        if obj.nullable and self.strict_nullable and isinstance(obj.type, str):
            obj.type = [obj.type, "null"]

        return super().get_data_type(obj)

    def _normalize_discriminator_mapping_ref(self, mapping_value: str) -> str:  # noqa: PLR6301
        """Normalize a discriminator mapping value to a full $ref path.

        Per OpenAPI spec, mapping values can be either:
        - Full refs: "#/components/schemas/Pet" or "./other.yaml#/components/schemas/Pet"
        - Short names: "Pet" or "Pet.V1" (relative to #/components/schemas/)
        - Relative paths: "schemas/Pet" or "./other.yaml"

        Values containing "/" or "#" are treated as paths/refs and passed through.
        All other values (including those with dots like "Pet.V1") are treated as
        short schema names and normalized to full refs.

        Note: Bare file references without path separators (e.g., "other.yaml") will be
        treated as schema names. Use "./other.yaml" format for file references.

        Note: This could be a staticmethod, but @snooper_to_methods() decorator
        converts staticmethods to regular functions when pysnooper is installed.
        """
        if "/" in mapping_value or "#" in mapping_value:
            return mapping_value
        return f"#/components/schemas/{mapping_value}"

    def _normalize_discriminator(self, discriminator: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of the discriminator dict with normalized mapping refs."""
        result = discriminator.copy()
        mapping = discriminator.get("mapping")
        if mapping:
            result["mapping"] = {
                k: self._normalize_discriminator_mapping_ref(v) for k, v in mapping.items() if isinstance(v, str)
            }
        return result

    def _get_discriminator_union_type(self, ref: str) -> DataType | None:
        """Create a union type for discriminator subtypes if available.

        First tries to use allOf subtypes. If none found, falls back to using
        the discriminator mapping to create the union type. This handles cases
        where schemas don't use allOf inheritance but have explicit discriminator mappings.
        """
        subtypes = self._discriminator_subtypes.get(ref, [])
        if not subtypes:
            discriminator = self._discriminator_schemas[ref]
            mapping = discriminator.get("mapping", {})
            if mapping:
                subtypes = [
                    self._normalize_discriminator_mapping_ref(v) for v in mapping.values() if isinstance(v, str)
                ]
        if not subtypes:
            return None
        refs = map(self.model_resolver.add_ref, subtypes)
        return self.data_type(data_types=[self.data_type(reference=r) for r in refs])

    def get_ref_data_type(self, ref: str) -> DataType:
        """Get data type for a reference, handling discriminator polymorphism."""
        if ref in self._discriminator_schemas and (union_type := self._get_discriminator_union_type(ref)):
            return union_type
        return super().get_ref_data_type(ref)

    def parse_object_fields(
        self,
        obj: JsonSchemaObject,
        path: list[str],
        module_name: Optional[str] = None,  # noqa: UP045
        class_name: Optional[str] = None,  # noqa: UP045
    ) -> list[DataModelFieldBase]:
        """Parse object fields, adding discriminator info for allOf polymorphism."""
        fields = super().parse_object_fields(obj, path, module_name, class_name=class_name)
        properties = obj.properties or {}

        result_fields: list[DataModelFieldBase] = []
        for field_obj in fields:
            field = properties.get(field_obj.original_name)

            if (
                isinstance(field, JsonSchemaObject)
                and field.ref
                and (discriminator := self._discriminator_schemas.get(field.ref))
            ):
                new_field_type = self._get_discriminator_union_type(field.ref) or field_obj.data_type
                normalized_discriminator = self._normalize_discriminator(discriminator)
                field_obj = self.data_model_field_type(**{  # noqa: PLW2901
                    **field_obj.__dict__,
                    "data_type": new_field_type,
                    "extras": {**field_obj.extras, "discriminator": normalized_discriminator},
                })
            result_fields.append(field_obj)

        return result_fields

    def resolve_object(self, obj: ReferenceObject | BaseModelT, object_type: type[BaseModelT]) -> BaseModelT:
        """Resolve a reference object to its actual type or return the object as-is."""
        if isinstance(obj, ReferenceObject):
            ref_obj = self.get_ref_model(obj.ref)
            return model_validate(object_type, ref_obj)
        return obj

    def _parse_schema_or_ref(
        self,
        name: str,
        schema: JsonSchemaObject | ReferenceObject | None,
        path: list[str],
    ) -> DataType | None:
        """Parse a schema object or resolve a reference to get DataType."""
        if schema is None:
            return None
        if isinstance(schema, JsonSchemaObject):
            return self.parse_schema(name, schema, path)
        self.resolve_ref(schema.ref)
        return self.get_ref_data_type(schema.ref)

    def _process_path_items(  # noqa: PLR0913
        self,
        items: dict[str, dict[str, Any]],
        base_path: list[str],
        scope_name: str,
        global_parameters: list[dict[str, Any]],
        security: list[dict[str, list[str]]] | None,
        *,
        strip_leading_slash: bool = True,
    ) -> None:
        """Process path or webhook items with operations."""
        scope_path = [*base_path, f"#/{scope_name}"]
        for item_name, methods_ in items.items():
            item_ref = methods_.get("$ref")
            if item_ref:
                methods = self.get_ref_model(item_ref)
                # Extract base path from reference for external file resolution
                resolved_ref = self.model_resolver.resolve_ref(item_ref)
                ref_file = resolved_ref.split("#")[0] if "#" in resolved_ref else resolved_ref
                ref_base_path = Path(ref_file).parent if ref_file and not is_url(ref_file) else None
            else:
                methods = methods_
                ref_base_path = None

            item_parameters = global_parameters.copy()
            if "parameters" in methods:
                item_parameters.extend(methods["parameters"])

            relative_name = item_name[1:] if strip_leading_slash else item_name.removeprefix("/")
            path = [*scope_path, relative_name] if relative_name else get_special_path("root", scope_path)

            base_path_context = (
                self.model_resolver.current_base_path_context(ref_base_path) if ref_base_path else nullcontext()
            )
            with base_path_context:
                for operation_name, raw_operation in methods.items():
                    if operation_name not in OPERATION_NAMES:
                        continue
                    if item_parameters:
                        if "parameters" in raw_operation:
                            raw_operation["parameters"].extend(item_parameters)
                        else:
                            raw_operation["parameters"] = item_parameters.copy()
                    if security is not None and "security" not in raw_operation:
                        raw_operation["security"] = security
                    self.parse_operation(raw_operation, [*path, operation_name])

    def parse_schema(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: list[str],
    ) -> DataType:
        """Parse a JSON schema object into a data type."""
        if obj.is_array:
            data_type = self.parse_array(name, obj, [*path, name])
        elif obj.allOf:  # pragma: no cover
            data_type = self.parse_all_of(name, obj, path)
        elif obj.oneOf or obj.anyOf:  # pragma: no cover
            data_type = self.parse_root_type(name, obj, path)
            if isinstance(data_type, EmptyDataType) and obj.properties:
                self.parse_object(name, obj, path)
        elif obj.is_object:
            data_type = self.parse_object(name, obj, path)
        elif obj.enum and not self.ignore_enum_constraints:  # pragma: no cover
            data_type = self.parse_enum(name, obj, path)
        elif obj.ref:  # pragma: no cover
            data_type = self.get_ref_data_type(obj.ref)
        else:
            data_type = self.get_data_type(obj)
        self.parse_ref(obj, path)
        return data_type

    def parse_request_body(
        self,
        name: str,
        request_body: RequestBodyObject,
        path: list[str],
    ) -> dict[str, DataType]:
        """Parse request body content into data types by media type."""
        data_types: dict[str, DataType] = {}
        for media_type, media_obj in request_body.content.items():
            data_type = self._parse_schema_or_ref(name, media_obj.schema_, [*path, media_type])
            if data_type:
                data_types[media_type] = data_type
        return data_types

    def parse_responses(
        self,
        name: str,
        responses: dict[str | int, ReferenceObject | ResponseObject],
        path: list[str],
    ) -> dict[str | int, dict[str, DataType]]:
        """Parse response objects into data types by status code and content type."""
        data_types: defaultdict[str | int, dict[str, DataType]] = defaultdict(dict)
        for status_code, detail in responses.items():
            response_name = f"{name}{str(status_code).capitalize()}" if self.use_status_code_in_response_name else name

            if isinstance(detail, ReferenceObject):
                if not detail.ref:  # pragma: no cover
                    continue
                ref_model = self.get_ref_model(detail.ref)
                content = {k: model_validate(MediaObject, v) for k, v in ref_model.get("content", {}).items()}
            else:
                content = detail.content

            if self.allow_responses_without_content and not content:
                data_types[status_code]["application/json"] = DataType(type="None")

            for content_type, obj in content.items():
                response_path: list[str] = [*path, str(status_code), str(content_type)]
                data_type = self._parse_schema_or_ref(response_name, obj.schema_, response_path)
                if data_type:
                    data_types[status_code][content_type] = data_type  # pyright: ignore[reportArgumentType]

        return data_types

    @classmethod
    def parse_tags(
        cls,
        name: str,  # noqa: ARG003
        tags: list[str],
        path: list[str],  # noqa: ARG003
    ) -> list[str]:
        """Parse operation tags."""
        return tags

    _field_name_resolver: FieldNameResolver = FieldNameResolver()

    @classmethod
    def _get_model_name(cls, path_name: str, method: str, suffix: str) -> str:
        normalized = cls._field_name_resolver.get_valid_name(path_name, ignore_snake_case_field=True)
        camel_path_name = snake_to_upper_camel(normalized)
        return f"{camel_path_name}{method.capitalize()}{suffix}"

    def parse_all_parameters(
        self,
        name: str,
        parameters: list[ReferenceObject | ParameterObject],
        path: list[str],
    ) -> DataType | None:
        """Parse all operation parameters into a data model."""
        fields: list[DataModelFieldBase] = []
        exclude_field_names: set[str] = set()
        seen_parameter_names: set[str] = set()
        reference = self.model_resolver.add(path, name, class_name=True, unique=True)
        for parameter_ in parameters:
            parameter = self.resolve_object(parameter_, ParameterObject)
            parameter_name = parameter.name
            if (
                not parameter_name
                or parameter.in_ not in {ParameterLocation.query, ParameterLocation.path}
                or (parameter.in_ == ParameterLocation.path and not self.include_path_parameters)
            ):
                continue

            if parameter_name in seen_parameter_names:
                msg = f"Parameter name '{parameter_name}' is used more than once."
                raise Exception(msg)  # noqa: TRY002
            seen_parameter_names.add(parameter_name)

            field_name, alias = self.model_resolver.get_valid_field_name_and_alias(
                field_name=parameter_name,
                excludes=exclude_field_names,
                model_type=self.field_name_model_type,
                class_name=name,
            )
            if parameter.schema_:
                fields.append(
                    self.get_object_field(
                        field_name=field_name,
                        field=parameter.schema_,
                        field_type=self.parse_item(field_name, parameter.schema_, [*path, name, parameter_name]),
                        original_field_name=parameter_name,
                        required=parameter.required,
                        alias=alias,
                    )
                )
            else:
                data_types: list[DataType] = []
                object_schema: JsonSchemaObject | None = None
                for (
                    media_type,
                    media_obj,
                ) in parameter.content.items():
                    if not media_obj.schema_:
                        continue
                    object_schema = self.resolve_object(media_obj.schema_, JsonSchemaObject)
                    data_types.append(
                        self.parse_item(
                            field_name,
                            object_schema,
                            [*path, name, parameter_name, media_type],
                        )
                    )

                if not data_types:
                    continue
                if len(data_types) == 1:
                    data_type = data_types[0]
                else:
                    data_type = self.data_type(data_types=data_types)
                    # multiple data_type parse as non-constraints field
                    object_schema = None
                fields.append(
                    self.data_model_field_type(
                        name=field_name,
                        default=object_schema.default if object_schema else None,
                        data_type=data_type,
                        required=parameter.required,
                        alias=alias,
                        constraints=model_dump(object_schema, exclude_none=True)
                        if object_schema and self.is_constraints_field(object_schema)
                        else None,
                        nullable=object_schema.nullable
                        if object_schema and self.strict_nullable and object_schema.nullable is not None
                        else (
                            False
                            if object_schema
                            and self.strict_nullable
                            and (object_schema.has_default or parameter.required)
                            else None
                        ),
                        strip_default_none=self.strip_default_none,
                        extras=self.get_field_extras(object_schema) if object_schema else {},
                        use_annotated=self.use_annotated,
                        use_serialize_as_any=self.use_serialize_as_any,
                        use_field_description=self.use_field_description,
                        use_field_description_example=self.use_field_description_example,
                        use_inline_field_description=self.use_inline_field_description,
                        use_default_kwarg=self.use_default_kwarg,
                        original_name=parameter_name,
                        has_default=object_schema.has_default if object_schema else False,
                        type_has_null=object_schema.type_has_null if object_schema else None,
                    )
                )

        if OpenAPIScope.Parameters in self.open_api_scopes and fields:
            # Using _create_data_model from parent class JsonSchemaParser
            # This method automatically adds frozen=True for DataClass types
            self.results.append(
                self._create_data_model(
                    fields=fields,
                    reference=reference,
                    custom_base_class=self._resolve_base_class(name),
                    custom_template_dir=self.custom_template_dir,
                    extra_template_data=self.extra_template_data,
                    keyword_only=self.keyword_only,
                    treat_dot_as_module=self.treat_dot_as_module,
                    dataclass_arguments=self.dataclass_arguments,
                )
            )
            return self.data_type(reference=reference)

        return None

    def parse_operation(
        self,
        raw_operation: dict[str, Any],
        path: list[str],
    ) -> None:
        """Parse an OpenAPI operation including parameters, request body, and responses."""
        operation = model_validate(Operation, raw_operation)
        path_name, method = path[-2:]
        if self.use_operation_id_as_name:
            if not operation.operationId:
                msg = (
                    f"All operations must have an operationId when --use_operation_id_as_name is set."
                    f"The following path was missing an operationId: {path_name}"
                )
                raise Error(msg)
            path_name = operation.operationId
            method = ""
        self.parse_all_parameters(
            self._get_model_name(
                path_name, method, suffix="Parameters" if self.include_path_parameters else "ParametersQuery"
            ),
            operation.parameters,
            [*path, "parameters"],
        )
        if operation.requestBody:
            if isinstance(operation.requestBody, ReferenceObject):
                ref_model = self.get_ref_model(operation.requestBody.ref)
                request_body = model_validate(RequestBodyObject, ref_model)
            else:
                request_body = operation.requestBody
            self.parse_request_body(
                name=self._get_model_name(path_name, method, suffix="Request"),
                request_body=request_body,
                path=[*path, "requestBody"],
            )
        self.parse_responses(
            name=self._get_model_name(path_name, method, suffix="Response"),
            responses=operation.responses,
            path=[*path, "responses"],
        )
        if OpenAPIScope.Tags in self.open_api_scopes:
            self.parse_tags(
                name=self._get_model_name(path_name, method, suffix="Tags"),
                tags=operation.tags,
                path=[*path, "tags"],
            )

    def parse_raw(self) -> None:  # noqa: PLR0912
        """Parse OpenAPI specification including schemas, paths, and operations."""
        for source, path_parts in self._get_context_source_path_parts():
            if self.validation:
                warn(
                    "Deprecated: `--validation` option is deprecated. the option will be removed in a future "
                    "release. please use another tool to validate OpenAPI.\n",
                    stacklevel=2,
                )

                if source.raw_data is not None:
                    warn(
                        "Warning: Validation was skipped for dict input. "
                        "The --validation option only works with file or text input.\n",
                        stacklevel=2,
                    )
                else:
                    try:
                        from prance import BaseParser  # noqa: PLC0415

                        BaseParser(
                            spec_string=source.text,
                            backend="openapi-spec-validator",
                            encoding=self.encoding,
                        )
                    except ImportError:  # pragma: no cover
                        warn(
                            "Warning: Validation was skipped for OpenAPI. "
                            "`prance` or `openapi-spec-validator` are not installed.\n"
                            "To use --validation option after datamodel-code-generator 0.24.0, "
                            "Please run `$pip install 'datamodel-code-generator[validation]'`.\n",
                            stacklevel=2,
                        )

            specification: dict[str, Any] = (
                dict(source.raw_data) if source.raw_data is not None else load_data(source.text)
            )
            self.raw_obj = specification
            self._collect_discriminator_schemas()
            schemas: dict[str, Any] = specification.get("components", {}).get("schemas", {})
            paths: dict[str, Any] = specification.get("paths", {})
            security: list[dict[str, list[str]]] | None = specification.get("security")
            # Warn if schemas is empty but paths exist and only Schemas scope is used
            if not schemas and self.open_api_scopes == [OpenAPIScope.Schemas] and paths:
                warn(
                    "No schemas found in components/schemas. If your schemas are defined in "
                    "external files referenced from paths, consider using --openapi-scopes paths",
                    stacklevel=2,
                )
            if OpenAPIScope.Schemas in self.open_api_scopes:
                for obj_name, raw_obj in schemas.items():
                    self.parse_raw_obj(
                        obj_name,
                        raw_obj,
                        [*path_parts, "#/components", "schemas", obj_name],
                    )
            if OpenAPIScope.Paths in self.open_api_scopes:
                # Resolve $ref in global parameter list
                global_parameters = [
                    self._get_ref_body(p["$ref"]) if isinstance(p, dict) and "$ref" in p else p
                    for p in paths.get("parameters", [])
                    if isinstance(p, dict)
                ]
                self._process_path_items(paths, path_parts, "paths", global_parameters, security)

            if OpenAPIScope.Webhooks in self.open_api_scopes:
                webhooks: dict[str, dict[str, Any]] = specification.get("webhooks", {})
                self._process_path_items(webhooks, path_parts, "webhooks", [], security, strip_leading_slash=False)

            if OpenAPIScope.RequestBodies in self.open_api_scopes:
                request_bodies: dict[str, Any] = specification.get("components", {}).get("requestBodies", {})
                for body_name, raw_body in request_bodies.items():
                    resolved_body = self.get_ref_model(raw_body["$ref"]) if "$ref" in raw_body else raw_body
                    content = resolved_body.get("content", {})
                    for media_type, media_obj in content.items():
                        schema = media_obj.get("schema")
                        if not schema:
                            continue
                        self.parse_raw_obj(
                            body_name,
                            schema,
                            [
                                *path_parts,
                                "#/components",
                                "requestBodies",
                                body_name,
                                "content",
                                media_type,
                                "schema",
                            ],
                        )

        self._resolve_unparsed_json_pointer()

    def _collect_discriminator_schemas(self) -> None:
        """Collect schemas with discriminators but no oneOf/anyOf, and find their subtypes."""
        schemas: dict[str, Any] = self.raw_obj.get("components", {}).get("schemas", {})
        potential_subtypes: dict[str, list[str]] = {}

        for schema_name, schema in schemas.items():
            discriminator = schema.get("discriminator")
            if discriminator and not schema.get("oneOf") and not schema.get("anyOf"):
                ref = f"#/components/schemas/{schema_name}"
                self._discriminator_schemas[ref] = discriminator

            all_of = schema.get("allOf")
            if all_of:
                refs = [item.get("$ref") for item in all_of if item.get("$ref")]
                if refs:
                    potential_subtypes[schema_name] = refs

        for schema_name, refs in potential_subtypes.items():
            for ref_in_allof in refs:
                if ref_in_allof in self._discriminator_schemas:
                    subtype_ref = f"#/components/schemas/{schema_name}"
                    self._discriminator_subtypes[ref_in_allof].append(subtype_ref)
