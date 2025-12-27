"""Main module for datamodel-code-generator CLI."""

from __future__ import annotations

import sys

# Fast path for --version (avoid importing heavy modules)
if len(sys.argv) == 2 and sys.argv[1] in {"--version", "-V"}:  # pragma: no cover  # noqa: PLR2004
    from importlib.metadata import version

    print(f"datamodel-codegen {version('datamodel-code-generator')}")  # noqa: T201
    sys.exit(0)

# Fast path for --help (avoid importing heavy modules)
if len(sys.argv) == 2 and sys.argv[1] in {"--help", "-h"}:  # pragma: no cover  # noqa: PLR2004
    from datamodel_code_generator.arguments import arg_parser

    arg_parser.print_help()
    sys.exit(0)

# Fast path for --generate-prompt
if any(arg.startswith("--generate-prompt") for arg in sys.argv[1:]):  # pragma: no cover
    from datamodel_code_generator.arguments import arg_parser

    namespace = arg_parser.parse_args()
    if namespace.generate_prompt is not None:
        from datamodel_code_generator.prompt import generate_prompt

        help_text = arg_parser.format_help()
        prompt_output = generate_prompt(namespace, help_text)
        print(prompt_output)  # noqa: T201
        sys.exit(0)

import difflib
import json
import os
import shlex
import signal
import tempfile
import warnings
from collections import defaultdict
from collections.abc import Sequence  # noqa: TC003  # pydantic needs it
from enum import IntEnum
from io import TextIOBase
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional, TypeAlias, Union, cast
from urllib.parse import ParseResult, urlparse

from pydantic import BaseModel

from datamodel_code_generator import (
    DEFAULT_SHARED_MODULE_NAME,
    AllExportsCollisionStrategy,
    AllExportsScope,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    DataModelType,
    Error,
    FieldTypeCollisionStrategy,
    InputFileType,
    InvalidClassNameError,
    ModuleSplitMode,
    NamingStrategy,
    OpenAPIScope,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    TargetPydanticVersion,
    enable_debug_message,
    generate,
)
from datamodel_code_generator.arguments import DEFAULT_ENCODING, arg_parser, namespace
from datamodel_code_generator.format import (
    DEFAULT_FORMATTERS,
    DateClassType,
    DatetimeClassType,
    Formatter,
    PythonVersion,
    PythonVersionMin,
    _get_black,
    is_supported_in_black,
)
from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: TC001 # needed for pydantic
from datamodel_code_generator.parser import LiteralType  # noqa: TC001 # needed for pydantic
from datamodel_code_generator.reference import is_url
from datamodel_code_generator.types import StrictTypes  # noqa: TC001 # needed for pydantic
from datamodel_code_generator.util import (
    ConfigDict,
    field_validator,
    is_pydantic_v2,
    load_toml,
    model_validator,
)

if TYPE_CHECKING:
    from argparse import Namespace

    from typing_extensions import Self

# Options that should be excluded from pyproject.toml config generation
EXCLUDED_CONFIG_OPTIONS: frozenset[str] = frozenset({
    "check",
    "generate_pyproject_config",
    "generate_cli_command",
    "generate_prompt",
    "ignore_pyproject",
    "profile",
    "version",
    "help",
    "debug",
    "no_color",
    "disable_warnings",
    "watch",
    "watch_delay",
})

BOOLEAN_OPTIONAL_OPTIONS: frozenset[str] = frozenset({
    "use_specialized_enum",
    "use_standard_collections",
})


class Exit(IntEnum):
    """Exit reasons."""

    OK = 0
    DIFF = 1
    ERROR = 2
    KeyboardInterrupt = 3


def sig_int_handler(_: int, __: Any) -> None:  # pragma: no cover
    """Handle SIGINT signal gracefully."""
    sys.exit(Exit.OK)


signal.signal(signal.SIGINT, sig_int_handler)


