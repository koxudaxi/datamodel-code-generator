#! /usr/bin/env python

"""
Main function.
"""

import json
import locale
import signal
import sys
from argparse import ArgumentParser, FileType, Namespace
from collections import defaultdict
from enum import IntEnum
from io import TextIOBase
from pathlib import Path
from typing import Any, DefaultDict, Dict, Optional, Sequence, cast

import argcomplete
import black
import toml
from pydantic import BaseModel, root_validator, validator

from datamodel_code_generator import (
    DEFAULT_BASE_CLASS,
    Error,
    InputFileType,
    InvalidClassNameError,
    enable_debug_message,
    generate,
)
from datamodel_code_generator.parser import LiteralType

from .format import PythonVersion, is_supported_in_black


class Exit(IntEnum):
    """Exit reasons."""

    OK = 0
    ERROR = 1
    KeyboardInterrupt = 2


def sig_int_handler(_: int, __: Any) -> None:  # pragma: no cover
    exit(Exit.OK)


signal.signal(signal.SIGINT, sig_int_handler)

DEFAULT_ENCODING = locale.getpreferredencoding()

arg_parser = ArgumentParser()
arg_parser.add_argument(
    '--input', help='Input file/directory (default: stdin)',
)
arg_parser.add_argument(
    '--input-file-type',
    help='Input file type (default: auto)',
    choices=[i.value for i in InputFileType],
)
arg_parser.add_argument('--output', help='Output file (default: stdout)')
arg_parser.add_argument(
    '--base-class', help='Base Class (default: pydantic.BaseModel)', type=str,
)
arg_parser.add_argument(
    '--field-constraints',
    help='Use field constraints and not con* annotations',
    action='store_true',
    default=None,
)
arg_parser.add_argument(
    '--snake-case-field',
    help='Change camel-case field name to snake-case',
    action='store_true',
    default=None,
)
arg_parser.add_argument(
    '--strip-default-none',
    help='Strip default None on fields',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--allow-population-by-field-name',
    help='Allow population by field name',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--use-default',
    help='Use default value even if a field is required',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--force-optional',
    help='Force optional for required fields',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--disable-timestamp',
    help='Disable timestamp on file headers',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--use-standard-collections',
    help='Use standard collections for type hinting (list, dict)',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--use-schema-description',
    help='Use schema description to populate class docstring',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--reuse-model',
    help='Re-use models on the field when a module has the model with the same content',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--enum-field-as-literal',
    help='Parse enum field as literal. '
    'all: all enum field type are Literal. '
    'one: field type is Literal when an enum has only one possible value',
    choices=[l.value for l in LiteralType],
    default=None,
)

arg_parser.add_argument(
    '--class-name', help='Set class name of root model', default=None,
)

arg_parser.add_argument(
    '--custom-template-dir', help='Custom template directory', type=str
)
arg_parser.add_argument(
    '--extra-template-data', help='Extra template data', type=FileType('rt')
)
arg_parser.add_argument('--aliases', help='Alias mapping file', type=FileType('rt'))
arg_parser.add_argument(
    '--target-python-version',
    help='target python version (default: 3.7)',
    choices=[v.value for v in PythonVersion],
)
arg_parser.add_argument(
    '--validation',
    help='Enable validation (Only OpenAPI)',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--encoding',
    help=f'The encoding of input and output (default: {DEFAULT_ENCODING})',
    default=DEFAULT_ENCODING,
)

arg_parser.add_argument(
    '--debug', help='show debug message', action='store_true', default=None
)
arg_parser.add_argument('--version', help='show version', action='store_true')


