"""Main module for datamodel-code-generator.

Provides the main `generate()` function and related enums/exceptions for generating
Python data models (Pydantic, dataclasses, TypedDict, msgspec) from various schema formats.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime, timezone
from functools import lru_cache as _lru_cache
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    TextIO,
    TypeAlias,
    TypeVar,
    cast,
)
from urllib.parse import ParseResult

from typing_extensions import TypeAliasType

from datamodel_code_generator.enums import (
    DEFAULT_SHARED_MODULE_NAME,
    MAX_VERSION,
    MIN_VERSION,
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
    CodeFormatter,
    DateClassType,
    DatetimeClassType,
    Formatter,
    PythonVersion,
    PythonVersionMin,
)
from datamodel_code_generator.parser import DefaultPutDict, LiteralType

if TYPE_CHECKING:
    from collections import defaultdict

    from datamodel_code_generator.model.pydantic_v2 import UnionMode
    from datamodel_code_generator.parser.base import Parser
    from datamodel_code_generator.types import StrictTypes

    YamlScalar: TypeAlias = str | int | float | bool | None
    YamlValue = TypeAliasType("YamlValue", "dict[str, YamlValue] | list[YamlValue] | YamlScalar")

T = TypeVar("T")

# Import is_pydantic_v2 here for module-level YamlValue type definition
from datamodel_code_generator.util import is_pydantic_v2  # noqa: E402

if not TYPE_CHECKING:  # pragma: no branch
    YamlScalar: TypeAlias = str | int | float | bool | None
    if is_pydantic_v2():
        YamlValue = TypeAliasType("YamlValue", "dict[str, YamlValue] | list[YamlValue] | YamlScalar")
    else:
        # Pydantic v1 cannot handle TypeAliasType, use Any for recursive parts
        YamlValue: TypeAlias = dict[str, Any] | list[Any] | YamlScalar


GeneratedModules: TypeAlias = dict[tuple[str, ...], str]
"""Type alias for multiple generated modules.

