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
    AllOfClassHierarchy,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    DataModelType,
    Error,
    FieldTypeCollisionStrategy,
    InputFileType,
    InputModelRefStrategy,
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
    input_model_ref_strategy: Optional[InputModelRefStrategy] = None  # noqa: UP045
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
    allof_class_hierarchy: AllOfClassHierarchy = AllOfClassHierarchy.IfNoConflict
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


# Types that are lost during JSON Schema conversion and need to be preserved
_PRESERVED_TYPE_ORIGINS: dict[type, str] = {}

# Marker for types that Pydantic cannot serialize to JSON Schema
_UNSERIALIZABLE_MARKER = "x-python-unserializable"


def _serialize_python_type_full(tp: type) -> str:  # noqa: PLR0911
    """Serialize ANY Python type to its string representation.

    Handles:
    - Basic types: str, int, bool, etc.
    - Generic types: List[str], Dict[str, int], etc.
    - Callable: Callable[[str], str], Callable[..., Any]
    - Union types: str | int, Optional[str]
    - Type: Type[BaseModel]
    - Custom classes: mymodule.MyClass
    - Nested generics: List[Callable[[str], str]]
    """
    import types  # noqa: PLC0415
    from typing import Union, get_args, get_origin  # noqa: PLC0415

    if tp is type(None):  # pragma: no cover
        return "None"

    if tp is ...:  # pragma: no cover
        return "..."

    origin = get_origin(tp)
    args = get_args(tp)

    if origin is None:
        module = getattr(tp, "__module__", "")
        name = getattr(tp, "__name__", None) or getattr(tp, "__qualname__", None)

        if name is None:
            return str(tp).replace("typing.", "")

        if module and module not in {"builtins", "typing", "collections.abc"}:
            return f"{module}.{name}"
        return name

    if _is_callable_origin(origin):
        return _serialize_callable(args)

    if origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):  # pragma: no cover
        parts = [_serialize_python_type_full(arg) for arg in args]
        return " | ".join(parts)

    if origin is type:
        if args:
            return f"Type[{_serialize_python_type_full(args[0])}]"
        return "Type"  # pragma: no cover

    origin_name = _get_origin_name(origin)
    if args:
        args_str = ", ".join(_serialize_python_type_full(arg) for arg in args)
        return f"{origin_name}[{args_str}]"

    return origin_name  # pragma: no cover


def _is_callable_origin(origin: type | None) -> bool:
    """Check if origin is Callable."""
    if origin is None:  # pragma: no cover
        return False
    from collections.abc import Callable as ABCCallable  # noqa: PLC0415

    if origin is ABCCallable:
        return True
    origin_str = str(origin)
    return "Callable" in origin_str or "callable" in origin_str


def _serialize_callable(args: tuple[type, ...]) -> str:
    """Serialize Callable type."""
    if not args:  # pragma: no cover
        return "Callable"

    params = args[:-1]
    ret = args[-1]

    if len(params) == 1 and params[0] is ...:
        return f"Callable[..., {_serialize_python_type_full(ret)}]"

    if len(params) == 1 and isinstance(params[0], (list, tuple)):  # pragma: no cover
        params = tuple(params[0])

    params_str = ", ".join(_serialize_python_type_full(p) for p in params)
    return f"Callable[[{params_str}], {_serialize_python_type_full(ret)}]"


def _get_origin_name(origin: type) -> str:
    """Get the fully qualified name of a generic origin.

    For types from builtins, typing, or collections.abc, returns just the name.
    For other types (custom generics), returns module.qualname format.
    """
    name = getattr(origin, "__qualname__", None) or getattr(origin, "__name__", None)
    if name:
        module = getattr(origin, "__module__", "")
        if module and module not in {"builtins", "typing", "collections.abc"}:
            return f"{module}.{name}"
        return name

    # Fallback for origins without __name__ (rare edge case)
    origin_str = str(origin)  # pragma: no cover
    if "typing." in origin_str:  # pragma: no cover
        return origin_str.replace("typing.", "")

    return origin_str  # pragma: no cover


