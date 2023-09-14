from __future__ import annotations

import locale
from argparse import ArgumentParser, FileType, HelpFormatter, Namespace
from enum import Enum
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from datamodel_code_generator import DataModelType, InputFileType, OpenAPIScope
from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.parser import LiteralType
from datamodel_code_generator.types import StrictTypes
from datamodel_code_generator.util import PYDANTIC_V2, BaseModel

if TYPE_CHECKING:
    from argparse import Action

DEFAULT_ENCODING = locale.getpreferredencoding()

namespace = Namespace(no_color=False)


class SortingHelpFormatter(HelpFormatter):
    def _bold_cyan(self, text: str) -> str:
        return f'\x1b[36;1m{text}\x1b[0m'

    def add_arguments(self, actions: Iterable[Action]) -> None:
        actions = sorted(actions, key=attrgetter('option_strings'))
        super().add_arguments(actions)

    def start_section(self, heading: Optional[str]) -> None:
        return super().start_section(
            heading if namespace.no_color or not heading else self._bold_cyan(heading)
        )


arg_parser = ArgumentParser(
    usage='\n  datamodel-codegen [options]',
    description='Generate Python data models from schema definitions or structured data',
    formatter_class=SortingHelpFormatter,
    add_help=False,
)


class ActionType(Enum):
    append_const = 'append_const'
    append = 'append'
    count = 'count'
    extend = 'extend'
    help = 'help'
    store_const = 'store_const'
    store_false = 'store_false'
    store_true = 'store_true'
    store = 'store'
    version = 'version'


class NArgsType(Enum):
    exactly_one = '?'
    one_ore_more = '+'
    zero_or_more = '*'


class Argument(BaseModel, arbitrary_types_allowed=True, use_enum_values=True):
    flags: List[str]
    action: Optional[ActionType] = None
    choices: Optional[List[str]] = None
    const: Any = None
    default: Any = None
    dest: Optional[str] = None
    help: Optional[str] = None
    metavar: Optional[Union[str, Tuple[str, ...]]] = None
    nargs: Optional[Union[int, NArgsType]] = None
    required: bool = False
    type: Optional[Callable[[str], Any]] = None
    version: Optional[str] = None


class ArgumentGroup(BaseModel):
    title: str
    arguments: list[Argument]


ArgumentGroups: Union[Type[ArgumentGroupsV2], Type[ArgumentGroupsV1]]

if PYDANTIC_V2:
    from pydantic import RootModel

    class ArgumentGroupsV2(RootModel[List[ArgumentGroup]]):
        def __getattr__(self, name: str) -> Any:
            return getattr(self.root, name)

        def __getitem__(self, item: int) -> Any:
            return self.root[item]

        def __iter__(self) -> Iterator[ArgumentGroup]:  # type: ignore[override]
            yield from self.root

    ArgumentGroups = ArgumentGroupsV2

else:

    class ArgumentGroupsV1(BaseModel):
        __root__: List[ArgumentGroup]

        def __getattr__(self, name: str) -> Any:
            return getattr(self.__root__, name)

        def __getitem__(self, item: int) -> Any:
            return self.__root__[item]

        def __init__(self, data: List[ArgumentGroup], **extra: Any):
            self.__root__ = data
            super().__init__(**extra)

        def __iter__(self) -> Iterator[ArgumentGroup]:  # type: ignore[override]
            yield from self.__root__

    ArgumentGroups = ArgumentGroupsV1

