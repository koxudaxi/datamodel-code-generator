import contextlib
import os
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
    Mapping,
    Optional,
    Sequence,
    TextIO,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import ParseResult

import pysnooper
import yaml

if TYPE_CHECKING:
    cached_property = property
    from yaml import SafeLoader

    Protocol = object
    runtime_checkable: Callable[..., Any]
else:
    try:
        from typing import Protocol
    except ImportError:
        from typing_extensions import Protocol
    try:
        from typing import runtime_checkable
    except ImportError:
        from typing_extensions import runtime_checkable
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:  # pragma: no cover
        from yaml import SafeLoader

    try:
        from functools import cached_property
    except ImportError:
        _NOT_FOUND = object()

        class cached_property:
            def __init__(self, func: Callable) -> None:
                self.func: Callable = func
                self.__doc__: Any = func.__doc__

            def __get__(self, instance: Any, owner: Any = None) -> Any:
                value = instance.__dict__.get(self.func.__name__, _NOT_FOUND)
                if value is _NOT_FOUND:  # pragma: no cover
                    value = instance.__dict__[self.func.__name__] = self.func(instance)
                return value


from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.model.pydantic import dump_resolve_reference_action
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.parser.base import Parser
from datamodel_code_generator.types import StrictTypes

T = TypeVar('T')

pysnooper.tracer.DISABLED = True

DEFAULT_BASE_CLASS: str = 'pydantic.BaseModel'

SafeLoader.yaml_constructors[
    'tag:yaml.org,2002:timestamp'
] = SafeLoader.yaml_constructors['tag:yaml.org,2002:str']


def load_yaml(stream: Union[str, TextIO]) -> Any:
    return yaml.load(stream, Loader=SafeLoader)


def load_yaml_from_path(path: Path, encoding: str) -> Any:
    with path.open(encoding=encoding) as f:
        return load_yaml(f)


def enable_debug_message() -> None:  # pragma: no cover
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


class InputFileType(Enum):
    Auto = 'auto'
    OpenAPI = 'openapi'
    JsonSchema = 'jsonschema'
    Json = 'json'
    Yaml = 'yaml'
    Dict = 'dict'
    CSV = 'csv'


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
    target_python_version: PythonVersion = PythonVersion.PY_37,
    base_class: str = DEFAULT_BASE_CLASS,
    custom_template_dir: Optional[Path] = None,
    extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
    validation: bool = False,
    field_constraints: bool = False,
    snake_case_field: bool = False,
    strip_default_none: bool = False,
    aliases: Optional[Mapping[str, str]] = None,
    disable_timestamp: bool = False,
    allow_population_by_field_name: bool = False,
    apply_default_values_for_required_fields: bool = False,
    force_optional_for_required_fields: bool = False,
    class_name: Optional[str] = None,
    use_standard_collections: bool = False,
    use_schema_description: bool = False,
    reuse_model: bool = False,
    encoding: str = 'utf-8',
    enum_field_as_literal: Optional[LiteralType] = None,
    set_default_enum_member: bool = False,
    strict_nullable: bool = False,
    use_generic_container_types: bool = False,
    enable_faux_immutability: bool = False,
    disable_appending_item_suffix: bool = False,
    strict_types: Optional[Sequence[StrictTypes]] = None,
    empty_enum_field_name: Optional[str] = None,
    custom_class_name_generator: Optional[Callable[[str], str]] = None,
) -> None:
    remote_text_cache: DefaultPutDict[str, str] = DefaultPutDict()
    if isinstance(input_, str):
        input_text: Optional[str] = input_
    elif isinstance(input_, ParseResult):
        from datamodel_code_generator.http import get_body

        input_text = remote_text_cache.get_or_put(
            input_.geturl(), default_factory=get_body
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
            input_file_type = (
                InputFileType.OpenAPI
                if is_openapi(input_text_)  # type: ignore
                else InputFileType.JsonSchema
            )
        except:
            raise Error('Invalid file format')

    if input_file_type == InputFileType.OpenAPI:
        from datamodel_code_generator.parser.openapi import OpenAPIParser

        parser_class: Type[Parser] = OpenAPIParser
    else:
        from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

        parser_class = JsonSchemaParser

        if input_file_type in (
            InputFileType.Json,
            InputFileType.Yaml,
            InputFileType.Dict,
            InputFileType.CSV,
        ):
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
            except:
                raise Error('Invalid file format')
            import json

            from genson import SchemaBuilder

            builder = SchemaBuilder()
            builder.add_object(obj)
            input_text = json.dumps(builder.to_schema())

    parser = parser_class(
        source=input_ if isinstance(input_, ParseResult) else input_text or input_,
        base_class=base_class,
        custom_template_dir=custom_template_dir,
        extra_template_data=extra_template_data,
        target_python_version=target_python_version,
        dump_resolve_reference_action=dump_resolve_reference_action,
        validation=validation,
        field_constraints=field_constraints,
        snake_case_field=snake_case_field,
        strip_default_none=strip_default_none,
        aliases=aliases,
        allow_population_by_field_name=allow_population_by_field_name,
        apply_default_values_for_required_fields=apply_default_values_for_required_fields,
        force_optional_for_required_fields=force_optional_for_required_fields,
        class_name=class_name,
        use_standard_collections=use_standard_collections,
        base_path=input_.parent
        if isinstance(input_, Path) and input_.is_file()
        else None,
        use_schema_description=use_schema_description,
        reuse_model=reuse_model,
        enum_field_as_literal=enum_field_as_literal,
        set_default_enum_member=set_default_enum_member,
        strict_nullable=strict_nullable,
        use_generic_container_types=use_generic_container_types,
        enable_faux_immutability=enable_faux_immutability,
        remote_text_cache=remote_text_cache,
        disable_appending_item_suffix=disable_appending_item_suffix,
        strict_types=strict_types,
        empty_enum_field_name=empty_enum_field_name,
        custom_class_name_generator=custom_class_name_generator,
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

    header = '''\
# generated by datamodel-codegen:
#   filename:  {}'''
    if not disable_timestamp:
        header += f'\n#   timestamp: {timestamp}'

    file: Optional[IO[Any]]
    for path, body_and_filename in modules.items():
        body, filename = body_and_filename
        if path is None:
            file = None
        else:
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
            file = path.open('wt', encoding=encoding)

        print(header.format(filename), file=file)
        if body:
            print('', file=file)
            print(body.rstrip(), file=file)

        if file is not None:
            file.close()
