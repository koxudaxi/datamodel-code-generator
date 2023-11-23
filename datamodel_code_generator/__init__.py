from __future__ import annotations

import contextlib
import os
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import ParseResult

import yaml

from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.parser.base import Parser
from datamodel_code_generator.types import StrictTypes
from datamodel_code_generator.util import SafeLoader  # type: ignore

T = TypeVar('T')

try:
    import pysnooper

    pysnooper.tracer.DISABLED = True
except ImportError:  # pragma: no cover
    pysnooper = None

DEFAULT_BASE_CLASS: str = 'pydantic.BaseModel'


def load_yaml(stream: Union[str, TextIO]) -> Any:
    return yaml.load(stream, Loader=SafeLoader)


def load_yaml_from_path(path: Path, encoding: str) -> Any:
    with path.open(encoding=encoding) as f:
        return load_yaml(f)


if TYPE_CHECKING:

    def get_version() -> str:
        ...

else:

    def get_version() -> str:
        package = 'datamodel-code-generator'

        try:
            from importlib.metadata import version

            return version(package)
        except ImportError:
            import pkg_resources

            return pkg_resources.get_distribution(package).version


def enable_debug_message() -> None:  # pragma: no cover
    if not pysnooper:
        raise Exception(
            "Please run `$pip install 'datamodel-code-generator[debug]'` to use debug option"
        )

    pysnooper.tracer.DISABLED = False


def snooper_to_methods(  # type: ignore
    output=None,
    watch=(),
    watch_explode=(),
    depth=1,
    prefix='',
    overwrite=False,
    thread_info=False,
    custom_repr=(),
    max_variable_length=100,
) -> Callable[..., Any]:
    def inner(cls: Type[T]) -> Type[T]:
        if not pysnooper:
            return cls
        import inspect

        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, method in methods:
            snooper_method = pysnooper.snoop(
                output,
                watch,
                watch_explode,
                depth,
                prefix,
                overwrite,
                thread_info,
                custom_repr,
                max_variable_length,
            )(method)
            setattr(cls, name, snooper_method)
        return cls

    return inner


@contextlib.contextmanager
def chdir(path: Optional[Path]) -> Iterator[None]:
    """Changes working directory and returns to previous on exit."""

    if path is None:
        yield
    else:
        prev_cwd = Path.cwd()
        try:
            os.chdir(path if path.is_dir() else path.parent)
            yield
        finally:
            os.chdir(prev_cwd)


def is_openapi(text: str) -> bool:
    return 'openapi' in load_yaml(text)


JSON_SCHEMA_URLS: Tuple[str, ...] = (
    'http://json-schema.org/',
    'https://json-schema.org/',
)


def is_schema(text: str) -> bool:
    data = load_yaml(text)
    if not isinstance(data, dict):
        return False
    schema = data.get('$schema')
    if isinstance(schema, str) and any(
        schema.startswith(u) for u in JSON_SCHEMA_URLS
    ):  # pragma: no cover
        return True
    if isinstance(data.get('type'), str):
        return True
    if any(
        isinstance(data.get(o), list)
        for o in (
            'allOf',
            'anyOf',
            'oneOf',
        )
    ):
        return True
    if isinstance(data.get('properties'), dict):
        return True
    return False


class InputFileType(Enum):
    Auto = 'auto'
    OpenAPI = 'openapi'
    JsonSchema = 'jsonschema'
    Json = 'json'
    Yaml = 'yaml'
    Dict = 'dict'
    CSV = 'csv'
    GraphQL = 'graphql'


RAW_DATA_TYPES: List[InputFileType] = [
    InputFileType.Json,
    InputFileType.Yaml,
    InputFileType.Dict,
    InputFileType.CSV,
    InputFileType.GraphQL,
]


class DataModelType(Enum):
    PydanticBaseModel = 'pydantic.BaseModel'
    PydanticV2BaseModel = 'pydantic_v2.BaseModel'
    DataclassesDataclass = 'dataclasses.dataclass'
    TypingTypedDict = 'typing.TypedDict'
    MsgspecStruct = 'msgspec.Struct'


class OpenAPIScope(Enum):
    Schemas = 'schemas'
    Paths = 'paths'
    Tags = 'tags'
    Parameters = 'parameters'


class GraphQLScope(Enum):
    Schema = 'schema'


class Error(Exception):
    def __init__(self, message: str) -> None:
        self.message: str = message

    def __str__(self) -> str:
        return self.message


class InvalidClassNameError(Error):
    def __init__(self, class_name: str) -> None:
        self.class_name = class_name
        message = f'title={repr(class_name)} is invalid class name.'
        super().__init__(message=message)