arg_groups_data = [
    {
        'title': 'Options',
        'arguments': [
            {
                'flags': ['--http-headers'],
                'help': 'Set headers in HTTP requests to the remote host. (example: "Authorization: Basic dXNlcjpwYXNz")',
                'metavar': 'HTTP_HEADER',
                'nargs': '+',
            },
            {
                'flags': ['--http-ignore-tls'],
                'help': "Disable verification of the remote host's TLS certificate",
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--input-file-type'],
                'help': 'Input file type (default: auto)',
                'choices': [i.value for i in InputFileType],
            },
            {
                'flags': ['--input'],
                'help': 'Input file/directory (default: stdin)',
            },
            {
                'flags': ['--output-model-type'],
                'help': 'Output model type (default: pydantic.BaseModel)',
                'choices': [i.value for i in DataModelType],
            },
            {
                'flags': ['--output'],
                'help': 'Output file (default: stdout)',
            },
            {
                'flags': ['--url'],
                'help': 'Input file URL. `--input` is ignored when `--url` is used',
            },
        ],
    },
    {
        'title': 'Typing customization',
        'arguments': [
            {
                'flags': ['--base-class'],
                'help': 'Base Class (default: pydantic.BaseModel)',
                'type': str,
            },
            {
                'flags': ['--enum-field-as-literal'],
                'help': 'Parse enum field as literal. all: all enum field type are Literal. one: field type is Literal when an enum has only one possible value',
                'choices': [lt.value for lt in LiteralType],
                'default': None,
            },
            {
                'flags': ['--field-constraints'],
                'help': 'Use field constraints and not con* annotations',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--set-default-enum-member'],
                'help': 'Set enum members as default values for enum field',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--strict-types'],
                'help': 'Use strict types',
                'choices': [t.value for t in StrictTypes],
                'nargs': '+',
            },
            {
                'flags': ['--use-annotated'],
                'help': 'Use typing.Annotated for Field(). Also, `--field-constraints` option will be enabled.',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-generic-container-types'],
                'help': 'Use generic container types for type hinting (typing.Sequence, typing.Mapping). If `--use-standard-collections` option is set, then import from collections.abc instead of typing',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-non-positive-negative-number-constrained-types'],
                'help': 'Use the Non{Positive,Negative}{FloatInt} types instead of the corresponding con* constrained types.',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-one-literal-as-default'],
                'help': 'Use one literal as default value for one literal field',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-standard-collections'],
                'help': 'Use standard collections for type hinting (list, dict)',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-subclass-enum'],
                'help': 'Define Enum class as subclass with field type when enum has type (int, float, bytes, str)',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-union-operator'],
                'help': 'Use | operator for Union type (PEP 604).',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-unique-items-as-set'],
                'help': 'define field type as `set` when the field attribute has `uniqueItems`',
                'action': 'store_true',
                'default': None,
            },
        ],
    },
    {
        'title': 'Field customization',
        'arguments': [
            {
                'flags': ['--capitalise-enum-members', '--capitalize-enum-members'],
                'help': 'Capitalize field names on enum',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--empty-enum-field-name'],
                'help': 'Set field name when enum value is empty (default:  `_`)',
                'default': None,
            },
            {
                'flags': ['--field-extra-keys-without-x-prefix'],
                'help': 'Add extra keys with `x-` prefix to field parameters. The extra keys are stripped of the `x-` prefix.',
                'type': str,
                'nargs': '+',
            },
            {
                'flags': ['--field-extra-keys'],
                'help': 'Add extra keys to field parameters',
                'type': str,
                'nargs': '+',
            },
            {
                'flags': ['--field-include-all-keys'],
                'help': 'Add all keys to field parameters',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--force-optional'],
                'help': 'Force optional for required fields',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--original-field-name-delimiter'],
                'help': 'Set delimiter to convert to snake case. This option only can be used with --snake-case-field (default: `_` )',
                'default': None,
            },
            {
                'flags': ['--remove-special-field-name-prefix'],
                'help': "Remove field name prefix when first character can't be used as Python field name",
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--snake-case-field'],
                'help': 'Change camel-case field name to snake-case',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--special-field-name-prefix'],
                'help': "Set field name prefix when first character can't be used as Python field name (default:  `field`)",
                'default': None,
            },
            {
                'flags': ['--strip-default-none'],
                'help': 'Strip default None on fields',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-default-kwarg'],
                'action': 'store_true',
                'help': 'Use `default=` instead of a positional argument for Fields that have default values.',
                'default': None,
            },
            {
                'flags': ['--use-default'],
                'help': 'Use default value even if a field is required',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-field-description'],
                'help': 'Use schema description to populate field docstring',
                'action': 'store_true',
                'default': None,
            },
        ],
    },
    {
        'title': 'Model customization',
        'arguments': [
            {
                'flags': ['--allow-extra-fields'],
                'help': 'Allow to pass extra fields, if this flag is not passed, extra fields are forbidden.',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--allow-population-by-field-name'],
                'help': 'Allow population by field name',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--class-name'],
                'help': 'Set class name of root model',
                'default': None,
            },
            {
                'flags': ['--collapse-root-models'],
                'action': 'store_true',
                'default': None,
                'help': 'Models generated with a root-type field will be mergedinto the models using that root-type model',
            },
            {
                'flags': ['--disable-appending-item-suffix'],
                'help': 'Disable appending `Item` suffix to model name in an array',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--disable-timestamp'],
                'help': 'Disable timestamp on file headers',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--enable-faux-immutability'],
                'help': 'Enable faux immutability',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--enable-version-header'],
                'help': 'Enable package version on file headers',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--keep-model-order'],
                'help': "Keep generated models' order",
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--reuse-model'],
                'help': 'Re-use models on the field when a module has the model with the same content',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--target-python-version'],
                'help': 'target python version (default: 3.7)',
                'choices': [v.value for v in PythonVersion],
            },
            {
                'flags': ['--use-schema-description'],
                'help': 'Use schema description to populate class docstring',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-title-as-name'],
                'help': 'use titles as class names of models',
                'action': 'store_true',
                'default': None,
            },
        ],
    },
    {
        'title': 'Template customization',
        'arguments': [
            {
                'flags': ['--aliases'],
                'help': 'Alias mapping file',
                'type': FileType('rt'),
            },
            {
                'flags': ['--custom-file-header-path'],
                'help': 'Custom file header file path',
                'default': None,
                'type': str,
            },
            {
                'flags': ['--custom-file-header'],
                'help': 'Custom file header',
                'type': str,
                'default': None,
            },
            {
                'flags': ['--custom-template-dir'],
                'help': 'Custom template directory',
                'type': str,
            },
            {
                'flags': ['--encoding'],
                'help': f'The encoding of input and output (default: {DEFAULT_ENCODING})',
                'default': None,
            },
            {
                'flags': ['--extra-template-data'],
                'help': 'Extra template data',
                'type': FileType('rt'),
            },
            {
                'flags': ['--use-double-quotes'],
                'action': 'store_true',
                'default': None,
                'help': 'Model generated with double quotes. Single quotes or your black config skip_string_normalization value will be used without this option.',
            },
            {
                'flags': ['--wrap-string-literal'],
                'help': 'Wrap string literal by using black `experimental-string-processing` option (require black 20.8b0 or later)',
                'action': 'store_true',
                'default': None,
            },
        ],
    },
    {
        'title': 'OpenAPI-only options',
        'arguments': [
            {
                'flags': ['--openapi-scopes'],
                'help': 'Scopes of OpenAPI model generation (default: schemas)',
                'choices': [o.value for o in OpenAPIScope],
                'nargs': '+',
                'default': None,
            },
            {
                'flags': ['--strict-nullable'],
                'help': 'Treat default field as a non-nullable field (Only OpenAPI)',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--use-operation-id-as-name'],
                'help': 'use operation id of OpenAPI as class names of models',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--validation'],
                'help': 'Enable validation (Only OpenAPI)',
                'action': 'store_true',
                'default': None,
            },
        ],
    },
    {
        'title': 'General options',
        'arguments': [
            {
                'flags': ['--debug'],
                'help': 'show debug message',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--disable-warnings'],
                'help': 'disable warnings',
                'action': 'store_true',
                'default': None,
            },
            {
                'flags': ['--no-color'],
                'help': 'disable colorized output',
                'action': 'store_true',
                'default': False,
            },
            {
                'flags': ['--version'],
                'help': 'show version',
                'action': 'store_true',
            },
            {
                'flags': ['-h', '--help'],
                'action': 'help',
                'default': '==SUPPRESS==',
                'help': 'show this help message and exit',
            },
        ],
    },
]

arg_groups = ArgumentGroups.parse_obj(arg_groups_data)

for arg_group in arg_groups:
    group = arg_parser.add_argument_group(arg_group.title)

    for argument in arg_group.arguments:
        arg_dict = argument.dict(exclude_unset=True)
        flags, kwargs = arg_dict.pop('flags'), arg_dict
        group.add_argument(*flags, **kwargs)


__all__ = [
    'arg_parser',
    'DEFAULT_ENCODING',
    'namespace',
]
