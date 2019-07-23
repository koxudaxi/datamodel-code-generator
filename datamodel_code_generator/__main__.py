#! /usr/bin/env python

"""
Main function.
"""

import os
import sys
from argparse import ArgumentParser, FileType
from enum import IntEnum
from typing import Optional, Sequence

import argcomplete

from datamodel_code_generator.model import BaseModel, DataModelField
from datamodel_code_generator.parser.openapi import Parser


class Exit(IntEnum):
    """Exit reasons."""

    OK = 0
    ERROR = 1


arg_parser = ArgumentParser()
arg_parser.add_argument("--input", help="Open API YAML file")
arg_parser.add_argument("--output", help="Output file", type=FileType("wt"), default=sys.stdout)


def main(args: Optional[Sequence[str]] = None) -> Exit:
    """Main function."""

    # add cli completion support
    argcomplete.autocomplete(arg_parser)

    if args is None:
        args = sys.argv[1:]

    args = arg_parser.parse_args(args)

    input_filename = os.path.abspath(os.path.expanduser(args.input))
    parser = Parser(BaseModel, DataModelField, filename=input_filename)
    with args.output as file:
        parser.parse(file)

    return Exit.OK


if __name__ == "__main__":
    sys.exit(main())
