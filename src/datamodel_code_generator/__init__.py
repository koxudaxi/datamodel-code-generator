"""Main module for datamodel-code-generator.

Provides the main `generate()` function and related enums/exceptions for generating
Python data models (Pydantic, dataclasses, TypedDict, msgspec) from various schema formats.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Callable,
    Final,
    TextIO,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import ParseResult

import yaml
import yaml.parser
from typing_extensions import TypeAlias, TypeAliasType, TypedDict

import datamodel_code_generator.pydantic_patch  # noqa: F401
from datamodel_code_generator.format import (
    DEFAULT_FORMATTERS,
    DatetimeClassType,
    Formatter,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.util import PYDANTIC_V2, SafeLoader

if TYPE_CHECKING:
    from collections import defaultdict

    from datamodel_code_generator.model.pydantic_v2 import UnionMode
    from datamodel_code_generator.parser.base import Parser
    from datamodel_code_generator.types import StrictTypes

    YamlScalar: TypeAlias = Union[str, int, float, bool, None]
    YamlValue = TypeAliasType("YamlValue", "Union[dict[str, YamlValue], list[YamlValue], YamlScalar]")

MIN_VERSION: Final[int] = 9
MAX_VERSION: Final[int] = 13
DEFAULT_SHARED_MODULE_NAME: Final[str] = "shared"

T = TypeVar("T")


class DataclassArguments(TypedDict, total=False):
    """Arguments for @dataclass decorator."""

    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool
    match_args: bool
    kw_only: bool
    slots: bool
    weakref_slot: bool


if not TYPE_CHECKING:
    YamlScalar: TypeAlias = Union[str, int, float, bool, None]
    if PYDANTIC_V2:
        YamlValue = TypeAliasType("YamlValue", "Union[dict[str, YamlValue], list[YamlValue], YamlScalar]")
    else:
        # Pydantic v1 cannot handle TypeAliasType, use Any for recursive parts
        YamlValue: TypeAlias = Union[dict[str, Any], list[Any], YamlScalar]

try:
    import pysnooper

    pysnooper.tracer.DISABLED = True
except ImportError:  # pragma: no cover
    pysnooper = None

DEFAULT_BASE_CLASS: str = "pydantic.BaseModel"


def load_yaml(stream: str | TextIO) -> YamlValue:
    """Load YAML content from a string or file-like object."""
    return yaml.load(stream, Loader=SafeLoader)  # noqa: S506


def load_yaml_dict(stream: str | TextIO) -> dict[str, YamlValue]:
    """Load YAML and return as dict. Raises TypeError if result is not a dict."""
    result = load_yaml(stream)
    if not isinstance(result, dict):
        msg = f"Expected dict, got {type(result).__name__}"
        raise TypeError(msg)
    return result


def load_yaml_dict_from_path(path: Path, encoding: str) -> dict[str, YamlValue]:
    """Load YAML and return as dict from a file path."""
    with path.open(encoding=encoding) as f:
        return load_yaml_dict(f)


def get_version() -> str:
    """Return the installed package version."""
    package = "datamodel-code-generator"

    from importlib.metadata import version  # noqa: PLC0415

    return version(package)


def enable_debug_message() -> None:  # pragma: no cover
    """Enable debug tracing with pysnooper."""
    if not pysnooper:
        msg = "Please run `$pip install 'datamodel-code-generator[debug]'` to use debug option"
        raise Exception(msg)  # noqa: TRY002

    pysnooper.tracer.DISABLED = False


DEFAULT_MAX_VARIABLE_LENGTH: int = 100


def snooper_to_methods() -> Callable[..., Any]:
    """Class decorator to add pysnooper tracing to all methods."""

    def inner(cls: type[T]) -> type[T]:
        if not pysnooper:
            return cls
        import inspect  # noqa: PLC0415

        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, method in methods:
            snooper_method = pysnooper.snoop(max_variable_length=DEFAULT_MAX_VARIABLE_LENGTH)(method)
            setattr(cls, name, snooper_method)
        return cls

    return inner


@contextlib.contextmanager
def chdir(path: Path | None) -> Iterator[None]:
    """Change working directory and return to previous on exit."""
    if path is None:
        yield
    else:
        prev_cwd = Path.cwd()
        try:
            os.chdir(path if path.is_dir() else path.parent)
            yield
        finally:
            os.chdir(prev_cwd)


def is_openapi(data: dict) -> bool:
    """Check if the data dict is an OpenAPI specification."""
    return "openapi" in data


JSON_SCHEMA_URLS: tuple[str, ...] = (
    "http://json-schema.org/",
    "https://json-schema.org/",
)


def is_schema(data: dict) -> bool:
    """Check if the data dict is a JSON Schema."""
    schema = data.get("$schema")
    if isinstance(schema, str) and any(schema.startswith(u) for u in JSON_SCHEMA_URLS):  # pragma: no cover
        return True
    if isinstance(data.get("type"), str):
        return True
    if any(
        isinstance(data.get(o), list)
        for o in (
            "allOf",
            "anyOf",
            "oneOf",
        )
    ):
        return True
    return isinstance(data.get("properties"), dict)


class InputFileType(Enum):
    """Supported input file types for schema parsing."""

    Auto = "auto"
    OpenAPI = "openapi"
    JsonSchema = "jsonschema"
    Json = "json"
    Yaml = "yaml"
    Dict = "dict"
    CSV = "csv"
    GraphQL = "graphql"


RAW_DATA_TYPES: list[InputFileType] = [
    InputFileType.Json,
    InputFileType.Yaml,
    InputFileType.Dict,
    InputFileType.CSV,
    InputFileType.GraphQL,
]


class DataModelType(Enum):
    """Supported output data model types."""

    PydanticBaseModel = "pydantic.BaseModel"
    PydanticV2BaseModel = "pydantic_v2.BaseModel"
    DataclassesDataclass = "dataclasses.dataclass"
    TypingTypedDict = "typing.TypedDict"
    MsgspecStruct = "msgspec.Struct"


class ReuseScope(Enum):
    """Scope for model reuse deduplication.

    module: Deduplicate identical models within each module (default).
    tree: Deduplicate identical models across all modules, placing shared models in shared.py.
    """

    Module = "module"
    Tree = "tree"


class OpenAPIScope(Enum):
    """Scopes for OpenAPI model generation."""

    Schemas = "schemas"
    Paths = "paths"
    Tags = "tags"
    Parameters = "parameters"
    Webhooks = "webhooks"


class AllExportsScope(Enum):
    """Scope for __all__ exports in __init__.py.

    children: Export models from direct child modules only.
    recursive: Export models from all descendant modules recursively.
    """

    Children = "children"
    Recursive = "recursive"


class AllExportsCollisionStrategy(Enum):
    """Strategy for handling name collisions in recursive exports.

    error: Raise an error when name collision is detected.
    minimal_prefix: Add module prefix only to colliding names.
    full_prefix: Add full module path prefix to all colliding names.
    """

    Error = "error"
    MinimalPrefix = "minimal-prefix"
    FullPrefix = "full-prefix"


class AllOfMergeMode(Enum):
    """Mode for field merging in allOf schemas.

    constraints: Merge only constraint fields (minItems, maxItems, pattern, etc.) from parent.
    all: Merge constraints plus annotation fields (default, examples) from parent.
    none: Do not merge any fields from parent properties.
    """

    Constraints = "constraints"
    All = "all"
    NoMerge = "none"


class GraphQLScope(Enum):
    """Scopes for GraphQL model generation."""

    Schema = "schema"


class ReadOnlyWriteOnlyModelType(Enum):
    """Model generation strategy for readOnly/writeOnly fields.

    RequestResponse: Generate only Request/Response model variants (no base model).
    All: Generate Base, Request, and Response models.
    """

    RequestResponse = "request-response"
    All = "all"


class ModuleSplitMode(Enum):
    """Mode for splitting generated models into separate files.

    Single: Generate one file per model class.
    """

    Single = "single"


class Error(Exception):
    """Base exception for datamodel-code-generator errors."""

    def __init__(self, message: str) -> None:
        """Initialize with message."""
        self.message: str = message

    def __str__(self) -> str:
        """Return string representation."""
        return self.message


class InvalidClassNameError(Error):
    """Raised when a schema title cannot be converted to a valid Python class name."""

    def __init__(self, class_name: str) -> None:
        """Initialize with class name."""
        self.class_name = class_name
        message = f"title={class_name!r} is invalid class name."
        super().__init__(message=message)


def get_first_file(path: Path) -> Path:  # pragma: no cover
    """Find and return the first file in a path (file or directory)."""
    if path.is_file():
        return path
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_file():
                return child
    msg = f"No file found in: {path}"
    raise FileNotFoundError(msg)


def _find_future_import_insertion_point(header: str) -> int:
    """Find position in header where __future__ import should be inserted."""
    import ast  # noqa: PLC0415

    try:
        tree = ast.parse(header)
    except SyntaxError:
        return 0

    lines = header.splitlines(keepends=True)

    def line_end_pos(line_num: int) -> int:
        return sum(len(lines[i]) for i in range(line_num))

    if not tree.body:
        return len(header)

    first_stmt = tree.body[0]
    is_docstring = isinstance(first_stmt, ast.Expr) and (
        (isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str))
        or isinstance(first_stmt.value, ast.JoinedStr)
    )
    if is_docstring:
        end_line = first_stmt.end_lineno or len(lines)
        pos = line_end_pos(end_line)
        while end_line < len(lines) and not lines[end_line].strip():
            pos += len(lines[end_line])
            end_line += 1
        return pos

    pos = 0
    for i in range(first_stmt.lineno - 1):
        pos += len(lines[i])
    return pos


def generate(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915
    input_: Path | str | ParseResult | Mapping[str, Any],
    *,
    input_filename: str | None = None,
    input_file_type: InputFileType = InputFileType.Auto,
    output: Path | None = None,
    output_model_type: DataModelType = DataModelType.PydanticBaseModel,
    target_python_version: PythonVersion = PythonVersionMin,
    base_class: str = "",
    additional_imports: list[str] | None = None,
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
    apply_default_values_for_required_fields: bool = False,
    force_optional_for_required_fields: bool = False,
    class_name: str | None = None,
    use_standard_collections: bool = False,
    use_schema_description: bool = False,
    use_field_description: bool = False,
    use_attribute_docstrings: bool = False,
    use_inline_field_description: bool = False,
    use_default_kwarg: bool = False,
    reuse_model: bool = False,
    reuse_scope: ReuseScope = ReuseScope.Module,
    shared_module_name: str = DEFAULT_SHARED_MODULE_NAME,
    encoding: str = "utf-8",
    enum_field_as_literal: LiteralType | None = None,
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
    openapi_scopes: list[OpenAPIScope] | None = None,
    include_path_parameters: bool = False,
    graphql_scopes: list[GraphQLScope] | None = None,  # noqa: ARG001
    wrap_string_literal: bool | None = None,
    use_title_as_name: bool = False,
    use_operation_id_as_name: bool = False,
    use_unique_items_as_set: bool = False,
    allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints,
    http_headers: Sequence[tuple[str, str]] | None = None,
    http_ignore_tls: bool = False,
    use_annotated: bool = False,
    use_serialize_as_any: bool = False,
    use_non_positive_negative_number_constrained_types: bool = False,
    use_decimal_for_multiple_of: bool = False,
    original_field_name_delimiter: str | None = None,
    use_double_quotes: bool = False,
    use_union_operator: bool = False,
    collapse_root_models: bool = False,
    skip_root_model: bool = False,
    use_type_alias: bool = False,
    special_field_name_prefix: str | None = None,
    remove_special_field_name_prefix: bool = False,
    capitalise_enum_members: bool = False,
    keep_model_order: bool = False,
    custom_file_header: str | None = None,
    custom_file_header_path: Path | None = None,
    custom_formatters: list[str] | None = None,
    custom_formatters_kwargs: dict[str, Any] | None = None,
    use_pendulum: bool = False,
    http_query_parameters: Sequence[tuple[str, str]] | None = None,
    treat_dot_as_module: bool = False,
    use_exact_imports: bool = False,
    union_mode: UnionMode | None = None,
    output_datetime_class: DatetimeClassType | None = None,
    keyword_only: bool = False,
    frozen_dataclasses: bool = False,
    no_alias: bool = False,
    use_frozen_field: bool = False,
    formatters: list[Formatter] = DEFAULT_FORMATTERS,
    settings_path: Path | None = None,
    parent_scoped_naming: bool = False,
    dataclass_arguments: DataclassArguments | None = None,
    disable_future_imports: bool = False,
    type_mappings: list[str] | None = None,
    read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None,
    all_exports_scope: AllExportsScope | None = None,
    all_exports_collision_strategy: AllExportsCollisionStrategy | None = None,
    module_split_mode: ModuleSplitMode | None = None,
) -> None:
    """Generate Python data models from schema definitions or structured data.

    This is the main entry point for code generation. Supports OpenAPI, JSON Schema,
    GraphQL, and raw data formats (JSON, YAML, Dict, CSV) as input.
    """
    remote_text_cache: DefaultPutDict[str, str] = DefaultPutDict()
    if isinstance(input_, str):
        input_text: str | None = input_
    elif isinstance(input_, ParseResult):
        from datamodel_code_generator.http import get_body  # noqa: PLC0415

        input_text = remote_text_cache.get_or_put(
            input_.geturl(),
            default_factory=lambda url: get_body(url, http_headers, http_ignore_tls, http_query_parameters),
        )
    else:
        input_text = None

    if dataclass_arguments is None:
        dataclass_arguments = {}
        if frozen_dataclasses:
            dataclass_arguments["frozen"] = True
        if keyword_only:
            dataclass_arguments["kw_only"] = True

    if isinstance(input_, Path) and not input_.is_absolute():
        input_ = input_.expanduser().resolve()
    if input_file_type == InputFileType.Auto:
        try:
            input_text_ = (
                get_first_file(input_).read_text(encoding=encoding) if isinstance(input_, Path) else input_text
            )
        except FileNotFoundError as exc:
            msg = "File not found"
            raise Error(msg) from exc

        try:
            assert isinstance(input_text_, str)
            input_file_type = infer_input_type(input_text_)
        except Exception as exc:
            msg = "Invalid file format"
            raise Error(msg) from exc
        else:
            print(  # noqa: T201
                inferred_message.format(input_file_type.value),
                file=sys.stderr,
            )

    kwargs: dict[str, Any] = {}
    if input_file_type == InputFileType.OpenAPI:  # noqa: PLR1702
        from datamodel_code_generator.parser.openapi import OpenAPIParser  # noqa: PLC0415

        parser_class: type[Parser] = OpenAPIParser
        kwargs["openapi_scopes"] = openapi_scopes
        kwargs["include_path_parameters"] = include_path_parameters
    elif input_file_type == InputFileType.GraphQL:
        from datamodel_code_generator.parser.graphql import GraphQLParser  # noqa: PLC0415

        parser_class: type[Parser] = GraphQLParser
    else:
        from datamodel_code_generator.parser.jsonschema import JsonSchemaParser  # noqa: PLC0415

        parser_class = JsonSchemaParser

        if input_file_type in RAW_DATA_TYPES:
            import json  # noqa: PLC0415

            try:
                if isinstance(input_, Path) and input_.is_dir():  # pragma: no cover
                    msg = f"Input must be a file for {input_file_type}"
                    raise Error(msg)  # noqa: TRY301
                obj: dict[str, Any]
                if input_file_type == InputFileType.CSV:
                    import csv  # noqa: PLC0415

                    def get_header_and_first_line(csv_file: IO[str]) -> dict[str, Any]:
                        csv_reader = csv.DictReader(csv_file)
                        assert csv_reader.fieldnames is not None
                        return dict(zip(csv_reader.fieldnames, next(csv_reader)))

                    if isinstance(input_, Path):
                        with input_.open(encoding=encoding) as f:
                            obj = get_header_and_first_line(f)
                    else:
                        import io  # noqa: PLC0415

                        obj = get_header_and_first_line(io.StringIO(input_text))
                elif input_file_type == InputFileType.Yaml:
                    if isinstance(input_, Path):
                        obj = load_yaml_dict(input_.read_text(encoding=encoding))
                    else:  # pragma: no cover
                        assert input_text is not None
                        obj = load_yaml_dict(input_text)
                elif input_file_type == InputFileType.Json:
                    if isinstance(input_, Path):
                        obj = json.loads(input_.read_text(encoding=encoding))
                    else:
                        assert input_text is not None
                        obj = json.loads(input_text)
                elif input_file_type == InputFileType.Dict:
                    import ast  # noqa: PLC0415

                    # Input can be a dict object stored in a python file
                    obj = (
                        ast.literal_eval(input_.read_text(encoding=encoding))
                        if isinstance(input_, Path)
                        else cast("dict[str, Any]", input_)
                    )
                else:  # pragma: no cover
                    msg = f"Unsupported input file type: {input_file_type}"
                    raise Error(msg)  # noqa: TRY301
            except Exception as exc:
                msg = "Invalid file format"
                raise Error(msg) from exc

            from genson import SchemaBuilder  # noqa: PLC0415

            builder = SchemaBuilder()
            builder.add_object(obj)
            input_text = json.dumps(builder.to_schema())

    if isinstance(input_, ParseResult) and input_file_type not in RAW_DATA_TYPES:
        input_text = None

    if union_mode is not None:
        if output_model_type == DataModelType.PydanticV2BaseModel:
            default_field_extras = {"union_mode": union_mode}
        else:  # pragma: no cover
            msg = "union_mode is only supported for pydantic_v2.BaseModel"
            raise Error(msg)
    else:
        default_field_extras = None

    from datamodel_code_generator.model import get_data_model_types  # noqa: PLC0415

    data_model_types = get_data_model_types(output_model_type, target_python_version, use_type_alias=use_type_alias)

    # Add GraphQL-specific model types if needed
    if input_file_type == InputFileType.GraphQL:
        kwargs["data_model_scalar_type"] = data_model_types.scalar_model
        kwargs["data_model_union_type"] = data_model_types.union_model

    source = input_text or input_
    assert not isinstance(source, Mapping)
    parser = parser_class(
        source=source,
        data_model_type=data_model_types.data_model,
        data_model_root_type=data_model_types.root_model,
        data_model_field_type=data_model_types.field_model,
        data_type_manager_type=data_model_types.data_type_manager,
        base_class=base_class,
        additional_imports=additional_imports,
        custom_template_dir=custom_template_dir,
        extra_template_data=extra_template_data,
        target_python_version=target_python_version,
        dump_resolve_reference_action=data_model_types.dump_resolve_reference_action,
        validation=validation,
        field_constraints=field_constraints,
        snake_case_field=snake_case_field,
        strip_default_none=strip_default_none,
        aliases=aliases,
        allow_population_by_field_name=allow_population_by_field_name,
        allow_extra_fields=allow_extra_fields,
        extra_fields=extra_fields,
        apply_default_values_for_required_fields=apply_default_values_for_required_fields,
        force_optional_for_required_fields=force_optional_for_required_fields,
        class_name=class_name,
        use_standard_collections=use_standard_collections,
        base_path=input_.parent if isinstance(input_, Path) and input_.is_file() else None,
        use_schema_description=use_schema_description,
        use_field_description=use_field_description,
        use_attribute_docstrings=use_attribute_docstrings,
        use_inline_field_description=use_inline_field_description,
        use_default_kwarg=use_default_kwarg,
        reuse_model=reuse_model,
        reuse_scope=reuse_scope,
        shared_module_name=shared_module_name,
        enum_field_as_literal=LiteralType.All
        if output_model_type == DataModelType.TypingTypedDict
        else enum_field_as_literal,
        use_one_literal_as_default=use_one_literal_as_default,
        use_enum_values_in_discriminator=use_enum_values_in_discriminator,
        set_default_enum_member=True
        if output_model_type == DataModelType.DataclassesDataclass
        else set_default_enum_member,
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
        wrap_string_literal=wrap_string_literal,
        use_title_as_name=use_title_as_name,
        use_operation_id_as_name=use_operation_id_as_name,
        use_unique_items_as_set=use_unique_items_as_set,
        allof_merge_mode=allof_merge_mode,
        http_headers=http_headers,
        http_ignore_tls=http_ignore_tls,
        use_annotated=use_annotated,
        use_serialize_as_any=use_serialize_as_any,
        use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
        use_decimal_for_multiple_of=use_decimal_for_multiple_of,
        original_field_name_delimiter=original_field_name_delimiter,
        use_double_quotes=use_double_quotes,
        use_union_operator=use_union_operator,
        collapse_root_models=collapse_root_models,
        skip_root_model=skip_root_model,
        use_type_alias=use_type_alias,
        special_field_name_prefix=special_field_name_prefix,
        remove_special_field_name_prefix=remove_special_field_name_prefix,
        capitalise_enum_members=capitalise_enum_members,
        keep_model_order=keep_model_order,
        known_third_party=data_model_types.known_third_party,
        custom_formatters=custom_formatters,
        custom_formatters_kwargs=custom_formatters_kwargs,
        use_pendulum=use_pendulum,
        http_query_parameters=http_query_parameters,
        treat_dot_as_module=treat_dot_as_module,
        use_exact_imports=use_exact_imports,
        default_field_extras=default_field_extras,
        target_datetime_class=output_datetime_class,
        keyword_only=keyword_only,
        frozen_dataclasses=frozen_dataclasses,
        no_alias=no_alias,
        use_frozen_field=use_frozen_field,
        formatters=formatters,
        encoding=encoding,
        parent_scoped_naming=parent_scoped_naming,
        dataclass_arguments=dataclass_arguments,
        type_mappings=type_mappings,
        read_only_write_only_model_type=read_only_write_only_model_type,
        **kwargs,
    )

    with chdir(output):
        results = parser.parse(
            settings_path=settings_path,
            disable_future_imports=disable_future_imports,
            all_exports_scope=all_exports_scope,
            all_exports_collision_strategy=all_exports_collision_strategy,
            module_split_mode=module_split_mode,
        )
    if not input_filename:  # pragma: no cover
        if isinstance(input_, str):
            input_filename = "<stdin>"
        elif isinstance(input_, ParseResult):
            input_filename = input_.geturl()
        elif input_file_type == InputFileType.Dict:
            # input_ might be a dict object provided directly, and missing a name field
            input_filename = getattr(input_, "name", "<dict>")
        else:
            assert isinstance(input_, Path)
            input_filename = input_.name
    if not results:
        msg = "Models not found in the input data"
        raise Error(msg)
    if isinstance(results, str):
        # Single-file output: body already contains future imports
        # Only store future_imports separately if we have a non-empty custom_file_header
        body = results
        future_imports = ""
        modules: dict[Path | None, tuple[str, str, str | None]] = {output: (body, future_imports, input_filename)}
    else:
        if output is None:
            msg = "Modular references require an output directory"
            raise Error(msg)
        if output.suffix:
            msg = "Modular references require an output directory, not a file"
            raise Error(msg)
        modules = {
            output.joinpath(*name): (
                result.body,
                result.future_imports,
                str(result.source.as_posix() if result.source else input_filename),
            )
            for name, result in sorted(results.items())
        }

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if custom_file_header is None and custom_file_header_path:
        custom_file_header = custom_file_header_path.read_text(encoding=encoding)

    header = """\