def _get_input_model_json_schema_class() -> type:
    """Get the InputModelJsonSchema class (lazy import to avoid Pydantic v1 issues)."""
    from pydantic.json_schema import GenerateJsonSchema  # noqa: PLC0415

    class InputModelJsonSchema(GenerateJsonSchema):
        """Custom schema generator that handles ALL unserializable types."""

        def handle_invalid_for_json_schema(  # noqa: PLR6301
            self,
            schema: Any,  # noqa: ARG002
            error_info: Any,  # noqa: ARG002
        ) -> dict[str, Any]:
            """Catch ALL types that Pydantic can't serialize to JSON Schema."""
            return {
                "type": "object",
                _UNSERIALIZABLE_MARKER: True,
            }

        def callable_schema(  # noqa: PLR6301
            self,
            schema: Any,  # noqa: ARG002
        ) -> dict[str, Any]:
            """Handle Callable types - these raise before handle_invalid_for_json_schema."""
            return {
                "type": "string",
                _UNSERIALIZABLE_MARKER: True,
            }

    return InputModelJsonSchema


def _is_type_origin(annotation: type) -> bool:
    """Check if annotation is Type[X]."""
    from typing import get_origin  # noqa: PLC0415

    origin = get_origin(annotation)
    return origin is type


def _process_unserializable_property(prop: dict[str, Any], annotation: type) -> None:
    """Process a single property, handling anyOf/oneOf/items structures."""
    if "anyOf" in prop:
        for item in prop["anyOf"]:
            if item.get(_UNSERIALIZABLE_MARKER):
                _set_python_type_for_unserializable(item, annotation)
    elif "oneOf" in prop:  # pragma: no cover
        for item in prop["oneOf"]:
            if item.get(_UNSERIALIZABLE_MARKER):
                _set_python_type_for_unserializable(item, annotation)
    elif prop.get(_UNSERIALIZABLE_MARKER):
        _set_python_type_for_unserializable(prop, annotation)
    elif "items" in prop and prop["items"].get(_UNSERIALIZABLE_MARKER):
        prop["x-python-type"] = _serialize_python_type_full(annotation)
        prop["items"].pop(_UNSERIALIZABLE_MARKER, None)
    elif _is_type_origin(annotation):
        prop["x-python-type"] = _serialize_python_type_full(annotation)


def _set_python_type_for_unserializable(item: dict[str, Any], annotation: type) -> None:
    """Set x-python-type and clean up markers."""
    from typing import Union, get_args, get_origin  # noqa: PLC0415

    origin = get_origin(annotation)
    actual_type = annotation

    if origin is Union:
        for arg in get_args(annotation):  # pragma: no branch
            if arg is not type(None):  # pragma: no branch
                actual_type = arg
                break

    item["x-python-type"] = _serialize_python_type_full(actual_type)
    item.pop(_UNSERIALIZABLE_MARKER, None)


def _add_python_type_for_unserializable(
    schema: dict[str, Any],
    model: type,
    visited_defs: set[str] | None = None,
) -> dict[str, Any]:
    """Add x-python-type to ALL fields marked as unserializable.

    Handles:
    - Top-level properties
    - Nested in anyOf/oneOf/allOf
    - $defs definitions
    """
    if visited_defs is None:
        visited_defs = set()

    if "properties" in schema:
        model_fields = getattr(model, "model_fields", {})
        for field_name, prop in schema["properties"].items():
            if field_name in model_fields:  # pragma: no branch
                annotation = model_fields[field_name].annotation
                _process_unserializable_property(prop, annotation)

    if "$defs" in schema:
        nested_models = _collect_nested_models(model)
        model_name = getattr(model, "__name__", None)
        if model_name:  # pragma: no branch
            nested_models[model_name] = model
        for def_name, def_schema in schema["$defs"].items():
            if def_name in visited_defs:  # pragma: no cover
                continue
            visited_defs.add(def_name)
            if def_name in nested_models:  # pragma: no branch
                _add_python_type_for_unserializable(def_schema, nested_models[def_name], visited_defs)

    return schema


