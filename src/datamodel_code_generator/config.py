"""Configuration models for datamodel-code-generator."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from datamodel_code_generator.enums import (
    DEFAULT_SHARED_MODULE_NAME,
    AllExportsCollisionStrategy,
    AllExportsScope,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    DataModelType,
    FieldTypeCollisionStrategy,
    GraphQLScope,
    InputFileType,
    ModuleSplitMode,
    NamingStrategy,
    OpenAPIScope,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    TargetPydanticVersion,
)
from datamodel_code_generator.format import (
    DEFAULT_FORMATTERS,
    DateClassType,
    DatetimeClassType,
    Formatter,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.util import ConfigDict, is_pydantic_v2

if TYPE_CHECKING:
    from pathlib import Path
    from urllib.parse import ParseResult

    from datamodel_code_generator.model.pydantic_v2 import UnionMode

    DataModel: TypeAlias = Any
    DataModelFieldBase: TypeAlias = Any
    DataTypeManager: TypeAlias = Any
    StrictTypes: TypeAlias = Any
else:
    if not is_pydantic_v2():
        Path = Any  # type: ignore[assignment]
        ParseResult = Any  # type: ignore[assignment]
        DataModel = Any  # type: ignore[assignment]
        DataModelFieldBase = Any  # type: ignore[assignment]
        DataTypeManager = Any  # type: ignore[assignment]
        StrictTypes = Any  # type: ignore[assignment]
    UnionMode = Any  # type: ignore[assignment]

if TYPE_CHECKING:
    CallableSchema: TypeAlias = Callable[[str], str]
    DumpResolveReferenceAction: TypeAlias = Callable[[Iterable[str]], str]
    DefaultPutDictSchema: TypeAlias = DefaultPutDict[str, str]
elif is_pydantic_v2():
    from typing import Annotated

    from pydantic import WithJsonSchema

    CallableSchema = Annotated[Callable[[str], str], WithJsonSchema({"type": "string"})]
    DumpResolveReferenceAction = Annotated[Callable[[Iterable[str]], str], WithJsonSchema({"type": "string"})]
    DefaultPutDictSchema = Annotated[DefaultPutDict[str, str], WithJsonSchema({"type": "object"})]
else:
    CallableSchema = Callable[[str], str]
    DumpResolveReferenceAction = Callable[[Iterable[str]], str]
    DefaultPutDictSchema = DefaultPutDict[str, str]


class GenerateConfigDict(TypedDict, total=False):
    """TypedDict for GenerateConfig options."""

    input_filename: str | None
    input_file_type: InputFileType
    output: Path | None
    output_model_type: DataModelType
    target_python_version: PythonVersion
    target_pydantic_version: TargetPydanticVersion | None
    base_class: str
    base_class_map: dict[str, str] | None
    additional_imports: list[str] | None
    class_decorators: list[str] | None
    custom_template_dir: Path | None
    extra_template_data: dict[str, dict[str, Any]] | None
    validation: bool
    field_constraints: bool
    snake_case_field: bool
    strip_default_none: bool
    aliases: Mapping[str, str] | None
    disable_timestamp: bool
    enable_version_header: bool
    enable_command_header: bool
    command_line: str | None
    allow_population_by_field_name: bool
    allow_extra_fields: bool
    extra_fields: str | None
    use_generic_base_class: bool
    apply_default_values_for_required_fields: bool
    force_optional_for_required_fields: bool
    class_name: str | None
    use_standard_collections: bool
    use_schema_description: bool
    use_field_description: bool
    use_field_description_example: bool
    use_attribute_docstrings: bool
    use_inline_field_description: bool
    use_default_kwarg: bool
    reuse_model: bool
    reuse_scope: ReuseScope
    shared_module_name: str
    encoding: str
    enum_field_as_literal: LiteralType | None
    enum_field_as_literal_map: dict[str, str] | None
    ignore_enum_constraints: bool
    use_one_literal_as_default: bool
    use_enum_values_in_discriminator: bool
    set_default_enum_member: bool
    use_subclass_enum: bool
    use_specialized_enum: bool
    strict_nullable: bool
    use_generic_container_types: bool
    enable_faux_immutability: bool
    disable_appending_item_suffix: bool
    strict_types: Sequence[StrictTypes] | None
    empty_enum_field_name: str | None
    custom_class_name_generator: Callable[[str], str] | None
    field_extra_keys: set[str] | None
    field_include_all_keys: bool
    field_extra_keys_without_x_prefix: set[str] | None
    model_extra_keys: set[str] | None
    model_extra_keys_without_x_prefix: set[str] | None
    openapi_scopes: list[OpenAPIScope] | None
    include_path_parameters: bool
    graphql_scopes: list[GraphQLScope] | None
    wrap_string_literal: bool | None
    use_title_as_name: bool
    use_operation_id_as_name: bool
    use_unique_items_as_set: bool
    use_tuple_for_fixed_items: bool
    allof_merge_mode: AllOfMergeMode
    http_headers: Sequence[tuple[str, str]] | None
    http_ignore_tls: bool
    http_timeout: float | None
    use_annotated: bool
    use_serialize_as_any: bool
    use_non_positive_negative_number_constrained_types: bool
    use_decimal_for_multiple_of: bool
    original_field_name_delimiter: str | None
    use_double_quotes: bool
    use_union_operator: bool
    collapse_root_models: bool
    collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None
    collapse_reuse_models: bool
    skip_root_model: bool
    use_type_alias: bool
    use_root_model_type_alias: bool
    special_field_name_prefix: str | None
    remove_special_field_name_prefix: bool
    capitalise_enum_members: bool
    keep_model_order: bool
    custom_file_header: str | None
    custom_file_header_path: Path | None
    custom_formatters: list[str] | None
    custom_formatters_kwargs: dict[str, Any] | None
    use_pendulum: bool
    use_standard_primitive_types: bool
    http_query_parameters: Sequence[tuple[str, str]] | None
    treat_dot_as_module: bool | None
    use_exact_imports: bool
    union_mode: UnionMode | None
    output_datetime_class: DatetimeClassType | None
    output_date_class: DateClassType | None
    keyword_only: bool
    frozen_dataclasses: bool
    no_alias: bool
    use_frozen_field: bool
    use_default_factory_for_optional_nested_models: bool
    formatters: list[Formatter]
    settings_path: Path | None
    parent_scoped_naming: bool
    naming_strategy: NamingStrategy | None
    duplicate_name_suffix: dict[str, str] | None
    dataclass_arguments: DataclassArguments | None
    disable_future_imports: bool
    type_mappings: list[str] | None
    type_overrides: dict[str, str] | None
    read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None
    use_status_code_in_response_name: bool
    all_exports_scope: AllExportsScope | None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None
    field_type_collision_strategy: FieldTypeCollisionStrategy | None
    module_split_mode: ModuleSplitMode | None


class ParserConfigDict(TypedDict, total=False):
    """TypedDict for ParserConfig options."""

    data_model_type: type[DataModel]
    data_model_root_type: type[DataModel]
    data_type_manager_type: type[DataTypeManager]
    data_model_field_type: type[DataModelFieldBase]
    base_class: str | None
    base_class_map: dict[str, str] | None
    additional_imports: list[str] | None
    class_decorators: list[str] | None
    custom_template_dir: Path | None
    extra_template_data: dict[str, dict[str, Any]] | None
    target_python_version: PythonVersion
    dump_resolve_reference_action: Callable[[Iterable[str]], str] | None
    validation: bool
    field_constraints: bool
    snake_case_field: bool
    strip_default_none: bool
    aliases: Mapping[str, str] | None
    allow_population_by_field_name: bool
    apply_default_values_for_required_fields: bool
    allow_extra_fields: bool
    extra_fields: str | None
    use_generic_base_class: bool
    force_optional_for_required_fields: bool
    class_name: str | None
    use_standard_collections: bool
    base_path: Path | None
    use_schema_description: bool
    use_field_description: bool
    use_field_description_example: bool
    use_attribute_docstrings: bool
    use_inline_field_description: bool
    use_default_kwarg: bool
    reuse_model: bool
    reuse_scope: ReuseScope | None
    shared_module_name: str
    encoding: str
    enum_field_as_literal: LiteralType | None
    enum_field_as_literal_map: dict[str, str] | None
    ignore_enum_constraints: bool
    set_default_enum_member: bool
    use_subclass_enum: bool
    use_specialized_enum: bool
    strict_nullable: bool
    use_generic_container_types: bool
    enable_faux_immutability: bool
    remote_text_cache: DefaultPutDict[str, str] | None
    disable_appending_item_suffix: bool
    strict_types: Sequence[StrictTypes] | None
    empty_enum_field_name: str | None
    custom_class_name_generator: Callable[[str], str] | None
    field_extra_keys: set[str] | None
    field_include_all_keys: bool
    field_extra_keys_without_x_prefix: set[str] | None
    model_extra_keys: set[str] | None
    model_extra_keys_without_x_prefix: set[str] | None
    wrap_string_literal: bool | None
    use_title_as_name: bool
    use_operation_id_as_name: bool
    use_unique_items_as_set: bool
    use_tuple_for_fixed_items: bool
    allof_merge_mode: AllOfMergeMode
    http_headers: Sequence[tuple[str, str]] | None
    http_ignore_tls: bool
    http_timeout: float | None
    use_annotated: bool
    use_serialize_as_any: bool
    use_non_positive_negative_number_constrained_types: bool
    use_decimal_for_multiple_of: bool
    original_field_name_delimiter: str | None
    use_double_quotes: bool
    use_union_operator: bool
    allow_responses_without_content: bool
    collapse_root_models: bool
    collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None
    collapse_reuse_models: bool
    skip_root_model: bool
    use_type_alias: bool
    special_field_name_prefix: str | None
    remove_special_field_name_prefix: bool
    capitalise_enum_members: bool
    keep_model_order: bool
    use_one_literal_as_default: bool
    use_enum_values_in_discriminator: bool
    known_third_party: list[str] | None
    custom_formatters: list[str] | None
    custom_formatters_kwargs: dict[str, Any] | None
    use_pendulum: bool
    use_standard_primitive_types: bool
    http_query_parameters: Sequence[tuple[str, str]] | None
    treat_dot_as_module: bool | None
    use_exact_imports: bool
    default_field_extras: dict[str, Any] | None
    target_datetime_class: DatetimeClassType | None
    target_date_class: DateClassType | None
    keyword_only: bool
    frozen_dataclasses: bool
    no_alias: bool
    use_frozen_field: bool
    use_default_factory_for_optional_nested_models: bool
    formatters: list[Formatter]
    defer_formatting: bool
    parent_scoped_naming: bool
    naming_strategy: NamingStrategy | None
    duplicate_name_suffix: dict[str, str] | None
    dataclass_arguments: DataclassArguments | None
    type_mappings: list[str] | None
    type_overrides: dict[str, str] | None
    read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None
    field_type_collision_strategy: FieldTypeCollisionStrategy | None
    target_pydantic_version: TargetPydanticVersion | None


class ParseConfigDict(TypedDict, total=False):
    """TypedDict for ParseConfig options."""

    with_import: bool | None
    format_: bool | None
    settings_path: Path | None
    disable_future_imports: bool
    all_exports_scope: AllExportsScope | None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None
    module_split_mode: ModuleSplitMode | None


class GenerateConfig(BaseModel):
    """Configuration model for generate()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:

        class Config:
            """Pydantic v1 configuration."""

            extra = "forbid"
            arbitrary_types_allowed = True

    input_filename: str | None = None
    input_file_type: InputFileType = InputFileType.Auto
    output: Path | None = None
    output_model_type: DataModelType = DataModelType.PydanticBaseModel
    target_python_version: PythonVersion = PythonVersionMin
    target_pydantic_version: TargetPydanticVersion | None = None
    base_class: str = ""
    base_class_map: dict[str, str] | None = None
    additional_imports: list[str] | None = None
    class_decorators: list[str] | None = None
    custom_template_dir: Path | None = None
    extra_template_data: dict[str, dict[str, Any]] | None = None
    validation: bool = False
    field_constraints: bool = False
    snake_case_field: bool = False
    strip_default_none: bool = False
    aliases: Mapping[str, str] | None = None
    disable_timestamp: bool = False
    enable_version_header: bool = False
    enable_command_header: bool = False
    command_line: str | None = None
    allow_population_by_field_name: bool = False
    allow_extra_fields: bool = False
    extra_fields: str | None = None
    use_generic_base_class: bool = False
    apply_default_values_for_required_fields: bool = False
    force_optional_for_required_fields: bool = False
    class_name: str | None = None
    use_standard_collections: bool = True
    use_schema_description: bool = False
    use_field_description: bool = False
    use_field_description_example: bool = False
    use_attribute_docstrings: bool = False
    use_inline_field_description: bool = False
    use_default_kwarg: bool = False
    reuse_model: bool = False
    reuse_scope: ReuseScope = ReuseScope.Module
    shared_module_name: str = DEFAULT_SHARED_MODULE_NAME
    encoding: str = "utf-8"
    enum_field_as_literal: LiteralType | None = None
    enum_field_as_literal_map: dict[str, str] | None = None
    ignore_enum_constraints: bool = False
    use_one_literal_as_default: bool = False
    use_enum_values_in_discriminator: bool = False
    set_default_enum_member: bool = False
    use_subclass_enum: bool = False
    use_specialized_enum: bool = True
    strict_nullable: bool = False
    use_generic_container_types: bool = False
    enable_faux_immutability: bool = False
    disable_appending_item_suffix: bool = False
    strict_types: Sequence[StrictTypes] | None = None
    empty_enum_field_name: str | None = None
    custom_class_name_generator: CallableSchema | None = None
    field_extra_keys: set[str] | None = None
    field_include_all_keys: bool = False
    field_extra_keys_without_x_prefix: set[str] | None = None
    model_extra_keys: set[str] | None = None
    model_extra_keys_without_x_prefix: set[str] | None = None
    openapi_scopes: list[OpenAPIScope] | None = None
    include_path_parameters: bool = False
    graphql_scopes: list[GraphQLScope] | None = None
    wrap_string_literal: bool | None = None
    use_title_as_name: bool = False
    use_operation_id_as_name: bool = False
    use_unique_items_as_set: bool = False
    use_tuple_for_fixed_items: bool = False
    allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints
    http_headers: Sequence[tuple[str, str]] | None = None
    http_ignore_tls: bool = False
    http_timeout: float | None = None
    use_annotated: bool = False
    use_serialize_as_any: bool = False
    use_non_positive_negative_number_constrained_types: bool = False
    use_decimal_for_multiple_of: bool = False
    original_field_name_delimiter: str | None = None
    use_double_quotes: bool = False
    use_union_operator: bool = True
    collapse_root_models: bool = False
    collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None = None
    collapse_reuse_models: bool = False
    skip_root_model: bool = False
    use_type_alias: bool = False
    use_root_model_type_alias: bool = False
    special_field_name_prefix: str | None = None
    remove_special_field_name_prefix: bool = False
    capitalise_enum_members: bool = False
    keep_model_order: bool = False
    custom_file_header: str | None = None
    custom_file_header_path: Path | None = None
    custom_formatters: list[str] | None = None
    custom_formatters_kwargs: dict[str, Any] | None = None
    use_pendulum: bool = False
    use_standard_primitive_types: bool = False
    http_query_parameters: Sequence[tuple[str, str]] | None = None
    treat_dot_as_module: bool | None = None
    use_exact_imports: bool = False
    union_mode: UnionMode | None = None
    output_datetime_class: DatetimeClassType | None = None
    output_date_class: DateClassType | None = None
    keyword_only: bool = False
    frozen_dataclasses: bool = False
    no_alias: bool = False
    use_frozen_field: bool = False
    use_default_factory_for_optional_nested_models: bool = False
    formatters: list[Formatter] = DEFAULT_FORMATTERS
    settings_path: Path | None = None
    parent_scoped_naming: bool = False
    naming_strategy: NamingStrategy | None = None
    duplicate_name_suffix: dict[str, str] | None = None
    dataclass_arguments: DataclassArguments | None = None
    disable_future_imports: bool = False
    type_mappings: list[str] | None = None
    type_overrides: dict[str, str] | None = None
    read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None
    use_status_code_in_response_name: bool = False
    all_exports_scope: AllExportsScope | None = None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None = None
    field_type_collision_strategy: FieldTypeCollisionStrategy | None = None
    module_split_mode: ModuleSplitMode | None = None


