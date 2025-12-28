"""Configuration models for datamodel-code-generator."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from datamodel_code_generator._types import GenerateConfigDict, ParseConfigDict, ParserConfigDict

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
from datamodel_code_generator.util import ConfigDict, is_pydantic_v2, model_dump, model_validate

if TYPE_CHECKING:
    from urllib.parse import ParseResult

    from datamodel_code_generator.model import DataModelSet
    from datamodel_code_generator.model.base import DataModel, DataModelFieldBase
    from datamodel_code_generator.model.pydantic_v2 import UnionMode
    from datamodel_code_generator.types import DataTypeManager, StrictTypes


if TYPE_CHECKING:
    CallableSchema = Callable[[str], str]
    DumpResolveReferenceAction = Callable[[Iterable[str]], str]
    DefaultPutDictSchema = DefaultPutDict[str, str]
elif is_pydantic_v2():
    from typing import Annotated

    from pydantic import WithJsonSchema

    CallableSchema = Annotated[
        Callable[[str], str],
        WithJsonSchema({"type": "string", "x-python-type": "Callable[[str], str]"}),
    ]
    DumpResolveReferenceAction = Annotated[
        Callable[[Iterable[str]], str],
        WithJsonSchema({"type": "string", "x-python-type": "Callable[[Iterable[str]], str]"}),
    ]
    DefaultPutDictSchema = Annotated[
        DefaultPutDict[str, str], WithJsonSchema({"type": "object", "x-python-type": "DefaultPutDict[str, str]"})
    ]
else:
    CallableSchema = Callable[[str], str]
    DumpResolveReferenceAction = Callable[[Iterable[str]], str]
    DefaultPutDictSchema = DefaultPutDict[str, str]


class GenerateConfig(BaseModel):
    """Configuration model for generate()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:

        class Config:
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


class ParserConfig(BaseModel):
    """Configuration model for Parser.__init__()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:

        class Config:
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

    @classmethod
    def _from_generate_config(
        cls,
        *,
        generate_config: GenerateConfig,
        data_model_types: DataModelSet,
        input_: Path | str | ParseResult | Mapping[str, Any],
        remote_text_cache: DefaultPutDict[str, str],
        default_field_extras: dict[str, Any] | None,
    ) -> ParserConfig:
        effective_dataclass_arguments = generate_config.dataclass_arguments
        if effective_dataclass_arguments is None:
            effective_dataclass_arguments = {}
            if generate_config.frozen_dataclasses:
                effective_dataclass_arguments["frozen"] = True
            if generate_config.keyword_only:
                effective_dataclass_arguments["kw_only"] = True

        effective_enum_field_as_literal = generate_config.enum_field_as_literal
        if (
            effective_enum_field_as_literal is None
            and generate_config.output_model_type == DataModelType.TypingTypedDict
        ):
            effective_enum_field_as_literal = LiteralType.All

        if generate_config.output_model_type == DataModelType.DataclassesDataclass:
            effective_set_default_enum_member = True
        else:
            effective_set_default_enum_member = generate_config.set_default_enum_member

        parser_fields = cls.model_fields if is_pydantic_v2() else cls.__fields__
        generate_fields = (
            generate_config.__class__.model_fields if is_pydantic_v2() else generate_config.__class__.__fields__
        )
        parser_config_data = model_dump(
            generate_config,
            include=set(parser_fields) & set(generate_fields),
        )
        parser_config_data.update(
            {
                "data_model_type": data_model_types.data_model,
                "data_model_root_type": data_model_types.root_model,
                "data_model_field_type": data_model_types.field_model,
                "data_type_manager_type": data_model_types.data_type_manager,
                "dump_resolve_reference_action": data_model_types.dump_resolve_reference_action,
                "base_path": input_.parent if isinstance(input_, Path) and input_.is_file() else None,
                "remote_text_cache": remote_text_cache,
                "known_third_party": data_model_types.known_third_party,
                "default_field_extras": default_field_extras,
                "target_datetime_class": generate_config.output_datetime_class,
                "target_date_class": generate_config.output_date_class,
                "defer_formatting": generate_config.output is not None and not generate_config.output.suffix,
                "dataclass_arguments": effective_dataclass_arguments,
                "enum_field_as_literal": effective_enum_field_as_literal,
                "set_default_enum_member": effective_set_default_enum_member,
            }
        )
        return model_validate(
            cls,
            {k: v for k, v in parser_config_data.items() if k in parser_fields},
        )


class ParseConfig(BaseModel):
    """Configuration model for Parser.parse()."""

    if is_pydantic_v2():
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:

        class Config:
            extra = "forbid"
            arbitrary_types_allowed = True

    with_import: bool | None = True
    format_: bool | None = True
    settings_path: Path | None = None
    disable_future_imports: bool = False
    all_exports_scope: AllExportsScope | None = None
    all_exports_collision_strategy: AllExportsCollisionStrategy | None = None
    module_split_mode: ModuleSplitMode | None = None

    @classmethod
    def _from_generate_config(cls, *, generate_config: GenerateConfig) -> ParseConfig:
        parse_fields = cls.model_fields if is_pydantic_v2() else cls.__fields__
        generate_fields = (
            generate_config.__class__.model_fields if is_pydantic_v2() else generate_config.__class__.__fields__
        )
        return model_validate(
            cls,
            model_dump(
                generate_config,
                include=set(parse_fields) & set(generate_fields),
            ),
        )


_CONFIG_MODELS_STATE = {"built": False}


def _rebuild_config_models() -> None:
    if _CONFIG_MODELS_STATE["built"]:
        return

    from datamodel_code_generator.model.base import DataModel, DataModelFieldBase  # noqa: PLC0415
    from datamodel_code_generator.types import DataTypeManager, StrictTypes  # noqa: PLC0415

    try:
        from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: PLC0415
    except ImportError:
        runtime_union_mode = Any
    else:
        runtime_union_mode = UnionMode

    types_namespace = {
        "Path": Path,
        "DataModel": DataModel,
        "DataModelFieldBase": DataModelFieldBase,
        "DataTypeManager": DataTypeManager,
        "StrictTypes": StrictTypes,
        "UnionMode": runtime_union_mode,
    }
    if is_pydantic_v2():
        GenerateConfig.model_rebuild(_types_namespace=types_namespace)
        ParserConfig.model_rebuild(_types_namespace=types_namespace)
        ParseConfig.model_rebuild(_types_namespace=types_namespace)
    else:
        GenerateConfig.update_forward_refs(**types_namespace)
        ParserConfig.update_forward_refs(**types_namespace)
        ParseConfig.update_forward_refs(**types_namespace)
    _CONFIG_MODELS_STATE["built"] = True
