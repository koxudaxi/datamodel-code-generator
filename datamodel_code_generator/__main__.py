#! /usr/bin/env python

"""
Main function.
"""

from __future__ import annotations

import json
import locale
import signal
import sys
from argparse import ArgumentParser, FileType, Namespace
from collections import defaultdict
from enum import IntEnum
from io import TextIOBase
from pathlib import Path
from typing import (
    Any,
    DefaultDict,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)
from urllib.parse import ParseResult, urlparse
from warnings import warn

import argcomplete
import black
import toml
from pydantic import BaseModel, root_validator, validator

from datamodel_code_generator import (
    DEFAULT_BASE_CLASS,
    Error,
    InputFileType,
    InvalidClassNameError,
    OpenAPIScope,
    enable_debug_message,
    generate,
)
from datamodel_code_generator.format import (
    PythonVersion,
    black_find_project_root,
    is_supported_in_black,
)
from datamodel_code_generator.parser import LiteralType
from datamodel_code_generator.reference import is_url
from datamodel_code_generator.types import StrictTypes


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
    '--input',
    help='Input file/directory (default: stdin)',
)
arg_parser.add_argument(
    '--url',
    help='Input file URL. `--input` is ignored when `--url` is used',
)

arg_parser.add_argument(
    '--http-headers',
    nargs='+',
    metavar='HTTP_HEADER',
    help='Set headers in HTTP requests to the remote host. (example: "Authorization: Basic dXNlcjpwYXNz")',
)

arg_parser.add_argument(
    '--http-ignore-tls',
    help="Disable verification of the remote host's TLS certificate",
    action='store_true',
    default=False,
)

arg_parser.add_argument(
    '--input-file-type',
    help='Input file type (default: auto)',
    choices=[i.value for i in InputFileType],
)
arg_parser.add_argument(
    '--openapi-scopes',
    help='Scopes of OpenAPI model generation (default: schemas)',
    choices=[o.value for o in OpenAPIScope],
    nargs='+',
    default=[OpenAPIScope.Schemas.value],
)
arg_parser.add_argument('--output', help='Output file (default: stdout)')

arg_parser.add_argument(
    '--base-class',
    help='Base Class (default: pydantic.BaseModel)',
    type=str,
)
arg_parser.add_argument(
    '--field-constraints',
    help='Use field constraints and not con* annotations',
    action='store_true',
    default=None,
)
arg_parser.add_argument(
    '--use-annotated',
    help='Use typing.Annotated for Field(). Also, `--field-constraints` option will be enabled.',
    action='store_true',
    default=None,
)
arg_parser.add_argument(
    '--use_non_positive_negative_number_constrained_types',
    help='Use the Non{Positive,Negative}{FloatInt} types instead of the corresponding con* constrained types.',
    action='store_true',
    default=None,
)
arg_parser.add_argument(
    '--field-extra-keys',
    help='Add extra keys to field parameters',
    type=str,
    nargs='+',
)
arg_parser.add_argument(
    '--field-include-all-keys',
    help='Add all keys to field parameters',
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
    '--original-field-name-delimiter',
    help='Set delimiter to convert to snake case. This option only can be used with --snake-case-field (default: `_` )',
    default=None,
)

arg_parser.add_argument(
    '--strip-default-none',
    help='Strip default None on fields',
    action='store_true',
    default=None,
)
arg_parser.add_argument(
    '--disable-appending-item-suffix',
    help='Disable appending `Item` suffix to model name in an array',
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
    '--enable-faux-immutability',
    help='Enable faux immutability',
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
    '--strict-nullable',
    help='Treat default field as a non-nullable field (Only OpenAPI)',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--strict-types',
    help='Use strict types',
    choices=[t.value for t in StrictTypes],
    nargs='+',
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
    '--use-generic-container-types',
    help='Use generic container types for type hinting (typing.Sequence, typing.Mapping). '
    'If `--use-standard-collections` option is set, then import from collections.abc instead of typing',
    action='store_true',
    default=None,
)
arg_parser.add_argument(
    '--use-union-operator',
    help='Use | operator for Union type (PEP 604).',
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
    '--use-field-description',
    help='Use schema description to populate field docstring',
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
    '--set-default-enum-member',
    help='Set enum members as default values for enum field',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--empty-enum-field-name',
    help='Set field name when enum value is empty (default:  `_`)',
    default=None,
)