class Config(BaseModel):
    """Configuration model for code generation."""

    if is_pydantic_v2():
        model_config = ConfigDict(arbitrary_types_allowed=True)  # pyright: ignore[reportAssignmentType]

        def get(self, item: str) -> Any:  # pragma: no cover
            """Get attribute value by name."""
            return getattr(self, item)

        def __getitem__(self, item: str) -> Any:  # pragma: no cover
            """Get item by key."""
            return self.get(item)

        @classmethod
        def parse_obj(cls, obj: Any) -> Self:
            """Parse object into Config model."""
            return cls.model_validate(obj)

        @classmethod
        def get_fields(cls) -> dict[str, Any]:
            """Get model fields."""
            return cls.model_fields

    else:

        class Config:
            """Pydantic v1 configuration."""

            # Pydantic 1.5.1 doesn't support validate_assignment correctly
            arbitrary_types_allowed = (TextIOBase,)

        @classmethod
        def get_fields(cls) -> dict[str, Any]:
            """Get model fields."""
            return cls.__fields__

    @field_validator("aliases", "extra_template_data", "custom_formatters_kwargs", mode="before")
    def validate_file(cls, value: Any) -> TextIOBase | None:  # noqa: N805
        """Validate and open file path."""
        if value is None:  # pragma: no cover
            return value

        path = Path(value)
        if path.is_file():
            return cast("TextIOBase", path.expanduser().resolve().open("rt"))

        msg = f"A file was expected but {value} is not a file."  # pragma: no cover
        raise Error(msg)  # pragma: no cover

    @field_validator(
        "input",
        "output",
        "custom_template_dir",
        "custom_file_header_path",
        mode="before",
    )
    def validate_path(cls, value: Any) -> Path | None:  # noqa: N805
        """Validate and resolve path."""
        if value is None or isinstance(value, Path):
            return value  # pragma: no cover
        return Path(value).expanduser().resolve()

    @field_validator("url", mode="before")
    def validate_url(cls, value: Any) -> ParseResult | None:  # noqa: N805
        """Validate and parse URL."""
        if isinstance(value, str) and is_url(value):  # pragma: no cover
            return urlparse(value)
        if value is None:  # pragma: no cover
            return None
        msg = f"Unsupported URL scheme. Supported: http, https, file. --input={value}"  # pragma: no cover
        raise Error(msg)  # pragma: no cover

    # Pydantic 1.5.1 doesn't support each_item=True correctly
    @field_validator("http_headers", mode="before")
    def validate_http_headers(cls, value: Any) -> list[tuple[str, str]] | None:  # noqa: N805
        """Validate HTTP headers."""
        if value is None:  # pragma: no cover
            return None

        def validate_each_item(each_item: str | tuple[str, str]) -> tuple[str, str]:
            if isinstance(each_item, str):  # pragma: no cover
                try:
                    field_name, field_value = each_item.split(":", maxsplit=1)
                    return field_name, field_value.lstrip()
                except ValueError as exc:
                    msg = f"Invalid http header: {each_item!r}"
                    raise Error(msg) from exc
            return each_item  # pragma: no cover

        if isinstance(value, list):
            return [validate_each_item(each_item) for each_item in value]
        msg = f"Invalid http_headers value: {value!r}"  # pragma: no cover
        raise Error(msg)  # pragma: no cover

    @field_validator("http_query_parameters", mode="before")
    def validate_http_query_parameters(cls, value: Any) -> list[tuple[str, str]] | None:  # noqa: N805
        """Validate HTTP query parameters."""
        if value is None:  # pragma: no cover
            return None

        def validate_each_item(each_item: str | tuple[str, str]) -> tuple[str, str]:
            if isinstance(each_item, str):  # pragma: no cover
                try:
                    field_name, field_value = each_item.split("=", maxsplit=1)
                    return field_name, field_value.lstrip()
                except ValueError as exc:
                    msg = f"Invalid http query parameter: {each_item!r}"
                    raise Error(msg) from exc
            return each_item  # pragma: no cover

        if isinstance(value, list):
            return [validate_each_item(each_item) for each_item in value]
        msg = f"Invalid http_query_parameters value: {value!r}"  # pragma: no cover
        raise Error(msg)  # pragma: no cover

    @model_validator(mode="before")
    def validate_additional_imports(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
        """Validate and split additional imports."""
        additional_imports = values.get("additional_imports")
        if additional_imports is not None:
            values["additional_imports"] = additional_imports.split(",")
        return values

    @model_validator(mode="before")
    def validate_custom_formatters(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
        """Validate and split custom formatters."""
        custom_formatters = values.get("custom_formatters")
        if custom_formatters is not None:
            values["custom_formatters"] = custom_formatters.split(",")
        return values

    @model_validator(mode="before")
    def validate_duplicate_name_suffix(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
        """Validate and parse duplicate_name_suffix JSON string."""
        duplicate_name_suffix = values.get("duplicate_name_suffix")
        if duplicate_name_suffix is not None and isinstance(duplicate_name_suffix, str):
            try:
                values["duplicate_name_suffix"] = json.loads(duplicate_name_suffix)
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON for --duplicate-name-suffix: {e}"
                raise Error(msg) from e
        return values

    @model_validator(mode="before")
    def validate_naming_strategy_migration(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
        """Migrate deprecated --parent-scoped-naming to --naming-strategy."""
        if values.get("parent_scoped_naming") and not values.get("naming_strategy"):
            values["naming_strategy"] = NamingStrategy.ParentPrefixed
            warnings.warn(
                "--parent-scoped-naming is deprecated. Use --naming-strategy parent-prefixed instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return values

    @model_validator(mode="before")
    def validate_class_decorators(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
        """Validate and split class decorators, adding @ prefix if missing."""
        class_decorators = values.get("class_decorators")
        if class_decorators is not None:
            decorators = []
            for raw_decorator in class_decorators.split(","):
                stripped = raw_decorator.strip()
                if stripped:
                    if not stripped.startswith("@"):
                        stripped = f"@{stripped}"
                    decorators.append(stripped)
            values["class_decorators"] = decorators
        return values

    __validate_output_datetime_class_err: ClassVar[str] = (
        '`--output-datetime-class` only allows "datetime" for '
        f"`--output-model-type` {DataModelType.DataclassesDataclass.value}"
    )

    __validate_original_field_name_delimiter_err: ClassVar[str] = (
        "`--original-field-name-delimiter` can not be used without `--snake-case-field`."
    )

    __validate_custom_file_header_err: ClassVar[str] = (
        "`--custom_file_header_path` can not be used with `--custom_file_header`."
    )
    __validate_keyword_only_err: ClassVar[str] = (
        f"`--keyword-only` requires `--target-python-version` {PythonVersion.PY_310.value} or higher."
    )

    __validate_all_exports_collision_strategy_err: ClassVar[str] = (
        "`--all-exports-collision-strategy` can only be used with `--all-exports-scope=recursive`."
    )

    if is_pydantic_v2():

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_output_datetime_class(self: Self) -> Self:  # pyright: ignore[reportRedeclaration]
            """Validate output datetime class compatibility."""
            datetime_class_type: DatetimeClassType | None = self.output_datetime_class
            if (
                datetime_class_type
                and datetime_class_type is not DatetimeClassType.Datetime
                and self.output_model_type == DataModelType.DataclassesDataclass
            ):
                raise Error(self.__validate_output_datetime_class_err)
            return self

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_original_field_name_delimiter(self: Self) -> Self:  # pyright: ignore[reportRedeclaration]
            """Validate original field name delimiter requires snake case."""
            if self.original_field_name_delimiter is not None and not self.snake_case_field:
                raise Error(self.__validate_original_field_name_delimiter_err)
            return self

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_custom_file_header(self: Self) -> Self:  # pyright: ignore[reportRedeclaration]
            """Validate custom file header options are mutually exclusive."""
            if self.custom_file_header and self.custom_file_header_path:
                raise Error(self.__validate_custom_file_header_err)
            return self

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_keyword_only(self: Self) -> Self:  # pyright: ignore[reportRedeclaration]
            """Validate keyword-only compatibility with target Python version."""
            output_model_type: DataModelType = self.output_model_type
            python_target: PythonVersion = self.target_python_version
            if (
                self.keyword_only
                and output_model_type == DataModelType.DataclassesDataclass
                and not python_target.has_kw_only_dataclass
            ):
                raise Error(self.__validate_keyword_only_err)
            return self

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_root(self: Self) -> Self:  # pyright: ignore[reportRedeclaration]
            """Validate root model configuration."""
            if self.use_annotated:
                self.field_constraints = True
            return self

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_all_exports_collision_strategy(self: Self) -> Self:  # pyright: ignore[reportRedeclaration]
            """Validate all_exports_collision_strategy requires recursive scope."""
            if self.all_exports_collision_strategy is not None and self.all_exports_scope != AllExportsScope.Recursive:
                raise Error(self.__validate_all_exports_collision_strategy_err)
            return self

    else:

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_output_datetime_class(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
            """Validate output datetime class compatibility."""
            datetime_class_type: DatetimeClassType | None = values.get("output_datetime_class")
            if (
                datetime_class_type
                and datetime_class_type is not DatetimeClassType.Datetime
                and values.get("output_model_type") == DataModelType.DataclassesDataclass
            ):
                raise Error(cls.__validate_output_datetime_class_err)
            return values

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_original_field_name_delimiter(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
            """Validate original field name delimiter requires snake case."""
            if values.get("original_field_name_delimiter") is not None and not values.get("snake_case_field"):
                raise Error(cls.__validate_original_field_name_delimiter_err)
            return values

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_custom_file_header(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
            """Validate custom file header options are mutually exclusive."""
            if values.get("custom_file_header") and values.get("custom_file_header_path"):
                raise Error(cls.__validate_custom_file_header_err)
            return values

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_keyword_only(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
            """Validate keyword-only compatibility with target Python version."""
            output_model_type: DataModelType = cast("DataModelType", values.get("output_model_type"))
            python_target: PythonVersion = cast("PythonVersion", values.get("target_python_version"))
            if (
                values.get("keyword_only")
                and output_model_type == DataModelType.DataclassesDataclass
                and not python_target.has_kw_only_dataclass
            ):
                raise Error(cls.__validate_keyword_only_err)
            return values

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_root(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
            """Validate root model configuration."""
            if values.get("use_annotated"):
                values["field_constraints"] = True
            return values

        @model_validator()  # pyright: ignore[reportArgumentType]
        def validate_all_exports_collision_strategy(cls, values: dict[str, Any]) -> dict[str, Any]:  # noqa: N805
            """Validate all_exports_collision_strategy requires recursive scope."""
            if (
                values.get("all_exports_collision_strategy") is not None
                and values.get("all_exports_scope") != AllExportsScope.Recursive
            ):
                raise Error(cls.__validate_all_exports_collision_strategy_err)
            return values

    input: Optional[Union[Path, str]] = None  # noqa: UP007, UP045
    input_model: Optional[str] = None  # noqa: UP045
    input_file_type: InputFileType = InputFileType.Auto
    output_model_type: DataModelType = DataModelType.PydanticBaseModel
    output: Optional[Path] = None  # noqa: UP045
    check: bool = False
    debug: bool = False
    disable_warnings: bool = False
    target_python_version: PythonVersion = PythonVersionMin
    target_pydantic_version: Optional[TargetPydanticVersion] = None  # noqa: UP045
    base_class: str = ""
    base_class_map: Optional[dict[str, str]] = None  # noqa: UP045
    additional_imports: Optional[list[str]] = None  # noqa: UP045
    class_decorators: Optional[list[str]] = None  # noqa: UP045
    custom_template_dir: Optional[Path] = None  # noqa: UP045
    extra_template_data: Optional[TextIOBase] = None  # noqa: UP045
    validation: bool = False
    field_constraints: bool = False
    snake_case_field: bool = False
    strip_default_none: bool = False
    aliases: Optional[TextIOBase] = None  # noqa: UP045
    disable_timestamp: bool = False
    enable_version_header: bool = False
    enable_command_header: bool = False
    allow_population_by_field_name: bool = False
    allow_extra_fields: bool = False
    extra_fields: Optional[str] = None  # noqa: UP045
    use_generic_base_class: bool = False
    use_default: bool = False
    force_optional: bool = False
    class_name: Optional[str] = None  # noqa: UP045
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
    encoding: str = DEFAULT_ENCODING
    enum_field_as_literal: Optional[LiteralType] = None  # noqa: UP045
    enum_field_as_literal_map: Optional[dict[str, str]] = None  # noqa: UP045
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
    url: Optional[ParseResult] = None  # noqa: UP045
    disable_appending_item_suffix: bool = False
    strict_types: list[StrictTypes] = []
    empty_enum_field_name: Optional[str] = None  # noqa: UP045
    field_extra_keys: Optional[set[str]] = None  # noqa: UP045
    field_include_all_keys: bool = False
    field_extra_keys_without_x_prefix: Optional[set[str]] = None  # noqa: UP045
    model_extra_keys: Optional[set[str]] = None  # noqa: UP045
    model_extra_keys_without_x_prefix: Optional[set[str]] = None  # noqa: UP045
    openapi_scopes: Optional[list[OpenAPIScope]] = [OpenAPIScope.Schemas]  # noqa: UP045
    include_path_parameters: bool = False
    wrap_string_literal: Optional[bool] = None  # noqa: UP045
    use_title_as_name: bool = False
    use_operation_id_as_name: bool = False
    use_unique_items_as_set: bool = False
    use_tuple_for_fixed_items: bool = False
    allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints
    http_headers: Optional[Sequence[tuple[str, str]]] = None  # noqa: UP045
    http_ignore_tls: bool = False
    http_timeout: Optional[float] = None  # noqa: UP045
    use_annotated: bool = False
    use_serialize_as_any: bool = False
    use_non_positive_negative_number_constrained_types: bool = False
    use_decimal_for_multiple_of: bool = False
    original_field_name_delimiter: Optional[str] = None  # noqa: UP045
    use_double_quotes: bool = False
    collapse_root_models: bool = False
    collapse_root_models_name_strategy: Optional[CollapseRootModelsNameStrategy] = None  # noqa: UP045
    collapse_reuse_models: bool = False
    skip_root_model: bool = False
    use_type_alias: bool = False
    use_root_model_type_alias: bool = False
    special_field_name_prefix: Optional[str] = None  # noqa: UP045
    remove_special_field_name_prefix: bool = False
    capitalise_enum_members: bool = False
    keep_model_order: bool = False
    custom_file_header: Optional[str] = None  # noqa: UP045
    custom_file_header_path: Optional[Path] = None  # noqa: UP045
    custom_formatters: Optional[list[str]] = None  # noqa: UP045
    custom_formatters_kwargs: Optional[TextIOBase] = None  # noqa: UP045
    use_pendulum: bool = False
    use_standard_primitive_types: bool = False
    http_query_parameters: Optional[Sequence[tuple[str, str]]] = None  # noqa: UP045
    treat_dot_as_module: Optional[bool] = None  # noqa: UP045
    use_exact_imports: bool = False
    union_mode: Optional[UnionMode] = None  # noqa: UP045
    output_datetime_class: Optional[DatetimeClassType] = None  # noqa: UP045
    output_date_class: Optional[DateClassType] = None  # noqa: UP045
    keyword_only: bool = False
    frozen_dataclasses: bool = False
    dataclass_arguments: Optional[DataclassArguments] = None  # noqa: UP045
    no_alias: bool = False
    use_frozen_field: bool = False
    use_default_factory_for_optional_nested_models: bool = False
    formatters: list[Formatter] = DEFAULT_FORMATTERS
    parent_scoped_naming: bool = False
    naming_strategy: Optional[NamingStrategy] = None  # noqa: UP045
    duplicate_name_suffix: Optional[dict[str, str]] = None  # noqa: UP045
    disable_future_imports: bool = False
    type_mappings: Optional[list[str]] = None  # noqa: UP045
    type_overrides: Optional[dict[str, str]] = None  # noqa: UP045
    read_only_write_only_model_type: Optional[ReadOnlyWriteOnlyModelType] = None  # noqa: UP045
    use_status_code_in_response_name: bool = False
    all_exports_scope: Optional[AllExportsScope] = None  # noqa: UP045
    all_exports_collision_strategy: Optional[AllExportsCollisionStrategy] = None  # noqa: UP045
    field_type_collision_strategy: Optional[FieldTypeCollisionStrategy] = None  # noqa: UP045
    module_split_mode: Optional[ModuleSplitMode] = None  # noqa: UP045
    watch: bool = False
    watch_delay: float = 0.5

    def merge_args(self, args: Namespace) -> None:
        """Merge command-line arguments into config."""
        set_args = {f: getattr(args, f) for f in self.get_fields() if getattr(args, f) is not None}

        if set_args.get("output_model_type") == DataModelType.MsgspecStruct.value:
            set_args["use_annotated"] = True

        if set_args.get("use_annotated"):
            set_args["field_constraints"] = True

        parsed_args = Config.parse_obj(set_args)
        for field_name in set_args:
            setattr(self, field_name, getattr(parsed_args, field_name))


def _extract_additional_imports(extra_template_data: defaultdict[str, dict[str, Any]]) -> list[str]:
    """Extract additional_imports from extra_template_data entries."""
    additional_imports: list[str] = []
    for type_data in extra_template_data.values():
        if "additional_imports" in type_data:
            imports = type_data.pop("additional_imports")
            if isinstance(imports, str):
                if imports.strip():
                    additional_imports.append(imports.strip())
            elif isinstance(imports, list):
                additional_imports.extend(item.strip() for item in imports if isinstance(item, str) and item.strip())
    return additional_imports


def _load_model_schema(  # noqa: PLR0912, PLR0915
    input_model: str,
    input_file_type: InputFileType,
) -> dict[str, object]:
    """Load schema from a Python import path.

    Args:
        input_model: Import path in 'module.path:ObjectName' format
        input_file_type: Current input file type setting for validation

    Returns:
        Schema dict

    Raises:
        Error: If format invalid, object cannot be loaded, or input_file_type invalid
    """
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415

    modname, sep, qualname = input_model.rpartition(":")
    if not sep or not modname:
        msg = f"Invalid --input-model format: {input_model!r}. Expected 'module:Object' or 'path/to/file.py:Object'."
        raise Error(msg)

    is_path = "/" in modname or "\\" in modname
    if not is_path and modname.endswith(".py"):
        is_path = Path(modname).exists()

    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    if is_path:
        file_path = Path(modname).resolve()
        if not file_path.exists():
            msg = f"File not found: {modname!r}"
            raise Error(msg)
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            msg = f"Cannot load module from {modname!r}"
            raise Error(msg)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    else:
        try:
            module = importlib.util.find_spec(modname)
            if module is None:
                msg = f"Cannot find module {modname!r}"
                raise Error(msg)
            module = importlib.import_module(modname)
        except ImportError as e:
            msg = f"Cannot import module {modname!r}: {e}"
            raise Error(msg) from e

    try:
        obj = getattr(module, qualname)
    except AttributeError as e:
        msg = f"Module {modname!r} has no attribute {qualname!r}"
        raise Error(msg) from e

    if isinstance(obj, dict):
        if input_file_type == InputFileType.Auto:
            msg = "--input-file-type is required when --input-model points to a dict"
            raise Error(msg)
        return obj

    if isinstance(obj, type) and issubclass(obj, BaseModel):
        if input_file_type not in {InputFileType.Auto, InputFileType.JsonSchema}:
            msg = (
                f"--input-file-type must be 'jsonschema' (or omitted) "
                f"when --input-model points to a Pydantic model, "
                f"got '{input_file_type.value}'"
            )
            raise Error(msg)
        if not hasattr(obj, "model_json_schema"):
            msg = "--input-model with Pydantic model requires Pydantic v2 runtime. Please upgrade Pydantic to v2."
            raise Error(msg)
        return obj.model_json_schema()

    # Check for dataclass or TypedDict - use TypeAdapter
    from dataclasses import is_dataclass  # noqa: PLC0415

    is_typed_dict = isinstance(obj, type) and hasattr(obj, "__required_keys__")
    if is_dataclass(obj) or is_typed_dict:
        if input_file_type not in {InputFileType.Auto, InputFileType.JsonSchema}:
            msg = (
                f"--input-file-type must be 'jsonschema' (or omitted) "
                f"when --input-model points to a dataclass or TypedDict, "
                f"got '{input_file_type.value}'"
            )
            raise Error(msg)
        try:
            from pydantic import TypeAdapter  # noqa: PLC0415

            return TypeAdapter(obj).json_schema()
        except ImportError as e:
            msg = "--input-model with dataclass/TypedDict requires Pydantic v2 runtime."
            raise Error(msg) from e

    msg = f"{qualname!r} is not a supported type. Supported: dict, Pydantic v2 BaseModel, dataclass, TypedDict"
    raise Error(msg)


def _get_pyproject_toml_config(source: Path, profile: str | None = None) -> dict[str, Any]:
    """Find and return the [tool.datamodel-codegen] section of the closest pyproject.toml if it exists."""
    current_path = source
    while current_path != current_path.parent:
        if (current_path / "pyproject.toml").is_file():
            pyproject_toml = load_toml(current_path / "pyproject.toml")
            if "datamodel-codegen" in pyproject_toml.get("tool", {}):
                tool_config = pyproject_toml["tool"]["datamodel-codegen"]

                base_config: dict[str, Any] = {k: v for k, v in tool_config.items() if k != "profiles"}

                if profile:
                    profiles = tool_config.get("profiles", {})
                    if profile not in profiles:
                        available = list(profiles.keys()) if profiles else "none"
                        msg = f"Profile '{profile}' not found in pyproject.toml. Available profiles: {available}"
                        raise Error(msg)
                    profile_config = profiles[profile]
                    base_config.update(profile_config)

                pyproject_config = {k.replace("-", "_"): v for k, v in base_config.items()}
                # Replace US-american spelling if present (ignore if british spelling is present)
                if (
                    "capitalize_enum_members" in pyproject_config and "capitalise_enum_members" not in pyproject_config
                ):  # pragma: no cover
                    pyproject_config["capitalise_enum_members"] = pyproject_config.pop("capitalize_enum_members")
                return pyproject_config

        if (current_path / ".git").exists():
            # Stop early if we see a git repository root.
            break

        current_path = current_path.parent

    # If profile was requested but no pyproject.toml config was found, raise an error
    if profile:
        msg = f"Profile '{profile}' requested but no [tool.datamodel-codegen] section found in pyproject.toml"
        raise Error(msg)

    return {}


TomlValue: TypeAlias = str | bool | list["TomlValue"] | tuple["TomlValue", ...]


def _format_toml_value(value: TomlValue) -> str:
    """Format a Python value as a TOML value string."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    formatted_items = [_format_toml_value(item) for item in value]
    return f"[{', '.join(formatted_items)}]"


def generate_pyproject_config(args: Namespace) -> str:
    """Generate pyproject.toml [tool.datamodel-codegen] section from CLI arguments."""
    lines: list[str] = ["[tool.datamodel-codegen]"]

    args_dict: dict[str, object] = vars(args)
    for key, value in sorted(args_dict.items()):
        if value is None:
            continue
        if key in EXCLUDED_CONFIG_OPTIONS:
            continue

        toml_key = key.replace("_", "-")
        toml_value = _format_toml_value(cast("TomlValue", value))
        lines.append(f"{toml_key} = {toml_value}")

    return "\n".join(lines) + "\n"


def _normalize_line_endings(text: str) -> str:
    """Normalize line endings to LF for cross-platform comparison."""
    return text.replace("\r\n", "\n")


def _compare_single_file(
    generated_path: Path,
    actual_path: Path,
    encoding: str,
) -> tuple[bool, list[str]]:
    """Compare generated file content with existing file.

    Returns:
        Tuple of (has_differences, diff_lines)
        - has_differences: True if files differ or actual file doesn't exist
        - diff_lines: List of diff lines for output
    """
    generated_content = _normalize_line_endings(generated_path.read_text(encoding=encoding))

    if not actual_path.exists():
        return True, [f"MISSING: {actual_path} (file does not exist but should be generated)"]

    actual_content = _normalize_line_endings(actual_path.read_text(encoding=encoding))

    if generated_content == actual_content:
        return False, []

    diff_lines = list(
        difflib.unified_diff(
            actual_content.splitlines(keepends=True),
            generated_content.splitlines(keepends=True),
            fromfile=str(actual_path),
            tofile=f"{actual_path} (expected)",
        )
    )
    return True, diff_lines


def _compare_directories(
    generated_dir: Path,
    actual_dir: Path,
    encoding: str,
) -> tuple[list[str], list[str], list[str]]:
    """Compare generated directory with existing directory."""
    diffs: list[str] = []

    generated_files = {path.relative_to(generated_dir) for path in generated_dir.rglob("*.py")}

    actual_files: set[Path] = set()
    if actual_dir.exists():
        for path in actual_dir.rglob("*.py"):
            if "__pycache__" not in path.parts:
                actual_files.add(path.relative_to(actual_dir))

    missing_files = [str(rel_path) for rel_path in sorted(generated_files - actual_files)]
    extra_files = [str(rel_path) for rel_path in sorted(actual_files - generated_files)]

    for rel_path in sorted(generated_files & actual_files):
        generated_content = _normalize_line_endings((generated_dir / rel_path).read_text(encoding=encoding))
        actual_content = _normalize_line_endings((actual_dir / rel_path).read_text(encoding=encoding))
        if generated_content != actual_content:
            diffs.extend(
                difflib.unified_diff(
                    actual_content.splitlines(keepends=True),
                    generated_content.splitlines(keepends=True),
                    fromfile=str(rel_path),
                    tofile=f"{rel_path} (expected)",
                )
            )

    return diffs, missing_files, extra_files


def _format_cli_value(value: str | list[str]) -> str:
    """Format a value for CLI argument."""
    if isinstance(value, list):
        return " ".join(f'"{v}"' if " " in v else v for v in value)
    return f'"{value}"' if " " in value else value


def generate_cli_command(config: dict[str, TomlValue]) -> str:
    """Generate CLI command from pyproject.toml configuration."""
    parts: list[str] = ["datamodel-codegen"]

    for key, value in sorted(config.items()):
        if key in EXCLUDED_CONFIG_OPTIONS:
            continue

        cli_key = key.replace("_", "-")

        if isinstance(value, bool):
            if value:
                parts.append(f"--{cli_key}")
            elif key in BOOLEAN_OPTIONAL_OPTIONS:
                parts.append(f"--no-{cli_key}")
        elif isinstance(value, list):
            parts.extend((f"--{cli_key}", _format_cli_value(cast("list[str]", value))))
        else:
            parts.extend((f"--{cli_key}", _format_cli_value(str(value))))

    return " ".join(parts) + "\n"


def run_generate_from_config(  # noqa: PLR0913, PLR0917
    config: Config,
    input_: Path | str | ParseResult,
    output: Path | None,
    extra_template_data: dict[str, Any] | None,
    aliases: dict[str, str] | None,
    command_line: str | None,
    custom_formatters_kwargs: dict[str, str] | None,
    settings_path: Path | None = None,
) -> None:
    """Run code generation with the given config and parameters."""
    result = generate(
        input_=input_,
        input_file_type=config.input_file_type,
        output=output,
        output_model_type=config.output_model_type,
        target_python_version=config.target_python_version,
        target_pydantic_version=config.target_pydantic_version,
        base_class=config.base_class,
        base_class_map=config.base_class_map,
        additional_imports=config.additional_imports,
        class_decorators=config.class_decorators,
        custom_template_dir=config.custom_template_dir,
        validation=config.validation,
        field_constraints=config.field_constraints,
        snake_case_field=config.snake_case_field,
        strip_default_none=config.strip_default_none,
        extra_template_data=extra_template_data,  # pyright: ignore[reportArgumentType]
        aliases=aliases,
        disable_timestamp=config.disable_timestamp,
        enable_version_header=config.enable_version_header,
        enable_command_header=config.enable_command_header,
        command_line=command_line,
        allow_population_by_field_name=config.allow_population_by_field_name,
        allow_extra_fields=config.allow_extra_fields,
        extra_fields=config.extra_fields,
        use_generic_base_class=config.use_generic_base_class,
        apply_default_values_for_required_fields=config.use_default,
        force_optional_for_required_fields=config.force_optional,
        class_name=config.class_name,
        use_standard_collections=config.use_standard_collections,
        use_schema_description=config.use_schema_description,
        use_field_description=config.use_field_description,
        use_field_description_example=config.use_field_description_example,
        use_attribute_docstrings=config.use_attribute_docstrings,
        use_inline_field_description=config.use_inline_field_description,
        use_default_kwarg=config.use_default_kwarg,
        reuse_model=config.reuse_model,
        reuse_scope=config.reuse_scope,
        shared_module_name=config.shared_module_name,
        encoding=config.encoding,
        enum_field_as_literal=config.enum_field_as_literal,
        enum_field_as_literal_map=config.enum_field_as_literal_map,
        ignore_enum_constraints=config.ignore_enum_constraints,
        use_one_literal_as_default=config.use_one_literal_as_default,
        use_enum_values_in_discriminator=config.use_enum_values_in_discriminator,
        set_default_enum_member=config.set_default_enum_member,
        use_subclass_enum=config.use_subclass_enum,
        use_specialized_enum=config.use_specialized_enum,
        strict_nullable=config.strict_nullable,
        use_generic_container_types=config.use_generic_container_types,
        enable_faux_immutability=config.enable_faux_immutability,
        disable_appending_item_suffix=config.disable_appending_item_suffix,
        strict_types=config.strict_types,
        empty_enum_field_name=config.empty_enum_field_name,
        field_extra_keys=config.field_extra_keys,
        field_include_all_keys=config.field_include_all_keys,
        field_extra_keys_without_x_prefix=config.field_extra_keys_without_x_prefix,
        model_extra_keys=config.model_extra_keys,
        model_extra_keys_without_x_prefix=config.model_extra_keys_without_x_prefix,
        openapi_scopes=config.openapi_scopes,
        include_path_parameters=config.include_path_parameters,
        wrap_string_literal=config.wrap_string_literal,
        use_title_as_name=config.use_title_as_name,
        use_operation_id_as_name=config.use_operation_id_as_name,
        use_unique_items_as_set=config.use_unique_items_as_set,
        use_tuple_for_fixed_items=config.use_tuple_for_fixed_items,
        allof_merge_mode=config.allof_merge_mode,
        http_headers=config.http_headers,
        http_ignore_tls=config.http_ignore_tls,
        http_timeout=config.http_timeout,
        use_annotated=config.use_annotated,
        use_serialize_as_any=config.use_serialize_as_any,
        use_non_positive_negative_number_constrained_types=config.use_non_positive_negative_number_constrained_types,
        use_decimal_for_multiple_of=config.use_decimal_for_multiple_of,
        original_field_name_delimiter=config.original_field_name_delimiter,
        use_double_quotes=config.use_double_quotes,
        collapse_root_models=config.collapse_root_models,
        collapse_root_models_name_strategy=config.collapse_root_models_name_strategy,
        collapse_reuse_models=config.collapse_reuse_models,
        skip_root_model=config.skip_root_model,
        use_type_alias=config.use_type_alias,
        use_root_model_type_alias=config.use_root_model_type_alias,
        use_union_operator=config.use_union_operator,
        special_field_name_prefix=config.special_field_name_prefix,
        remove_special_field_name_prefix=config.remove_special_field_name_prefix,
        capitalise_enum_members=config.capitalise_enum_members,
        keep_model_order=config.keep_model_order,
        custom_file_header=config.custom_file_header,
        custom_file_header_path=config.custom_file_header_path,
        custom_formatters=config.custom_formatters,
        custom_formatters_kwargs=custom_formatters_kwargs,
        use_pendulum=config.use_pendulum,
        use_standard_primitive_types=config.use_standard_primitive_types,
        http_query_parameters=config.http_query_parameters,
        treat_dot_as_module=config.treat_dot_as_module,
        use_exact_imports=config.use_exact_imports,
        union_mode=config.union_mode,
        output_datetime_class=config.output_datetime_class,
        output_date_class=config.output_date_class,
        keyword_only=config.keyword_only,
        frozen_dataclasses=config.frozen_dataclasses,
        no_alias=config.no_alias,
        use_frozen_field=config.use_frozen_field,
        use_default_factory_for_optional_nested_models=config.use_default_factory_for_optional_nested_models,
        formatters=config.formatters,
        settings_path=settings_path,
        parent_scoped_naming=config.parent_scoped_naming,
        naming_strategy=config.naming_strategy,
        duplicate_name_suffix=config.duplicate_name_suffix,
        dataclass_arguments=config.dataclass_arguments,
        disable_future_imports=config.disable_future_imports,
        type_mappings=config.type_mappings,
        type_overrides=config.type_overrides,
        read_only_write_only_model_type=config.read_only_write_only_model_type,
        use_status_code_in_response_name=config.use_status_code_in_response_name,
        all_exports_scope=config.all_exports_scope,
        all_exports_collision_strategy=config.all_exports_collision_strategy,
        field_type_collision_strategy=config.field_type_collision_strategy,
        module_split_mode=config.module_split_mode,
    )

    if output is None and result is not None:  # pragma: no cover
        if isinstance(result, str):
            sys.stdout.write(result + "\n")
        else:
            for content in result.values():
                sys.stdout.write(content + "\n")


def main(args: Sequence[str] | None = None) -> Exit:  # noqa: PLR0911, PLR0912, PLR0914, PLR0915
    """Execute datamodel code generation from command-line arguments."""
    if "_ARGCOMPLETE" in os.environ:  # pragma: no cover
        import argcomplete  # noqa: PLC0415

        argcomplete.autocomplete(arg_parser)

    if args is None:  # pragma: no cover
        args = sys.argv[1:]

    arg_parser.parse_args(args, namespace=namespace)

    if namespace.version:
        from datamodel_code_generator import get_version  # noqa: PLC0415

        print(get_version())  # noqa: T201
        sys.exit(0)

    if namespace.generate_pyproject_config:
        config_output = generate_pyproject_config(namespace)
        print(config_output)  # noqa: T201
        return Exit.OK

    if namespace.generate_prompt is not None:
        from datamodel_code_generator.prompt import generate_prompt  # noqa: PLC0415

        help_text = arg_parser.format_help()
        prompt_output = generate_prompt(namespace, help_text)
        print(prompt_output)  # noqa: T201
        return Exit.OK

    # Handle --ignore-pyproject and --profile options
    if namespace.ignore_pyproject:
        pyproject_config: dict[str, Any] = {}
    else:
        try:
            pyproject_config = _get_pyproject_toml_config(Path.cwd(), profile=namespace.profile)
        except Error as e:
            print(e.message, file=sys.stderr)  # noqa: T201
            return Exit.ERROR

    if namespace.generate_cli_command:
        if not pyproject_config:
            print(  # noqa: T201
                "No [tool.datamodel-codegen] section found in pyproject.toml",
                file=sys.stderr,
            )
            return Exit.ERROR
        command_output = generate_cli_command(pyproject_config)
        print(command_output)  # noqa: T201
        return Exit.OK

    try:
        config = Config.parse_obj(pyproject_config)
        config.merge_args(namespace)
    except Error as e:
        print(e.message, file=sys.stderr)  # noqa: T201
        return Exit.ERROR

    if not config.input and not config.url and not config.input_model and sys.stdin.isatty():
        print(  # noqa: T201
            "Not Found Input: require `stdin` or arguments `--input`, `--url`, or `--input-model`",
            file=sys.stderr,
        )
        arg_parser.print_help()
        return Exit.ERROR

    if config.input_model and (config.input or config.url):
        print(  # noqa: T201
            "Error: --input-model cannot be used with --input or --url",
            file=sys.stderr,
        )
        return Exit.ERROR

    if config.check and config.output is None:
        print(  # noqa: T201
            "Error: --check cannot be used with stdout output (no --output specified)",
            file=sys.stderr,
        )
        return Exit.ERROR

    if config.watch and config.check:
        print(  # noqa: T201
            "Error: --watch and --check cannot be used together",
            file=sys.stderr,
        )
        return Exit.ERROR

    if config.watch and config.input_model:
        print(  # noqa: T201
            "Error: --watch cannot be used with --input-model",
            file=sys.stderr,
        )
        return Exit.ERROR

    if config.watch and (config.input is None or is_url(str(config.input))):
        print(  # noqa: T201
            "Error: --watch requires --input file path (not URL or stdin)",
            file=sys.stderr,
        )
        return Exit.ERROR

    if not is_supported_in_black(config.target_python_version):  # pragma: no cover
        print(  # noqa: T201
            f"Installed black doesn't support Python version {config.target_python_version.value}.\n"
            f"You have to install a newer black.\n"
            f"Installed black version: {_get_black().__version__}",
            file=sys.stderr,
        )
        return Exit.ERROR

    if config.debug:  # pragma: no cover
        enable_debug_message()

    if config.disable_warnings:
        warnings.simplefilter("ignore")

    if config.reuse_scope == ReuseScope.Tree and not config.reuse_model:
        print(  # noqa: T201
            "Warning: --reuse-scope=tree has no effect without --reuse-model",
            file=sys.stderr,
        )

    if config.collapse_root_models_name_strategy and not config.collapse_root_models:
        print(  # noqa: T201
            "Error: --collapse-root-models-name-strategy requires --collapse-root-models",
            file=sys.stderr,
        )
        return Exit.ERROR

    if (
        config.use_specialized_enum
        and namespace.use_specialized_enum is not False  # CLI didn't disable it
        and (namespace.use_specialized_enum is True or pyproject_config.get("use_specialized_enum") is True)
        and not config.target_python_version.has_strenum
    ):
        print(  # noqa: T201
            f"Error: --use-specialized-enum requires --target-python-version 3.11 or later.\n"
            f"Current target version: {config.target_python_version.value}\n"
            f"StrEnum is only available in Python 3.11+.",
            file=sys.stderr,
        )
        return Exit.ERROR

    extra_template_data: defaultdict[str, dict[str, Any]] | None
    if config.extra_template_data is None:
        extra_template_data = None
    else:
        with config.extra_template_data as data:
            try:
                extra_template_data = json.load(data, object_hook=lambda d: defaultdict(dict, **d))
            except json.JSONDecodeError as e:
                print(f"Unable to load extra template data: {e}", file=sys.stderr)  # noqa: T201
                return Exit.ERROR

        # Extract additional_imports from extra_template_data entries and merge with config
        assert extra_template_data is not None
        additional_imports_from_template_data = _extract_additional_imports(extra_template_data)
        if additional_imports_from_template_data:
            if config.additional_imports is None:
                config.additional_imports = additional_imports_from_template_data
            else:
                config.additional_imports = list(config.additional_imports) + additional_imports_from_template_data

    if config.aliases is None:
        aliases = None
    else:
        with config.aliases as data:
            try:
                aliases = json.load(data)
            except json.JSONDecodeError as e:
                print(f"Unable to load alias mapping: {e}", file=sys.stderr)  # noqa: T201
                return Exit.ERROR
        if not isinstance(aliases, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()
        ):
            print(  # noqa: T201
                'Alias mapping must be a JSON string mapping (e.g. {"from": "to", ...})',
                file=sys.stderr,
            )
            return Exit.ERROR

    if config.custom_formatters_kwargs is None:
        custom_formatters_kwargs = None
    else:
        with config.custom_formatters_kwargs as data:
            try:
                custom_formatters_kwargs = json.load(data)
            except json.JSONDecodeError as e:  # pragma: no cover
                print(  # noqa: T201
                    f"Unable to load custom_formatters_kwargs mapping: {e}",
                    file=sys.stderr,
                )
                return Exit.ERROR
        if not isinstance(custom_formatters_kwargs, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in custom_formatters_kwargs.items()
        ):  # pragma: no cover
            print(  # noqa: T201
                'Custom formatters kwargs mapping must be a JSON string mapping (e.g. {"from": "to", ...})',
                file=sys.stderr,
            )
            return Exit.ERROR

    if config.check:
        config_output = cast("Path", config.output)
        is_directory_output = not config_output.suffix
        temp_context: tempfile.TemporaryDirectory[str] | None = tempfile.TemporaryDirectory()
        temp_dir = Path(temp_context.name)
        if is_directory_output:
            generate_output: Path | None = temp_dir / config_output.name
        else:
            generate_output = temp_dir / "output.py"
    else:
        temp_context = None
        generate_output = config.output
        is_directory_output = False

    try:
        input_: Path | str | ParseResult
        if config.input_model:
            schema = _load_model_schema(config.input_model, config.input_file_type)
            input_ = json.dumps(schema)
            if config.input_file_type == InputFileType.Auto:
                config.input_file_type = InputFileType.JsonSchema
        else:
            input_ = config.url or config.input or sys.stdin.read()

        run_generate_from_config(
            config=config,
            input_=input_,
            output=generate_output,
            extra_template_data=extra_template_data,
            aliases=aliases,
            command_line=shlex.join(["datamodel-codegen", *args]) if config.enable_command_header else None,
            custom_formatters_kwargs=custom_formatters_kwargs,
            settings_path=config.output,
        )
    except InvalidClassNameError as e:
        print(f"{e} You have to set `--class-name` option", file=sys.stderr)  # noqa: T201
        if temp_context is not None:
            temp_context.cleanup()
        return Exit.ERROR
    except Error as e:
        print(str(e), file=sys.stderr)  # noqa: T201
        if temp_context is not None:
            temp_context.cleanup()
        return Exit.ERROR
    except Exception:  # noqa: BLE001
        import traceback  # noqa: PLC0415

        print(traceback.format_exc(), file=sys.stderr)  # noqa: T201
        if temp_context is not None:
            temp_context.cleanup()
        return Exit.ERROR

    if config.check and config.output is not None and generate_output is not None:
        has_differences = False

        if is_directory_output:
            diffs, missing_files, extra_files = _compare_directories(generate_output, config.output, config.encoding)
            if diffs:
                print("".join(diffs), end="")  # noqa: T201
                has_differences = True
            for missing in missing_files:
                print(f"MISSING: {missing} (should be generated)")  # noqa: T201
                has_differences = True
            for extra in extra_files:
                print(f"EXTRA: {extra} (no longer generated)")  # noqa: T201
                has_differences = True
        else:
            diff_found, diff_lines = _compare_single_file(generate_output, config.output, config.encoding)
            if diff_found:
                print("".join(diff_lines), end="")  # noqa: T201
                has_differences = True

        if temp_context is not None:  # pragma: no branch
            temp_context.cleanup()

        return Exit.DIFF if has_differences else Exit.OK

    if config.watch:
        try:
            from datamodel_code_generator.watch import watch_and_regenerate  # noqa: PLC0415

            return watch_and_regenerate(config, extra_template_data, aliases, custom_formatters_kwargs)
        except Exception as e:  # noqa: BLE001
            print(str(e), file=sys.stderr)  # noqa: T201
            return Exit.ERROR

    return Exit.OK


if __name__ == "__main__":
    sys.exit(main())
