"""Public API signature baselines from origin/main."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from datamodel_code_generator import DEFAULT_FORMATTERS, DEFAULT_SHARED_MODULE_NAME, generate
from datamodel_code_generator.enums import (
    AllExportsCollisionStrategy,
    AllExportsScope,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
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
from datamodel_code_generator.format import PythonVersionMin
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model.pydantic import BaseModel
from datamodel_code_generator.parser.base import Parser, YamlValue, title_to_class_name

if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Callable, Iterable, Mapping, Sequence
    from pathlib import Path
    from urllib.parse import ParseResult

    from datamodel_code_generator.config import GenerateConfig
    from datamodel_code_generator.format import DateClassType, DatetimeClassType, Formatter, PythonVersion
    from datamodel_code_generator.model.dataclass import DataclassArguments
    from datamodel_code_generator.model.pydantic import DataTypeManager
    from datamodel_code_generator.model.pydantic_v2 import UnionMode
    from datamodel_code_generator.parser import DefaultPutDict, LiteralType
    from datamodel_code_generator.types import StrictTypes


def _baseline_generate(
    input_: Path | str | ParseResult | Mapping[str, Any],
    *,
    config: GenerateConfig | None = None,
    input_filename: str | None = None,
    input_file_type: InputFileType = InputFileType.Auto,
    output: Path | None = None,
    output_model_type: DataModelType = DataModelType.PydanticBaseModel,
    target_python_version: PythonVersion = PythonVersionMin,
    target_pydantic_version: TargetPydanticVersion | None = None,
    base_class: str = "",
    base_class_map: dict[str, str] | None = None,
    additional_imports: list[str] | None = None,
    class_decorators: list[str] | None = None,
    custom_template_dir: Path | None = None,
    extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
    validation: bool = False,
    field_constraints: bool = False,
    snake_case_field: bool = False,
    strip_default_none: bool = False,
    aliases: Mapping[str, str] | None = None,
    disable_timestamp: bool = False,
    enable_version_header: bool = False,
    enable_command_header: bool = False,
    command_line: str | None = None,
    allow_population_by_field_name: bool = False,
    allow_extra_fields: bool = False,
    extra_fields: str | None = None,
    use_generic_base_class: bool = False,
    apply_default_values_for_required_fields: bool = False,
    force_optional_for_required_fields: bool = False,
    class_name: str | None = None,
    use_standard_collections: bool = True,
    use_schema_description: bool = False,
    use_field_description: bool = False,
    use_field_description_example: bool = False,
    use_attribute_docstrings: bool = False,
    use_inline_field_description: bool = False,
    use_default_kwarg: bool = False,
    reuse_model: bool = False,
    reuse_scope: ReuseScope = ReuseScope.Module,
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
    graphql_scopes: list[GraphQLScope] | None = None,
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
    use_union_operator: bool = True,
    collapse_root_models: bool = False,
    collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None = None,
    collapse_reuse_models: bool = False,
    skip_root_model: bool = False,
    use_type_alias: bool = False,
    use_root_model_type_alias: bool = False,
    special_field_name_prefix: str | None = None,
    remove_special_field_name_prefix: bool = False,
    capitalise_enum_members: bool = False,
    keep_model_order: bool = False,
    custom_file_header: str | None = None,
    custom_file_header_path: Path | None = None,
    custom_formatters: list[str] | None = None,
    custom_formatters_kwargs: dict[str, Any] | None = None,
    use_pendulum: bool = False,
    use_standard_primitive_types: bool = False,
    http_query_parameters: Sequence[tuple[str, str]] | None = None,
    treat_dot_as_module: bool | None = None,
    use_exact_imports: bool = False,
    union_mode: UnionMode | None = None,
    output_datetime_class: DatetimeClassType | None = None,
    output_date_class: DateClassType | None = None,
    keyword_only: bool = False,
    frozen_dataclasses: bool = False,
    no_alias: bool = False,
    use_frozen_field: bool = False,
    use_default_factory_for_optional_nested_models: bool = False,
    formatters: list[Formatter] = DEFAULT_FORMATTERS,
    settings_path: Path | None = None,
    parent_scoped_naming: bool = False,
    naming_strategy: NamingStrategy | None = None,
    duplicate_name_suffix: dict[str, str] | None = None,
    dataclass_arguments: DataclassArguments | None = None,
    disable_future_imports: bool = False,
    type_mappings: list[str] | None = None,
    type_overrides: dict[str, str] | None = None,
    read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None,
    use_status_code_in_response_name: bool = False,
    all_exports_scope: AllExportsScope | None = None,
    all_exports_collision_strategy: AllExportsCollisionStrategy | None = None,
    field_type_collision_strategy: FieldTypeCollisionStrategy | None = None,
    module_split_mode: ModuleSplitMode | None = None,
) -> str | object | None:
    raise NotImplementedError


class _BaselineParser:
    def __init__(
        self,
        source: str | Path | list[Path] | ParseResult | dict[str, YamlValue],
        *,
        data_model_type: type[DataModel] = BaseModel,
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
        custom_class_name_generator: Callable[[str], str] | None = title_to_class_name,
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
        use_one_literal_as_default: bool = False,
        use_enum_values_in_discriminator: bool = False,
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
        raise NotImplementedError


def _kwonly_params(signature: inspect.Signature) -> list[inspect.Parameter]:
    return [param for param in signature.parameters.values() if param.kind is inspect.Parameter.KEYWORD_ONLY]


def _kwonly_by_name(signature: inspect.Signature) -> dict[str, inspect.Parameter]:
    return {param.name: param for param in _kwonly_params(signature)}


def test_generate_signature_matches_baseline() -> None:
    """Ensure generate keeps the origin/main kw-only args and annotations."""
    expected = inspect.signature(_baseline_generate)
    actual = inspect.signature(generate)
    assert _kwonly_by_name(actual).keys() == _kwonly_by_name(expected).keys()
    for name, param in _kwonly_by_name(expected).items():
        assert _kwonly_by_name(actual)[name].annotation == param.annotation


def test_parser_signature_matches_baseline() -> None:
    """Ensure Parser.__init__ keeps the origin/main kw-only args and annotations."""
    expected = inspect.signature(_BaselineParser.__init__)
    actual = inspect.signature(Parser.__init__)
    assert _kwonly_by_name(actual).keys() == _kwonly_by_name(expected).keys()
    for name, param in _kwonly_by_name(expected).items():
        assert _kwonly_by_name(actual)[name].annotation == param.annotation


def test_generate_config_dict_fields_match_generate_config() -> None:
    """Ensure GenerateConfigDict has same field names as GenerateConfig."""
    from datamodel_code_generator.config import GenerateConfig
    from datamodel_code_generator._types import GenerateConfigDict

    config_fields = set(GenerateConfig.model_fields.keys())
    dict_fields = set(GenerateConfigDict.__annotations__.keys())
    assert config_fields == dict_fields, f"Mismatch: {config_fields ^ dict_fields}"


def _normalize_type_str(type_str: str) -> str:
    """Normalize type string for comparison."""
    import re

    # Remove ForwardRef wrapper and extract inner type
    match = re.match(r"ForwardRef\('(.+?)'", type_str)
    if match:
        type_str = match.group(1)
    # Remove NotRequired wrapper
    type_str = re.sub(r"^NotRequired\[(.+)\]$", r"\1", type_str)
    # Normalize module prefixes
    type_str = type_str.replace("typing.", "")
    type_str = type_str.replace("collections.abc.", "")
    type_str = type_str.replace("pathlib.", "")
    type_str = type_str.replace("datamodel_code_generator.enums.", "")
    type_str = type_str.replace("datamodel_code_generator.format.", "")
    type_str = type_str.replace("datamodel_code_generator.parser.", "")
    type_str = type_str.replace("datamodel_code_generator.types.", "")
    type_str = type_str.replace("datamodel_code_generator.model.base.", "")
    type_str = type_str.replace("datamodel_code_generator.model.pydantic_v2.", "")
    # Normalize enum representation
    type_str = re.sub(r"<enum '(\w+)'>", r"\1", type_str)
    # Normalize class representation
    type_str = re.sub(r"<class '([\w.]+)'>", r"\1", type_str)
    return type_str


def test_generate_config_dict_types_match_generate_config() -> None:
    """Ensure GenerateConfigDict field types match GenerateConfig."""
    from datamodel_code_generator.config import GenerateConfig
    from datamodel_code_generator._types import GenerateConfigDict

    for field_name, field_info in GenerateConfig.model_fields.items():
        config_type = _normalize_type_str(str(field_info.annotation))
        dict_type = _normalize_type_str(str(GenerateConfigDict.__annotations__[field_name]))
        assert config_type == dict_type, (
            f"Type mismatch for {field_name}: Config={config_type}, Dict={dict_type}"
        )


def test_parser_config_dict_fields_match_parser_config() -> None:
    """Ensure ParserConfigDict has same field names as ParserConfig."""
    from datamodel_code_generator.config import ParserConfig
    from datamodel_code_generator._types import ParserConfigDict

    config_fields = set(ParserConfig.model_fields.keys())
    dict_fields = set(ParserConfigDict.__annotations__.keys())
    assert config_fields == dict_fields, f"Mismatch: {config_fields ^ dict_fields}"


def test_parse_config_dict_fields_match_parse_config() -> None:
    """Ensure ParseConfigDict has same field names as ParseConfig."""
    from datamodel_code_generator.config import ParseConfig
    from datamodel_code_generator._types import ParseConfigDict

    config_fields = set(ParseConfig.model_fields.keys())
    dict_fields = set(ParseConfigDict.__annotations__.keys())
    assert config_fields == dict_fields, f"Mismatch: {config_fields ^ dict_fields}"
