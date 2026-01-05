# 🔍 Quick Reference

All CLI options in one page for easy **Ctrl+F** searching.

👆 Click any option to see detailed documentation with examples.

---

```text
datamodel-codegen [OPTIONS]
```

## 📂 All Options by Category

### 📁 Base Options

| Option | Description |
|--------|-------------|
| [`--encoding`](base-options.md#encoding) | Specify character encoding for input and output files. |
| [`--input`](base-options.md#input) | Specify the input schema file path. |
| [`--input-file-type`](base-options.md#input-file-type) | Specify the input file type for code generation. |
| [`--input-model`](base-options.md#input-model) | Import a Python type or dict schema from a module. |
| [`--input-model-ref-strategy`](base-options.md#input-model-ref-strategy) | Strategy for referenced types when using --input-model. |
| [`--output`](base-options.md#output) | Specify the destination path for generated Python code. |
| [`--schema-version`](base-options.md#schema-version) | Schema version to use for parsing. |
| [`--schema-version-mode`](base-options.md#schema-version-mode) | Schema version validation mode. |
| [`--url`](base-options.md#url) | Fetch schema from URL with custom HTTP headers. |

### 🔧 Typing Customization

| Option | Description |
|--------|-------------|
| [`--allof-class-hierarchy`](typing-customization.md#allof-class-hierarchy) | Controls how allOf schemas are represented in the generated class hierarchy. |
| [`--allof-merge-mode`](typing-customization.md#allof-merge-mode) | Merge constraints from root model references in allOf schemas. |
| [`--disable-future-imports`](typing-customization.md#disable-future-imports) | Prevent automatic addition of __future__ imports in generated code. |
| [`--enum-field-as-literal`](typing-customization.md#enum-field-as-literal) | Convert all enum fields to Literal types instead of Enum classes. |
| [`--enum-field-as-literal-map`](typing-customization.md#enum-field-as-literal-map) | Override enum/literal generation per-field via JSON mapping. |
| [`--ignore-enum-constraints`](typing-customization.md#ignore-enum-constraints) | Ignore enum constraints and use base string type instead of Enum classes. |
| [`--no-use-specialized-enum`](typing-customization.md#no-use-specialized-enum) | Disable specialized Enum classes for Python 3.11+ code generation. |
| [`--no-use-standard-collections`](typing-customization.md#no-use-standard-collections) | Use typing.Dict/List instead of built-in dict/list for container types. |
| [`--no-use-union-operator`](typing-customization.md#no-use-union-operator) | Use Union[X, Y] / Optional[X] instead of X | Y union operator. |
| [`--output-date-class`](typing-customization.md#output-date-class) | Specify date class type for date schema fields. |
| [`--output-datetime-class`](typing-customization.md#output-datetime-class) | Specify datetime class type for date-time schema fields. |
| [`--strict-types`](typing-customization.md#strict-types) | Enable strict type validation for specified Python types. |
| [`--type-mappings`](typing-customization.md#type-mappings) | Override default type mappings for schema formats. |
| [`--type-overrides`](typing-customization.md#type-overrides) | Replace schema model types with custom Python types via JSON mapping. |
| [`--use-annotated`](typing-customization.md#use-annotated) | Use typing.Annotated for Field() with constraints. |
| [`--use-decimal-for-multiple-of`](typing-customization.md#use-decimal-for-multiple-of) | Generate Decimal types for fields with multipleOf constraint. |
| [`--use-generic-container-types`](typing-customization.md#use-generic-container-types) | Use generic container types (Sequence, Mapping) for type hinting. |
| [`--use-non-positive-negative-number-constrained-types`](typing-customization.md#use-non-positive-negative-number-constrained-types) | Use NonPositive/NonNegative types for number constraints. |
| [`--use-pendulum`](typing-customization.md#use-pendulum) | Use pendulum types for date/time fields instead of datetime module. |
| [`--use-root-model-type-alias`](typing-customization.md#use-root-model-type-alias) | Generate RootModel as type alias format for better mypy support. |
| [`--use-specialized-enum`](typing-customization.md#use-specialized-enum) | Generate StrEnum/IntEnum for string/integer enums (Python 3.11+). |
| [`--use-standard-collections`](typing-customization.md#use-standard-collections) | Use built-in dict/list instead of typing.Dict/List. |
| [`--use-standard-primitive-types`](typing-customization.md#use-standard-primitive-types) | Use Python standard library types for string formats instead of str. |
| [`--use-tuple-for-fixed-items`](typing-customization.md#use-tuple-for-fixed-items) | Generate tuple types for arrays with items array syntax. |
| [`--use-type-alias`](typing-customization.md#use-type-alias) | Use TypeAlias instead of root models for type definitions (experimental). |
| [`--use-union-operator`](typing-customization.md#use-union-operator) | Use | operator for Union types (PEP 604). |
| [`--use-unique-items-as-set`](typing-customization.md#use-unique-items-as-set) | Generate set types for arrays with uniqueItems constraint. |

### 🏷️ Field Customization

| Option | Description |
|--------|-------------|
| [`--aliases`](field-customization.md#aliases) | Apply custom field and class name aliases from JSON file. |
| [`--capitalize-enum-members`](field-customization.md#capitalize-enum-members) | Capitalize enum member names to UPPER_CASE format. |
| [`--default-values`](field-customization.md#default-values) | Override field default values from external JSON file. |
| [`--empty-enum-field-name`](field-customization.md#empty-enum-field-name) | Name for empty string enum field values. |
| [`--extra-fields`](field-customization.md#extra-fields) | Configure how generated models handle extra fields not defined in schema. |
| [`--field-constraints`](field-customization.md#field-constraints) | Generate Field() with validation constraints from schema. |
| [`--field-extra-keys`](field-customization.md#field-extra-keys) | Include specific extra keys in Field() definitions. |
| [`--field-extra-keys-without-x-prefix`](field-customization.md#field-extra-keys-without-x-prefix) | Include schema extension keys in Field() without requiring 'x-' prefix. |
| [`--field-include-all-keys`](field-customization.md#field-include-all-keys) | Include all schema keys in Field() json_schema_extra. |
| [`--field-type-collision-strategy`](field-customization.md#field-type-collision-strategy) | Rename type class instead of field when names collide (Pydantic v2 only). |
| [`--no-alias`](field-customization.md#no-alias) | Disable Field alias generation for non-Python-safe property names. |
| [`--original-field-name-delimiter`](field-customization.md#original-field-name-delimiter) | Specify delimiter for original field names when using snake-case conversion. |
| [`--remove-special-field-name-prefix`](field-customization.md#remove-special-field-name-prefix) | Remove the special prefix from field names. |
| [`--set-default-enum-member`](field-customization.md#set-default-enum-member) | Set the first enum member as the default value for enum fields. |
| [`--snake-case-field`](field-customization.md#snake-case-field) | Convert field names to snake_case format. |
| [`--special-field-name-prefix`](field-customization.md#special-field-name-prefix) | Prefix to add to special field names (like reserved keywords). |
| [`--use-attribute-docstrings`](field-customization.md#use-attribute-docstrings) | Generate field descriptions as attribute docstrings instead of Field description... |
| [`--use-enum-values-in-discriminator`](field-customization.md#use-enum-values-in-discriminator) | Use enum values in discriminator mappings for union types. |
| [`--use-field-description`](field-customization.md#use-field-description) | Include schema descriptions as Field docstrings. |
| [`--use-field-description-example`](field-customization.md#use-field-description-example) | Add field examples to docstrings. |
| [`--use-inline-field-description`](field-customization.md#use-inline-field-description) | Add field descriptions as inline comments. |
| [`--use-schema-description`](field-customization.md#use-schema-description) | Use schema description as class docstring. |
| [`--use-serialization-alias`](field-customization.md#use-serialization-alias) | Use serialization_alias instead of alias for field aliasing (Pydantic v2 only). |
| [`--use-title-as-name`](field-customization.md#use-title-as-name) | Use schema title as the generated class name. |

### 🏗️ Model Customization

| Option | Description |
|--------|-------------|
| [`--allow-extra-fields`](model-customization.md#allow-extra-fields) | Allow extra fields in generated Pydantic models (extra='allow'). |
| [`--allow-population-by-field-name`](model-customization.md#allow-population-by-field-name) | Allow Pydantic model population by field name (not just alias). |
| [`--base-class`](model-customization.md#base-class) | Specify a custom base class for generated models. |
| [`--base-class-map`](model-customization.md#base-class-map) | Specify different base classes for specific models via JSON mapping. |
| [`--class-name`](model-customization.md#class-name) | Override the auto-generated class name with a custom name. |
| [`--class-name-affix-scope`](model-customization.md#class-name-affix-scope) | Control which classes receive the prefix/suffix. |
| [`--class-name-prefix`](model-customization.md#class-name-prefix) | Add a prefix to all generated class names. |
| [`--class-name-suffix`](model-customization.md#class-name-suffix) | Add a suffix to all generated class names. |
| [`--collapse-reuse-models`](model-customization.md#collapse-reuse-models) | Collapse duplicate models by replacing references instead of inheritance. |
| [`--collapse-root-models`](model-customization.md#collapse-root-models) | Inline root model definitions instead of creating separate wrapper classes. |
| [`--collapse-root-models-name-strategy`](model-customization.md#collapse-root-models-name-strategy) | Select which name to keep when collapsing root models with object references. |
| [`--dataclass-arguments`](model-customization.md#dataclass-arguments) | Customize dataclass decorator arguments via JSON dictionary. |
| [`--duplicate-name-suffix`](model-customization.md#duplicate-name-suffix) | Customize suffix for duplicate model names. |
| [`--enable-faux-immutability`](model-customization.md#enable-faux-immutability) | Enable faux immutability in Pydantic v1 models (allow_mutation=False). |
| [`--force-optional`](model-customization.md#force-optional) | Force all fields to be Optional regardless of required status. |
| [`--frozen-dataclasses`](model-customization.md#frozen-dataclasses) | Generate frozen dataclasses with optional keyword-only fields. |
| [`--keep-model-order`](model-customization.md#keep-model-order) | Keep model definition order as specified in schema. |
| [`--keyword-only`](model-customization.md#keyword-only) | Generate dataclasses with keyword-only fields (Python 3.10+). |
| [`--model-extra-keys`](model-customization.md#model-extra-keys) | Add model-level schema extensions to ConfigDict json_schema_extra. |
| [`--model-extra-keys-without-x-prefix`](model-customization.md#model-extra-keys-without-x-prefix) | Strip x- prefix from model-level schema extensions and add to ConfigDict json_sc... |
| [`--naming-strategy`](model-customization.md#naming-strategy) | Use parent-prefixed naming strategy for duplicate model names. |
| [`--output-model-type`](model-customization.md#output-model-type) | Select the output model type (Pydantic v1/v2, dataclasses, TypedDict, msgspec). |
| [`--parent-scoped-naming`](model-customization.md#parent-scoped-naming) | Namespace models by their parent scope to avoid naming conflicts. |
| [`--reuse-model`](model-customization.md#reuse-model) | Reuse identical model definitions instead of generating duplicates. |
| [`--reuse-scope`](model-customization.md#reuse-scope) | Scope for model reuse detection (root or tree). |
| [`--skip-root-model`](model-customization.md#skip-root-model) | Skip generation of root model when schema contains nested definitions. |
| [`--strict-nullable`](model-customization.md#strict-nullable) | Treat default field as a non-nullable field. |
| [`--strip-default-none`](model-customization.md#strip-default-none) | Remove fields with None as default value from generated models. |
| [`--target-pydantic-version`](model-customization.md#target-pydantic-version) | Target Pydantic version for generated code compatibility. |
| [`--target-python-version`](model-customization.md#target-python-version) | Target Python version for generated code syntax and imports. |
| [`--union-mode`](model-customization.md#union-mode) | Union mode for combining anyOf/oneOf schemas (smart or left_to_right). |
| [`--use-default`](model-customization.md#use-default) | Use default values from schema in generated models. |
| [`--use-default-factory-for-optional-nested-models`](model-customization.md#use-default-factory-for-optional-nested-models) | Generate default_factory for optional nested model fields. |
| [`--use-default-kwarg`](model-customization.md#use-default-kwarg) | Use default= keyword argument instead of positional argument for fields with def... |
| [`--use-frozen-field`](model-customization.md#use-frozen-field) | Generate frozen (immutable) field definitions for readOnly properties. |
| [`--use-generic-base-class`](model-customization.md#use-generic-base-class) | Generate a shared base class with model configuration to avoid repetition (DRY).... |
| [`--use-one-literal-as-default`](model-customization.md#use-one-literal-as-default) | Use single literal value as default when enum has only one option. |
| [`--use-serialize-as-any`](model-customization.md#use-serialize-as-any) | Wrap fields with subtypes in Pydantic's SerializeAsAny. |
| [`--use-subclass-enum`](model-customization.md#use-subclass-enum) | Generate typed Enum subclasses for enums with specific field types. |

### 🎨 Template Customization

| Option | Description |
|--------|-------------|
| [`--additional-imports`](template-customization.md#additional-imports) | Add custom imports to generated output files. |
| [`--class-decorators`](template-customization.md#class-decorators) | Add custom decorators to generated model classes. |
| [`--custom-file-header`](template-customization.md#custom-file-header) | Add custom header text to the generated file. |
| [`--custom-file-header-path`](template-customization.md#custom-file-header-path) | Add custom header content from file to generated code. |
| [`--custom-formatters`](template-customization.md#custom-formatters) | Apply custom Python code formatters to generated output. |
| [`--custom-formatters-kwargs`](template-customization.md#custom-formatters-kwargs) | Pass custom arguments to custom formatters via JSON file. |
| [`--custom-template-dir`](template-customization.md#custom-template-dir) | Use custom Jinja2 templates for model generation. |
| [`--disable-appending-item-suffix`](template-customization.md#disable-appending-item-suffix) | Disable appending 'Item' suffix to array item types. |
| [`--disable-timestamp`](template-customization.md#disable-timestamp) | Disable timestamp in generated file header for reproducible output. |
| [`--enable-command-header`](template-customization.md#enable-command-header) | Include command-line options in file header for reproducibility. |
| [`--enable-version-header`](template-customization.md#enable-version-header) | Include tool version information in file header. |
| [`--extra-template-data`](template-customization.md#extra-template-data) | Pass custom template variables from JSON file for code generation. |
| [`--formatters`](template-customization.md#formatters) | Specify code formatters to apply to generated output. |
| [`--no-treat-dot-as-module`](template-customization.md#no-treat-dot-as-module) | Keep dots in schema names as underscores for flat output. |
| [`--treat-dot-as-module`](template-customization.md#treat-dot-as-module) | Treat dots in schema names as module separators. |
| [`--use-double-quotes`](template-customization.md#use-double-quotes) | Use double quotes for string literals in generated code. |
| [`--use-exact-imports`](template-customization.md#use-exact-imports) | Import exact types instead of modules. |
| [`--validators`](template-customization.md#validators) | Add custom field validators to generated Pydantic v2 models. |
| [`--wrap-string-literal`](template-customization.md#wrap-string-literal) | Wrap long string literals across multiple lines. |

### 📘 OpenAPI-only Options

| Option | Description |
|--------|-------------|
| [`--include-path-parameters`](openapi-only-options.md#include-path-parameters) | Include OpenAPI path parameters in generated parameter models. |
| [`--openapi-include-paths`](openapi-only-options.md#openapi-include-paths) | Filter OpenAPI paths to include in model generation. |
| [`--openapi-scopes`](openapi-only-options.md#openapi-scopes) | Specify OpenAPI scopes to generate (schemas, paths, parameters). |
| [`--read-only-write-only-model-type`](openapi-only-options.md#read-only-write-only-model-type) | Generate separate request and response models for readOnly/writeOnly fields. |
| [`--use-operation-id-as-name`](openapi-only-options.md#use-operation-id-as-name) | Use OpenAPI operationId as the generated function/class name. |
| [`--use-status-code-in-response-name`](openapi-only-options.md#use-status-code-in-response-name) | Include HTTP status code in response model names. |
| [`--validation`](openapi-only-options.md#validation) | Enable validation constraints (deprecated, use --field-constraints). |

### 📋 GraphQL-only Options

| Option | Description |
|--------|-------------|
| [`--graphql-no-typename`](graphql-only-options.md#graphql-no-typename) | Exclude __typename field from generated GraphQL models. |

### ⚙️ General Options

| Option | Description |
|--------|-------------|
| [`--all-exports-collision-strategy`](general-options.md#all-exports-collision-strategy) | Handle name collisions when exporting recursive module hierarchies. |
| [`--all-exports-scope`](general-options.md#all-exports-scope) | Generate __all__ exports for child modules in __init__.py files. |
| [`--check`](general-options.md#check) | Verify generated code matches existing output without modifying files. |
| [`--disable-warnings`](general-options.md#disable-warnings) | Suppress warning messages during code generation. |
| [`--generate-cli-command`](general-options.md#generate-cli-command) | Generate CLI command from pyproject.toml configuration. |
| [`--generate-pyproject-config`](general-options.md#generate-pyproject-config) | Generate pyproject.toml configuration from CLI arguments. |
| [`--http-headers`](general-options.md#http-headers) | Fetch schema from URL with custom HTTP headers. |
| [`--http-ignore-tls`](general-options.md#http-ignore-tls) | Disable TLS certificate verification for HTTPS requests. |
| [`--http-query-parameters`](general-options.md#http-query-parameters) | Add query parameters to HTTP requests for remote schemas. |
| [`--http-timeout`](general-options.md#http-timeout) | Set timeout for HTTP requests to remote hosts. |
| [`--ignore-pyproject`](general-options.md#ignore-pyproject) | Ignore pyproject.toml configuration file. |
| [`--module-split-mode`](general-options.md#module-split-mode) | Split generated models into separate files, one per model class. |
| [`--shared-module-name`](general-options.md#shared-module-name) | Customize the name of the shared module for deduplicated models. |
| [`--watch`](general-options.md#watch) | Watch input file(s) for changes and regenerate output automatically. |
| [`--watch-delay`](general-options.md#watch-delay) | Set debounce delay in seconds for watch mode. |

### 📝 Utility Options

| Option | Description |
|--------|-------------|
| [`--debug`](utility-options.md#debug) | Show debug messages during code generation |
| [`--generate-prompt`](utility-options.md#generate-prompt) | Generate a prompt for consulting LLMs about CLI options |
| [`--help`](utility-options.md#help) | Show help message and exit |
| [`--no-color`](utility-options.md#no-color) | Disable colorized output |
| [`--profile`](utility-options.md#profile) | Use a named profile from pyproject.toml |
| [`--version`](utility-options.md#version) | Show program version and exit |

---

## 🔤 Alphabetical Index

All options sorted alphabetically:

- [`--additional-imports`](template-customization.md#additional-imports) - Add custom imports to generated output files.
- [`--aliases`](field-customization.md#aliases) - Apply custom field and class name aliases from JSON file.
- [`--all-exports-collision-strategy`](general-options.md#all-exports-collision-strategy) - Handle name collisions when exporting recursive module hiera...
- [`--all-exports-scope`](general-options.md#all-exports-scope) - Generate __all__ exports for child modules in __init__.py fi...
- [`--allof-class-hierarchy`](typing-customization.md#allof-class-hierarchy) - Controls how allOf schemas are represented in the generated ...
- [`--allof-merge-mode`](typing-customization.md#allof-merge-mode) - Merge constraints from root model references in allOf schema...
- [`--allow-extra-fields`](model-customization.md#allow-extra-fields) - Allow extra fields in generated Pydantic models (extra='allo...
- [`--allow-population-by-field-name`](model-customization.md#allow-population-by-field-name) - Allow Pydantic model population by field name (not just alia...
- [`--base-class`](model-customization.md#base-class) - Specify a custom base class for generated models.
- [`--base-class-map`](model-customization.md#base-class-map) - Specify different base classes for specific models via JSON ...
- [`--capitalize-enum-members`](field-customization.md#capitalize-enum-members) - Capitalize enum member names to UPPER_CASE format.
- [`--check`](general-options.md#check) - Verify generated code matches existing output without modify...
- [`--class-decorators`](template-customization.md#class-decorators) - Add custom decorators to generated model classes.
- [`--class-name`](model-customization.md#class-name) - Override the auto-generated class name with a custom name.
- [`--class-name-affix-scope`](model-customization.md#class-name-affix-scope) - Control which classes receive the prefix/suffix.
- [`--class-name-prefix`](model-customization.md#class-name-prefix) - Add a prefix to all generated class names.
- [`--class-name-suffix`](model-customization.md#class-name-suffix) - Add a suffix to all generated class names.
- [`--collapse-reuse-models`](model-customization.md#collapse-reuse-models) - Collapse duplicate models by replacing references instead of...
- [`--collapse-root-models`](model-customization.md#collapse-root-models) - Inline root model definitions instead of creating separate w...
- [`--collapse-root-models-name-strategy`](model-customization.md#collapse-root-models-name-strategy) - Select which name to keep when collapsing root models with o...
- [`--custom-file-header`](template-customization.md#custom-file-header) - Add custom header text to the generated file.
- [`--custom-file-header-path`](template-customization.md#custom-file-header-path) - Add custom header content from file to generated code.
- [`--custom-formatters`](template-customization.md#custom-formatters) - Apply custom Python code formatters to generated output.
- [`--custom-formatters-kwargs`](template-customization.md#custom-formatters-kwargs) - Pass custom arguments to custom formatters via JSON file.
- [`--custom-template-dir`](template-customization.md#custom-template-dir) - Use custom Jinja2 templates for model generation.
- [`--dataclass-arguments`](model-customization.md#dataclass-arguments) - Customize dataclass decorator arguments via JSON dictionary.
- [`--debug`](utility-options.md#debug) - Show debug messages during code generation
- [`--default-values`](field-customization.md#default-values) - Override field default values from external JSON file.
- [`--disable-appending-item-suffix`](template-customization.md#disable-appending-item-suffix) - Disable appending 'Item' suffix to array item types.
- [`--disable-future-imports`](typing-customization.md#disable-future-imports) - Prevent automatic addition of __future__ imports in generate...
- [`--disable-timestamp`](template-customization.md#disable-timestamp) - Disable timestamp in generated file header for reproducible ...
- [`--disable-warnings`](general-options.md#disable-warnings) - Suppress warning messages during code generation.
- [`--duplicate-name-suffix`](model-customization.md#duplicate-name-suffix) - Customize suffix for duplicate model names.
- [`--empty-enum-field-name`](field-customization.md#empty-enum-field-name) - Name for empty string enum field values.
- [`--enable-command-header`](template-customization.md#enable-command-header) - Include command-line options in file header for reproducibil...
- [`--enable-faux-immutability`](model-customization.md#enable-faux-immutability) - Enable faux immutability in Pydantic v1 models (allow_mutati...
- [`--enable-version-header`](template-customization.md#enable-version-header) - Include tool version information in file header.
- [`--encoding`](base-options.md#encoding) - Specify character encoding for input and output files.
- [`--enum-field-as-literal`](typing-customization.md#enum-field-as-literal) - Convert all enum fields to Literal types instead of Enum cla...
- [`--enum-field-as-literal-map`](typing-customization.md#enum-field-as-literal-map) - Override enum/literal generation per-field via JSON mapping.
- [`--extra-fields`](field-customization.md#extra-fields) - Configure how generated models handle extra fields not defin...
- [`--extra-template-data`](template-customization.md#extra-template-data) - Pass custom template variables from JSON file for code gener...
- [`--field-constraints`](field-customization.md#field-constraints) - Generate Field() with validation constraints from schema.
- [`--field-extra-keys`](field-customization.md#field-extra-keys) - Include specific extra keys in Field() definitions.
- [`--field-extra-keys-without-x-prefix`](field-customization.md#field-extra-keys-without-x-prefix) - Include schema extension keys in Field() without requiring '...
- [`--field-include-all-keys`](field-customization.md#field-include-all-keys) - Include all schema keys in Field() json_schema_extra.
- [`--field-type-collision-strategy`](field-customization.md#field-type-collision-strategy) - Rename type class instead of field when names collide (Pydan...
- [`--force-optional`](model-customization.md#force-optional) - Force all fields to be Optional regardless of required statu...
- [`--formatters`](template-customization.md#formatters) - Specify code formatters to apply to generated output.
- [`--frozen-dataclasses`](model-customization.md#frozen-dataclasses) - Generate frozen dataclasses with optional keyword-only field...
- [`--generate-cli-command`](general-options.md#generate-cli-command) - Generate CLI command from pyproject.toml configuration.
- [`--generate-prompt`](utility-options.md#generate-prompt) - Generate a prompt for consulting LLMs about CLI options
- [`--generate-pyproject-config`](general-options.md#generate-pyproject-config) - Generate pyproject.toml configuration from CLI arguments.
- [`--graphql-no-typename`](graphql-only-options.md#graphql-no-typename) - Exclude __typename field from generated GraphQL models.
- [`--help`](utility-options.md#help) - Show help message and exit
- [`--http-headers`](general-options.md#http-headers) - Fetch schema from URL with custom HTTP headers.
- [`--http-ignore-tls`](general-options.md#http-ignore-tls) - Disable TLS certificate verification for HTTPS requests.
- [`--http-query-parameters`](general-options.md#http-query-parameters) - Add query parameters to HTTP requests for remote schemas.
- [`--http-timeout`](general-options.md#http-timeout) - Set timeout for HTTP requests to remote hosts.
- [`--ignore-enum-constraints`](typing-customization.md#ignore-enum-constraints) - Ignore enum constraints and use base string type instead of ...
- [`--ignore-pyproject`](general-options.md#ignore-pyproject) - Ignore pyproject.toml configuration file.
- [`--include-path-parameters`](openapi-only-options.md#include-path-parameters) - Include OpenAPI path parameters in generated parameter model...
- [`--input`](base-options.md#input) - Specify the input schema file path.
- [`--input-file-type`](base-options.md#input-file-type) - Specify the input file type for code generation.
- [`--input-model`](base-options.md#input-model) - Import a Python type or dict schema from a module.
- [`--input-model-ref-strategy`](base-options.md#input-model-ref-strategy) - Strategy for referenced types when using --input-model.
- [`--keep-model-order`](model-customization.md#keep-model-order) - Keep model definition order as specified in schema.
- [`--keyword-only`](model-customization.md#keyword-only) - Generate dataclasses with keyword-only fields (Python 3.10+)...
- [`--model-extra-keys`](model-customization.md#model-extra-keys) - Add model-level schema extensions to ConfigDict json_schema_...
- [`--model-extra-keys-without-x-prefix`](model-customization.md#model-extra-keys-without-x-prefix) - Strip x- prefix from model-level schema extensions and add t...
- [`--module-split-mode`](general-options.md#module-split-mode) - Split generated models into separate files, one per model cl...
- [`--naming-strategy`](model-customization.md#naming-strategy) - Use parent-prefixed naming strategy for duplicate model name...
- [`--no-alias`](field-customization.md#no-alias) - Disable Field alias generation for non-Python-safe property ...
- [`--no-color`](utility-options.md#no-color) - Disable colorized output
- [`--no-treat-dot-as-module`](template-customization.md#no-treat-dot-as-module) - Keep dots in schema names as underscores for flat output.
- [`--no-use-specialized-enum`](typing-customization.md#no-use-specialized-enum) - Disable specialized Enum classes for Python 3.11+ code gener...
- [`--no-use-standard-collections`](typing-customization.md#no-use-standard-collections) - Use typing.Dict/List instead of built-in dict/list for conta...
- [`--no-use-union-operator`](typing-customization.md#no-use-union-operator) - Use Union[X, Y] / Optional[X] instead of X | Y union operato...
- [`--openapi-include-paths`](openapi-only-options.md#openapi-include-paths) - Filter OpenAPI paths to include in model generation.
- [`--openapi-scopes`](openapi-only-options.md#openapi-scopes) - Specify OpenAPI scopes to generate (schemas, paths, paramete...
- [`--original-field-name-delimiter`](field-customization.md#original-field-name-delimiter) - Specify delimiter for original field names when using snake-...
- [`--output`](base-options.md#output) - Specify the destination path for generated Python code.
- [`--output-date-class`](typing-customization.md#output-date-class) - Specify date class type for date schema fields.
- [`--output-datetime-class`](typing-customization.md#output-datetime-class) - Specify datetime class type for date-time schema fields.
- [`--output-model-type`](model-customization.md#output-model-type) - Select the output model type (Pydantic v1/v2, dataclasses, T...
- [`--parent-scoped-naming`](model-customization.md#parent-scoped-naming) - Namespace models by their parent scope to avoid naming confl...
- [`--profile`](utility-options.md#profile) - Use a named profile from pyproject.toml
- [`--read-only-write-only-model-type`](openapi-only-options.md#read-only-write-only-model-type) - Generate separate request and response models for readOnly/w...
- [`--remove-special-field-name-prefix`](field-customization.md#remove-special-field-name-prefix) - Remove the special prefix from field names.
- [`--reuse-model`](model-customization.md#reuse-model) - Reuse identical model definitions instead of generating dupl...
- [`--reuse-scope`](model-customization.md#reuse-scope) - Scope for model reuse detection (root or tree).
- [`--schema-version`](base-options.md#schema-version) - Schema version to use for parsing.
- [`--schema-version-mode`](base-options.md#schema-version-mode) - Schema version validation mode.
- [`--set-default-enum-member`](field-customization.md#set-default-enum-member) - Set the first enum member as the default value for enum fiel...
- [`--shared-module-name`](general-options.md#shared-module-name) - Customize the name of the shared module for deduplicated mod...
- [`--skip-root-model`](model-customization.md#skip-root-model) - Skip generation of root model when schema contains nested de...
- [`--snake-case-field`](field-customization.md#snake-case-field) - Convert field names to snake_case format.
- [`--special-field-name-prefix`](field-customization.md#special-field-name-prefix) - Prefix to add to special field names (like reserved keywords...
- [`--strict-nullable`](model-customization.md#strict-nullable) - Treat default field as a non-nullable field.
- [`--strict-types`](typing-customization.md#strict-types) - Enable strict type validation for specified Python types.
- [`--strip-default-none`](model-customization.md#strip-default-none) - Remove fields with None as default value from generated mode...
- [`--target-pydantic-version`](model-customization.md#target-pydantic-version) - Target Pydantic version for generated code compatibility.
- [`--target-python-version`](model-customization.md#target-python-version) - Target Python version for generated code syntax and imports.
- [`--treat-dot-as-module`](template-customization.md#treat-dot-as-module) - Treat dots in schema names as module separators.
- [`--type-mappings`](typing-customization.md#type-mappings) - Override default type mappings for schema formats.
- [`--type-overrides`](typing-customization.md#type-overrides) - Replace schema model types with custom Python types via JSON...
- [`--union-mode`](model-customization.md#union-mode) - Union mode for combining anyOf/oneOf schemas (smart or left_...
- [`--url`](base-options.md#url) - Fetch schema from URL with custom HTTP headers.
- [`--use-annotated`](typing-customization.md#use-annotated) - Use typing.Annotated for Field() with constraints.
- [`--use-attribute-docstrings`](field-customization.md#use-attribute-docstrings) - Generate field descriptions as attribute docstrings instead ...
- [`--use-decimal-for-multiple-of`](typing-customization.md#use-decimal-for-multiple-of) - Generate Decimal types for fields with multipleOf constraint...
- [`--use-default`](model-customization.md#use-default) - Use default values from schema in generated models.
- [`--use-default-factory-for-optional-nested-models`](model-customization.md#use-default-factory-for-optional-nested-models) - Generate default_factory for optional nested model fields.
- [`--use-default-kwarg`](model-customization.md#use-default-kwarg) - Use default= keyword argument instead of positional argument...
- [`--use-double-quotes`](template-customization.md#use-double-quotes) - Use double quotes for string literals in generated code.
- [`--use-enum-values-in-discriminator`](field-customization.md#use-enum-values-in-discriminator) - Use enum values in discriminator mappings for union types.
- [`--use-exact-imports`](template-customization.md#use-exact-imports) - Import exact types instead of modules.
- [`--use-field-description`](field-customization.md#use-field-description) - Include schema descriptions as Field docstrings.
- [`--use-field-description-example`](field-customization.md#use-field-description-example) - Add field examples to docstrings.
- [`--use-frozen-field`](model-customization.md#use-frozen-field) - Generate frozen (immutable) field definitions for readOnly p...
- [`--use-generic-base-class`](model-customization.md#use-generic-base-class) - Generate a shared base class with model configuration to avo...
- [`--use-generic-container-types`](typing-customization.md#use-generic-container-types) - Use generic container types (Sequence, Mapping) for type hin...
- [`--use-inline-field-description`](field-customization.md#use-inline-field-description) - Add field descriptions as inline comments.
- [`--use-non-positive-negative-number-constrained-types`](typing-customization.md#use-non-positive-negative-number-constrained-types) - Use NonPositive/NonNegative types for number constraints.
- [`--use-one-literal-as-default`](model-customization.md#use-one-literal-as-default) - Use single literal value as default when enum has only one o...
- [`--use-operation-id-as-name`](openapi-only-options.md#use-operation-id-as-name) - Use OpenAPI operationId as the generated function/class name...
- [`--use-pendulum`](typing-customization.md#use-pendulum) - Use pendulum types for date/time fields instead of datetime ...
- [`--use-root-model-type-alias`](typing-customization.md#use-root-model-type-alias) - Generate RootModel as type alias format for better mypy supp...
- [`--use-schema-description`](field-customization.md#use-schema-description) - Use schema description as class docstring.
- [`--use-serialization-alias`](field-customization.md#use-serialization-alias) - Use serialization_alias instead of alias for field aliasing ...
- [`--use-serialize-as-any`](model-customization.md#use-serialize-as-any) - Wrap fields with subtypes in Pydantic's SerializeAsAny.
- [`--use-specialized-enum`](typing-customization.md#use-specialized-enum) - Generate StrEnum/IntEnum for string/integer enums (Python 3....
- [`--use-standard-collections`](typing-customization.md#use-standard-collections) - Use built-in dict/list instead of typing.Dict/List.
- [`--use-standard-primitive-types`](typing-customization.md#use-standard-primitive-types) - Use Python standard library types for string formats instead...
- [`--use-status-code-in-response-name`](openapi-only-options.md#use-status-code-in-response-name) - Include HTTP status code in response model names.
- [`--use-subclass-enum`](model-customization.md#use-subclass-enum) - Generate typed Enum subclasses for enums with specific field...
- [`--use-title-as-name`](field-customization.md#use-title-as-name) - Use schema title as the generated class name.
- [`--use-tuple-for-fixed-items`](typing-customization.md#use-tuple-for-fixed-items) - Generate tuple types for arrays with items array syntax.
- [`--use-type-alias`](typing-customization.md#use-type-alias) - Use TypeAlias instead of root models for type definitions (e...
- [`--use-union-operator`](typing-customization.md#use-union-operator) - Use | operator for Union types (PEP 604).
- [`--use-unique-items-as-set`](typing-customization.md#use-unique-items-as-set) - Generate set types for arrays with uniqueItems constraint.
- [`--validation`](openapi-only-options.md#validation) - Enable validation constraints (deprecated, use --field-const...
- [`--validators`](template-customization.md#validators) - Add custom field validators to generated Pydantic v2 models.
- [`--version`](utility-options.md#version) - Show program version and exit
- [`--watch`](general-options.md#watch) - Watch input file(s) for changes and regenerate output automa...
- [`--watch-delay`](general-options.md#watch-delay) - Set debounce delay in seconds for watch mode.
- [`--wrap-string-literal`](template-customization.md#wrap-string-literal) - Wrap long string literals across multiple lines.