# generated by datamodel-codegen:
#   filename:  {}"""
    if not disable_timestamp:
        header += f"\n#   timestamp: {timestamp}"
    if enable_version_header:
        header += f"\n#   version:   {get_version()}"
    if enable_command_header and command_line:
        safe_command_line = command_line.replace("\n", " ").replace("\r", " ")
        header += f"\n#   command:   {safe_command_line}"

    file: IO[Any] | None
    for path, (body, future_imports, filename) in modules.items():
        if path is None:
            file = None
        else:
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
            file = path.open("wt", encoding=encoding)

        safe_filename = filename.replace("\n", " ").replace("\r", " ") if filename else ""
        effective_header = custom_file_header or header.format(safe_filename)

        if custom_file_header and body:
            # Extract future imports from body for correct placement after custom_file_header
            body_without_future = body
            extracted_future = future_imports  # Use pre-extracted if available
            lines = body.split("\n")
            future_indices = [i for i, line in enumerate(lines) if line.strip().startswith("from __future__")]
            if future_indices:
                if not extracted_future:
                    # Extract future imports from body
                    extracted_future = "\n".join(lines[i] for i in future_indices)
                remaining_lines = [line for i, line in enumerate(lines) if i not in future_indices]
                body_without_future = "\n".join(remaining_lines).lstrip("\n")

            if extracted_future:
                insertion_point = _find_future_import_insertion_point(custom_file_header)
                header_before = custom_file_header[:insertion_point].rstrip()
                header_after = custom_file_header[insertion_point:].strip()
                if header_after:
                    content = header_before + "\n" + extracted_future + "\n\n" + header_after
                else:
                    content = header_before + "\n\n" + extracted_future
                print(content, file=file)
                print(file=file)
                print(body_without_future.rstrip(), file=file)
            else:
                print(effective_header, file=file)
                print(file=file)
                print(body.rstrip(), file=file)
        else:
            # Body already contains future imports, just print as-is
            print(effective_header, file=file)
            if body:
                print(file=file)
                print(body.rstrip(), file=file)

        if file is not None:
            file.close()


def infer_input_type(text: str) -> InputFileType:
    """Automatically detect the input file type from text content."""
    try:
        data = load_yaml(text)
    except yaml.parser.ParserError:
        return InputFileType.CSV
    if isinstance(data, dict):
        if is_openapi(data):
            return InputFileType.OpenAPI
        if is_schema(data):
            return InputFileType.JsonSchema
        return InputFileType.Json
    msg = (
        "Can't infer input file type from the input data. "
        "Please specify the input file type explicitly with --input-file-type option."
    )
    raise Error(msg)


inferred_message = (
    "The input file type was determined to be: {}\nThis can be specified explicitly with the "
    "`--input-file-type` option."
)

__all__ = [
    "MAX_VERSION",
    "MIN_VERSION",
    "AllExportsCollisionStrategy",
    "AllExportsScope",
    "DatetimeClassType",
    "DefaultPutDict",
    "Error",
    "InputFileType",
    "InvalidClassNameError",
    "LiteralType",
    "ModuleSplitMode",
    "PythonVersion",
    "ReadOnlyWriteOnlyModelType",
    "generate",
]
