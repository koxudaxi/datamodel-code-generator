import contextlib
import inspect
import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    IO,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
)

import pysnooper
import yaml

from .format import PythonVersion
from .model.pydantic import (
    BaseModel,
    CustomRootType,
    DataModelField,
    dump_resolve_reference_action,
)
from .model.pydantic.types import DataTypeManager
from .parser.base import Parser
from .version import version as __version__

T = TypeVar('T')

pysnooper.tracer.DISABLED = True

DEFAULT_BASE_CLASS: str = 'pydantic.BaseModel'

# ALL_MODEL: str = '#all#'


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
    return 'openapi' in yaml.safe_load(text)


class InputFileType(Enum):
    Auto = 'auto'
    OpenAPI = 'openapi'
    JsonSchema = 'jsonschema'
    Json = 'json'
    Yaml = 'yaml'


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
    input_: Union[Path, str],
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
) -> None:
    input_text: Optional[str] = None
    if input_file_type == InputFileType.Auto:
        try:
            input_text = (
                input_
                if isinstance(input_, str)
                else get_first_file(input_).read_text()
            )
            input_file_type = (
                InputFileType.OpenAPI
                if is_openapi(input_text)
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

        if input_file_type in [InputFileType.Json, InputFileType.Yaml]:
            try:
                if isinstance(input_, Path) and input_.is_dir():  # pragma: no cover
                    raise Error(f'Input must be a file for {input_file_type}')
                input_text = input_ if isinstance(input_, str) else input_.read_text()
                obj: Dict[Any, Any] = yaml.safe_load(input_text)
            except:
                raise Error('Invalid file format')
            from genson import SchemaBuilder

            builder = SchemaBuilder()
            builder.add_object(obj)
            input_text = json.dumps(builder.to_schema())

    parser = parser_class(
        source=input_text or input_,
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
    )

    with chdir(output):
        results = parser.parse()
    if not input_filename:  # pragma: no cover
        if isinstance(input_, str):
            input_filename = '<stdin>'
        else:
            input_filename = input_.name
    if isinstance(results, str):

        modules = {output: (results, input_filename)}
    else:
        if output is None:
            raise Error('Modular references require an output directory')
        if output.suffix:
            raise Error('Modular references require an output directory, not a file')
        modules = {
            output.joinpath(*name): (result.body, str(result.source or input_filename))
            for name, result in sorted(results.items())
        }

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    header = f'''\
# generated by datamodel-codegen:
#   filename:  {{filename}}'''
    if not disable_timestamp:
        header += f'\n#   timestamp: {timestamp}'

    file: Optional[IO[Any]]
    for path, body_and_filename in modules.items():
        body, filename = body_and_filename
        if path is not None:
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
            file = path.open('wt')
        else:
            file = None

        print(header.format(filename=filename), file=file)
        if body:
            print('', file=file)
            print(body.rstrip(), file=file)

        if file is not None:
            file.close()
