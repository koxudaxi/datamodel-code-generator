#! /usr/bin/env python

"""
Main function.
"""

import contextlib
import json
import os
import signal
import sys
from argparse import ArgumentParser, FileType, Namespace
from collections import defaultdict
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import IO, Any, DefaultDict, Dict, Iterator, Optional, Sequence, Type

import argcomplete

from datamodel_code_generator import (
    PythonVersion,
    enable_debug_message,
    load_json_or_yaml,
)
from datamodel_code_generator.model.pydantic import (
    BaseModel,
    CustomRootType,
    dump_resolve_reference_action,
)
from datamodel_code_generator.model.pydantic.base_model import DataModelField
from datamodel_code_generator.parser.base import Parser


class Exit(IntEnum):
    """Exit reasons."""

    OK = 0
    ERROR = 1
    KeyboardInterrupt = 2


def sig_int_handler(_: int, __: Any) -> None:  # pragma: no cover
    exit(Exit.OK)


signal.signal(signal.SIGINT, sig_int_handler)


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


arg_parser = ArgumentParser()
arg_parser.add_argument(
    '--input',
    help='Open API YAML file (default: stdin)',
    type=FileType('rt'),
    default=sys.stdin,
)
arg_parser.add_argument(
    '--input-file-type',
    help='Input file type (default: auto)',
    choices=['auto', 'openapi', 'jsonschema'],
    default='auto',
)
arg_parser.add_argument('--output', help='Output file (default: stdout)')
arg_parser.add_argument(
    '--base-class',
    help='Base Class (default: pydantic.BaseModel)',
    type=str,
    default='pydantic.BaseModel',
)
arg_parser.add_argument(
    '--custom-template-dir', help='Custom Template Directory', type=str
)
arg_parser.add_argument(
    '--extra-template-data', help='Extra Template Data', type=FileType('rt')
)
arg_parser.add_argument(
    '--target-python-version',
    help='target python version (default: 3.7)',
    choices=['3.6', '3.7'],
    default='3.7',
)
arg_parser.add_argument(
    '--validation', help='Enable validation (Only OpenAPI)', action='store_true'
)
arg_parser.add_argument('--debug', help='show debug message', action='store_true')
arg_parser.add_argument('--version', help='show version', action='store_true')


def main(args: Optional[Sequence[str]] = None) -> Exit:
    """Main function."""

    # add cli completion support
    argcomplete.autocomplete(arg_parser)

    if args is None:
        args = sys.argv[1:]

    namespace: Namespace = arg_parser.parse_args(args)

    if namespace.version:  # pragma: no cover
        from datamodel_code_generator.version import version

        print(version)
        exit(0)

    if namespace.debug:  # pragma: no cover
        enable_debug_message()

    extra_template_data: Optional[DefaultDict[str, Dict]]
    if namespace.extra_template_data is not None:
        with namespace.extra_template_data as data:
            extra_template_data = json.load(
                data, object_hook=lambda d: defaultdict(dict, **d)
            )
    else:
        extra_template_data = None

    text: str = namespace.input.read()

    input_file_type: str = namespace.input_file_type

    if input_file_type == 'auto':
        try:
            input_file_type = 'openapi' if is_openapi(text) else 'jsonschema'
        except:
            print('Invalid file format')
            return Exit.ERROR

    if input_file_type == 'openapi':
        from datamodel_code_generator.parser.openapi import OpenAPIParser

        parser_class: Type[Parser] = OpenAPIParser
    else:
        from datamodel_code_generator.parser.jsonschema import JsonSchemaParser

        parser_class = JsonSchemaParser

    parser = parser_class(
        BaseModel,
        CustomRootType,
        DataModelField,
        base_class=namespace.base_class,
        custom_template_dir=namespace.custom_template_dir,
        extra_template_data=extra_template_data,
        target_python_version=PythonVersion(namespace.target_python_version),
        text=text,
        dump_resolve_reference_action=dump_resolve_reference_action,
        validation=namespace.validation,
    )

    output = Path(namespace.output) if namespace.output is not None else None

    with chdir(output):
        result = parser.parse()

    if isinstance(result, str):
        modules = {output: result}
    else:
        if output is None:
            print('Modular references require an output directory')
            return Exit.ERROR
        if output.suffix:
            print('Modular references require an output directory, not a file')
            return Exit.ERROR
        modules = {
            output.joinpath(*name): body for name, body in sorted(result.items())
        }

    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    header = f'''\
# generated by datamodel-codegen:
#   filename:  {Path(namespace.input.name).name}
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

    return Exit.OK


if __name__ == '__main__':
    sys.exit(main())