arg_parser.add_argument(
    '--use-subclass-enum',
    help='Define Enum class as subclass with field type when enum has type (int, float, bytes, str)',
    action='store_true',
    default=False,
)

arg_parser.add_argument(
    '--class-name',
    help='Set class name of root model',
    default=None,
)

arg_parser.add_argument(
    '--use-title-as-name',
    help='use titles as class names of models',
    action='store_true',
    default=None,
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
    '--wrap-string-literal',
    help='Wrap string literal by using black `experimental-string-processing` option (require black 20.8b0 or later)',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    '--validation',
    help='Enable validation (Only OpenAPI)',
    action='store_true',
    default=None,
)

arg_parser.add_argument(
    "--use-double-quotes",
    action='store_true',
    default=False,
    help="Model generated with double quotes. Single quotes or "
    "your black config skip_string_normalization value will be used without this option.",
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
        # validate_assignment = True
        # Pydantic 1.5.1 doesn't support validate_assignment correctly
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

    @validator('url', pre=True)
    def validate_url(cls, value: Any) -> Optional[ParseResult]:
        if isinstance(value, str) and is_url(value):  # pragma: no cover
            return urlparse(value)
        elif value is None:  # pragma: no cover
            return None
        raise Error(
            f'This protocol doesn\'t support only http/https. --input={value}'
        )  # pragma: no cover

    @root_validator
    def validate_use_generic_container_types(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if values.get('use_generic_container_types'):
            target_python_version: PythonVersion = values['target_python_version']
            if target_python_version == target_python_version.PY_36:
                raise Error(
                    f"`--use-generic-container-types` can not be used with `--target-python_version` {target_python_version.PY_36.value}.\n"  # type: ignore
                    " The version will be not supported in a future version"
                )
        return values

    @root_validator
    def validate_original_field_name_delimiter(
        cls, values: Dict[str, Any]
    ) -> Dict[str, Any]:
        if values.get('original_field_name_delimiter') is not None:
            if not values.get('snake_case_field'):
                raise Error(
                    "`--original-field-name-delimiter` can not be used without `--snake-case-field`."
                )
        return values

    # Pydantic 1.5.1 doesn't support each_item=True correctly
    @validator('http_headers', pre=True)
    def validate_http_headers(cls, value: Any) -> Optional[List[Tuple[str, str]]]:
        def validate_each_item(each_item: Any) -> Tuple[str, str]:
            if isinstance(each_item, str):  # pragma: no cover
                try:
                    field_name, field_value = each_item.split(
                        ':', maxsplit=1
                    )  # type: str, str
                    return field_name, field_value.lstrip()
                except ValueError:
                    raise Error(f'Invalid http header: {each_item!r}')
            return each_item  # pragma: no cover

        if isinstance(value, list):
            return [validate_each_item(each_item) for each_item in value]
        return value  # pragma: no cover

    @root_validator()
    def validate_root(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values = cls._validate_use_annotated(values)
        return cls._validate_use_union_operator(values)

    @classmethod
    def _validate_use_annotated(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get('use_annotated'):
            values['field_constraints'] = True
        return values

    @classmethod
    def _validate_use_union_operator(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get('use_union_operator'):
            target_python_version: PythonVersion = values.get(
                'target_python_version', PythonVersion.PY_37
            )
            if not target_python_version.has_union_operator:
                warn(
                    f"`--use-union-operator` can not be used with `--target-python_version` {target_python_version.value}.\n"
                    f"`--target-python_version` {PythonVersion.PY_310.value} will be used."
                )
                values['target_python_version'] = PythonVersion.PY_310
        return values

    input: Optional[Union[Path, str]]
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
    use_field_description: bool = False
    reuse_model: bool = False
    encoding: str = 'utf-8'
    enum_field_as_literal: Optional[LiteralType] = None
    set_default_enum_member: bool = False
    use_subclass_enum: bool = False
    strict_nullable: bool = False
    use_generic_container_types: bool = False
    use_union_operator: bool = False
    enable_faux_immutability: bool = False
    url: Optional[ParseResult] = None
    disable_appending_item_suffix: bool = False
    strict_types: List[StrictTypes] = []
    empty_enum_field_name: Optional[str] = None
    field_extra_keys: Optional[Set[str]] = None
    field_include_all_keys: bool = False
    openapi_scopes: Optional[List[OpenAPIScope]] = None
    wrap_string_literal: Optional[bool] = None
    use_title_as_name: bool = False
    http_headers: Optional[Sequence[Tuple[str, str]]] = None
    http_ignore_tls: bool = False
    use_annotated: bool = False
    use_non_positive_negative_number_constrained_types: bool = False
    original_field_name_delimiter: Optional[str] = None
    use_double_quotes: bool = False

    def merge_args(self, args: Namespace) -> None:
        set_args = {
            f: getattr(args, f) for f in self.__fields__ if getattr(args, f) is not None
        }
        set_args = self._validate_use_annotated(set_args)
        set_args = self._validate_use_union_operator(set_args)
        parsed_args = self.parse_obj(set_args)
        for field_name in set_args:
            setattr(self, field_name, getattr(parsed_args, field_name))


def main(args: Optional[Sequence[str]] = None) -> Exit:
    """Main function."""

    # add cli completion support
    argcomplete.autocomplete(arg_parser)

    if args is None:
        args = sys.argv[1:]

    namespace: Namespace = arg_parser.parse_args(args)

    if namespace.version:
        from datamodel_code_generator.version import version

        print(version)
        exit(0)

    root = black_find_project_root((Path().resolve(),))
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

    if not config.input and not config.url and sys.stdin.isatty():
        print(
            'Not Found Input: require `stdin` or arguments `--input` or `--url`',
            file=sys.stderr,
        )
        arg_parser.print_help()
        return Exit.ERROR

    if not is_supported_in_black(config.target_python_version):  # pragma: no cover
        print(
            f"Installed black doesn't support Python version {config.target_python_version.value}.\n"  # type: ignore
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
            input_=config.url or config.input or sys.stdin.read(),
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
            use_field_description=config.use_field_description,
            reuse_model=config.reuse_model,
            encoding=config.encoding,
            enum_field_as_literal=config.enum_field_as_literal,
            set_default_enum_member=config.set_default_enum_member,
            use_subclass_enum=config.use_subclass_enum,
            strict_nullable=config.strict_nullable,
            use_generic_container_types=config.use_generic_container_types,
            enable_faux_immutability=config.enable_faux_immutability,
            disable_appending_item_suffix=config.disable_appending_item_suffix,
            strict_types=config.strict_types,
            empty_enum_field_name=config.empty_enum_field_name,
            field_extra_keys=config.field_extra_keys,
            field_include_all_keys=config.field_include_all_keys,
            openapi_scopes=config.openapi_scopes,
            wrap_string_literal=config.wrap_string_literal,
            use_title_as_name=config.use_title_as_name,
            http_headers=config.http_headers,
            http_ignore_tls=config.http_ignore_tls,
            use_annotated=config.use_annotated,
            use_non_positive_negative_number_constrained_types=config.use_non_positive_negative_number_constrained_types,
            original_field_name_delimiter=config.original_field_name_delimiter,
            use_double_quotes=config.use_double_quotes,
            use_union_operator=config.use_union_operator,
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
