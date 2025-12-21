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
| [`--output`](base-options.md#output) | Specify the destination path for generated Python code. |
| [`--url`](base-options.md#url) | Fetch schema from URL with custom HTTP headers. |

### 🔧 Typing Customization

| Option | Description |
|--------|-------------|
| [`--allof-merge-mode`](typing-customization.md#allof-merge-mode) | Merge constraints from root model references in allOf schemas. |
| [`--disable-future-imports`](typing-customization.md#disable-future-imports) | Prevent automatic addition of __future__ imports in generated code. |
| [`--enum-field-as-literal`](typing-customization.md#enum-field-as-literal) | Convert all enum fields to Literal types instead of Enum classes. |
| [`--ignore-enum-constraints`](typing-customization.md#ignore-enum-constraints) | Ignore enum constraints and use base string type instead of Enum classes. |
| [`--no-use-specialized-enum`](typing-customization.md#no-use-specialized-enum) | Disable specialized Enum classes for Python 3.11+ code generation. |
| [`--no-use-standard-collections`](typing-customization.md#no-use-standard-collections) | Use built-in dict/list instead of typing.Dict/List. |
| [`--no-use-union-operator`](typing-customization.md#no-use-union-operator) | Test GraphQL annotated types with standard collections and union operator. |
| [`--output-datetime-class`](typing-customization.md#output-datetime-class) | Specify datetime class type for date-time schema fields. |
| [`--strict-types`](typing-customization.md#strict-types) | Enable strict type validation for specified Python types. |
| [`--type-mappings`](typing-customization.md#type-mappings) | Override default type mappings for schema formats. |
| [`--use-annotated`](typing-customization.md#use-annotated) | Test GraphQL annotated types with standard collections and union operator. |
| [`--use-decimal-for-multiple-of`](typing-customization.md#use-decimal-for-multiple-of) | Generate Decimal types for fields with multipleOf constraint. |
| [`--use-generic-container-types`](typing-customization.md#use-generic-container-types) | Use typing.Dict/List instead of dict/list for container types. |
| [`--use-non-positive-negative-number-constrained-types`](typing-customization.md#use-non-positive-negative-number-constrained-types) | Use NonPositive/NonNegative types for number constraints. |
| [`--use-pendulum`](typing-customization.md#use-pendulum) | Use pendulum types for date/time fields instead of datetime module. |
| [`--use-type-alias`](typing-customization.md#use-type-alias) | Use TypeAlias instead of root models for type definitions (experimental). |
| [`--use-unique-items-as-set`](typing-customization.md#use-unique-items-as-set) | Generate set types for arrays with uniqueItems constraint. |

### 🏷️ Field Customization

| Option | Description |
|--------|-------------|
| [`--aliases`](field-customization.md#aliases) | Apply custom field and class name aliases from JSON file. |
| [`--capitalize-enum-members`](field-customization.md#capitalize-enum-members) | Capitalize enum member names to UPPER_CASE format. |
| [`--empty-enum-field-name`](field-customization.md#empty-enum-field-name) | Name for empty string enum field values. |
| [`--extra-fields`](field-customization.md#extra-fields) | Configure how generated models handle extra fields not defined in schema. |
| [`--field-constraints`](field-customization.md#field-constraints) | Generate Field() with validation constraints from schema. |
| [`--field-extra-keys`](field-customization.md#field-extra-keys) | Include specific extra keys in Field() definitions. |
| [`--field-extra-keys-without-x-prefix`](field-customization.md#field-extra-keys-without-x-prefix) | Include specified schema extension keys in Field() without requiring 'x-' prefix... |
| [`--field-include-all-keys`](field-customization.md#field-include-all-keys) | Include all schema keys in Field() json_schema_extra. |
| [`--no-alias`](field-customization.md#no-alias) | Disable Field alias generation for non-Python-safe property names. |
| [`--original-field-name-delimiter`](field-customization.md#original-field-name-delimiter) | Specify delimiter for original field names when using snake-case conversion. |
| [`--remove-special-field-name-prefix`](field-customization.md#remove-special-field-name-prefix) | Remove the special prefix from field names. |
| [`--set-default-enum-member`](field-customization.md#set-default-enum-member) | Set the first enum member as the default value for enum fields. |
| [`--snake-case-field`](field-customization.md#snake-case-field) | Convert field names to snake_case format. |
| [`--special-field-name-prefix`](field-customization.md#special-field-name-prefix) | Prefix to add to special field names (like reserved keywords). |
| [`--use-attribute-docstrings`](field-customization.md#use-attribute-docstrings) | Generate field descriptions as attribute docstrings instead of Field description... |
| [`--use-enum-values-in-discriminator`](field-customization.md#use-enum-values-in-discriminator) | Use enum values in discriminator mappings for union types. |
| [`--use-field-description`](field-customization.md#use-field-description) | Include schema descriptions as Field docstrings. |
| [`--use-inline-field-description`](field-customization.md#use-inline-field-description) | Add field descriptions as inline comments. |
| [`--use-schema-description`](field-customization.md#use-schema-description) | Use schema description as class docstring. |
| [`--use-title-as-name`](field-customization.md#use-title-as-name) | Use schema title as the generated class name. |

### 🏗️ Model Customization

| Option | Description |
|--------|-------------|
| [`--allow-extra-fields`](model-customization.md#allow-extra-fields) | Allow extra fields in generated Pydantic models (extra='allow'). |
| [`--allow-population-by-field-name`](model-customization.md#allow-population-by-field-name) | Allow Pydantic model population by field name (not just alias). |
| [`--base-class`](model-customization.md#base-class) | Specify a custom base class for generated models. |
| [`--class-name`](model-customization.md#class-name) | Override the auto-generated class name with a custom name. |
| [`--collapse-root-models`](model-customization.md#collapse-root-models) | Inline root model definitions instead of creating separate wrapper classes. |
| [`--dataclass-arguments`](model-customization.md#dataclass-arguments) | Customize dataclass decorator arguments via JSON dictionary. |
| [`--enable-faux-immutability`](model-customization.md#enable-faux-immutability) | Enable faux immutability in Pydantic v1 models (allow_mutation=False). |
| [`--force-optional`](model-customization.md#force-optional) | Force all fields to be Optional regardless of required status. |
| [`--frozen-dataclasses`](model-customization.md#frozen-dataclasses) | Generate frozen dataclasses with optional keyword-only fields. |
| [`--keep-model-order`](model-customization.md#keep-model-order) | Keep model definition order as specified in schema. |
| [`--keyword-only`](model-customization.md#keyword-only) | Generate dataclasses with keyword-only fields (Python 3.10+). |
| [`--output-model-type`](model-customization.md#output-model-type) | Select the output model type (Pydantic v1/v2, dataclasses, TypedDict, msgspec). |
| [`--parent-scoped-naming`](model-customization.md#parent-scoped-naming) | Namespace models by their parent scope to avoid naming conflicts. |
| [`--reuse-model`](model-customization.md#reuse-model) | Reuse identical model definitions instead of generating duplicates. |
| [`--reuse-scope`](model-customization.md#reuse-scope) | Scope for model reuse detection (root or tree). |
| [`--skip-root-model`](model-customization.md#skip-root-model) | Skip generation of root model when schema contains nested definitions. |
| [`--strict-nullable`](model-customization.md#strict-nullable) | Treat default field as a non-nullable field. |
| [`--strip-default-none`](model-customization.md#strip-default-none) | Remove fields with None as default value from generated models. |
| [`--target-python-version`](model-customization.md#target-python-version) | Target Python version for generated code syntax and imports. |
| [`--union-mode`](model-customization.md#union-mode) | Union mode for combining anyOf/oneOf schemas (smart or left_to_right). |
| [`--use-default`](model-customization.md#use-default) | Use default values from schema in generated models. |
| [`--use-default-factory-for-optional-nested-models`](model-customization.md#use-default-factory-for-optional-nested-models) | Generate default_factory for optional nested model fields. |
| [`--use-default-kwarg`](model-customization.md#use-default-kwarg) | Use default= keyword argument instead of positional argument for fields with def... |
| [`--use-frozen-field`](model-customization.md#use-frozen-field) | Generate frozen (immutable) field definitions for readOnly properties. |
| [`--use-one-literal-as-default`](model-customization.md#use-one-literal-as-default) | Use single literal value as default when enum has only one option. |
| [`--use-serialize-as-any`](model-customization.md#use-serialize-as-any) | Wrap fields with subtypes in Pydantic's SerializeAsAny. |
| [`--use-subclass-enum`](model-customization.md#use-subclass-enum) | Generate typed Enum subclasses for enums with specific field types. |

### 🎨 Template Customization

| Option | Description |
|--------|-------------|
| [`--additional-imports`](template-customization.md#additional-imports) | Add custom imports to generated output files. |
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
| [`--treat-dot-as-module`](template-customization.md#treat-dot-as-module) | Treat dots in schema names as module separators. |
| [`--use-double-quotes`](template-customization.md#use-double-quotes) | Use double quotes for string literals in generated code. |
| [`--use-exact-imports`](template-customization.md#use-exact-imports) | Import exact types instead of modules. |
| [`--wrap-string-literal`](template-customization.md#wrap-string-literal) | Wrap long string literals across multiple lines. |

### 📘 OpenAPI-only Options

| Option | Description |
|--------|-------------|
| [`--include-path-parameters`](openapi-only-options.md#include-path-parameters) | Include OpenAPI path parameters in generated parameter models. |
| [`--openapi-scopes`](openapi-only-options.md#openapi-scopes) | Specify OpenAPI scopes to generate (schemas, paths, parameters). |
| [`--read-only-write-only-model-type`](openapi-only-options.md#read-only-write-only-model-type) | Generate separate request and response models for readOnly/writeOnly fields. |
| [`--use-operation-id-as-name`](openapi-only-options.md#use-operation-id-as-name) | Use OpenAPI operationId as the generated function/class name. |
| [`--use-status-code-in-response-name`](openapi-only-options.md#use-status-code-in-response-name) | Include HTTP status code in response model names. |
| [`--validation`](openapi-only-options.md#validation) | Enable validation constraints (deprecated, use --field-constraints). |

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
| [`--ignore-pyproject`](general-options.md#ignore-pyproject) | Ignore pyproject.toml configuration file. |
| [`--module-split-mode`](general-options.md#module-split-mode) | Split generated models into separate files, one per model class. |
| [`--shared-module-name`](general-options.md#shared-module-name) | Customize the name of the shared module for deduplicated models. |
| [`--watch`](general-options.md#watch) | Watch mode cannot be used with --check mode. |
| [`--watch-delay`](general-options.md#watch-delay) | Watch mode starts file watcher and handles clean exit. |

### 📝 Utility Options

| Option | Description |
|--------|-------------|
| [`--debug`](utility-options.md#debug) | Show debug messages during code generation |
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
- [`--allof-merge-mode`](typing-customization.md#allof-merge-mode) - Merge constraints from root model references in allOf schema...
- [`--allow-extra-fields`](model-customization.md#allow-extra-fields) - Allow extra fields in generated Pydantic models (extra='allo...
- [`--allow-population-by-field-name`](model-customization.md#allow-population-by-field-name) - Allow Pydantic model population by field name (not just alia...
- [`--base-class`](model-customization.md#base-class) - Specify a custom base class for generated models.
- [`--capitalize-enum-members`](field-customization.md#capitalize-enum-members) - Capitalize enum member names to UPPER_CASE format.
- [`--check`](general-options.md#check) - Verify generated code matches existing output without modify...
- [`--class-name`](model-customization.md#class-name) - Override the auto-generated class name with a custom name.
- [`--collapse-root-models`](model-customization.md#collapse-root-models) - Inline root model definitions instead of creating separate w...
- [`--custom-file-header`](template-customization.md#custom-file-header) - Add custom header text to the generated file.
- [`--custom-file-header-path`](template-customization.md#custom-file-header-path) - Add custom header content from file to generated code.
- [`--custom-formatters`](template-customization.md#custom-formatters) - Apply custom Python code formatters to generated output.
- [`--custom-formatters-kwargs`](template-customization.md#custom-formatters-kwargs) - Pass custom arguments to custom formatters via JSON file.
- [`--custom-template-dir`](template-customization.md#custom-template-dir) - Use custom Jinja2 templates for model generation.
- [`--dataclass-arguments`](model-customization.md#dataclass-arguments) - Customize dataclass decorator arguments via JSON dictionary.
- [`--debug`](utility-options.md#debug) - Show debug messages during code generation
- [`--disable-appending-item-suffix`](template-customization.md#disable-appending-item-suffix) - Disable appending 'Item' suffix to array item types.
- [`--disable-future-imports`](typing-customization.md#disable-future-imports) - Prevent automatic addition of __future__ imports in generate...
- [`--disable-timestamp`](template-customization.md#disable-timestamp) - Disable timestamp in generated file header for reproducible ...
- [`--disable-warnings`](general-options.md#disable-warnings) - Suppress warning messages during code generation.
- [`--empty-enum-field-name`](field-customization.md#empty-enum-field-name) - Name for empty string enum field values.
- [`--enable-command-header`](template-customization.md#enable-command-header) - Include command-line options in file header for reproducibil...
- [`--enable-faux-immutability`](model-customization.md#enable-faux-immutability) - Enable faux immutability in Pydantic v1 models (allow_mutati...
- [`--enable-version-header`](template-customization.md#enable-version-header) - Include tool version information in file header.
- [`--encoding`](base-options.md#encoding) - Specify character encoding for input and output files.
- [`--enum-field-as-literal`](typing-customization.md#enum-field-as-literal) - Convert all enum fields to Literal types instead of Enum cla...
- [`--extra-fields`](field-customization.md#extra-fields) - Configure how generated models handle extra fields not defin...
- [`--extra-template-data`](template-customization.md#extra-template-data) - Pass custom template variables from JSON file for code gener...
- [`--field-constraints`](field-customization.md#field-constraints) - Generate Field() with validation constraints from schema.
- [`--field-extra-keys`](field-customization.md#field-extra-keys) - Include specific extra keys in Field() definitions.
- [`--field-extra-keys-without-x-prefix`](field-customization.md#field-extra-keys-without-x-prefix) - Include specified schema extension keys in Field() without r...
- [`--field-include-all-keys`](field-customization.md#field-include-all-keys) - Include all schema keys in Field() json_schema_extra.
- [`--force-optional`](model-customization.md#force-optional) - Force all fields to be Optional regardless of required statu...
- [`--formatters`](template-customization.md#formatters) - Specify code formatters to apply to generated output.
- [`--frozen-dataclasses`](model-customization.md#frozen-dataclasses) - Generate frozen dataclasses with optional keyword-only field...
- [`--generate-cli-command`](general-options.md#generate-cli-command) - Generate CLI command from pyproject.toml configuration.
- [`--generate-pyproject-config`](general-options.md#generate-pyproject-config) - Generate pyproject.toml configuration from CLI arguments.
- [`--help`](utility-options.md#help) - Show help message and exit
- [`--http-headers`](general-options.md#http-headers) - Fetch schema from URL with custom HTTP headers.
- [`--http-ignore-tls`](general-options.md#http-ignore-tls) - Disable TLS certificate verification for HTTPS requests.
- [`--http-query-parameters`](general-options.md#http-query-parameters) - Add query parameters to HTTP requests for remote schemas.
- [`--ignore-enum-constraints`](typing-customization.md#ignore-enum-constraints) - Ignore enum constraints and use base string type instead of ...
- [`--ignore-pyproject`](general-options.md#ignore-pyproject) - Ignore pyproject.toml configuration file.
- [`--include-path-parameters`](openapi-only-options.md#include-path-parameters) - Include OpenAPI path parameters in generated parameter model...
- [`--input`](base-options.md#input) - Specify the input schema file path.
- [`--input-file-type`](base-options.md#input-file-type) - Specify the input file type for code generation.
- [`--keep-model-order`](model-customization.md#keep-model-order) - Keep model definition order as specified in schema.
- [`--keyword-only`](model-customization.md#keyword-only) - Generate dataclasses with keyword-only fields (Python 3.10+)...
- [`--module-split-mode`](general-options.md#module-split-mode) - Split generated models into separate files, one per model cl...
- [`--no-alias`](field-customization.md#no-alias) - Disable Field alias generation for non-Python-safe property ...
- [`--no-color`](utility-options.md#no-color) - Disable colorized output
- [`--no-use-specialized-enum`](typing-customization.md#no-use-specialized-enum) - Disable specialized Enum classes for Python 3.11+ code gener...
- [`--no-use-standard-collections`](typing-customization.md#no-use-standard-collections) - Use built-in dict/list instead of typing.Dict/List.
- [`--no-use-union-operator`](typing-customization.md#no-use-union-operator) - Test GraphQL annotated types with standard collections and u...
- [`--openapi-scopes`](openapi-only-options.md#openapi-scopes) - Specify OpenAPI scopes to generate (schemas, paths, paramete...
- [`--original-field-name-delimiter`](field-customization.md#original-field-name-delimiter) - Specify delimiter for original field names when using snake-...
- [`--output`](base-options.md#output) - Specify the destination path for generated Python code.
- [`--output-datetime-class`](typing-customization.md#output-datetime-class) - Specify datetime class type for date-time schema fields.
- [`--output-model-type`](model-customization.md#output-model-type) - Select the output model type (Pydantic v1/v2, dataclasses, T...
- [`--parent-scoped-naming`](model-customization.md#parent-scoped-naming) - Namespace models by their parent scope to avoid naming confl...
- [`--profile`](utility-options.md#profile) - Use a named profile from pyproject.toml
- [`--read-only-write-only-model-type`](openapi-only-options.md#read-only-write-only-model-type) - Generate separate request and response models for readOnly/w...
- [`--remove-special-field-name-prefix`](field-customization.md#remove-special-field-name-prefix) - Remove the special prefix from field names.
- [`--reuse-model`](model-customization.md#reuse-model) - Reuse identical model definitions instead of generating dupl...
- [`--reuse-scope`](model-customization.md#reuse-scope) - Scope for model reuse detection (root or tree).
- [`--set-default-enum-member`](field-customization.md#set-default-enum-member) - Set the first enum member as the default value for enum fiel...
- [`--shared-module-name`](general-options.md#shared-module-name) - Customize the name of the shared module for deduplicated mod...
- [`--skip-root-model`](model-customization.md#skip-root-model) - Skip generation of root model when schema contains nested de...
- [`--snake-case-field`](field-customization.md#snake-case-field) - Convert field names to snake_case format.
- [`--special-field-name-prefix`](field-customization.md#special-field-name-prefix) - Prefix to add to special field names (like reserved keywords...
- [`--strict-nullable`](model-customization.md#strict-nullable) - Treat default field as a non-nullable field.
- [`--strict-types`](typing-customization.md#strict-types) - Enable strict type validation for specified Python types.
- [`--strip-default-none`](model-customization.md#strip-default-none) - Remove fields with None as default value from generated mode...
- [`--target-python-version`](model-customization.md#target-python-version) - Target Python version for generated code syntax and imports.
- [`--treat-dot-as-module`](template-customization.md#treat-dot-as-module) - Treat dots in schema names as module separators.
- [`--type-mappings`](typing-customization.md#type-mappings) - Override default type mappings for schema formats.
- [`--union-mode`](model-customization.md#union-mode) - Union mode for combining anyOf/oneOf schemas (smart or left_...
- [`--url`](base-options.md#url) - Fetch schema from URL with custom HTTP headers.
- [`--use-annotated`](typing-customization.md#use-annotated) - Test GraphQL annotated types with standard collections and u...
- [`--use-attribute-docstrings`](field-customization.md#use-attribute-docstrings) - Generate field descriptions as attribute docstrings instead ...
- [`--use-decimal-for-multiple-of`](typing-customization.md#use-decimal-for-multiple-of) - Generate Decimal types for fields with multipleOf constraint...
- [`--use-default`](model-customization.md#use-default) - Use default values from schema in generated models.
- [`--use-default-factory-for-optional-nested-models`](model-customization.md#use-default-factory-for-optional-nested-models) - Generate default_factory for optional nested model fields.
- [`--use-default-kwarg`](model-customization.md#use-default-kwarg) - Use default= keyword argument instead of positional argument...
- [`--use-double-quotes`](template-customization.md#use-double-quotes) - Use double quotes for string literals in generated code.
- [`--use-enum-values-in-discriminator`](field-customization.md#use-enum-values-in-discriminator) - Use enum values in discriminator mappings for union types.
- [`--use-exact-imports`](template-customization.md#use-exact-imports) - Import exact types instead of modules.
- [`--use-field-description`](field-customization.md#use-field-description) - Include schema descriptions as Field docstrings.
- [`--use-frozen-field`](model-customization.md#use-frozen-field) - Generate frozen (immutable) field definitions for readOnly p...
- [`--use-generic-container-types`](typing-customization.md#use-generic-container-types) - Use typing.Dict/List instead of dict/list for container type...
- [`--use-inline-field-description`](field-customization.md#use-inline-field-description) - Add field descriptions as inline comments.
- [`--use-non-positive-negative-number-constrained-types`](typing-customization.md#use-non-positive-negative-number-constrained-types) - Use NonPositive/NonNegative types for number constraints.
- [`--use-one-literal-as-default`](model-customization.md#use-one-literal-as-default) - Use single literal value as default when enum has only one o...
- [`--use-operation-id-as-name`](openapi-only-options.md#use-operation-id-as-name) - Use OpenAPI operationId as the generated function/class name...
- [`--use-pendulum`](typing-customization.md#use-pendulum) - Use pendulum types for date/time fields instead of datetime ...
- [`--use-schema-description`](field-customization.md#use-schema-description) - Use schema description as class docstring.
- [`--use-serialize-as-any`](model-customization.md#use-serialize-as-any) - Wrap fields with subtypes in Pydantic's SerializeAsAny.
- [`--use-status-code-in-response-name`](openapi-only-options.md#use-status-code-in-response-name) - Include HTTP status code in response model names.
- [`--use-subclass-enum`](model-customization.md#use-subclass-enum) - Generate typed Enum subclasses for enums with specific field...
- [`--use-title-as-name`](field-customization.md#use-title-as-name) - Use schema title as the generated class name.
- [`--use-type-alias`](typing-customization.md#use-type-alias) - Use TypeAlias instead of root models for type definitions (e...
- [`--use-unique-items-as-set`](typing-customization.md#use-unique-items-as-set) - Generate set types for arrays with uniqueItems constraint.
- [`--validation`](openapi-only-options.md#validation) - Enable validation constraints (deprecated, use --field-const...
- [`--version`](utility-options.md#version) - Show program version and exit
- [`--watch`](general-options.md#watch) - Watch mode cannot be used with --check mode.
- [`--watch-delay`](general-options.md#watch-delay) - Watch mode starts file watcher and handles clean exit.
- [`--wrap-string-literal`](template-customization.md#wrap-string-literal) - Wrap long string literals across multiple lines.