Maps module path tuples (e.g., ("models", "user.py")) to generated code strings.
Returned by generate() when output=None and multiple modules are generated.
"""

DEFAULT_BASE_CLASS: str = "pydantic.BaseModel"


def load_yaml(stream: str | TextIO) -> YamlValue:
    """Load YAML content from a string or file-like object."""
    import yaml  # noqa: PLC0415

    from datamodel_code_generator.util import SafeLoader  # noqa: PLC0415

    return yaml.load(stream, Loader=SafeLoader)  # noqa: S506


def load_yaml_dict(stream: str | TextIO) -> dict[str, YamlValue]:
    """Load YAML and return as dict. Raises TypeError if result is not a dict."""
    result = load_yaml(stream)
    if not isinstance(result, dict):
        msg = f"Expected dict, got {type(result).__name__}"
        raise TypeError(msg)
    return result


def load_yaml_dict_from_path(path: Path, encoding: str) -> dict[str, YamlValue]:
    """Load YAML and return as dict from a file path.

    Uses LRU cache with (path, mtime) as key for performance optimization.
    This avoids re-reading the same file multiple times during $ref resolution.
    """
    return _load_yaml_dict_from_path_cached(path, path.stat().st_mtime, encoding)


@_lru_cache(maxsize=128)
def _load_yaml_dict_from_path_cached(
    path: Path,
    mtime: float,  # noqa: ARG001  # Used as cache key for invalidation
    encoding: str,
) -> dict[str, YamlValue]:
    """Load YAML dict from path with caching (internal implementation)."""
    with path.open(encoding=encoding) as f:
        return load_yaml_dict(f)


def _is_json_text(text: str) -> bool:
    """Check if text likely contains JSON by examining the first non-whitespace character.

    Skips BOM, spaces, tabs, carriage returns, and newlines.
    Returns True if the first significant character is '{' or '['.
    """
    for ch in text:
        if ch in {"\ufeff", " ", "\t", "\r", "\n"}:
            continue
        return ch in {"{", "["}
    return False


def load_data(text: str) -> dict[str, YamlValue]:
    """Load text as JSON or YAML based on content.

    For stdin/string input: tries JSON first if content looks like JSON,
    falls back to YAML on failure.
    """
    import json  # noqa: PLC0415

    if _is_json_text(text):
        with contextlib.suppress(json.JSONDecodeError):
            result = json.loads(text)
            if isinstance(result, dict):
                return result
    return load_yaml_dict(text)


def load_data_from_path(path: Path, encoding: str) -> dict[str, YamlValue]:
    """Load file as JSON or YAML based on file extension.

    For file input: tries json.load() for .json files (more efficient than
    read_text + json.loads), falls back to YAML if JSON parsing fails
    (e.g., trailing commas) or if content is not a dict. Uses YAML for all other extensions.
    """
    import json  # noqa: PLC0415

    if path.suffix.lower() == ".json":
        with contextlib.suppress(json.JSONDecodeError), path.open(encoding=encoding) as f:
            result = json.load(f)
            if isinstance(result, dict):
                return result
    return load_yaml_dict_from_path(path, encoding)


@_lru_cache(maxsize=256)
def cached_path_exists(path: Path) -> bool:
    """Check if a path exists with LRU caching.

    Caches the result of Path.exists() to reduce filesystem I/O
    when checking the same path multiple times (e.g., custom template directories).

    Note: This cache is safe for CLI usage where files don't change during execution.
    """
    return path.exists()


def get_version() -> str:
    """Return the installed package version."""
    package = "datamodel-code-generator"

    from importlib.metadata import version  # noqa: PLC0415

    return version(package)


def enable_debug_message() -> None:  # pragma: no cover
    """Enable debug tracing with pysnooper."""
    global _pysnooper_default_state_set  # noqa: PLW0603
    try:
        import pysnooper  # noqa: PLC0415

        pysnooper.tracer.DISABLED = False
        _pysnooper_default_state_set = True
    except ImportError as err:
        msg = "Please run `$pip install 'datamodel-code-generator[debug]'` to use debug option"
        raise Exception(msg) from err  # noqa: TRY002


DEFAULT_MAX_VARIABLE_LENGTH: int = 100


_pysnooper_default_state_set: bool = False


def snooper_to_methods() -> Callable[..., Any]:
    """Class decorator to add pysnooper tracing to all methods."""

    def inner(cls: type[T]) -> type[T]:
        global _pysnooper_default_state_set  # noqa: PLW0603
        try:
            import pysnooper  # noqa: PLC0415
        except ImportError:
            return cls

        # Ensure tracing is disabled by default (only enabled via --debug flag)
        if not _pysnooper_default_state_set:
            pysnooper.tracer.DISABLED = True
            _pysnooper_default_state_set = True

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


RAW_DATA_TYPES: list[InputFileType] = [
    InputFileType.Json,
    InputFileType.Yaml,
    InputFileType.Dict,
    InputFileType.CSV,
    InputFileType.GraphQL,
]


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


class InvalidFileFormatError(Error):
    """Raised when the input file format is invalid or cannot be parsed."""

    def __init__(
        self,
        original_error: Exception,
        input_file_type: InputFileType | None = None,
    ) -> None:
        """Initialize with original error and optional input file type."""
        self.original_error = original_error
        self.input_file_type = input_file_type
        error_detail = f"{type(original_error).__name__}: {original_error}"
        if input_file_type is not None:
            message = f"Invalid file format for {input_file_type.value}: {error_detail}"
        else:
            message = f"Invalid file format: {error_detail}"
        super().__init__(message=message)


class SchemaParseError(Error):
    """Raised when an error occurs during schema parsing with path context."""

    def __init__(
        self,
        message: str,
        path: list[str] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize with message, schema path, and optional original error."""
        self.path = path or []
        self.original_error = original_error
        full_message = self._format_message(message)
        super().__init__(message=full_message)

    def _format_message(self, message: str) -> str:
        """Format message with schema path context."""
        if self.path:
            path_str = "/".join(self.path)
            return f"Error at schema path '{path_str}': {message}"
        return message


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


def _build_module_content(
    body: str,
    header: str,
    custom_file_header: str | None,
) -> str:
    """Build module content by combining header and body.

    Handles future imports extraction and placement when custom_file_header is provided.
    """
    lines: list[str] = []

    if custom_file_header and body:
        # Extract future imports from body for correct placement after custom_file_header
        body_without_future = body
        extracted_future = ""
        body_lines = body.split("\n")
        future_indices = [i for i, line in enumerate(body_lines) if line.strip().startswith("from __future__")]
        if future_indices:
            extracted_future = "\n".join(body_lines[i] for i in future_indices)
            remaining_lines = [line for i, line in enumerate(body_lines) if i not in future_indices]
            body_without_future = "\n".join(remaining_lines).lstrip("\n")

        if extracted_future:
            insertion_point = _find_future_import_insertion_point(custom_file_header)
            header_before = custom_file_header[:insertion_point].rstrip()
            header_after = custom_file_header[insertion_point:].strip()
            if header_after:
                content = header_before + "\n" + extracted_future + "\n\n" + header_after
            else:
                content = header_before + "\n\n" + extracted_future
            lines.extend((content, "", body_without_future.rstrip()))
        else:
            lines.extend((custom_file_header, "", body.rstrip()))
    else:
        lines.append(header)
        if body:
            lines.extend(("", body.rstrip()))

    return "\n".join(lines)


