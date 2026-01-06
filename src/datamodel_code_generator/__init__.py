"""Main module for datamodel-code-generator.

Provides the main `generate()` function and related enums/exceptions for generating
Python data models (Pydantic, dataclasses, TypedDict, msgspec) from various schema formats.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping
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

from typing_extensions import TypeAliasType, Unpack

from datamodel_code_generator.enums import (
    DEFAULT_SHARED_MODULE_NAME,
    MAX_VERSION,
    MIN_VERSION,
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
    InputModelRefStrategy,
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
    from datamodel_code_generator._types import (
        GraphQLParserConfigDict,
        JSONSchemaParserConfigDict,
        OpenAPIParserConfigDict,
        ParserConfigDict,
    )
    from datamodel_code_generator._types.generate_config_dict import GenerateConfigDict
    from datamodel_code_generator.config import GenerateConfig, ParserConfig

    YamlScalar: TypeAlias = str | int | float | bool | None
    YamlValue = TypeAliasType("YamlValue", "dict[str, YamlValue] | list[YamlValue] | YamlScalar")

T = TypeVar("T")
_ConfigT = TypeVar("_ConfigT", bound="ParserConfig")

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


def is_openapi(data: Mapping[str, Any]) -> bool:
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


def _create_parser_config(
    config_class: type[_ConfigT],
    generate_config: GenerateConfig,
    additional_options: ParserConfigDict
    | JSONSchemaParserConfigDict
    | OpenAPIParserConfigDict
    | GraphQLParserConfigDict,
) -> _ConfigT:
    """Create a parser config from GenerateConfig with additional options.

    Filters GenerateConfig fields to only those expected by the parser config class,
    then merges with additional_options.
    """
    if is_pydantic_v2():
        parser_config_fields = set(config_class.model_fields.keys())
        all_options = {
            k: v
            for k, v in generate_config.model_dump().items()
            if k in parser_config_fields and k not in additional_options
        } | dict(additional_options)
        return config_class.model_validate(all_options)
    parser_config_fields = set(config_class.__fields__.keys())
    all_options = {
        k: v for k, v in generate_config.dict().items() if k in parser_config_fields and k not in additional_options
    } | dict(additional_options)
    return config_class.parse_obj(all_options)


def generate(  # noqa: PLR0912, PLR0914, PLR0915
    input_: Path | str | ParseResult | Mapping[str, Any],
    *,
    config: GenerateConfig | None = None,
    **options: Unpack[GenerateConfigDict],
) -> str | GeneratedModules | None:
    """Generate Python data models from schema definitions or structured data.

    This is the main entry point for code generation. Supports OpenAPI, JSON Schema,
    GraphQL, and raw data formats (JSON, YAML, Dict, CSV) as input.

    Args:
        input_: The input source (file path, string content, URL, or dict).
        config: A GenerateConfig object with all options. Cannot be used together with **options.
        **options: Individual options matching GenerateConfig fields. Cannot be used together with config.

    Returns:
        - When output is a Path: None (writes to file system)
        - When output is None and single module: str (generated code)
        - When output is None and multiple modules: GeneratedModules (dict mapping
          module path tuples to generated code strings)

    Raises:
        ValueError: If both config and **options are provided.
    """
    from datamodel_code_generator.config import GenerateConfig  # noqa: PLC0415

    if config is not None and options:
        msg = "Cannot specify both 'config' and keyword arguments. Use one or the other."
        raise ValueError(msg)

    if config is None:
        if is_pydantic_v2():
            from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: PLC0415
            from datamodel_code_generator.types import StrictTypes  # noqa: PLC0415

            GenerateConfig.model_rebuild(_types_namespace={"StrictTypes": StrictTypes, "UnionMode": UnionMode})
            config = GenerateConfig.model_validate(options)
        else:
            from datamodel_code_generator.enums import UnionMode  # noqa: PLC0415
            from datamodel_code_generator.types import StrictTypes  # noqa: PLC0415

            GenerateConfig.update_forward_refs(StrictTypes=StrictTypes, UnionMode=UnionMode)
            config = GenerateConfig(**options)

    # Variables that may be modified during processing
    input_filename = config.input_filename
    input_file_type = config.input_file_type
    extra_template_data: defaultdict[str, dict[str, Any]] | None = None
    if config.extra_template_data is not None:
        extra_template_data = defaultdict(dict, config.extra_template_data)
    dataclass_arguments = config.dataclass_arguments
    custom_file_header = config.custom_file_header

    remote_text_cache: DefaultPutDict[str, str] = DefaultPutDict()
    match input_:
        case str():
            input_text: str | None = input_
        case ParseResult():
            from datamodel_code_generator.http import DEFAULT_HTTP_TIMEOUT, get_body  # noqa: PLC0415

            timeout = config.http_timeout if config.http_timeout is not None else DEFAULT_HTTP_TIMEOUT
            input_text = remote_text_cache.get_or_put(
                input_.geturl(),
                default_factory=lambda url: get_body(
                    url,
                    config.http_headers,
                    config.http_ignore_tls,
                    config.http_query_parameters,
                    timeout,
                ),
            )
        case _:
            input_text = None

    if dataclass_arguments is None:
        dataclass_arguments = DataclassArguments()
        if config.frozen_dataclasses:
            dataclass_arguments["frozen"] = True
        if config.keyword_only:
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
            if isinstance(input_, Path):
                input_text_ = get_first_file(input_).read_text(encoding=config.encoding)
            else:
                input_text_ = input_text
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

    if input_file_type not in {InputFileType.OpenAPI, InputFileType.GraphQL} and input_file_type in RAW_DATA_TYPES:
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
                    with input_.open(encoding=config.encoding) as f:
                        obj = get_header_and_first_line(f)
                else:
                    import io  # noqa: PLC0415

                    obj = get_header_and_first_line(io.StringIO(input_text))
            elif input_file_type == InputFileType.Yaml:
                if isinstance(input_, Path):
                    obj = load_yaml_dict(input_.read_text(encoding=config.encoding))
                else:  # pragma: no cover
                    assert input_text is not None
                    obj = load_yaml_dict(input_text)
            elif input_file_type == InputFileType.Json:
                if isinstance(input_, Path):
                    obj = json.loads(input_.read_text(encoding=config.encoding))
                else:
                    assert input_text is not None
                    obj = json.loads(input_text)
            elif input_file_type == InputFileType.Dict:
                import ast  # noqa: PLC0415

                obj = (
                    ast.literal_eval(input_.read_text(encoding=config.encoding))
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

    if config.union_mode is not None:
        if config.output_model_type == DataModelType.PydanticV2BaseModel:
            default_field_extras = {"union_mode": config.union_mode}
        else:  # pragma: no cover
            msg = "union_mode is only supported for pydantic_v2.BaseModel"
            raise Error(msg)
    else:
        default_field_extras = None

    from datamodel_code_generator.model import get_data_model_types  # noqa: PLC0415

    data_model_types = get_data_model_types(
        config.output_model_type,
        config.target_python_version,
        use_type_alias=config.use_type_alias,
        use_root_model_type_alias=config.use_root_model_type_alias,
    )

    if isinstance(input_, Mapping) and input_file_type not in RAW_DATA_TYPES:
        source = dict(input_)
    else:
        source = input_text or input_
        assert not isinstance(source, Mapping)

    defer_formatting = config.output is not None and not config.output.suffix

    from datamodel_code_generator.config import (  # noqa: PLC0415
        GraphQLParserConfig,
        JSONSchemaParserConfig,
        OpenAPIParserConfig,
    )

    additional_options: ParserConfigDict = {
        "data_model_type": data_model_types.data_model,
        "data_model_root_type": data_model_types.root_model,
        "data_model_field_type": data_model_types.field_model,
        "data_type_manager_type": data_model_types.data_type_manager,
        "dump_resolve_reference_action": data_model_types.dump_resolve_reference_action,
        "extra_template_data": extra_template_data,
        "base_path": input_.parent if isinstance(input_, Path) and input_.is_file() else None,
        "remote_text_cache": remote_text_cache,
        "known_third_party": data_model_types.known_third_party,
        "default_field_extras": default_field_extras,
        "target_datetime_class": (
            config.output_datetime_class
            if config.output_datetime_class is not None
            else (
                DatetimeClassType.Datetime
                if input_file_type == InputFileType.GraphQL
                else DatetimeClassType.Awaredatetime
            )
        ),
        "target_date_class": config.output_date_class,
        "dataclass_arguments": dataclass_arguments,
        "defer_formatting": defer_formatting,
        "enum_field_as_literal": (
            config.enum_field_as_literal
            if config.enum_field_as_literal is not None
            else (LiteralType.All if config.output_model_type == DataModelType.TypingTypedDict else None)
        ),
        "set_default_enum_member": (
            True if config.output_model_type == DataModelType.DataclassesDataclass else config.set_default_enum_member
        ),
    }

    # Convert schema_version string to appropriate enum based on input type
    jsonschema_version: JsonSchemaVersion | None = None
    openapi_version: OpenAPIVersion | None = None
    if config.schema_version and config.schema_version != "auto":
        if input_file_type == InputFileType.OpenAPI:
            try:
                openapi_version = OpenAPIVersion(config.schema_version)
            except ValueError:
                valid = [v.value for v in OpenAPIVersion]
                msg = f"Invalid OpenAPI version: {config.schema_version}. Valid values: {valid}"
                raise Error(msg) from None
        elif input_file_type == InputFileType.GraphQL:
            msg = f"--schema-version is not supported for {input_file_type.value}"
            raise Error(msg)
        else:
            try:
                jsonschema_version = JsonSchemaVersion(config.schema_version)
            except ValueError:
                valid = [v.value for v in JsonSchemaVersion]
                msg = f"Invalid JSON Schema version: {config.schema_version}. Valid values: {valid}"
                raise Error(msg) from None

    if input_file_type == InputFileType.OpenAPI:
        from datamodel_code_generator.parser.openapi import OpenAPIParser  # noqa: PLC0415

        openapi_additional_options: OpenAPIParserConfigDict = {
            "openapi_scopes": config.openapi_scopes,
            "include_path_parameters": config.include_path_parameters,
            "use_status_code_in_response_name": config.use_status_code_in_response_name,
            "openapi_include_paths": config.openapi_include_paths,
            "openapi_version": openapi_version,
            **additional_options,
        }
        parser_config = _create_parser_config(OpenAPIParserConfig, config, openapi_additional_options)
        parser = OpenAPIParser(source=source, config=parser_config)  # ty: ignore
    elif input_file_type == InputFileType.GraphQL:
        from datamodel_code_generator.parser.graphql import GraphQLParser  # noqa: PLC0415

        graphql_additional_options: GraphQLParserConfigDict = {
            "data_model_scalar_type": data_model_types.scalar_model,
            "data_model_union_type": data_model_types.union_model,
            **additional_options,
        }
        parser_config = _create_parser_config(GraphQLParserConfig, config, graphql_additional_options)
        parser = GraphQLParser(source=source, config=parser_config)  # ty: ignore
    else:
        from datamodel_code_generator.parser.jsonschema import JsonSchemaParser  # noqa: PLC0415

        jsonschema_additional_options: JSONSchemaParserConfigDict = {
            "jsonschema_version": jsonschema_version,
            **additional_options,
        }
        parser_config = _create_parser_config(JSONSchemaParserConfig, config, jsonschema_additional_options)
        parser = JsonSchemaParser(source=source, config=parser_config)  # ty: ignore

    with chdir(config.output):
        results = parser.parse(
            settings_path=config.settings_path,
            disable_future_imports=config.disable_future_imports,
            all_exports_scope=config.all_exports_scope,
            all_exports_collision_strategy=config.all_exports_collision_strategy,
            module_split_mode=config.module_split_mode,
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

    if custom_file_header is None and config.custom_file_header_path:
        custom_file_header = config.custom_file_header_path.read_text(encoding=config.encoding)

    header = """\
