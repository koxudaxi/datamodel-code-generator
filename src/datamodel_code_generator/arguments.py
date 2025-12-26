"""CLI argument definitions for datamodel-codegen.

Defines the ArgumentParser and all command-line options organized into groups:
base options, typing customization, field customization, model customization,
template customization, OpenAPI-specific options, and general options.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser, ArgumentTypeError, BooleanOptionalAction, Namespace, RawDescriptionHelpFormatter
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, cast

from datamodel_code_generator.enums import (
    DEFAULT_SHARED_MODULE_NAME,
    AllExportsCollisionStrategy,
    AllExportsScope,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    DataModelType,
    FieldTypeCollisionStrategy,
    InputFileType,
    ModuleSplitMode,
    NamingStrategy,
    OpenAPIScope,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    StrictTypes,
    TargetPydanticVersion,
    UnionMode,
)
from datamodel_code_generator.format import DateClassType, DatetimeClassType, Formatter, PythonVersion
from datamodel_code_generator.parser import LiteralType

if TYPE_CHECKING:
    from argparse import Action
    from collections.abc import Iterable

DEFAULT_ENCODING = "utf-8"

namespace = Namespace(no_color=False)


def _dataclass_arguments(value: str) -> DataclassArguments:
    """Parse JSON string and validate it as DataclassArguments."""
    try:
        result = json.loads(value)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON: {e}"
        raise ArgumentTypeError(msg) from e
    if not isinstance(result, dict):
        msg = f"Expected a JSON dictionary, got {type(result).__name__}"
        raise ArgumentTypeError(msg)
    valid_keys = set(DataclassArguments.__annotations__.keys())
    invalid_keys = set(result.keys()) - valid_keys
    if invalid_keys:
        msg = f"Invalid keys: {invalid_keys}. Valid keys are: {valid_keys}"
        raise ArgumentTypeError(msg)
    for key, val in result.items():
        if not isinstance(val, bool):
            msg = f"Expected bool for '{key}', got {type(val).__name__}"
            raise ArgumentTypeError(msg)
    return cast("DataclassArguments", result)


class SortingHelpFormatter(RawDescriptionHelpFormatter):
    """Help formatter that sorts arguments, adds color to section headers, and preserves epilog formatting."""

    def _bold_cyan(self, text: str) -> str:  # noqa: PLR6301
        """Wrap text in ANSI bold cyan escape codes."""
        return f"\x1b[36;1m{text}\x1b[0m"

    def add_arguments(self, actions: Iterable[Action]) -> None:
        """Add arguments sorted by option strings."""
        actions = sorted(actions, key=attrgetter("option_strings"))
        super().add_arguments(actions)

    def start_section(self, heading: str | None) -> None:
        """Start a section with optional colored heading."""
        return super().start_section(heading if namespace.no_color or not heading else self._bold_cyan(heading))


arg_parser = ArgumentParser(
    usage="\n  datamodel-codegen [options]",
    description="Generate Python data models from schema definitions or structured data\n\n"
    "For detailed usage, see: https://datamodel-code-generator.koxudaxi.dev",
    epilog="Documentation: https://datamodel-code-generator.koxudaxi.dev\n"
    "GitHub: https://github.com/koxudaxi/datamodel-code-generator",
    formatter_class=SortingHelpFormatter,
    add_help=False,
)

base_options = arg_parser.add_argument_group("Options")
typing_options = arg_parser.add_argument_group("Typing customization")
field_options = arg_parser.add_argument_group("Field customization")
model_options = arg_parser.add_argument_group("Model customization")
extra_fields_model_options = model_options.add_mutually_exclusive_group()
template_options = arg_parser.add_argument_group("Template customization")
openapi_options = arg_parser.add_argument_group("OpenAPI-only options")
general_options = arg_parser.add_argument_group("General options")

# ======================================================================================
# Base options for input/output
# ======================================================================================
base_options.add_argument(
    "--http-headers",
    nargs="+",
    metavar="HTTP_HEADER",
    help='Set headers in HTTP requests to the remote host. (example: "Authorization: Basic dXNlcjpwYXNz")',
)
base_options.add_argument(
    "--http-query-parameters",
    nargs="+",
    metavar="HTTP_QUERY_PARAMETERS",
    help='Set query parameters in HTTP requests to the remote host. (example: "ref=branch")',
)
base_options.add_argument(
    "--http-ignore-tls",
    help="Disable verification of the remote host's TLS certificate",
    action="store_true",
    default=None,
)
base_options.add_argument(
    "--http-timeout",
    type=float,
    default=None,
    help="Timeout in seconds for HTTP requests to remote hosts (default: 30)",
)
base_options.add_argument(
    "--input",
    help="Input file/directory (default: stdin)",
)
base_options.add_argument(
    "--input-file-type",
    help=(
        "Input file type (default: auto). "
        "Use 'jsonschema', 'openapi', or 'graphql' for schema definitions. "
        "Use 'json', 'yaml', or 'csv' for raw sample data to infer a schema automatically."
    ),
    choices=[i.value for i in InputFileType],
)
base_options.add_argument(
    "--output",
    help="Output file (default: stdout)",
)
base_options.add_argument(
    "--output-model-type",
    help="Output model type (default: pydantic.BaseModel)",
    choices=[i.value for i in DataModelType],
)
base_options.add_argument(
    "--url",
    help="Input file URL. `--input` is ignored when `--url` is used",
)
base_options.add_argument(
    "--input-model",
    help="Python import path to a Pydantic v2 model or schema dict "
    "(e.g., 'mypackage.module:ClassName' or 'mypackage.schemas:SCHEMA_DICT'). "
    "For dict input, --input-file-type is required. "
    "Cannot be used with --input or --url.",
    metavar="MODULE:NAME",
)

# ======================================================================================
# Customization options for generated models
# ======================================================================================
extra_fields_model_options.add_argument(
    "--allow-extra-fields",
    help="Deprecated: Allow passing extra fields. This flag is deprecated. Use `--extra-fields=allow` instead.",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--allow-population-by-field-name",
    help="Allow population by field name",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--class-name",
    help="Set class name of root model",
    default=None,
)
model_options.add_argument(
    "--collapse-root-models",
    action="store_true",
    default=None,
    help="Models generated with a root-type field will be merged into the models using that root-type model",
)
model_options.add_argument(
    "--collapse-root-models-name-strategy",
    help="Strategy for naming when collapsing root models that reference other models. "
    "'child': Keep inner model's name (default). 'parent': Use wrapper's name for inner model. "
    "Requires --collapse-root-models to be set.",
    choices=[s.value for s in CollapseRootModelsNameStrategy],
    default=None,
)
model_options.add_argument(
    "--collapse-reuse-models",
    action="store_true",
    default=None,
    help="When used with --reuse-model, collapse duplicate models by replacing references instead of creating "
    "empty inheritance subclasses. This eliminates 'class Foo(Bar): pass' patterns",
)
model_options.add_argument(
    "--skip-root-model",
    action="store_true",
    default=None,
    help="Skip generating the model for the root schema element",
)
model_options.add_argument(
    "--disable-appending-item-suffix",
    help="Disable appending `Item` suffix to model name in an array",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--disable-timestamp",
    help="Disable timestamp on file headers",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--enable-faux-immutability",
    help="Enable faux immutability",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--enable-version-header",
    help="Enable package version on file headers",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--enable-command-header",
    help="Enable command-line options on file headers for reproducibility",
    action="store_true",
    default=None,
)
extra_fields_model_options.add_argument(
    "--extra-fields",
    help="Set the generated models to allow, forbid, or ignore extra fields.",
    choices=["allow", "ignore", "forbid"],
    default=None,
)
model_options.add_argument(
    "--keep-model-order",
    help="Keep generated models' order",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--keyword-only",
    help="Defined models as keyword only (for example dataclass(kw_only=True)).",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--frozen-dataclasses",
    help="Generate frozen dataclasses (dataclass(frozen=True)). Only applies to dataclass output.",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--dataclass-arguments",
    type=_dataclass_arguments,
    default=None,
    help=(
        "Custom dataclass arguments as a JSON dictionary, "
        'e.g. \'{"frozen": true, "kw_only": true}\'. '
        "Overrides --frozen-dataclasses and similar flags."
    ),
)
model_options.add_argument(
    "--reuse-model",
    help="Reuse models on the field when a module has the model with the same content",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--reuse-scope",
    help="Scope for model reuse deduplication: module (per-file, default) or tree (cross-file with shared module). "
    "Only effective when --reuse-model is set.",
    choices=[s.value for s in ReuseScope],
    default=None,
)
model_options.add_argument(
    "--shared-module-name",
    help=f'Name of the shared module for --reuse-scope=tree (default: "{DEFAULT_SHARED_MODULE_NAME}"). '
    f'Use this option if your schema has a file named "{DEFAULT_SHARED_MODULE_NAME}".',
    default=None,
)
model_options.add_argument(
    "--target-python-version",
    help="target python version",
    choices=[v.value for v in PythonVersion],
)
model_options.add_argument(
    "--target-pydantic-version",
    help="Target Pydantic version for generated code. "
    "'2': Pydantic 2.0+ compatible (default, uses populate_by_name). "
    "'2.11': Pydantic 2.11+ (uses validate_by_name).",
    choices=[v.value for v in TargetPydanticVersion],
    default=None,
)
model_options.add_argument(
    "--treat-dot-as-module",
    help="Treat dotted schema names as module paths, creating nested directory structures (e.g., 'foo.bar.Model' "
    "becomes 'foo/bar.py'). Use --no-treat-dot-as-module to keep dots in names as underscores for single-file output.",
    action=BooleanOptionalAction,
    default=None,
)
model_options.add_argument(
    "--use-generic-base-class",
    help="Generate a shared base class with model configuration (e.g., extra='forbid') "
    "instead of repeating the configuration in each model. Keeps code DRY.",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--use-schema-description",
    help="Use schema description to populate class docstring",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--use-title-as-name",
    help="use titles as class names of models",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--use-pendulum",
    help="use pendulum instead of datetime",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--use-standard-primitive-types",
    help="Use Python standard library types for string formats (UUID, IPv4Address, etc.) "
    "instead of str. Affects dataclass, msgspec, TypedDict output. "
    "Pydantic already uses these types by default.",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--use-exact-imports",
    help='import exact types instead of modules, for example: "from .foo import Bar" instead of '
    '"from . import foo" with "foo.Bar"',
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--output-datetime-class",
    help="Choose Datetime class between AwareDatetime, NaiveDatetime, PastDatetime, FutureDatetime or datetime. "
    "Each output model has its default mapping (for example pydantic: datetime, dataclass: str, ...)",
    choices=[i.value for i in DatetimeClassType],
    default=None,
)
model_options.add_argument(
    "--output-date-class",
    help="Choose Date class between PastDate, FutureDate or date. (Pydantic v2 only) "
    "Each output model has its default mapping.",
    choices=[i.value for i in DateClassType],
    default=None,
)
model_options.add_argument(
    "--parent-scoped-naming",
    help="[Deprecated: use --naming-strategy parent-prefixed] Set name of models defined inline from the parent model",
    action="store_true",
    default=None,
)
model_options.add_argument(
    "--naming-strategy",
    help="Strategy for generating unique model names when duplicates occur. "
    "'numbered' (default): Append numeric suffix (Address, Address1, Address2). "
    "Simple but names don't indicate context. "
    "'parent-prefixed': Prefix with parent model name using underscore "
    "(Company_Address, Company_Employee_Address for nested). Names show hierarchy. "
    "'full-path': Similar to parent-prefixed but joins with CamelCase "
    "(CompanyAddress, CompanyEmployeeAddress). More readable for deep nesting. "
    "'primary-first': Keep clean names for primary definitions (in /definitions/ or "
    "/components/schemas/), only add suffix to inline/nested duplicates.",
    choices=[s.value for s in NamingStrategy],
    default=None,
)
model_options.add_argument(
    "--duplicate-name-suffix",
    help="JSON mapping of type to suffix for resolving duplicate name conflicts. "
    'Example: \'{"model": "Schema"}\' changes Address1 to AddressSchema. '
    "Keys: 'model' (for classes), 'enum' (for enums), 'default' (fallback). "
    "When not specified, uses numeric suffix (Address1, Address2).",
    type=str,
    default=None,
)
model_options.add_argument(
    "--all-exports-scope",
    help="Generate __all__ in __init__.py with re-exports. "
    "'children': export from direct child modules only. "
    "'recursive': export from all descendant modules.",
    choices=[s.value for s in AllExportsScope],
    default=None,
)
model_options.add_argument(
    "--all-exports-collision-strategy",
    help="Strategy for name collisions when using --all-exports-scope=recursive. "
    "'error': raise an error (default). "
    "'minimal-prefix': add module prefix only to colliding names. "
    "'full-prefix': add full module path prefix to colliding names.",
    choices=[s.value for s in AllExportsCollisionStrategy],
    default=None,
)
model_options.add_argument(
    "--module-split-mode",
    help="Split generated models into separate files. 'single': generate one file per model class.",
    choices=[m.value for m in ModuleSplitMode],
    default=None,
)

# ======================================================================================
# Typing options for generated models
# ======================================================================================
typing_options.add_argument(
    "--base-class",
    help="Base Class (default: pydantic.BaseModel)",
    type=str,
)
typing_options.add_argument(
    "--base-class-map",
    help="Model-specific base class mapping (JSON). "
    'Example: \'{"MyModel": "custom.BaseA", "OtherModel": "custom.BaseB"}\'. '
    "Priority: base-class-map > customBasePath (in schema) > base-class.",
    type=json.loads,
    default=None,
)
typing_options.add_argument(
    "--enum-field-as-literal",
    help="Parse enum field as literal. "
    "all: all enum field type are Literal. "
    "one: field type is Literal when an enum has only one possible value. "
    "none: always use Enum class (never convert to Literal)",
    choices=[lt.value for lt in LiteralType],
    default=None,
)
typing_options.add_argument(
    "--enum-field-as-literal-map",
    help="Per-field override for enum/literal generation. "
    "Format: JSON object mapping field names to 'literal' or 'enum'. "
    'Example: \'{"status": "literal", "priority": "enum"}\'. '
    "Overrides --enum-field-as-literal for matched fields.",
    type=json.loads,
    default=None,
)
typing_options.add_argument(
    "--ignore-enum-constraints",
    help="Ignore enum constraints and use the base type (e.g., str, int) instead of generating Enum classes",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--field-constraints",
    help="Use field constraints and not con* annotations",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--set-default-enum-member",
    help="Set enum members as default values for enum field",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--strict-types",
    help="Use strict types",
    choices=[t.value for t in StrictTypes],
    nargs="+",
)
typing_options.add_argument(
    "--use-annotated",
    help="Use typing.Annotated for Field(). Also, `--field-constraints` option will be enabled.",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-serialize-as-any",
    help="Use pydantic.SerializeAsAny for fields with types that have subtypes (Pydantic v2 only)",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-generic-container-types",
    help="Use generic container types for type hinting (typing.Sequence, typing.Mapping). "
    "If `--use-standard-collections` option is set, then import from collections.abc instead of typing",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-non-positive-negative-number-constrained-types",
    help="Use the Non{Positive,Negative}{FloatInt} types instead of the corresponding con* constrained types.",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-decimal-for-multiple-of",
    help="Use condecimal instead of confloat for float/number fields with multipleOf constraint "
    "(Pydantic only). Avoids floating-point precision issues in validation.",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-one-literal-as-default",
    help="Use one literal as default value for one literal field",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-enum-values-in-discriminator",
    help="Use enum member literals in discriminator fields instead of string literals",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-standard-collections",
    help="Use standard collections for type hinting (list, dict). Default: enabled",
    action=BooleanOptionalAction,
    default=None,
)
typing_options.add_argument(
    "--use-subclass-enum",
    help="Define generic Enum class as subclass with field type when enum has type (int, float, bytes, str)",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-specialized-enum",
    help="Use specialized Enum class (StrEnum, IntEnum). Requires --target-python-version 3.11+",
    action=BooleanOptionalAction,
    default=None,
)
typing_options.add_argument(
    "--use-union-operator",
    help="Use | operator for Union type (PEP 604). Default: enabled",
    action=BooleanOptionalAction,
    default=None,
)
typing_options.add_argument(
    "--use-unique-items-as-set",
    help="define field type as `set` when the field attribute has `uniqueItems`",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-tuple-for-fixed-items",
    help="Generate tuple types for arrays with items array syntax when minItems equals maxItems equals items length",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--allof-merge-mode",
    help="Mode for field merging in allOf schemas. "
    "'constraints': merge only constraints (minItems, maxItems, pattern, etc.) from parent (default). "
    "'all': merge constraints plus annotations (default, examples) from parent. "
    "'none': do not merge any fields from parent properties.",
    choices=[m.value for m in AllOfMergeMode],
    default=None,
)
typing_options.add_argument(
    "--use-type-alias",
    help="Use TypeAlias instead of root models (experimental)",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--use-root-model-type-alias",
    help="Use type alias format for RootModel (e.g., Foo = RootModel[Bar]) "
    "instead of class inheritance (Pydantic v2 only)",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--disable-future-imports",
    help="Disable __future__ imports",
    action="store_true",
    default=None,
)
typing_options.add_argument(
    "--type-mappings",
    help="Override default type mappings. "
    'Format: "type+format=target" (e.g., "string+binary=string" to map binary format to string type) '
    'or "format=target" (e.g., "binary=string"). '
    "Can be specified multiple times.",
    nargs="+",
    type=str,
    default=None,
)
typing_options.add_argument(
    "--type-overrides",
    help="Replace schema model types with custom Python types. "
    "Format: JSON object mapping model names to Python import paths. "
    'Model-level: \'{"CustomType": "my_app.types.MyType"}\' replaces all references. '
    'Scoped: \'{"User.field": "my_app.Type"}\' replaces specific field only.',
    type=json.loads,
    default=None,
)

# ======================================================================================
# Customization options for generated model fields
# ======================================================================================
field_options.add_argument(
    "--capitalise-enum-members",
    "--capitalize-enum-members",
    help="Capitalize field names on enum",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--empty-enum-field-name",
    help="Set field name when enum value is empty (default:  `_`)",
    default=None,
)
field_options.add_argument(
    "--field-extra-keys",
    help="Add extra keys to field parameters",
    type=str,
    nargs="+",
)
field_options.add_argument(
    "--field-extra-keys-without-x-prefix",
    help="Add extra keys with `x-` prefix to field parameters. The extra keys are stripped of the `x-` prefix.",
    type=str,
    nargs="+",
)
field_options.add_argument(
    "--field-include-all-keys",
    help="Add all keys to field parameters",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--model-extra-keys",
    help="Add extra keys from schema extensions (x-* fields) to model_config json_schema_extra",
    type=str,
    nargs="+",
)
field_options.add_argument(
    "--model-extra-keys-without-x-prefix",
    help="Add extra keys with `x-` prefix to model_config json_schema_extra. "
    "The extra keys are stripped of the `x-` prefix.",
    type=str,
    nargs="+",
)
field_options.add_argument(
    "--force-optional",
    help="Force optional for required fields",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--original-field-name-delimiter",
    help="Set delimiter to convert to snake case. This option only can be used with --snake-case-field (default: `_` )",
    default=None,
)
field_options.add_argument(
    "--remove-special-field-name-prefix",
    help="Remove field name prefix if it has a special meaning e.g. underscores",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--snake-case-field",
    help="Change camel-case field name to snake-case",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--special-field-name-prefix",
    help="Set field name prefix when first character can't be used as Python field name (default:  `field`)",
    default=None,
)
field_options.add_argument(
    "--strict-nullable",
    help="Treat default field as a non-nullable field",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--strip-default-none",
    help="Strip default None on fields",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--use-default",
    help="Use default value even if a field is required",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--use-default-kwarg",
    action="store_true",
    help="Use `default=` instead of a positional argument for Fields that have default values.",
    default=None,
)
field_options.add_argument(
    "--use-field-description",
    help="Use schema description to populate field docstring",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--use-field-description-example",
    help="Use schema example to populate field docstring",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--use-attribute-docstrings",
    help="Set use_attribute_docstrings=True in Pydantic v2 ConfigDict",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--use-inline-field-description",
    help="Use schema description to populate field docstring as inline docstring",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--union-mode",
    help="Union mode for only pydantic v2 field",
    choices=[u.value for u in UnionMode],
    default=None,
)
field_options.add_argument(
    "--no-alias",
    help="""Do not add a field alias. E.g., if --snake-case-field is used along with a base class, which has an
            alias_generator""",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--use-frozen-field",
    help="Use Field(frozen=True) for readOnly fields (Pydantic v2) or Field(allow_mutation=False) (Pydantic v1)",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--use-default-factory-for-optional-nested-models",
    help="Use default_factory for optional nested model fields instead of None default. "
    "E.g., `field: Model | None = Field(default_factory=Model)` instead of `field: Model | None = None`",
    action="store_true",
    default=None,
)
field_options.add_argument(
    "--field-type-collision-strategy",
    help="Strategy for handling field name and type name collisions (Pydantic v2 only). "
    "'rename-field': rename field with suffix and add alias (default). "
    "'rename-type': rename type class with suffix to preserve field name.",
    choices=[s.value for s in FieldTypeCollisionStrategy],
    default=None,
)

# ======================================================================================
# Options for templating output
# ======================================================================================
template_options.add_argument(
    "--aliases",
    help="Alias mapping file (JSON) for renaming fields. "
    "Supports hierarchical formats: "
    "Flat: {'field': 'alias'} applies to all occurrences. "
    "Scoped: {'ClassName.field': 'alias'} applies to specific class. "
    "Priority: scoped > flat. "
    "Example: {'User.name': 'user_name', 'Address.name': 'addr_name', 'id': 'id_'}",
    type=Path,
)
template_options.add_argument(
    "--custom-file-header",
    help="Custom file header",
    type=str,
    default=None,
)
template_options.add_argument(
    "--custom-file-header-path",
    help="Custom file header file path",
    default=None,
    type=str,
)
template_options.add_argument(
    "--custom-template-dir",
    help="Custom template directory",
    type=str,
)
template_options.add_argument(
    "--encoding",
    help=f"The encoding of input and output (default: {DEFAULT_ENCODING})",
    default=None,
)
template_options.add_argument(
    "--extra-template-data",
    help="Extra template data for output models. Input is supposed to be a json/yaml file. "
    "For OpenAPI and Jsonschema the keys are the spec path of the object, or the name of the object if you want to "
    "apply the template data to multiple objects with the same name. "
    "If you are using another input file type (e.g. GraphQL), the key is the name of the object. "
    "The value is a dictionary of the template data to add.",
    type=Path,
)
template_options.add_argument(
    "--use-double-quotes",
    action="store_true",
    default=None,
    help="Model generated with double quotes. Single quotes or "
    "your black config skip_string_normalization value will be used without this option.",
)
template_options.add_argument(
    "--wrap-string-literal",
    help="Wrap string literal by using black `experimental-string-processing` option (require black 20.8b0 or later)",
    action="store_true",
    default=None,
)
base_options.add_argument(
    "--additional-imports",
    help='Custom imports for output (delimited list input). For example "datetime.date,datetime.datetime"',
    type=str,
    default=None,
)
base_options.add_argument(
    "--class-decorators",
    help="Custom decorators for generated model classes (delimited list input). "
    'For example "@dataclass_json(letter_case=LetterCase.CAMEL)". '
    'The "@" prefix is optional and will be added automatically if missing.',
    type=str,
    default=None,
)
base_options.add_argument(
    "--formatters",
    help="Formatters for output (default: [black, isort])",
    choices=[f.value for f in Formatter],
    nargs="+",
    default=None,
)
base_options.add_argument(
    "--custom-formatters",
    help="List of modules with custom formatter (delimited list input).",
    type=str,
    default=None,
)
template_options.add_argument(
    "--custom-formatters-kwargs",
    help="A file with kwargs for custom formatters.",
    type=Path,
)

# ======================================================================================
# Options specific to OpenAPI input schemas
# ======================================================================================
openapi_options.add_argument(
    "--openapi-scopes",
    help="Scopes of OpenAPI model generation (default: schemas)",
    choices=[o.value for o in OpenAPIScope],
    nargs="+",
    default=None,
)
openapi_options.add_argument(
    "--use-operation-id-as-name",
    help="use operation id of OpenAPI as class names of models",
    action="store_true",
    default=None,
)
openapi_options.add_argument(
    "--include-path-parameters",
    help="Include path parameters in generated parameter models in addition to query parameters (Only OpenAPI)",
    action="store_true",
    default=None,
)
openapi_options.add_argument(
    "--validation",
    help="Deprecated: Enable validation (Only OpenAPI). this option is deprecated. it will be removed in future "
    "releases",
    action="store_true",
    default=None,
)
openapi_options.add_argument(
    "--read-only-write-only-model-type",
    help="Model generation for readOnly/writeOnly fields: "
    "'request-response' = Request/Response models only (no base model), "
    "'all' = Base + Request + Response models.",
    choices=[e.value for e in ReadOnlyWriteOnlyModelType],
    default=None,
)
openapi_options.add_argument(
    "--use-status-code-in-response-name",
    help="Include HTTP status code in response model names (e.g., ResourceGetResponse200, ResourceGetResponseDefault)",
    action="store_true",
    default=None,
)

# ======================================================================================
# General options
# ======================================================================================
general_options.add_argument(
    "--check",
    action="store_true",
    default=None,
    help="Verify generated files are up-to-date without modifying them. "
    "Exits with code 1 if differences found, 0 if up-to-date. "
    "Useful for CI to ensure generated code is committed.",
)
general_options.add_argument(
    "--debug",
    help="show debug message (require \"debug\". `$ pip install 'datamodel-code-generator[debug]'`)",
    action="store_true",
    default=None,
)
general_options.add_argument(
    "--disable-warnings",
    help="disable warnings",
    action="store_true",
    default=None,
)
general_options.add_argument(
    "-h",
    "--help",
    action="help",
    default="==SUPPRESS==",
    help="show this help message and exit",
)
general_options.add_argument(
    "--no-color",
    action="store_true",
    default=False,
    help="disable colorized output",
)
general_options.add_argument(
    "--generate-pyproject-config",
    action="store_true",
    default=None,
    help="Generate pyproject.toml configuration from the provided CLI arguments and exit",
)
general_options.add_argument(
    "--generate-cli-command",
    action="store_true",
    default=None,
    help="Generate CLI command from pyproject.toml configuration and exit",
)
general_options.add_argument(
    "--generate-prompt",
    type=str,
    nargs="?",
    const="",
    default=None,
    metavar="QUESTION",
    help=(
        "Generate a prompt for consulting LLMs about CLI options. "
        "Optionally provide your question as an argument. "
        "Pipe to CLI tools (e.g., `| claude -p`, `| codex exec`) "
        "or copy to clipboard (e.g., `| pbcopy`, `| xclip`) for web LLM chats."
    ),
)
general_options.add_argument(
    "--ignore-pyproject",
    action="store_true",
    default=False,
    help="Ignore pyproject.toml configuration",
)
general_options.add_argument(
    "--profile",
    help="Use a named profile from pyproject.toml [tool.datamodel-codegen.profiles.<name>]",
    default=None,
)
general_options.add_argument(
    "--watch",
    action="store_true",
    default=None,
    help="Watch input file(s) for changes and regenerate output automatically",
)
general_options.add_argument(
    "--watch-delay",
    type=float,
    default=None,
    help="Debounce delay in seconds for watch mode (default: 0.5)",
)
general_options.add_argument(
    "--version",
    action="store_true",
    help="show version",
)

__all__ = [
    "DEFAULT_ENCODING",
    "arg_parser",
    "namespace",
]
