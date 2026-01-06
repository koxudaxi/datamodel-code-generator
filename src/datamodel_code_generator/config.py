"""Configuration models for datamodel-code-generator."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path  # noqa: TC003 - used at runtime by Pydantic
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, Field

from datamodel_code_generator.enums import (
    DEFAULT_SHARED_MODULE_NAME,
    AllExportsCollisionStrategy,
    AllExportsScope,
    AllOfClassHierarchy,
    AllOfMergeMode,
    ClassNameAffixScope,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    DataModelType,
    FieldTypeCollisionStrategy,
    GraphQLScope,
    InputFileType,
    JsonSchemaVersion,
    ModuleSplitMode,
    NamingStrategy,
    OpenAPIScope,
    OpenAPIVersion,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    TargetPydanticVersion,
    VersionMode,
)
from datamodel_code_generator.format import (
    DateClassType,
    DatetimeClassType,
    Formatter,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model.base import (  # noqa: TC001 - used by Pydantic at runtime
    DataModel,
    DataModelFieldBase,
)
from datamodel_code_generator.model.scalar import DataTypeScalar
from datamodel_code_generator.model.union import DataTypeUnion
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.types import DataTypeManager, StrictTypes  # noqa: TC001 - used by Pydantic at runtime
from datamodel_code_generator.util import ConfigDict, is_pydantic_v2
from datamodel_code_generator.validators import ModelValidators  # noqa: TC001 - used by Pydantic at runtime

if TYPE_CHECKING:
    from datamodel_code_generator.model.pydantic_v2 import UnionMode


CallableSchema = Callable[[str], str]
DumpResolveReferenceAction = Callable[[Iterable[str]], str]
DefaultPutDictSchema = DefaultPutDict[str, str]
if TYPE_CHECKING:
    ExtraTemplateDataType = defaultdict[str, dict[str, Any]]
elif is_pydantic_v2():
    ExtraTemplateDataType = defaultdict[str, Annotated[dict[str, Any], Field(default_factory=dict)]]
else:  # pragma: no cover
    ExtraTemplateDataType = defaultdict[str, dict[str, Any]]


class GenerateConfig(BaseModel):
    """Configuration model for generate()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:  # pragma: no cover

        class Config:
            """Pydantic v1 model config."""

            extra = "forbid"
            arbitrary_types_allowed = True

    input_filename: str | None = None
    input_file_type: InputFileType = InputFileType.Auto
    output: Path | None = None
    output_model_type: DataModelType = DataModelType.PydanticBaseModel
    target_python_version: PythonVersion = PythonVersionMin
    target_pydantic_version: TargetPydanticVersion | None = None
    base_class: str = ""
    base_class_map: dict[str, str | list[str]] | None = None
    additional_imports: list[str] | None = None
    class_decorators: list[str] | None = None
    custom_template_dir: Path | None = None
    extra_template_data: ExtraTemplateDataType | None = None
    validators: Mapping[str, ModelValidators] | None = None
    validation: bool = False
    field_constraints: bool = False
    snake_case_field: bool = False
    strip_default_none: bool = False
    aliases: Mapping[str, str | list[str]] | None = None
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
    class_name_prefix: str | None = None
    class_name_suffix: str | None = None
    class_name_affix_scope: ClassNameAffixScope = ClassNameAffixScope.All
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
    openapi_include_paths: list[str] | None = None
    graphql_scopes: list[GraphQLScope] | None = None
    graphql_no_typename: bool = False
    wrap_string_literal: bool | None = None
    use_title_as_name: bool = False
    use_operation_id_as_name: bool = False
    use_unique_items_as_set: bool = False
    use_tuple_for_fixed_items: bool = False
    allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints
    allof_class_hierarchy: AllOfClassHierarchy = AllOfClassHierarchy.IfNoConflict
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
    use_serialization_alias: bool = False
    use_frozen_field: bool = False
    use_default_factory_for_optional_nested_models: bool = False
    formatters: list[Formatter] | None = None
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
    default_value_overrides: Mapping[str, Any] | None = None
    schema_version: str | None = None
    schema_version_mode: VersionMode | None = None


class ParserConfig(BaseModel):
    """Configuration model for Parser.__init__()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:  # pragma: no cover

        class Config:
            """Pydantic v1 model config."""

            extra = "forbid"
            arbitrary_types_allowed = True

    data_model_type: type[DataModel] = pydantic_model.BaseModel
    data_model_root_type: type[DataModel] = pydantic_model.CustomRootType
    data_type_manager_type: type[DataTypeManager] = pydantic_model.DataTypeManager
    data_model_field_type: type[DataModelFieldBase] = pydantic_model.DataModelField
    base_class: str | None = None
    base_class_map: dict[str, str | list[str]] | None = None
    additional_imports: list[str] | None = None
    class_decorators: list[str] | None = None
    custom_template_dir: Path | None = None
    extra_template_data: ExtraTemplateDataType | None = None
    validators: Mapping[str, ModelValidators] | None = None
    target_python_version: PythonVersion = PythonVersionMin
    dump_resolve_reference_action: DumpResolveReferenceAction | None = None
    validation: bool = False
    field_constraints: bool = False
    snake_case_field: bool = False
    strip_default_none: bool = False
    aliases: Mapping[str, str | list[str]] | None = None
    allow_population_by_field_name: bool = False
    apply_default_values_for_required_fields: bool = False
    allow_extra_fields: bool = False
    extra_fields: str | None = None
    use_generic_base_class: bool = False
    force_optional_for_required_fields: bool = False
    class_name: str | None = None
    class_name_prefix: str | None = None
    class_name_suffix: str | None = None
    class_name_affix_scope: ClassNameAffixScope = ClassNameAffixScope.All
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
    allof_class_hierarchy: AllOfClassHierarchy = AllOfClassHierarchy.IfNoConflict
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
    use_serialization_alias: bool = False
    use_frozen_field: bool = False
    use_default_factory_for_optional_nested_models: bool = False
    formatters: list[Formatter] | None = None
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
    default_value_overrides: Mapping[str, Any] | None = None


class GraphQLParserConfig(ParserConfig):
    """Configuration model for GraphQLParser.__init__()."""

    data_model_scalar_type: type[DataModel] = DataTypeScalar
    data_model_union_type: type[DataModel] = DataTypeUnion
    graphql_no_typename: bool = False


class JSONSchemaParserConfig(ParserConfig):
    """Configuration model for JsonSchemaParser.__init__()."""

    jsonschema_version: JsonSchemaVersion | None = None
    schema_version_mode: VersionMode | None = None


class OpenAPIParserConfig(JSONSchemaParserConfig):
    """Configuration model for OpenAPIParser.__init__()."""

    openapi_scopes: list[OpenAPIScope] | None = None
    include_path_parameters: bool = False
    use_status_code_in_response_name: bool = False
    openapi_include_paths: list[str] | None = None
    openapi_version: OpenAPIVersion | None = None


class ParseConfig(BaseModel):
    """Configuration model for Parser.parse()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:  # pragma: no cover

        class Config:
            """Pydantic v1 model config."""

            extra = "forbid"
            arbitrary_types_allowed = True

    with_import: bool | None = True
    format_: bool | None = True
    settings_path: Path | None = None
    disable_future_imports: bool = False
    all_exports_scope: AllExportsScope | None = None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None = None
    module_split_mode: ModuleSplitMode | None = None