def _init_preserved_type_origins() -> dict[type, str]:
    """Initialize preserved type origins mapping (lazy initialization)."""
    from collections import ChainMap, Counter, OrderedDict, defaultdict, deque  # noqa: PLC0415
    from collections.abc import Mapping as ABCMapping  # noqa: PLC0415
    from collections.abc import MutableMapping as ABCMutableMapping  # noqa: PLC0415
    from collections.abc import MutableSequence as ABCMutableSequence  # noqa: PLC0415
    from collections.abc import MutableSet as ABCMutableSet  # noqa: PLC0415
    from collections.abc import Sequence as ABCSequence  # noqa: PLC0415
    from collections.abc import Set as AbstractSet  # noqa: PLC0415

    return {
        set: "set",
        frozenset: "frozenset",
        defaultdict: "defaultdict",
        OrderedDict: "OrderedDict",
        Counter: "Counter",
        deque: "deque",
        ChainMap: "ChainMap",
        AbstractSet: "AbstractSet",
        ABCMutableSet: "MutableSet",
        ABCMapping: "Mapping",
        ABCMutableMapping: "MutableMapping",
        ABCSequence: "Sequence",
        ABCMutableSequence: "MutableSequence",
    }


def _get_preserved_type_origins() -> dict[type, str]:
    """Get the preserved type origins mapping, initializing if needed."""
    global _PRESERVED_TYPE_ORIGINS  # noqa: PLW0603
    if not _PRESERVED_TYPE_ORIGINS:
        _PRESERVED_TYPE_ORIGINS = _init_preserved_type_origins()
    return _PRESERVED_TYPE_ORIGINS


def _serialize_python_type(tp: type) -> str | None:  # noqa: PLR0911
    """Serialize Python type to a string for x-python-type field.

    Returns None if the type doesn't need to be preserved (e.g., standard dict, list).
    """
    import types  # noqa: PLC0415
    from typing import get_args, get_origin  # noqa: PLC0415

    origin = get_origin(tp)
    args = get_args(tp)
    preserved_origins = _get_preserved_type_origins()

    # Handle types.UnionType (X | Y syntax) in Python 3.10-3.13
    # In Python 3.10-3.13, get_origin(X | Y) returns types.UnionType which is distinct from typing.Union
    # In Python 3.14+, types.UnionType is the same as typing.Union, so this check is skipped
    from typing import Union  # noqa: PLC0415

    if (
        hasattr(types, "UnionType")
        and types.UnionType is not Union  # Only applies to Python 3.10-3.13
        and origin is types.UnionType
    ):
        if args:
            nested = [_serialize_python_type(a) for a in args]
            if any(n is not None for n in nested):
                return " | ".join(n or _simple_type_name(a) for n, a in zip(nested, args, strict=False))
        return None  # pragma: no cover

    # Handle Annotated types - extract the base type and ignore metadata
    from typing import Annotated  # noqa: PLC0415

    if origin is Annotated:
        if args:
            return _serialize_python_type(args[0]) or _simple_type_name(args[0])
        return None  # pragma: no cover

    type_name: str | None = None
    if origin is not None:
        type_name = preserved_origins.get(origin)
        if type_name is None and getattr(origin, "__module__", None) == "collections":  # pragma: no cover
            type_name = _simple_type_name(origin)
    if type_name is not None:
        if args:
            args_str = ", ".join(_serialize_python_type(a) or _simple_type_name(a) for a in args)
            return f"{type_name}[{args_str}]"
        return type_name  # pragma: no cover

    if args:
        nested = [_serialize_python_type(a) for a in args]
        if any(n is not None for n in nested):
            origin_name = _simple_type_name(origin or tp)
            args_str = ", ".join(n or _simple_type_name(a) for n, a in zip(nested, args, strict=False))
            return f"{origin_name}[{args_str}]"

    return None


def _simple_type_name(tp: type) -> str:
    """Get a simple string representation of a type."""
    from typing import get_origin  # noqa: PLC0415

    if tp is type(None):
        return "None"
    # For generic types (e.g., dict[str, Any]), use full string representation
    if get_origin(tp) is not None:
        return str(tp).replace("typing.", "")
    if hasattr(tp, "__name__"):
        return tp.__name__
    return str(tp).replace("typing.", "")  # pragma: no cover


def _collect_nested_models(model: type, visited: set[type] | None = None) -> dict[str, type]:
    """Collect all nested types (BaseModel, Enum, dataclass) from a model's fields."""
    if visited is None:
        visited = set()

    if model in visited:  # pragma: no cover
        return {}
    visited.add(model)

    result: dict[str, type] = {}

    model_fields = getattr(model, "model_fields", None)
    if model_fields is not None:
        for field_info in model_fields.values():
            tp = field_info.annotation
            _find_models_in_type(tp, result, visited)
    else:
        type_hints = _get_type_hints_safe(model)
        for tp in type_hints.values():
            _find_models_in_type(tp, result, visited)

    return result