class CliConfigSchema(BaseModel):
    """Configuration model for CLI options (schema only)."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:

        class Config:
            """Pydantic v1 configuration."""

            extra = "forbid"
            arbitrary_types_allowed = True

    input: Path | str | None = None
    input_model: str | None = None
    input_file_type: InputFileType = InputFileType.Auto
    output_model_type: DataModelType = DataModelType.PydanticBaseModel
    output: Path | None = None
    check: bool = False
    debug: bool = False
    disable_warnings: bool = False
    target_python_version: PythonVersion = PythonVersionMin
    target_pydantic_version: TargetPydanticVersion | None = None
    base_class: str = ""
    base_class_map: dict[str, str] | None = None
    additional_imports: list[str] | None = None
    class_decorators: list[str] | None = None
    custom_template_dir: Path | None = None
    extra_template_data: dict[str, dict[str, Any]] | None = None
    validation: bool = False
    field_constraints: bool = False
    snake_case_field: bool = False
    strip_default_none: bool = False
    aliases: Mapping[str, str] | None = None
    disable_timestamp: bool = False
    enable_version_header: bool = False
    enable_command_header: bool = False
    allow_population_by_field_name: bool = False
    allow_extra_fields: bool = False
    extra_fields: str | None = None
    use_generic_base_class: bool = False
    use_default: bool = False
    force_optional: bool = False
    class_name: str | None = None
    use_standard_collections: bool = True
    use_schema_description: bool = False
    use_field_description: bool = False
    use_field_description_example: bool = False
    use_attribute_docstrings: bool = False
    use_inline_field_description: bool = False
    use_default_kwarg: bool = False
    reuse_model: bool = False
    reuse_scope: ReuseScope = ReuseScope.Module
    shared_module_name: str = DEFAULT_SHARED_MODULE_NAME
    encoding: str = "utf-8"
    enum_field_as_literal: LiteralType | None = None
    enum_field_as_literal_map: dict[str, str] | None = None
    ignore_enum_constraints: bool = False
    use_one_literal_as_default: bool = False
    use_enum_values_in_discriminator: bool = False
    set_default_enum_member: bool = False
    use_subclass_enum: bool = False
    use_specialized_enum: bool = True
    strict_nullable: bool = False
    use_generic_container_types: bool = False
    use_union_operator: bool = True
    enable_faux_immutability: bool = False
    url: ParseResult | None = None
    disable_appending_item_suffix: bool = False
    strict_types: Sequence[StrictTypes] | None = None
    empty_enum_field_name: str | None = None
    field_extra_keys: set[str] | None = None
    field_include_all_keys: bool = False
    field_extra_keys_without_x_prefix: set[str] | None = None
    model_extra_keys: set[str] | None = None
    model_extra_keys_without_x_prefix: set[str] | None = None
    openapi_scopes: list[OpenAPIScope] | None = Field(default_factory=lambda: [OpenAPIScope.Schemas])
    include_path_parameters: bool = False
    wrap_string_literal: bool | None = None
    use_title_as_name: bool = False
    use_operation_id_as_name: bool = False
    use_unique_items_as_set: bool = False
    use_tuple_for_fixed_items: bool = False
    allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints
    http_headers: Sequence[tuple[str, str]] | None = None
    http_ignore_tls: bool = False
    http_timeout: float | None = None
    use_annotated: bool = False
    use_serialize_as_any: bool = False
    use_non_positive_negative_number_constrained_types: bool = False
    use_decimal_for_multiple_of: bool = False
    original_field_name_delimiter: str | None = None
    use_double_quotes: bool = False
    collapse_root_models: bool = False
    collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None = None
    collapse_reuse_models: bool = False
    skip_root_model: bool = False
    use_type_alias: bool = False
    use_root_model_type_alias: bool = False
    special_field_name_prefix: str | None = None
    remove_special_field_name_prefix: bool = False
    capitalise_enum_members: bool = False
    keep_model_order: bool = False
    custom_file_header: str | None = None
    custom_file_header_path: Path | None = None
    custom_formatters: list[str] | None = None
    custom_formatters_kwargs: dict[str, Any] | None = None
    use_pendulum: bool = False
    use_standard_primitive_types: bool = False
    http_query_parameters: Sequence[tuple[str, str]] | None = None
    treat_dot_as_module: bool | None = None
    use_exact_imports: bool = False
    union_mode: UnionMode | None = None
    output_datetime_class: DatetimeClassType | None = None
    output_date_class: DateClassType | None = None
    keyword_only: bool = False
    frozen_dataclasses: bool = False
    dataclass_arguments: DataclassArguments | None = None
    no_alias: bool = False
    use_frozen_field: bool = False
    use_default_factory_for_optional_nested_models: bool = False
    formatters: list[Formatter] = DEFAULT_FORMATTERS
    parent_scoped_naming: bool = False
    naming_strategy: NamingStrategy | None = None
    duplicate_name_suffix: dict[str, str] | None = None
    disable_future_imports: bool = False
    type_mappings: list[str] | None = None
    type_overrides: dict[str, str] | None = None
    read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None
    use_status_code_in_response_name: bool = False
    all_exports_scope: AllExportsScope | None = None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None = None
    field_type_collision_strategy: FieldTypeCollisionStrategy | None = None
    module_split_mode: ModuleSplitMode | None = None
    watch: bool = False
    watch_delay: float = 0.5


class ParserConfig(BaseModel):
    """Configuration model for Parser.__init__()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:

        class Config:
            """Pydantic v1 configuration."""

            extra = "forbid"
            arbitrary_types_allowed = True

    data_model_type: type[DataModel] = pydantic_model.BaseModel
    data_model_root_type: type[DataModel] = pydantic_model.CustomRootType
    data_type_manager_type: type[DataTypeManager] = pydantic_model.DataTypeManager
    data_model_field_type: type[DataModelFieldBase] = pydantic_model.DataModelField
    base_class: str | None = None
    base_class_map: dict[str, str] | None = None
    additional_imports: list[str] | None = None
    class_decorators: list[str] | None = None
    custom_template_dir: Path | None = None
    extra_template_data: dict[str, dict[str, Any]] | None = None
    target_python_version: PythonVersion = PythonVersionMin
    dump_resolve_reference_action: DumpResolveReferenceAction | None = None
    validation: bool = False
    field_constraints: bool = False
    snake_case_field: bool = False
    strip_default_none: bool = False
    aliases: Mapping[str, str] | None = None
    allow_population_by_field_name: bool = False
    apply_default_values_for_required_fields: bool = False
    allow_extra_fields: bool = False
    extra_fields: str | None = None
    use_generic_base_class: bool = False
    force_optional_for_required_fields: bool = False
    class_name: str | None = None
    use_standard_collections: bool = False
    base_path: Path | None = None
    use_schema_description: bool = False
    use_field_description: bool = False
    use_field_description_example: bool = False
    use_attribute_docstrings: bool = False
    use_inline_field_description: bool = False
    use_default_kwarg: bool = False
    reuse_model: bool = False
    reuse_scope: ReuseScope | None = None
    shared_module_name: str = DEFAULT_SHARED_MODULE_NAME
    encoding: str = "utf-8"
    enum_field_as_literal: LiteralType | None = None
    enum_field_as_literal_map: dict[str, str] | None = None
    ignore_enum_constraints: bool = False
    set_default_enum_member: bool = False
    use_subclass_enum: bool = False
    use_specialized_enum: bool = True
    strict_nullable: bool = False
    use_generic_container_types: bool = False
    enable_faux_immutability: bool = False
    remote_text_cache: DefaultPutDictSchema | None = None
    disable_appending_item_suffix: bool = False
    strict_types: Sequence[StrictTypes] | None = None
    empty_enum_field_name: str | None = None
    custom_class_name_generator: CallableSchema | None = None
    field_extra_keys: set[str] | None = None
    field_include_all_keys: bool = False
    field_extra_keys_without_x_prefix: set[str] | None = None
    model_extra_keys: set[str] | None = None
    model_extra_keys_without_x_prefix: set[str] | None = None
    wrap_string_literal: bool | None = None
    use_title_as_name: bool = False
    use_operation_id_as_name: bool = False
    use_unique_items_as_set: bool = False
    use_tuple_for_fixed_items: bool = False
    allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints
    http_headers: Sequence[tuple[str, str]] | None = None
    http_ignore_tls: bool = False
    http_timeout: float | None = None
    use_annotated: bool = False
    use_serialize_as_any: bool = False
    use_non_positive_negative_number_constrained_types: bool = False
    use_decimal_for_multiple_of: bool = False
    original_field_name_delimiter: str | None = None
    use_double_quotes: bool = False
    use_union_operator: bool = False
    allow_responses_without_content: bool = False
    collapse_root_models: bool = False
    collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None = None
    collapse_reuse_models: bool = False
    skip_root_model: bool = False
    use_type_alias: bool = False
    special_field_name_prefix: str | None = None
    remove_special_field_name_prefix: bool = False
    capitalise_enum_members: bool = False
    keep_model_order: bool = False
    use_one_literal_as_default: bool = False
    use_enum_values_in_discriminator: bool = False
    known_third_party: list[str] | None = None
    custom_formatters: list[str] | None = None
    custom_formatters_kwargs: dict[str, Any] | None = None
    use_pendulum: bool = False
    use_standard_primitive_types: bool = False
    http_query_parameters: Sequence[tuple[str, str]] | None = None
    treat_dot_as_module: bool | None = None
    use_exact_imports: bool = False
    default_field_extras: dict[str, Any] | None = None
    target_datetime_class: DatetimeClassType | None = None
    target_date_class: DateClassType | None = None
    keyword_only: bool = False
    frozen_dataclasses: bool = False
    no_alias: bool = False
    use_frozen_field: bool = False
    use_default_factory_for_optional_nested_models: bool = False
    formatters: list[Formatter] = DEFAULT_FORMATTERS
    defer_formatting: bool = False
    parent_scoped_naming: bool = False
    naming_strategy: NamingStrategy | None = None
    duplicate_name_suffix: dict[str, str] | None = None
    dataclass_arguments: DataclassArguments | None = None
    type_mappings: list[str] | None = None
    type_overrides: dict[str, str] | None = None
    read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None
    field_type_collision_strategy: FieldTypeCollisionStrategy | None = None
    target_pydantic_version: TargetPydanticVersion | None = None


