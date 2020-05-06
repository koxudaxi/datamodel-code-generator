import contextlib
import inspect
import json
import os
from datetime import datetime, timezone
from enum import Enum
from json import JSONDecodeError
from pathlib import Path
from typing import (
    IO,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    Optional,
    Type,
    TypeVar,
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
from .parser.base import Parser
from .version import version as __version__

T = TypeVar('T')

pysnooper.tracer.DISABLED = True

DEFAULT_BASE_CLASS: str = 'pydantic.BaseModel'


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


def load_json_or_yaml(text: str) -> Dict[Any, Any]:
    try:
        data = json.loads(text)
    except JSONDecodeError:
        data = yaml.safe_load(text)
    return data


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
    return 'openapi' in load_json_or_yaml(text)


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


def generate(
    input_name: str,
    input_text: str,
    input_file_type: InputFileType,
    output: Optional[Path],
    target_python_version: PythonVersion,
    base_class: str = DEFAULT_BASE_CLASS,
    custom_template_dir: Optional[str] = None,
    extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
    validation: bool = False,
) -> None:
    if input_file_type == InputFileType.Auto:
        try:
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
                if input_file_type == InputFileType.Json:
                    obj: Dict[Any, Any] = json.loads(input_text)
                else:
                    import yaml

                    obj = yaml.safe_load(input_text)
            except:
                raise Error('Invalid file format')
            from genson import SchemaBuilder

            builder = SchemaBuilder()
            builder.add_object(obj)
            input_text = json.dumps(builder.to_schema())

    parser = parser_class(
        BaseModel,
        CustomRootType,
        DataModelField,
        base_class=base_class,
        custom_template_dir=custom_template_dir,
        extra_template_data=extra_template_data,
        target_python_version=target_python_version,
        text=input_text,
        dump_resolve_reference_action=dump_resolve_reference_action,
        validation=validation,
    )

    with chdir(output):
        result = parser.parse()

    if isinstance(result, str):
        modules = {output: result}
    else:
        if output is None:
            raise Error('Modular references require an output directory')
        if output.suffix:
            raise Error('Modular references require an output directory, not a file')
        modules = {
            output.joinpath(*name): body for name, body in sorted(result.items())
        }

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    header = f'''\
# generated by datamodel-codegen:
#   filename:  {Path(input_name).name}
#   timestamp: {timestamp}'''

    file: Optional[IO[Any]]
    for path, body in modules.items():
        if path is not None:
            if not path.parent.exists():
                path.parent.mkdir(parents=True)
            file = path.open('wt')
        else:
            file = None

        print(header, file=file)
        if body:
            print('', file=file)
            print(body.rstrip(), file=file)

        if file is not None:
            file.close()