def _find_models_in_type(tp: type, result: dict[str, type], visited: set[type]) -> None:
    """Recursively find BaseModel, Enum, dataclass, TypedDict, and msgspec in a type annotation."""
    from dataclasses import is_dataclass  # noqa: PLC0415
    from enum import Enum as PyEnum  # noqa: PLC0415
    from typing import get_args  # noqa: PLC0415

    if isinstance(tp, type) and tp not in visited:
        if issubclass(tp, BaseModel):
            result[tp.__name__] = tp
            result.update(_collect_nested_models(tp, visited))
        elif (
            issubclass(tp, PyEnum)
            or is_dataclass(tp)
            or hasattr(tp, "__required_keys__")
            or hasattr(tp, "__struct_fields__")
        ):
            result[tp.__name__] = tp

    for arg in get_args(tp):
        _find_models_in_type(arg, result, visited)


def _get_type_hints_safe(obj: type) -> dict[str, Any]:
    """Safely get type hints from a class, handling forward references."""
    from typing import get_type_hints  # noqa: PLC0415

    try:
        return get_type_hints(obj)
    except Exception:  # noqa: BLE001  # pragma: no cover
        return getattr(obj, "__annotations__", {})


def _add_python_type_to_properties(
    properties: dict[str, Any],
    model_fields: dict[str, Any],
) -> None:
    """Add x-python-type to properties dict for given model fields."""
    for field_name, field_info in model_fields.items():
        if field_name not in properties:  # pragma: no cover
            continue
        serialized = _serialize_python_type(field_info.annotation)
        if serialized:
            properties[field_name]["x-python-type"] = serialized


def _add_python_type_info(schema: dict[str, Any], model: type) -> dict[str, Any]:
    """Add x-python-type information to JSON Schema for types lost during conversion.

    This preserves type information for Set, FrozenSet, Mapping, and other types
    that are converted to array/object in JSON Schema.
    """
    model_fields = getattr(model, "model_fields", None)
    if model_fields and "properties" in schema:
        _add_python_type_to_properties(schema["properties"], model_fields)

    if "$defs" in schema:
        nested_models = _collect_nested_models(model)
        model_name = getattr(model, "__name__", None)
        if model_name and model_name in schema["$defs"]:
            nested_models[model_name] = model
        for def_name, def_schema in schema["$defs"].items():
            if def_name not in nested_models or "properties" not in def_schema:  # pragma: no cover
                continue
            nested_model = nested_models[def_name]
            nested_fields = getattr(nested_model, "model_fields", None)
            if nested_fields:  # pragma: no branch
                _add_python_type_to_properties(def_schema["properties"], nested_fields)

    return schema


def _add_python_type_info_generic(schema: dict[str, Any], obj: type) -> dict[str, Any]:
    """Add x-python-type information using get_type_hints (for dataclass/TypedDict)."""
    type_hints = _get_type_hints_safe(obj)
    if type_hints and "properties" in schema:  # pragma: no branch
        for field_name, field_type in type_hints.items():
            if field_name in schema["properties"]:  # pragma: no branch
                serialized = _serialize_python_type(field_type)
                if serialized:
                    schema["properties"][field_name]["x-python-type"] = serialized

    return schema


_TYPE_FAMILY_ENUM = "enum"
_TYPE_FAMILY_PYDANTIC = "pydantic"
_TYPE_FAMILY_DATACLASS = "dataclass"
_TYPE_FAMILY_TYPEDDICT = "typeddict"
_TYPE_FAMILY_MSGSPEC = "msgspec"
_TYPE_FAMILY_OTHER = "other"