class ParseConfig(BaseModel):
    """Configuration model for Parser.parse()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:

        class Config:
            """Pydantic v1 configuration."""

            extra = "forbid"
            arbitrary_types_allowed = True

    with_import: bool | None = True
    format_: bool | None = True
    settings_path: Path | None = None
    disable_future_imports: bool = False
    all_exports_scope: AllExportsScope | None = None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None = None
    module_split_mode: ModuleSplitMode | None = None


_CONFIG_MODELS_STATE = {"built": False}


def _rebuild_config_models() -> None:
    if _CONFIG_MODELS_STATE["built"]:
        return
    from pathlib import Path  # noqa: PLC0415
    from urllib.parse import ParseResult  # noqa: PLC0415

    model_base = importlib.import_module("datamodel_code_generator.model.base")
    types_module = importlib.import_module("datamodel_code_generator.types")
    data_model_class = model_base.DataModel
    data_model_field_base_class = model_base.DataModelFieldBase
    data_type_manager_class = types_module.DataTypeManager
    strict_types_class = types_module.StrictTypes

    try:
        from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        runtime_union_mode = Any  # pragma: no cover
    else:
        runtime_union_mode = UnionMode

    types_namespace = {
        "Path": Path,
        "ParseResult": ParseResult,
        "DataModel": data_model_class,
        "DataModelFieldBase": data_model_field_base_class,
        "DataTypeManager": data_type_manager_class,
        "StrictTypes": strict_types_class,
        "UnionMode": runtime_union_mode,
    }
    if is_pydantic_v2():
        GenerateConfig.model_rebuild(_types_namespace=types_namespace)
        ParserConfig.model_rebuild(_types_namespace=types_namespace)
        ParseConfig.model_rebuild(_types_namespace=types_namespace)
        CliConfigSchema.model_rebuild(_types_namespace=types_namespace)
    else:
        GenerateConfig.update_forward_refs(**types_namespace)
        ParserConfig.update_forward_refs(**types_namespace)
        ParseConfig.update_forward_refs(**types_namespace)
        CliConfigSchema.update_forward_refs(**types_namespace)
    _CONFIG_MODELS_STATE["built"] = True