def get_first_file(path: Path) -> Path:  # pragma: no cover
    if path.is_file():
        return path
    elif path.is_dir():
        for child in path.rglob('*'):
            if child.is_file():
                return child
    raise Error('File not found')


def generate(
    input_: Union[Path, str, ParseResult],
    *,
    input_filename: Optional[str] = None,
    input_file_type: InputFileType = InputFileType.Auto,
    output: Optional[Path] = None,
    output_model_type: DataModelType = DataModelType.PydanticBaseModel,
    target_python_version: PythonVersion = PythonVersion.PY_37,
    base_class: str = '',
    additional_imports: Optional[List[str]] = None,
    custom_template_dir: Optional[Path] = None,
    extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
    validation: bool = False,
    field_constraints: bool = False,
    snake_case_field: bool = False,
    strip_default_none: bool = False,
    aliases: Optional[Mapping[str, str]] = None,
    disable_timestamp: bool = False,
    enable_version_header: bool = False,
    allow_population_by_field_name: bool = False,
    allow_extra_fields: bool = False,
    apply_default_values_for_required_fields: bool = False,
    force_optional_for_required_fields: bool = False,
    class_name: Optional[str] = None,
    use_standard_collections: bool = False,
    use_schema_description: bool = False,
    use_field_description: bool = False,
    use_default_kwarg: bool = False,
    reuse_model: bool = False,
    encoding: str = 'utf-8',
    enum_field_as_literal: Optional[LiteralType] = None,
    use_one_literal_as_default: bool = False,
    set_default_enum_member: bool = False,
    use_subclass_enum: bool = False,
    strict_nullable: bool = False,
    use_generic_container_types: bool = False,
    enable_faux_immutability: bool = False,
    disable_appending_item_suffix: bool = False,
    strict_types: Optional[Sequence[StrictTypes]] = None,
    empty_enum_field_name: Optional[str] = None,
    custom_class_name_generator: Optional[Callable[[str], str]] = None,
    field_extra_keys: Optional[Set[str]] = None,
    field_include_all_keys: bool = False,
    field_extra_keys_without_x_prefix: Optional[Set[str]] = None,
    openapi_scopes: Optional[List[OpenAPIScope]] = None,
    graphql_scopes: Optional[List[GraphQLScope]] = None,
    wrap_string_literal: Optional[bool] = None,
    use_title_as_name: bool = False,
    use_operation_id_as_name: bool = False,
    use_unique_items_as_set: bool = False,
    http_headers: Optional[Sequence[Tuple[str, str]]] = None,
    http_ignore_tls: bool = False,
    use_annotated: bool = False,
    use_non_positive_negative_number_constrained_types: bool = False,
    original_field_name_delimiter: Optional[str] = None,
    use_double_quotes: bool = False,
    use_union_operator: bool = False,
    collapse_root_models: bool = False,
    special_field_name_prefix: Optional[str] = None,
    remove_special_field_name_prefix: bool = False,
    capitalise_enum_members: bool = False,
    keep_model_order: bool = False,
    custom_file_header: Optional[str] = None,
    custom_file_header_path: Optional[Path] = None,
    custom_formatters: Optional[List[str]] = None,
    custom_formatters_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    remote_text_cache: DefaultPutDict[str, str] = DefaultPutDict()
    if isinstance(input_, str):
        input_text: Optional[str] = input_
    elif isinstance(input_, ParseResult):
        from datamodel_code_generator.http import get_body

        input_text = remote_text_cache.get_or_put(
            input_.geturl(),
            default_factory=lambda url: get_body(url, http_headers, http_ignore_tls),
        )
    else:
        input_text = None

    if isinstance(input_, Path) and not input_.is_absolute():
        input_ = input_.expanduser().resolve()
    if input_file_type == InputFileType.Auto:
        try:
            input_text_ = (
                get_first_file(input_).read_text(encoding=encoding)
                if isinstance(input_, Path)
                else input_text
            )
            assert isinstance(input_text_, str)
            input_file_type = infer_input_type(input_text_)
            print(
                inferred_message.format(input_file_type.value),
                file=sys.stderr,
            )
        except:  # noqa
            raise Error('Invalid file format')

    kwargs: Dict[str, Any] = {}
    if input_file_type == InputFileType.OpenAPI:
        from datamodel_code_generator.parser.openapi import OpenAPIParser

        parser_class: Type[Parser] = OpenAPIParser
        kwargs['openapi_scopes'] = openapi_scopes
    elif input_file_type == InputFileType.GraphQL:
        from datamodel_code_generator.parser.graphql import GraphQLParser

        parser_class: Type[Parser] = GraphQLParser
    else:
        from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

        parser_class = JsonSchemaParser

        if input_file_type in RAW_DATA_TYPES:
            try:
                if isinstance(input_, Path) and input_.is_dir():  # pragma: no cover
                    raise Error(f'Input must be a file for {input_file_type}')
                obj: Dict[Any, Any]
                if input_file_type == InputFileType.CSV:
                    import csv

                    def get_header_and_first_line(csv_file: IO[str]) -> Dict[str, Any]:
                        csv_reader = csv.DictReader(csv_file)
                        return dict(zip(csv_reader.fieldnames, next(csv_reader)))  # type: ignore

                    if isinstance(input_, Path):
                        with input_.open(encoding=encoding) as f:
                            obj = get_header_and_first_line(f)
                    else:
                        import io

                        obj = get_header_and_first_line(io.StringIO(input_text))
                else:
                    obj = load_yaml(
                        input_.read_text(encoding=encoding)  # type: ignore
                        if isinstance(input_, Path)
                        else input_text
                    )
            except:  # noqa
                raise Error('Invalid file format')
            import json

            from genson import SchemaBuilder

            builder = SchemaBuilder()
            builder.add_object(obj)
            input_text = json.dumps(builder.to_schema())

    if isinstance(input_, ParseResult) and input_file_type not in RAW_DATA_TYPES:
        input_text = None

    from datamodel_code_generator.model import get_data_model_types

    data_model_types = get_data_model_types(output_model_type, target_python_version)
    parser = parser_class(
        source=input_text or input_,
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
        apply_default_values_for_required_fields=apply_default_values_for_required_fields,
        force_optional_for_required_fields=force_optional_for_required_fields,
        class_name=class_name,
        use_standard_collections=use_standard_collections,
        base_path=input_.parent
        if isinstance(input_, Path) and input_.is_file()
        else None,
        use_schema_description=use_schema_description,
        use_field_description=use_field_description,
        use_default_kwarg=use_default_kwarg,
        reuse_model=reuse_model,
        enum_field_as_literal=LiteralType.All
        if output_model_type == DataModelType.TypingTypedDict
        else enum_field_as_literal,
        use_one_literal_as_default=use_one_literal_as_default,
        set_default_enum_member=True
        if output_model_type == DataModelType.DataclassesDataclass
        else set_default_enum_member,
        use_subclass_enum=use_subclass_enum,
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
        http_headers=http_headers,
        http_ignore_tls=http_ignore_tls,
        use_annotated=use_annotated,
        use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
        original_field_name_delimiter=original_field_name_delimiter,
        use_double_quotes=use_double_quotes,
        use_union_operator=use_union_operator,
        collapse_root_models=collapse_root_models,
        special_field_name_prefix=special_field_name_prefix,
        remove_special_field_name_prefix=remove_special_field_name_prefix,
        capitalise_enum_members=capitalise_enum_members,
        keep_model_order=keep_model_order,
        known_third_party=data_model_types.known_third_party,
        custom_formatters=custom_formatters,
        custom_formatters_kwargs=custom_formatters_kwargs,
        **kwargs,
    )

    with chdir(output):
        results = parser.parse()
    if not input_filename:  # pragma: no cover
        if isinstance(input_, str):
            input_filename = '<stdin>'
        elif isinstance(input_, ParseResult):
            input_filename = input_.geturl()
        else:
            input_filename = input_.name
    if not results:
        raise Error('Models not found in the input data')
    elif isinstance(results, str):
        modules = {output: (results, input_filename)}
    else:
        if output is None:
            raise Error('Modular references require an output directory')
        if output.suffix:
            raise Error('Modular references require an output directory, not a file')
        modules = {
            output.joinpath(*name): (
                result.body,
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
        header += f'\n#   timestamp: {timestamp}'
    if enable_version_header:
        header += f'\n#   version:   {get_version()}'

    file: Optional[IO[Any]]
    for path, (body, filename) in modules.items():
        if path is None:
            file = None
        else:
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
            file = path.open('wt', encoding=encoding)

        print(custom_file_header or header.format(filename), file=file)
        if body:
            print('', file=file)
            print(body.rstrip(), file=file)

        if file is not None:
            file.close()


def infer_input_type(text: str) -> InputFileType:
    if is_openapi(text):
        return InputFileType.OpenAPI
    elif is_schema(text):
        return InputFileType.JsonSchema
    return InputFileType.Json


inferred_message = (
    'The input file type was determined to be: {}\nThis can be specificied explicitly with the '
    '`--input-file-type` option.'
)

__all__ = [
    'DefaultPutDict',
    'Error',
    'InputFileType',
    'InvalidClassNameError',
    'LiteralType',
    'PythonVersion',
    'generate',
]