class Config(BaseModel):
    class Config:
        validate_assignment = True
        arbitrary_types_allowed = (TextIOBase,)

    @validator("aliases", "extra_template_data", pre=True)
    def validate_file(cls, value: Any) -> Optional[TextIOBase]:
        if value is None or isinstance(value, TextIOBase):
            return value
        return cast(TextIOBase, Path(value).expanduser().resolve().open("rt"))

    @validator("input", "output", "custom_template_dir", pre=True)
    def validate_path(cls, value: Any) -> Optional[Path]:
        if value is None or isinstance(value, Path):
            return value  # pragma: no cover
        return Path(value).expanduser().resolve()

    @root_validator
    def validate_literal_option(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get('enum_field_as_literal'):
            target_python_version: PythonVersion = values['target_python_version']
            if not target_python_version.has_literal_type:
                raise Error(
                    f"`--enum-field-as-literal` isn't compatible with `--target-python-version {target_python_version.value}`.\n"  # type: ignore
                    f"You have to set `--target-python-version {target_python_version.PY_38.value}` or later version."
                )
        return values

    input: Optional[Path]
    input_file_type: InputFileType = InputFileType.Auto
    output: Optional[Path]
    debug: bool = False
    target_python_version: PythonVersion = PythonVersion.PY_37
    base_class: str = DEFAULT_BASE_CLASS
    custom_template_dir: Optional[Path]
    extra_template_data: Optional[TextIOBase]
    validation: bool = False
    field_constraints: bool = False
    snake_case_field: bool = False
    strip_default_none: bool = False
    aliases: Optional[TextIOBase]
    disable_timestamp: bool = False
    allow_population_by_field_name: bool = False
    use_default: bool = False
    force_optional: bool = False
    class_name: Optional[str] = None
    use_standard_collections: bool = False
    use_schema_description: bool = False
    reuse_model: bool = False
    encoding: str = 'utf-8'
    enum_field_as_literal: Optional[LiteralType] = None

    def merge_args(self, args: Namespace) -> None:
        for field_name in self.__fields__:
            arg = getattr(args, field_name)
            if arg is None:
                continue
            setattr(self, field_name, arg)


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

    root = black.find_project_root((Path().resolve(),))
    pyproject_toml_path = root / "pyproject.toml"
    if pyproject_toml_path.is_file():
        pyproject_toml: Dict[str, Any] = {
            k.replace('-', '_'): v
            for k, v in toml.load(str(pyproject_toml_path))
            .get('tool', {})
            .get('datamodel-codegen', {})
            .items()
        }
    else:
        pyproject_toml = {}

    try:
        config = Config.parse_obj(pyproject_toml)
        config.merge_args(namespace)
    except Error as e:
        print(e.message, file=sys.stderr)
        return Exit.ERROR

    if not is_supported_in_black(config.target_python_version):  # pragma: no cover
        print(
            f"Installed black doesn't support Python version {config.target_python_version.value}.\n"
            f"You have to install a newer black.\n"
            f"Installed black version: {black.__version__}",
            file=sys.stderr,
        )
        return Exit.ERROR

    if config.debug:  # pragma: no cover
        enable_debug_message()

    extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]]
    if config.extra_template_data is None:
        extra_template_data = None
    else:
        with config.extra_template_data as data:
            try:
                extra_template_data = json.load(
                    data, object_hook=lambda d: defaultdict(dict, **d)
                )
            except json.JSONDecodeError as e:
                print(f"Unable to load extra template data: {e}", file=sys.stderr)
                return Exit.ERROR

    if config.aliases is None:
        aliases = None
    else:
        with config.aliases as data:
            try:
                aliases = json.load(data)
            except json.JSONDecodeError as e:
                print(f"Unable to load alias mapping: {e}", file=sys.stderr)
                return Exit.ERROR
        if not isinstance(aliases, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()
        ):
            print(
                'Alias mapping must be a JSON string mapping (e.g. {"from": "to", ...})',
                file=sys.stderr,
            )
            return Exit.ERROR

    try:
        generate(
            input_=config.input or sys.stdin.read(),
            input_file_type=config.input_file_type,
            output=config.output,
            target_python_version=config.target_python_version,
            base_class=config.base_class,
            custom_template_dir=config.custom_template_dir,
            validation=config.validation,
            field_constraints=config.field_constraints,
            snake_case_field=config.snake_case_field,
            strip_default_none=config.strip_default_none,
            extra_template_data=extra_template_data,
            aliases=aliases,
            disable_timestamp=config.disable_timestamp,
            allow_population_by_field_name=config.allow_population_by_field_name,
            apply_default_values_for_required_fields=config.use_default,
            force_optional_for_required_fields=config.force_optional,
            class_name=config.class_name,
            use_standard_collections=config.use_standard_collections,
            use_schema_description=config.use_schema_description,
            reuse_model=config.reuse_model,
            encoding=config.encoding,
            enum_field_as_literal=config.enum_field_as_literal,
        )
        return Exit.OK
    except InvalidClassNameError as e:
        print(f'{e} You have to set `--class-name` option', file=sys.stderr)
        return Exit.ERROR
    except Error as e:
        print(str(e), file=sys.stderr)
        return Exit.ERROR
    except Exception:
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return Exit.ERROR


if __name__ == '__main__':
    sys.exit(main())