def generate(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915
    input_: Path | str | ParseResult | Mapping[str, Any],
    *,
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
    graphql_scopes: list[GraphQLScope] | None = None,  # noqa: ARG001
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
) -> str | GeneratedModules | None:
    """Generate Python data models from schema definitions or structured data.

    This is the main entry point for code generation. Supports OpenAPI, JSON Schema,
    GraphQL, and raw data formats (JSON, YAML, Dict, CSV) as input.

    Returns:
        - When output is a Path: None (writes to file system)
        - When output is None and single module: str (generated code)
        - When output is None and multiple modules: GeneratedModules (dict mapping
          module path tuples to generated code strings)
    """
    remote_text_cache: DefaultPutDict[str, str] = DefaultPutDict()
    match input_:
        case str():
            input_text: str | None = input_
        case ParseResult():
            from datamodel_code_generator.http import DEFAULT_HTTP_TIMEOUT, get_body  # noqa: PLC0415

            timeout = http_timeout if http_timeout is not None else DEFAULT_HTTP_TIMEOUT
            input_text = remote_text_cache.get_or_put(
                input_.geturl(),
                default_factory=lambda url: get_body(
                    url, http_headers, http_ignore_tls, http_query_parameters, timeout
                ),
            )
        case _:
            input_text = None

    if dataclass_arguments is None:
        dataclass_arguments = {}
        if frozen_dataclasses:
            dataclass_arguments["frozen"] = True
        if keyword_only:
            dataclass_arguments["kw_only"] = True

    if isinstance(input_, Path) and not input_.is_absolute():
        input_ = input_.expanduser().resolve()
    if input_file_type == InputFileType.Auto and isinstance(input_, Mapping):
        msg = (
            "input_file_type=Auto is not supported for dict input. "
            "Please specify input_file_type explicitly (e.g., InputFileType.JsonSchema)."
        )
        raise Error(msg)

    if isinstance(input_, Mapping) and input_file_type == InputFileType.GraphQL:
        msg = "Dict input is not supported for GraphQL. GraphQL requires text input (SDL format)."
        raise Error(msg)

    if isinstance(input_, Mapping) and input_file_type in {
        InputFileType.Json,
        InputFileType.Yaml,
        InputFileType.CSV,
    }:
        msg = (
            f"Dict input is not supported for {input_file_type.value}. "
            f"Use InputFileType.Dict to generate schema from dict data, "
            f"or provide text/file input for {input_file_type.value} format."
        )
        raise Error(msg)

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
            raise InvalidFileFormatError(exc) from exc
        else:
            print(  # noqa: T201
                inferred_message.format(input_file_type.value),
                file=sys.stderr,
            )
            # Reuse already-read text for single Path file to avoid re-reading
            # Only for OpenAPI/JsonSchema (RAW_DATA_TYPES are transformed by genson)
            if isinstance(input_, Path) and input_.is_file() and input_file_type not in RAW_DATA_TYPES:
                input_text = input_text_

    kwargs: dict[str, Any] = {}
    if input_file_type == InputFileType.OpenAPI:  # noqa: PLR1702
        from datamodel_code_generator.parser.openapi import OpenAPIParser  # noqa: PLC0415

        parser_class: type[Parser] = OpenAPIParser
        kwargs["openapi_scopes"] = openapi_scopes
        kwargs["include_path_parameters"] = include_path_parameters
        kwargs["use_status_code_in_response_name"] = use_status_code_in_response_name
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
                        return dict(zip(csv_reader.fieldnames, next(csv_reader), strict=False))

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
            except Error:
                raise
            except Exception as exc:
                raise InvalidFileFormatError(exc, input_file_type) from exc

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

    data_model_types = get_data_model_types(
        output_model_type,
        target_python_version,
        use_type_alias=use_type_alias,
        use_root_model_type_alias=use_root_model_type_alias,
    )

    # Add GraphQL-specific model types if needed
    if input_file_type == InputFileType.GraphQL:
        kwargs["data_model_scalar_type"] = data_model_types.scalar_model
        kwargs["data_model_union_type"] = data_model_types.union_model

    if isinstance(input_, Mapping) and input_file_type not in RAW_DATA_TYPES:
        source = dict(input_)
    else:
        source = input_text or input_
        assert not isinstance(source, Mapping)

    defer_formatting = output is not None and not output.suffix

    parser = parser_class(
        source=source,
        data_model_type=data_model_types.data_model,
        data_model_root_type=data_model_types.root_model,
        data_model_field_type=data_model_types.field_model,
        data_type_manager_type=data_model_types.data_type_manager,
        base_class=base_class,
        base_class_map=base_class_map,
        additional_imports=additional_imports,
        class_decorators=class_decorators,
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
        use_generic_base_class=use_generic_base_class,
        apply_default_values_for_required_fields=apply_default_values_for_required_fields,
        force_optional_for_required_fields=force_optional_for_required_fields,
        class_name=class_name,
        use_standard_collections=use_standard_collections,
        base_path=input_.parent if isinstance(input_, Path) and input_.is_file() else None,
        use_schema_description=use_schema_description,
        use_field_description=use_field_description,
        use_field_description_example=use_field_description_example,
        use_attribute_docstrings=use_attribute_docstrings,
        use_inline_field_description=use_inline_field_description,
        use_default_kwarg=use_default_kwarg,
        reuse_model=reuse_model,
        reuse_scope=reuse_scope,
        shared_module_name=shared_module_name,
        enum_field_as_literal=enum_field_as_literal
        if enum_field_as_literal is not None
        else (LiteralType.All if output_model_type == DataModelType.TypingTypedDict else None),
        enum_field_as_literal_map=enum_field_as_literal_map,
        ignore_enum_constraints=ignore_enum_constraints,
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
        collapse_root_models=collapse_root_models,
        collapse_root_models_name_strategy=collapse_root_models_name_strategy,
        collapse_reuse_models=collapse_reuse_models,
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
        use_standard_primitive_types=use_standard_primitive_types,
        http_query_parameters=http_query_parameters,
        treat_dot_as_module=treat_dot_as_module,
        use_exact_imports=use_exact_imports,
        default_field_extras=default_field_extras,
        target_datetime_class=output_datetime_class,
        target_date_class=output_date_class,
        keyword_only=keyword_only,
        frozen_dataclasses=frozen_dataclasses,
        no_alias=no_alias,
        use_frozen_field=use_frozen_field,
        use_default_factory_for_optional_nested_models=use_default_factory_for_optional_nested_models,
        formatters=formatters,
        defer_formatting=defer_formatting,
        encoding=encoding,
        parent_scoped_naming=parent_scoped_naming,
        naming_strategy=naming_strategy,
        duplicate_name_suffix=duplicate_name_suffix,
        dataclass_arguments=dataclass_arguments,
        type_mappings=type_mappings,
        type_overrides=type_overrides,
        read_only_write_only_model_type=read_only_write_only_model_type,
        field_type_collision_strategy=field_type_collision_strategy,
        target_pydantic_version=target_pydantic_version,
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
        match input_:
            case str():
                input_filename = "<stdin>"
            case ParseResult():
                input_filename = input_.geturl()
            case Path():
                input_filename = input_.name
            case _:
                # input_ might be a dict object provided directly, and missing a name field
                input_filename = getattr(input_, "name", "<dict>")
    if not results:
        msg = "Models not found in the input data"
        raise Error(msg)
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

    # When output is None, return generated code as string(s) instead of writing to files
    if output is None:
        if isinstance(results, str):
            # Single-file output: return str
            safe_filename = input_filename.replace("\n", " ").replace("\r", " ") if input_filename else ""
            effective_header = custom_file_header or header.format(safe_filename)
            return _build_module_content(results, effective_header, custom_file_header)
        # Multiple modules: return GeneratedModules dict
        generated: GeneratedModules = {}
        for name, result in sorted(results.items()):
            source_filename = str(result.source.as_posix() if result.source else input_filename)
            safe_filename = source_filename.replace("\n", " ").replace("\r", " ") if source_filename else ""
            effective_header = custom_file_header or header.format(safe_filename)
            generated[name] = _build_module_content(result.body, effective_header, custom_file_header)
        return generated

    # When output is a Path, write to file system
    if isinstance(results, str):
        # Single-file output: body already contains future imports
        body = results
        future_imports = ""
        modules: dict[Path, tuple[str, str, str | None]] = {output: (body, future_imports, input_filename)}
    else:
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

    file: IO[Any] | None
    for path, (body, future_imports, filename) in modules.items():
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

        file.close()

    if defer_formatting and (Formatter.RUFF_CHECK in formatters or Formatter.RUFF_FORMAT in formatters):
        code_formatter = CodeFormatter(
            target_python_version,
            settings_path,
            wrap_string_literal,
            skip_string_normalization=not use_double_quotes,
            known_third_party=data_model_types.known_third_party,
            custom_formatters=custom_formatters,
            custom_formatters_kwargs=custom_formatters_kwargs,
            encoding=encoding,
            formatters=formatters,
        )
        code_formatter.format_directory(output)

    return None


def infer_input_type(text: str) -> InputFileType:
    """Automatically detect the input file type from text content."""
    import yaml.parser  # noqa: PLC0415

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
    "DateClassType",
    "DatetimeClassType",
    "DefaultPutDict",
    "Error",
    "GeneratedModules",
    "InputFileType",
    "InvalidClassNameError",
    "InvalidFileFormatError",
    "LiteralType",
    "ModuleSplitMode",
    "NamingStrategy",
    "PythonVersion",
    "ReadOnlyWriteOnlyModelType",
    "SchemaParseError",
    "TargetPydanticVersion",
    "generate",
]
