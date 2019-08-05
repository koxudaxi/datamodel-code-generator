#! /usr/bin/env python

"""
Main function.
"""

import os
import sys
from argparse import ArgumentParser, FileType, Namespace
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional, Sequence, Union

import argcomplete
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.openapi import OpenAPIParser


class Exit(IntEnum):
    """Exit reasons."""

    OK = 0
    ERROR = 1


arg_parser = ArgumentParser()
arg_parser.add_argument('--input', help='Open API YAML file')
arg_parser.add_argument(
    '--output', help='Output file', type=FileType('wt'), default=sys.stdout
)
arg_parser.add_argument(
    '--base-class', help='Base Class', type=str, default='pydantic.BaseModel'
)


def main(args: Optional[Sequence[str]] = None) -> Exit:
    """Main function."""

    # add cli completion support
    argcomplete.autocomplete(arg_parser)

    if args is None:
        args = sys.argv[1:]

    namespace: Namespace = arg_parser.parse_args(args)

    input_filename = os.path.abspath(os.path.expanduser(namespace.input))
    parser = OpenAPIParser(BaseModel, CustomRootType, filename=input_filename, base_class=namespace.base_class)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    header = f'''\
# generated by datamodel-codegen:
#   filename:  {os.path.split(input_filename)[1]}
#   timestamp: {timestamp}

from typing import List, Optional

from pydantic import BaseModel


'''
    with namespace.output as file:
        print(header, file=file)
        print(parser.parse(), file=file)

    return Exit.OK


if __name__ == '__main__':
    sys.exit(main())