def _get_type_family(tp: type) -> str:  # noqa: PLR0911
    """Determine the type family of a Python type."""
    from dataclasses import is_dataclass  # noqa: PLC0415
    from enum import Enum as PyEnum  # noqa: PLC0415

    if isinstance(tp, type) and issubclass(tp, PyEnum):
        return _TYPE_FAMILY_ENUM

    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return _TYPE_FAMILY_PYDANTIC

    if hasattr(tp, "__pydantic_fields__") and is_dataclass(tp):  # pragma: no cover
        return _TYPE_FAMILY_PYDANTIC

    if is_dataclass(tp):
        return _TYPE_FAMILY_DATACLASS

    if isinstance(tp, type) and hasattr(tp, "__required_keys__"):
        return _TYPE_FAMILY_TYPEDDICT

    if isinstance(tp, type) and hasattr(tp, "__struct_fields__"):  # pragma: no cover
        return _TYPE_FAMILY_MSGSPEC

    return _TYPE_FAMILY_OTHER  # pragma: no cover


def _get_output_family(output_model_type: DataModelType) -> str:
    """Get the type family corresponding to a DataModelType."""
    pydantic_types = {
        DataModelType.PydanticBaseModel,
        DataModelType.PydanticV2BaseModel,
        DataModelType.PydanticV2Dataclass,
    }
    if output_model_type in pydantic_types:
        return _TYPE_FAMILY_PYDANTIC
    if output_model_type == DataModelType.DataclassesDataclass:
        return _TYPE_FAMILY_DATACLASS
    if output_model_type == DataModelType.TypingTypedDict:
        return _TYPE_FAMILY_TYPEDDICT
    if output_model_type == DataModelType.MsgspecStruct:
        return _TYPE_FAMILY_MSGSPEC
    return _TYPE_FAMILY_OTHER  # pragma: no cover


def _should_reuse_type(source_family: str, output_family: str) -> bool:
    """Determine if a source type can be reused without conversion.

    Returns True if the source type should be imported and reused,
    False if it needs to be regenerated into the output type.
    """
    if source_family == _TYPE_FAMILY_ENUM:
        return True
    return source_family == output_family


def _filter_defs_by_strategy(
    schema: dict[str, Any],
    nested_models: dict[str, type],
    output_model_type: DataModelType,
    strategy: InputModelRefStrategy,
) -> dict[str, Any]:
    """Filter $defs based on ref strategy, marking reused types with x-python-import."""
    if strategy == InputModelRefStrategy.RegenerateAll:  # pragma: no cover
        return schema

    if "$defs" not in schema:  # pragma: no cover
        return schema

    output_family = _get_output_family(output_model_type)
    new_defs: dict[str, Any] = {}

    for def_name, def_schema in schema["$defs"].items():
        if def_name not in nested_models:  # pragma: no cover
            new_defs[def_name] = def_schema
            continue

        nested_type = nested_models[def_name]
        type_family = _get_type_family(nested_type)

        should_reuse = strategy == InputModelRefStrategy.ReuseAll or (
            strategy == InputModelRefStrategy.ReuseForeign and _should_reuse_type(type_family, output_family)
        )

        if should_reuse:
            new_defs[def_name] = {
                "x-python-import": {
                    "module": nested_type.__module__,
                    "name": nested_type.__name__,
                },
            }
        else:
            new_defs[def_name] = def_schema

    return {**schema, "$defs": new_defs}


def _try_rebuild_model(obj: type) -> None:
    """Try to rebuild a Pydantic model, handling config models specially."""
    module = getattr(obj, "__module__", "")
    class_name = getattr(obj, "__name__", "")
    config_classes = {"GenerateConfig", "ParserConfig", "ParseConfig"}
    if module in {"datamodel_code_generator.config", "config"} and class_name in config_classes:
        from datamodel_code_generator.model.base import DataModel, DataModelFieldBase  # noqa: PLC0415
        from datamodel_code_generator.types import DataTypeManager, StrictTypes  # noqa: PLC0415

        try:
            from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            from typing import Any  # noqa: PLC0415

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
        obj.model_rebuild(_types_namespace=types_namespace)
    else:
        obj.model_rebuild()


