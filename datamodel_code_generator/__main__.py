#! /usr/bin/env python

"""
Main function.
"""

import json
import signal
import sys
from argparse import ArgumentParser, FileType, Namespace
from collections import defaultdict
from enum import IntEnum
from pathlib import Path
from typing import Any, DefaultDict, Dict, Optional, Sequence

import argcomplete

from datamodel_code_generator import (
    DEFAULT_BASE_CLASS,
    Error,
    InputFileType,
    enable_debug_message,
    generate,
)

from .format import PythonVersion


class Exit(IntEnum):
    """Exit reasons."""

    OK = 0
    ERROR = 1
    KeyboardInterrupt = 2


def sig_int_handler(_: int, __: Any) -> None:  # pragma: no cover
    exit(Exit.OK)


signal.signal(signal.SIGINT, sig_int_handler)


arg_parser = ArgumentParser()
arg_parser.add_argument(
    '--input',
    help='Input file (default: stdin)',
    type=FileType('rt'),
    default=sys.stdin,
)
arg_parser.add_argument(
    '--input-file-type',
    help='Input file type (default: auto)',
    choices=[i.value for i in InputFileType],
    default='auto',
)
arg_parser.add_argument('--output', help='Output file (default: stdout)')
arg_parser.add_argument(
    '--base-class',
    help='Base Class (default: pydantic.BaseModel)',
    type=str,
    default=DEFAULT_BASE_CLASS,
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

    extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]]
    if namespace.extra_template_data is not None:
        with namespace.extra_template_data as data:
            extra_template_data = json.load(
                data, object_hook=lambda d: defaultdict(dict, **d)
            )
    else:
        extra_template_data = None

    try:
        generate(
            input_name=namespace.input.name,
            input_text=namespace.input.read(),
            input_file_type=InputFileType(namespace.input_file_type),
            output=Path(namespace.output) if namespace.output is not None else None,
            target_python_version=PythonVersion(namespace.target_python_version),
            base_class=namespace.base_class,
            custom_template_dir=namespace.custom_template_dir,
            extra_template_data=extra_template_data,
            validation=namespace.validation,
        )
        return Exit.OK
    except Error as e:
        print(str(e), file=sys.stderr)
        return Exit.ERROR
    except Exception:
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return Exit.ERROR


if __name__ == '__main__':
    sys.exit(main())