# generated by datamodel-codegen:
#   filename:  {}"""
    if not config.disable_timestamp:
        header += f"\n#   timestamp: {timestamp}"
    if config.enable_version_header:
        header += f"\n#   version:   {get_version()}"
    if config.enable_command_header and config.command_line:
        safe_command_line = config.command_line.replace("\n", " ").replace("\r", " ")
        header += f"\n#   command:   {safe_command_line}"

    # When output is None, return generated code as string(s) instead of writing to files
    if config.output is None:
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
    output = config.output
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
        file = path.open("wt", encoding=config.encoding)

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

    if (
        defer_formatting
        and config.formatters
        and (Formatter.RUFF_CHECK in config.formatters or Formatter.RUFF_FORMAT in config.formatters)
    ):
        code_formatter = CodeFormatter(
            config.target_python_version,
            config.settings_path,
            config.wrap_string_literal,
            skip_string_normalization=not config.use_double_quotes,
            known_third_party=data_model_types.known_third_party,
            custom_formatters=config.custom_formatters,
            custom_formatters_kwargs=config.custom_formatters_kwargs,
            encoding=config.encoding,
            formatters=config.formatters,
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


_LAZY_IMPORTS = {
    "clear_dynamic_models_cache": "datamodel_code_generator.dynamic",
    "detect_jsonschema_version": "datamodel_code_generator.parser.schema_version",
    "detect_openapi_version": "datamodel_code_generator.parser.schema_version",
    "generate_dynamic_models": "datamodel_code_generator.dynamic",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib  # noqa: PLC0415

        module = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(module, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "DEFAULT_FORMATTERS",
    "DEFAULT_SHARED_MODULE_NAME",
    "MAX_VERSION",
    "MIN_VERSION",
    "AllExportsCollisionStrategy",
    "AllExportsScope",
    "AllOfClassHierarchy",
    "AllOfMergeMode",
    "ClassNameAffixScope",
    "CollapseRootModelsNameStrategy",
    "DateClassType",
    "DatetimeClassType",
    "DefaultPutDict",
    "Error",
    "FieldTypeCollisionStrategy",
    "GeneratedModules",
    "GraphQLScope",
    "InputFileType",
    "InputModelRefStrategy",
    "InvalidClassNameError",
    "InvalidFileFormatError",
    "JsonSchemaVersion",
    "LiteralType",
    "ModuleSplitMode",
    "NamingStrategy",
    "OpenAPIScope",
    "OpenAPIVersion",
    "PythonVersion",
    "PythonVersionMin",
    "ReadOnlyWriteOnlyModelType",
    "ReuseScope",
    "SchemaParseError",
    "TargetPydanticVersion",
    "VersionMode",
    "clear_dynamic_models_cache",  # noqa: F822
    "detect_jsonschema_version",  # noqa: F822
    "detect_openapi_version",  # noqa: F822
    "generate",
    "generate_dynamic_models",  # noqa: F822
]