def _load_model_schema(  # noqa: PLR0912, PLR0914, PLR0915
    input_model: str,
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None = None,
    output_model_type: DataModelType = DataModelType.PydanticBaseModel,
) -> dict[str, object]:
    """Load schema from a Python import path.

    Args:
        input_model: Import path in 'module.path:ObjectName' format
        input_file_type: Current input file type setting for validation
        ref_strategy: Strategy for handling referenced types
        output_model_type: Target output model type for reuse-foreign strategy

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
        if hasattr(obj, "model_rebuild"):  # pragma: no branch
            _try_rebuild_model(obj)
        schema_generator = _get_input_model_json_schema_class()
        schema = obj.model_json_schema(schema_generator=schema_generator)
        schema = _add_python_type_for_unserializable(schema, obj)
        schema = _add_python_type_info(schema, obj)

        if ref_strategy and ref_strategy != InputModelRefStrategy.RegenerateAll:
            nested_models = _collect_nested_models(obj)
            model_name = getattr(obj, "__name__", None)
            if model_name and "$defs" in schema and model_name in schema["$defs"]:  # pragma: no cover
                nested_models[model_name] = obj
            schema = _filter_defs_by_strategy(schema, nested_models, output_model_type, ref_strategy)

        return schema

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

            schema = TypeAdapter(obj).json_schema()
            schema = _add_python_type_info_generic(schema, cast("type", obj))

            if ref_strategy and ref_strategy != InputModelRefStrategy.RegenerateAll:
                obj_type = cast("type", obj)
                nested_models = _collect_nested_models(obj_type)
                obj_name = getattr(obj, "__name__", None)
                if obj_name and "$defs" in schema and obj_name in schema["$defs"]:  # pragma: no cover
                    nested_models[obj_name] = obj_type
                schema = _filter_defs_by_strategy(schema, nested_models, output_model_type, ref_strategy)
        except ImportError as e:
            msg = "--input-model with dataclass/TypedDict requires Pydantic v2 runtime."
            raise Error(msg) from e

        return schema

    msg = f"{qualname!r} is not a supported type. Supported: dict, Pydantic v2 BaseModel, dataclass, TypedDict"
    raise Error(msg)


def _resolve_profile_extends(
    profiles: dict[str, Any],
    profile_name: str,
    visited: set[str] | None = None,
) -> dict[str, Any]:
    """Resolve profile inheritance via extends key."""
    if visited is None:
        visited = set()

    if profile_name in visited:
        chain = " -> ".join(visited) + f" -> {profile_name}"
        msg = f"Circular extends detected: {chain}"
        raise Error(msg)

    if profile_name not in profiles:
        available = list(profiles.keys()) if profiles else "none"
        msg = f"Extended profile '{profile_name}' not found in pyproject.toml. Available profiles: {available}"
        raise Error(msg)

    visited.add(profile_name)
    profile = profiles[profile_name]
    extends = profile.get("extends")

    if not extends:
        return dict(profile.items())

    parents = [extends] if isinstance(extends, str) else extends
    result: dict[str, Any] = {}

    for parent in parents:
        if parent == profile_name:
            msg = f"Profile '{profile_name}' cannot extend itself"
            raise Error(msg)
        parent_config = _resolve_profile_extends(profiles, parent, visited.copy())
        result.update(parent_config)

    result.update({k: v for k, v in profile.items() if k != "extends"})
    return result


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
                    resolved_profile = _resolve_profile_extends(profiles, profile)
                    base_config.update(resolved_profile)

                pyproject_config = {k.replace("-", "_"): v for k, v in base_config.items()}
                if (
                    "capitalize_enum_members" in pyproject_config and "capitalise_enum_members" not in pyproject_config
                ):  # pragma: no cover
                    pyproject_config["capitalise_enum_members"] = pyproject_config.pop("capitalize_enum_members")
                return pyproject_config

        if (current_path / ".git").exists():
            break

        current_path = current_path.parent

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
        allof_class_hierarchy=config.allof_class_hierarchy,
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

    if not is_pydantic_v2():
        warnings.warn(
            "Pydantic v1 runtime support is deprecated and will be removed in a future version. "
            "Please upgrade to Pydantic v2.",
            DeprecationWarning,
            stacklevel=1,
        )

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
            isinstance(k, str) and (isinstance(v, str) or (isinstance(v, list) and all(isinstance(i, str) for i in v)))
            for k, v in aliases.items()
        ):
            print(  # noqa: T201
                "Alias mapping must be a JSON mapping with string keys and string or list of strings values "
                '(e.g. {"from": "to", "field": ["alias1", "alias2"]})',
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
            schema = _load_model_schema(
                config.input_model,
                config.input_file_type,
                config.input_model_ref_strategy,
                config.output_model_type,
            )
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
