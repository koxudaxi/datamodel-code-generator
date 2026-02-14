# Changelog

All notable changes to this project are documented in this file.
This changelog is automatically generated from GitHub Releases.

---
## [0.54.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.54.0) - 2026-02-14

## Breaking Changes



### Code Generation Changes
* Enum member names from oneOf/anyOf const constructs now use `title` field when provided - Previously, when creating enums from `oneOf`/`anyOf` constructs with `const` values, the `title` field was incorrectly ignored and enum member names were generated using the pattern `{type}_{value}` (e.g., `integer_200`). Now, when a `title` is specified, it is correctly used as the enum member name (e.g., `OK` instead of `integer_200`). Users who have code depending on the previously generated enum member names will need to update their references. (#2975)
  Before:
  ```python
  class StatusCode(IntEnum):
      integer_200 = 200
      integer_404 = 404
      integer_500 = 500
  ```
  After:
  ```python
  class StatusCode(IntEnum):
      OK = 200
      Not_Found = 404
      Server_Error = 500
  ```
* Field names matching Python builtins are now automatically sanitized - When a field name matches a Python builtin type AND the field's type annotation uses that same builtin (e.g., `int: int`, `list: list[str]`, `dict: dict[str, Any]`), the field is now renamed with a trailing underscore (e.g., `int_`) and an alias is added to preserve the original JSON field name. This prevents Python syntax issues and shadowing of builtin types. Previously, such fields were generated as-is (e.g., `int: int | None = None`), which could cause code that shadows Python builtins. After this change, the same field becomes `int_: int | None = Field(None, alias='int')`. This affects fields named: `int`, `float`, `bool`, `str`, `bytes`, `list`, `dict`, `set`, `frozenset`, `tuple`, and other Python builtins when their type annotation uses the matching builtin type. (#2968)
* $ref with non-standard metadata fields no longer triggers schema merging - Previously, when a `$ref` was combined with non-standard fields like `markdownDescription`, `if`, `then`, `else`, or other extras not in the whitelist, the generator would merge schemas and potentially create duplicate models (e.g., `UserWithExtra` alongside `User`). Now, only whitelisted schema-affecting extras (currently just `const`) trigger merging. This means:
  - Fewer merged/duplicate models will be generated
  - References are preserved directly instead of being expanded
  - Field types may change from inline merged types to direct references
  Example schema:
  ```yaml
  properties:
    user:
      $ref: "#/definitions/User"
      nullable: true
      markdownDescription: "A user object"
  ```
  Before: Could generate a merged `UserWithMarkdownDescription` model
  After: Directly uses `User | None` reference (#2993)
* Enum member names no longer get underscore suffix with `--capitalise-enum-members` - Previously, enum values like `replace`, `count`, `index` would generate `REPLACE_`, `COUNT_`, `INDEX_` when using `--capitalise-enum-members`. Now they correctly generate `REPLACE`, `COUNT`, `INDEX`. The underscore suffix is only added when `--use-subclass-enum` is also used AND the lowercase name conflicts with builtin type methods. Users relying on the previous naming (e.g., referencing `MyEnum.REPLACE_` in code) will need to update to use the new names without trailing underscores. (#2999)
* Fields using `$ref` with inline keywords now include merged metadata - When a schema property uses `$ref` alongside additional keywords (e.g., `const`, `enum`, `readOnly`, constraints), the generator now correctly merges metadata (description, title, constraints, defaults, readonly/writeOnly) from the referenced schema into the field definition. Previously, this metadata was lost. For example, a field like `type: Type` may now become `type: Type = Field(..., description='Type of this object.', title='type')` when the referenced schema includes those attributes. This also affects `additionalProperties` and OpenAPI parameter schemas. (#2997)

## What's Changed
* Refactor ruff check+format to use sequential subprocess calls by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2967
* Fix title ignored when creating enums from merging `allOf`'s or `anyOf`'s objects by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2975
* Fix aliased imports not applied to base classes and non-matching fields by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2981
* Fix handling of falsy default values for enums in set-default-enum-member option by @kkinugasa in https://github.com/koxudaxi/datamodel-code-generator/pull/2977
* Fix use_union_operator with Python builtin type field names by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2968
* Support $recursiveRef/$dynamicRef in JSON Schema and OpenAPI by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2982
* Address review feedback for recursive/dynamic ref support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2985
* Fix RecursionError in _merge_ref_with_schema for circular $ref by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2983
* Fix missing Field import with multiple aliases on required fields by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2992
* Fix patternProperties/propertyNames key constraints lost with field_constraints by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2994
* Fix type loss when $ref is used with non-standard metadata fields by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2993
* Fix missing | None for nullable enum literals in TypedDict by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2991
* Fix exact imports with module/class name collision by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2998
* Fix extra underscore on enum members like replace with --capitalise-enum-members by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2999
* Fix merged result in parse_item not passed back to parse_object_fields by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2997
* Fix codespeed python version by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/3000
* Fix incorrect relative imports with --use-exact-imports and --collapse-root-models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2996

## New Contributors
* @kkinugasa made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2977

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.53.0...0.54.0

---

## [0.53.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.53.0) - 2026-01-12

## Breaking Changes





### Custom Template Update Required
* Parser subclass signature change - The `Parser` base class now requires two generic type parameters: `Parser[ParserConfigT, SchemaFeaturesT]` instead of just `Parser[ParserConfigT]`. Custom parser subclasses must be updated to include the second type parameter. (#2929)
  ```python
  # Before
  class MyCustomParser(Parser["MyParserConfig"]):
      ...
  # After
  class MyCustomParser(Parser["MyParserConfig", "JsonSchemaFeatures"]):
      ...
  ```
* New abstract `schema_features` property required - Custom parser subclasses must now implement the `schema_features` abstract property that returns a `JsonSchemaFeatures` (or subclass) instance. (#2929)
  ```python
  from functools import cached_property
  from datamodel_code_generator.parser.schema_version import JsonSchemaFeatures
  from datamodel_code_generator.enums import JsonSchemaVersion
  class MyCustomParser(Parser["MyParserConfig", "JsonSchemaFeatures"]):
      @cached_property
      def schema_features(self) -> JsonSchemaFeatures:
          return JsonSchemaFeatures.from_version(JsonSchemaVersion.Draft202012)
  ```
* Parser `_create_default_config` refactored to use class variable - Subclasses that override `_create_default_config` should now set the `_config_class_name` class variable instead. The base implementation uses this variable to dynamically instantiate the correct config class. (#2929)
  ```python
  # Before
  @classmethod
  def _create_default_config(cls, options: MyConfigDict) -> MyParserConfig:
      # custom implementation...
  # After
  _config_class_name: ClassVar[str] = "MyParserConfig"
  # No need to override _create_default_config if using standard config creation
  ```
* Template condition for default values changed - If you use custom Jinja2 templates based on `BaseModel_root.jinja2` or `RootModel.jinja2`, the condition for including default values has changed from `field.required` to `(field.required and not field.has_default)`. Update your custom templates if you override these files. (#2960)

### Code Generation Changes
* RootModel default values now included in generated code - Previously, default values defined in JSON Schema or OpenAPI specifications for root models were not being applied to the generated Pydantic code. Now these defaults are correctly included. For example, a schema defining a root model with `default: 1` will generate `__root__: int = 1` (Pydantic v1) or `root: int = 1` (Pydantic v2) instead of just `__root__: int` or `root: int`. This may affect code that relied on the previous behavior where RootModel fields had no default values. (#2960)
* Required fields with list defaults now use `default_factory` - Previously, required fields with list-type defaults (like `__root__: list[ID] = ['abc', 'efg']`) were generated with direct list assignments. Now they correctly use `Field(default_factory=lambda: ...)` which follows Python best practices for mutable defaults. This changes the structure of generated code for root models and similar patterns with list defaults. (#2958)
  Before:
  ```python
  class Family(BaseModel):
      __root__: list[ID] = ['abc', 'efg']
  ```
  After:
  ```python
  class Family(BaseModel):
      __root__: list[ID] = Field(
          default_factory=lambda: [ID.parse_obj(v) for v in ['abc', 'efg']]
      )
  ```

## What's Changed
* Separate pytest-benchmark into dedicated benchmark dependency group by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2937
* Support ClassVar for Pydantic v2 by @ubaumann in https://github.com/koxudaxi/datamodel-code-generator/pull/2920
* Add schema version detection and feature flags by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2924
* Fix MRO ordering for multiple inheritance in GraphQL and JSON Schema/OpenAPI by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2941
* Add schema_features property to parsers for version detection by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2929
* Fix $ref handling in request-response mode for readOnly/writeOnly schemas by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2942
* Ensure codecov upload runs even when coverage check fails by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2944
* Add FeatureMetadata to schema feature classes for doc generation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2945
* Add schema-docs auto-generation with pre-commit and CI by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2949
* Add comprehensive feature metadata to schema version dataclasses by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2946
* fix: move UnionMode import outside TYPE_CHECKING for Pydantic runtime… by @phil65 in https://github.com/koxudaxi/datamodel-code-generator/pull/2950
* Fix IndexError when using --reuse-scope=tree with single file output by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2954
* Add --use-closed-typed-dict option to control PEP 728 TypedDict generation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2956
* Fix RootModel default value not being applied by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2960
* Fix required list fields ignoring empty default values by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2958
* Add GenerateConfig lazy import from top-level module by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2961
* Fix allOf array property merging to preserve child $ref by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2962
* Fix array RootModel default value handling in parser by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2963
* Fix bug in handling of graphql empty list defaults by @rpmcginty in https://github.com/koxudaxi/datamodel-code-generator/pull/2948

## New Contributors
* @ubaumann made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2920
* @phil65 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2950

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.52.2...0.53.0

---

## [0.52.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.52.2) - 2026-01-05

## What's Changed
* Add support for multiple base classes in base_class_map and customBasePath by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2916
* Add __hash__ to Pydantic v2 models used in sets by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2918
* fix: Handle class name prefix correctly in GraphQL parser by @siminn-arnorgj in https://github.com/koxudaxi/datamodel-code-generator/pull/2926
* Add TypedDict closed and extra_items support (PEP 728) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2922
* Fix release-draft workflow to use pull_request_target and increase max_turns to 50 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2930
* Migrate from pyright to ty type checker by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2928
* Fix URL port handling in get_url_path_parts by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2933


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.52.1...0.52.2

---

## [0.52.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.52.1) - 2026-01-03

## What's Changed
* Add --validators option for Pydantic v2 field validators by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2906
* Add dynamic model generation support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2901
* Sync zensical.toml nav with docs directory by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2908
* Add deprecation warning for default output-model-type by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2910
* Add deprecation warning and explicit --output-model-type to docs by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2911
* Add llms.txt generator for LLM-friendly documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2912
* Move coverage fail_under check to combined coverage environment by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2909
* Fix YAML scientific notation parsing as float by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2913
* Add deprecated field support for Pydantic v2 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2915
* Add deprecation warning for Pydantic v2 without --use-annotated by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2914


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.52.0...0.52.1

---

## [0.52.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.52.0) - 2026-01-02

## Breaking Changes




### Code Generation Changes
* Union fields with titles now wrapped in named models when `--use-title-as-name` is enabled - Previously, union-typed fields with a `title` were generated as inline union types (e.g., `TypeA | TypeB | TypeC | None`). Now they generate a separate wrapper model using the title name, and the field references this wrapper type (e.g., `ProcessingStatusUnionTitle | None`). This affects code that directly accesses union field values, as they now need to access the `.root` attribute (Pydantic v2) or `.__root__` (Pydantic v1) of the wrapper model. (#2889)
  **Before:**
  ```python
  class ProcessingTaskTitle(BaseModel):
      processing_status_union: (
          ProcessingStatusDetail | ExtendedProcessingTask | ProcessingStatusTitle | None
      ) = Field('COMPLETED', title='Processing Status Union Title')
  ```
  **After:**
  ```python
  class ProcessingStatusUnionTitle(BaseModel):
      __root__: (
          ProcessingStatusDetail | ExtendedProcessingTask | ProcessingStatusTitle
      ) = Field(..., title='Processing Status Union Title')
  class ProcessingTaskTitle(BaseModel):
      processing_status_union: ProcessingStatusUnionTitle | None = Field(
          default_factory=lambda: ProcessingStatusUnionTitle.parse_obj('COMPLETED'),
          title='Processing Status Union Title',
      )
  ```
* Inline types with titles now generate named type aliases when `--use-title-as-name` is enabled - Arrays, dicts, enums-as-literals, and oneOf/anyOf unions that have a `title` in the schema now generate named type aliases or RootModel classes instead of being inlined. This improves readability but changes the generated type structure. For TypedDict output, generates `type MyArrayName = list[str]`. For Pydantic output, generates `class MyArrayName(RootModel[list[str]])`. (#2889)
* Default value handling changed for wrapped union fields - Fields that previously had simple default values now use `default_factory` with a lambda that calls `parse_obj()` (Pydantic v1) or `model_validate()` (Pydantic v2) to construct the wrapper model. Code that introspects field defaults will see a factory function instead of a direct value. (#2889)
* Different output for `$ref` with `nullable: true` - When a JSON Schema property has a `$ref` combined with only `nullable: true` (and optionally metadata like `title`/`description`), the generator now uses the referenced type directly with `Optional` annotation instead of creating a new merged model. For example, a schema with multiple properties referencing `User` with `nullable: true` will now generate `user_a: User | None` instead of creating separate `UserA`, `UserB` model classes. This is a bug fix that reduces redundant model generation, but existing code that depends on the previously generated class names will break. (#2890)
  Before:
  ```python
  class UserA(BaseModel):
      name: str
  class UserB(BaseModel):
      name: str
  class Model(BaseModel):
      user_a: UserA | None = None
      user_b: UserB | None = None
  ```
  After:
  ```python
  class User(BaseModel):
      name: str
  class Model(BaseModel):
      user_a: User | None = None
      user_b: User | None = None
  ```
* Type alias generation expanded for `--use-title-as-name` - When using `--use-title-as-name`, the generator now creates type aliases for additional cases: nested array items with titles, additionalProperties values with titles, oneOf/anyOf branches with titles, patternProperties, propertyNames, and primitive types with titles. Previously these were inlined; now they generate named type aliases. This is a bug fix per #2887, but changes generated output for schemas with titles on nested elements. (#2891)
* Title no longer inherited in combined schemas - In anyOf/oneOf/allOf schemas, the parent schema's `title` is now excluded when merging with child schemas. This prevents unintended title inheritance that could affect model naming when `--use-title-as-name` is enabled. (#2891)
* `allOf` with single `$ref` no longer creates wrapper class - When a schema property uses `allOf` with only a single `$ref` and no additional properties, the generator now directly references the target type instead of creating an unnecessary wrapper class. This may affect code that depends on the previously generated wrapper class names or structure. For example, a property defined as `allOf: [$ref: '#/components/schemas/ACHClass']` will now generate `ach_class: ACHClass | None` instead of creating an intermediate wrapper type. (#2902)

## What's Changed
* Add ULID and Email format documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2886
* Add --class-name-prefix, --class-name-suffix, and --class-name-affix-scope options by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2885
* Use class-name-suffix for parser config TypedDicts by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2888
* Create type aliases for inline types with title when use-title-as-name is enabled by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2889
* Fix duplicate model generation for $ref with nullable by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2890
* Create type aliases for nested elements with titles when use-title-as-name is enabled by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2891
* Clarify --aliases help text to explain schema field becomes Pydantic alias by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2892
* Document external library import use case for --type-overrides by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2893
* Add documentation for reducing duplicate field types by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2896
* Add FutureWarning for upcoming ruff default formatters by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2895
* Add --openapi-include-paths option for path-based model filtering by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2894
* Add --graphql-no-typename option to exclude typename field by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2899
* Add --default-values CLI option for overriding field defaults by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2897
* Fix allOf with single ref creating unnecessary wrapper class by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2902
* Fix --reuse-model --collapse-reuse-models to deduplicate identical inline definitions by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2903
* Add --use-serialization-alias option for Pydantic v2 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2905
* Fix Pydantic v2 discriminated unions in array fields by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2907


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.51.0...0.52.0

---

## [0.51.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.51.0) - 2026-01-01

## Breaking Changes



### Code Generation Changes
* Different output when using `--input-model` with Set, FrozenSet, Mapping, or Sequence types - When using `--input-model` to convert Pydantic models or dataclasses, types that were previously converted to `list` or `dict` are now preserved as their original Python types. For example, a field typed as `Set[str]` now generates `set[str]` instead of `list[str]`, `FrozenSet[T]` generates `frozenset[T]`, `Mapping[K, V]` generates `Mapping[K, V]` instead of `dict[K, V]`, and `Sequence[T]` generates `Sequence[T]` instead of `list[T]`. This may cause type checking differences or runtime behavior changes if your code depended on the previous output types. (#2837)
* allOf multi-ref with property overrides now preserves inheritance - Schemas using `allOf` with multiple `$ref` items where the child schema also defines properties that override parent properties will now generate classes with multiple inheritance (e.g., `class Person(Thing, Location)`) instead of a flattened single class with all properties merged inline. Previously, child property overrides were incorrectly treated as conflicts, triggering schema merging. Users relying on the flattened output may need to adjust their code. (#2838)
  Before:
  ```python
  class Person(BaseModel):
      type: str | None = 'playground:Person'
      name: constr(min_length=1) | None = None
      address: constr(min_length=5)
      age: int | None = None
  ```
  After:
  ```python
  class Thing(BaseModel):
      type: str
      name: constr(min_length=1)
  class Location(BaseModel):
      address: constr(min_length=5)
  class Person(Thing, Location):
      type: str | None = 'playground:Person'
      name: constr(min_length=1) | None = None
      age: int | None = None
  ```
* Ruff unsafe fixes now applied automatically - When using the `ruff-check` formatter, the `--unsafe-fixes` flag is now passed to ruff, which enables fixes that may change code behavior in potentially incorrect ways. This includes removing unused imports that might have side effects, removing unused variables that could affect debugging, and other transformations ruff considers "unsafe". Users who relied on the previous conservative safe-only fix behavior may see different generated code output. To restore the previous behavior, users can configure ruff via `pyproject.toml` or `ruff.toml` to disable specific unsafe rules. (#2847)
* Type aliases now generate as class inheritance - When using `--reuse-model` (Pydantic v2 only), models that would previously generate as type aliases (`ChildModel = ParentModel`) now generate as explicit subclasses (`class ChildModel(ParentModel): pass`). This change improves type checker compatibility and maintains proper type identity, but may affect code that relied on type alias semantics or compared types directly. (#2853)
  Before:
  ```python
  ArmLeft = ArmRight
  ```
  After:
  ```python
  class ArmLeft(ArmRight):
      pass
  ```
* Fields with `const` values in anyOf/oneOf now generate `Literal` types instead of inferred base types - Previously, a `const` value like `"MODE_2D"` in an anyOf/oneOf schema would generate `str` type. Now it generates `Literal["MODE_2D"]`. This change affects type hints in generated models and may require updates to code that type-checks against the generated output. For example:
  ```python
  # Before (v0.x)
  map_view_mode: str = Field("MODE_2D", alias="mapViewMode", const=True)
  apiVersion: str = Field('v1', const=True)
  # After (this PR)
  map_view_mode: Literal["MODE_2D"] = Field("MODE_2D", alias="mapViewMode", const=True)
  apiVersion: Literal['v1'] = Field('v1', const=True)
  ```
  This is a bug fix that makes the generated code more type-safe, but downstream code performing type comparisons or using `isinstance(field, str)` checks may need adjustment. (#2864)

### Custom Template Update Required
* New DataType flags available for custom templates - Three new boolean flags have been added to the `DataType` class: `is_frozen_set`, `is_mapping`, and `is_sequence`. Custom Jinja2 templates that inspect DataType flags may need to be updated to handle these new type variations if they contain logic that depends on exhaustive type flag checks. (#2837)
* Pydantic v2 BaseModel.jinja2 template structure changed - If you have a custom template that extends or modifies the default `pydantic_v2/BaseModel.jinja2` template, you need to update it. The conditional block that generated type aliases (`{% if base_class != "BaseModel" and ... %}{{ class_name }} = {{ base_class }}{% else %}...{% endif %}`) has been removed. Templates should now always generate class declarations. (#2853)

### Default Behavior Changes
* `--input-model-ref-strategy reuse-foreign` behavior changed - Previously, this strategy compared the source type family against the **input** model's family (e.g., if input was Pydantic, any non-Pydantic type like dataclass was considered "foreign" and reused). Now it compares against the **output** model's family. This means types that were previously imported/reused may now be regenerated, and vice versa. For example, when converting a Pydantic model containing a dataclass to TypedDict output, the dataclass was previously imported (it was "foreign" to Pydantic input), but now it will be regenerated (it's not the same family as TypedDict output). Enums are always reused regardless of output type. (#2854)

### API/CLI Changes
* Mixing config and keyword arguments now raises ValueError - Previously, `generate()` allowed passing both a `config` object and individual keyword arguments, with keyword arguments overriding config values. Now, providing both raises `ValueError: "Cannot specify both 'config' and keyword arguments. Use one or the other."` Users must choose one approach: either pass a `GenerateConfig` object or use keyword arguments, but not both. (#2874)
  ```python
  # Before (worked): keyword args overrode config values
  generate(input_=schema, config=config, output=some_path)
  # After (raises ValueError): must use one or the other
  # Option 1: Use config only (include output in config)
  config = GenerateConfig(output=some_path, ...)
  generate(input_=schema, config=config)
  # Option 2: Use keyword args only
  generate(input_=schema, output=some_path, ...)
  ```
* Parser signature simplified to config + options pattern - `Parser.__init__`, `JsonSchemaParser.__init__`, `OpenAPIParser.__init__`, and `GraphQLParser.__init__` now accept either a `config: ParserConfig` object OR keyword arguments via `**options: Unpack[ParserConfigDict]`, but not both simultaneously. Passing both raises a `ValueError`. Existing code using only keyword arguments continues to work unchanged. (#2877)
  ```python
  # Before: Could potentially mix config with kwargs (undefined behavior)
  parser = JsonSchemaParser(source="{}", config=some_config, field_constraints=True)
  # After: Raises ValueError - must use one approach or the other
  parser = JsonSchemaParser(source="{}", config=some_config)  # Use config object
  # OR
  parser = JsonSchemaParser(source="{}", field_constraints=True)  # Use keyword args
  ```
* Subclass compatibility - Code that subclasses `Parser`, `JsonSchemaParser`, `OpenAPIParser`, or `GraphQLParser` may need updates if they override `__init__` and call `super().__init__()` with explicit parameter lists. The new signature uses `**options: Unpack[ParserConfigDict]` instead of explicit parameters. (#2877)
* `Config.input_model` type changed from `str` to `list[str]` - The `input_model` field in the `Config` class now stores a list of strings instead of a single string. While backward compatibility is maintained when *setting* the value (single strings are automatically coerced to lists), code that *reads* `config.input_model` will now receive a `list[str]` instead of `str | None`. Users who programmatically access this field should update their code to handle the list type. (#2881)
  ```python
  # Before
  if config.input_model:
      process_model(config.input_model)  # config.input_model was str
  # After
  if config.input_model:
      for model in config.input_model:  # config.input_model is now list[str]
          process_model(model)
  ```

## What's Changed
* Add public API signature baselines by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2832
* Add deprecation warning for Pydantic v1 runtime by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2833
* Fix --use-generic-container-types documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2835
* Add extends support for profile inheritance by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2834
* Fix CLI option docstrings and add missing tests by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2836
* Preserve Python types (Set, Mapping, Sequence) in --input-model by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2837
* Replace docstring with option_description in cli_doc marker by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2839
* Fix allOf multi-ref to preserve inheritance with property overrides by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2838
* Fix x-python-type for Optional container types in anyOf schemas by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2840
* Support incompatible Python types in x-python-type extension by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2841
* Fix nested type imports in x-python-type override by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2842
* Fix deep hierarchy type inheritance in allOf property overrides by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2843
* Fix CLI doc option_description errors in tests and build script by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2846
* Add --unsafe-fixes to ruff-check formatter by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2847
* Add support for multiple aliases using Pydantic v2 AliasChoices by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2845
* Handle types.UnionType in _serialize_python_type for Python 3.10-3.13 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2848
* Fix set/frozenset duplicate output in x-python-type serialization by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2849
* Add --input-model-ref-strategy option for controlling type reuse by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2850
* Fix DataType deepcopy infinite recursion with circular references by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2852
* Add automatic handling of unserializable types in --input-model by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2851
* Fix reuse-foreign to compare with output type instead of input type by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2854
* Fix reuse-model generating type aliases instead of class inheritance by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2853
* Add AST-based type string parsing helpers by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2856
* Fix x-python-type qualified name imports using AST helper by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2857
* Fix generic type import with module path by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2858
* Use __qualname__ for nested class support and add DefaultPutDict test by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2859
* fix: handle type definitions from grand(grand...) parent schemas by @simontaurus in https://github.com/koxudaxi/datamodel-code-generator/pull/2861
* Add defaultdict and Any to PYTHON_TYPE_IMPORTS by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2860
* Add defaultdict to preserved type origins for TypedDict generation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2866
* Handle Annotated types in _serialize_python_type for TypedDict generation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2867
* Remove WithJsonSchema from ExtraTemplateDataType by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2868
* Fix const in anyOf/oneOf to generate Literal type by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2864
* Optimize deepcopy for empty lists by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2862
* Fix pre-commit hooks and pytest for Windows environments by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2871
* Fix _normalize_union_str to handle nested generic types by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2875
* Fix _normalize_union_str to recursively normalize nested unions by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2876
* feat: add --allof-class-hierarchy option by @simontaurus in https://github.com/koxudaxi/datamodel-code-generator/pull/2869
* Simplify generate() function signature using Unpack[GenerateConfigDict] by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2874
* Simplify Parser.__init__ signature using Unpack[ParserConfigDict] by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2877
* Refactor generate() and Parser to use config directly by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2878
* Update using_as_module.md to document config parameter by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2879
* fix: Always merge multiple GraphQL schemas before parsing by @siminn-arnorgj in https://github.com/koxudaxi/datamodel-code-generator/pull/2873
* Refactor: Use model_validate/parse_obj for Parser config initialization by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2880
* Add multiple --input-model support with inheritance preservation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2881
* Exclude OpenAPI/JSON Schema extension fields (x-*) by @ahmetveburak in https://github.com/koxudaxi/datamodel-code-generator/pull/2801
* Add pre-commit hook setup instructions to contributing guide by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2882
* Consolidate ParserConfig TypedDict profiles with inheritance preservation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2883
* Add release notification workflow by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2884

## New Contributors
* @simontaurus made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2861

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.50.0...0.51.0

---

## [0.50.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.50.0) - 2025-12-28

## Breaking Changes


















### Code Generation Changes
* Models with `unevaluatedProperties` now generate extra field configuration - JSON Schemas containing `unevaluatedProperties: false` will now generate models with `extra='forbid'` (Pydantic v2) or `extra = Extra.forbid` (Pydantic v1), and schemas with `unevaluatedProperties: true` will generate `extra='allow'`. Previously this keyword was ignored. This may cause validation errors for data that was previously accepted. (#2797)
  Example - a schema like:
  ```json
  {
    "title": "Resource",
    "type": "object",
    "properties": { "name": { "type": "string" } },
    "unevaluatedProperties": false
  }
  ```
  Previously generated:
  ```python
  class Resource(BaseModel):
      name: str | None = None
  ```
  Now generates:
  ```python
  class Resource(BaseModel):
      model_config = ConfigDict(extra='forbid')
      name: str | None = None
  ```

### Default Behavior Changes
* Default encoding changed from system locale to UTF-8 - The default encoding for reading input files and writing output is now always `utf-8` instead of the system's locale-preferred encoding (e.g., `cp1252` on Windows). Users who rely on locale-specific encoding must now explicitly use `--encoding` to specify their desired encoding (#2802)

## What's Changed
* Fix missing model_config in query parameter classes by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2795
* Escape backslash and triple quotes in docstrings by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2796
* Add unevaluatedProperties support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2797
* Expose schema $id and path to template context by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2798
* Improve CLI startup time with lazy imports by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2799
* Use UTF-8 as default encoding instead of locale-preferred by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2802
* Add model-level json_schema_extra support for Pydantic v2 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2803
* Add input_model field support to cli_doc marker by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2805
* Add dict input support for generate() function by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2806
* Optimize extra_template_data copy in DataModel init by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2811
* Add LRU cache for file loading and path existence checks by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2810
* Optimize JSON/YAML loading with auto-detection and json.load by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2809
* Migrate docs deployment to Cloudflare Pages by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2812
* Optimize CI workflow with tox cache and remove dev check by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2815
* Fix superfluous None when using $ref with nullable type aliases by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2814
* Remove tox cache that breaks Windows CI by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2816
* Add --input-model option for Pydantic models and dicts by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2804
* Add ReadOnly support for TypedDict with --use-frozen-field by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2813
* Exclude perf tests from regular test runs by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2817
* Add extreme-scale performance tests with dynamic schema generation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2818
* Add ULID type support by @ahmetveburak in https://github.com/koxudaxi/datamodel-code-generator/pull/2820
* Add --enum-field-as-literal-map option and x-enum-field-as-literal schema extension by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2821
* Fix propertyNames constraint ignored when using $ref to enum definition by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2824
* Reduce CodSpeed benchmark tests for faster CI by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2826
* Optimize propertyNames $ref handling by calling get_ref_data_type directly by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2825
* Add missing path and ulid type mappings to TypedDict type manager by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2828
* Fix --check to use output path's pyproject.toml settings by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2831

## New Contributors
* @ahmetveburak made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2820

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.49.0...0.50.0

---

## [0.49.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.49.0) - 2025-12-25

## Breaking Changes

  ### SchemaParseError for Invalid Schema Data
  * Schema validation errors now raise `SchemaParseError` instead of Pydantic `ValidationError` - When parsing invalid schema data (e.g., `"minimum": "not_a_number"`), the library now raises `SchemaParseError` instead of passing through Pydantic's `ValidationError`. Users catching `pydantic.ValidationError` for schema validation failures should update to catch `SchemaParseError`. The original error is preserved in the `original_error` attribute. (#2786)

  ## Bug Fixes

  ### CLI Now Correctly Outputs to stdout
  * Fixed CLI to actually output to stdout when `--output` is not specified - The `--output` argument has always documented `(default: stdout)` in `--help`, but previously no output was produced. Now works as documented. (#2787)

  ## Other Notable Changes

  * `generate()` function now returns `str | GeneratedModules | None` instead of `None` - Existing code ignoring the return value is unaffected. (#2787)
  * Error message for multi-module output without directory changed to be more descriptive. (#2787)

## What's Changed
* Merge duplicate breaking change headings in release notes by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2776
* Optimize O(n²) algorithms and reduce redundant iterations by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2778
* Optimize performance with LRU caching and O(n) algorithms by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2777
* Optimize Jinja2 environment caching and ruff batch formatting by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2779
* Remove YAML parsing cache and deepcopy overhead by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2781
* Add performance e2e tests with large schema fixtures by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2782
* Convert Import class from Pydantic to dataclass for performance by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2783
* Add schema path context to error messages by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2786
* Return str or dict when output=None in generate() by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2787
* Add --http-timeout CLI option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2788
* Pass schema extensions to templates by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2790
* Add propertyNames and x-propertyNames support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2789
* Add support for additional_imports in extra-template-data JSON by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2793
* Update zensical to 0.0.15 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2794
* Add --use-field-description-example option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2792
* Add --collapse-root-models-name-strategy option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2791


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.48.0...0.49.0

---

## [0.48.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.48.0) - 2025-12-24

## Breaking Changes
















### Code Generation Changes
* Custom class name generator now applied consistently during duplicate name resolution - Previously, when using `custom_class_name_generator`, the default PascalCase naming was incorrectly applied during duplicate name resolution. Now the custom generator is respected throughout, which may change generated class names. For example, a class name like `nested_object_result` with a custom generator `f"Custom{name}"` will now produce `CustomNested_object_result` instead of `CustomNestedObjectResult`. Users relying on the previous behavior should update their code to expect the new, correct class names. (#2757)

* YAML 1.1 boolean keywords now preserved as strings in enums - Values like `YES`, `NO`, `on`, `off`, `y`, `n` that were previously converted to Python booleans are now preserved as their original string values. This fixes issues where string enum values were incorrectly converted but may change generated output for schemas that relied on the previous behavior. For example, a YAML enum with `YES` will now generate `YES = 'YES'` instead of being converted to `True`. (#2767)

### Default Behavior Changes
* YAML boolean parsing restricted to YAML 1.2 semantics - Only `true`, `false`, `True`, `False`, `TRUE`, `FALSE` are now recognized as boolean values. YAML 1.1 boolean aliases (`yes`, `no`, `on`, `off`, `y`, `n`, etc.) are no longer parsed as booleans and will be treated as strings. Non-lowercase forms (`True`, `False`, `TRUE`, `FALSE`) now emit a deprecation warning indicating future versions will only support lowercase `true`/`false`. (#2767)

## What's Changed
* Fix Google Analytics config for Zensical by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2748
* ci: add release draft workflow with Claude Code Action by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2749
* fix: improve release-draft workflow configuration by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2750
* fix: quote JSON schema in claude_args to preserve double quotes by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2751
* fix: remove redundant --output-format json from claude_args by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2752
* fix: increase max-turns from 5 to 10 for structured output by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2753
* chore: increase max-turns to 20 for better margin by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2754
* Add pydantic_v2.dataclass output type and remove pydantic v1 dataclass by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2746
* Fix Pydantic v2 deprecation warnings by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2747
* Add --use-tuple-for-fixed-items option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2756
* Fix custom_class_name_generator not applied consistently by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2757
* Add --base-class-map option for model-specific base classes by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2759
* Support 'timestamp with time zone' format by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2762
* Add --type-overrides option to replace schema types with custom Python types by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2758
* Add --use-root-model-type-alias option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2763
* Add --class-decorators option for custom model decorators by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2760
* Add --naming-strategy and --duplicate-name-suffix CLI options by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2761
* Add --generate-prompt option for LLM consultation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2764
* Add pydantic_v2.dataclass to output model types documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2765
* Clarify --input-file-type help text and CLI documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2768
* Support boolean values in patternProperties for JSON Schema 2020-12 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2766
* Use YAML 1.2-like bool semantics to fix YES/NO/on/off enum issues by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2767
* Add InvalidFileFormatError with detailed error messages by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2771
* Merge multiple patternProperties with same value type into single regex pattern by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2770
* Sync Common Recipes and badges between README and docs by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2773
* Fix primary-first naming for multi-file schemas with same-named definitions by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2772
* Optimize performance for large schema processing by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2774


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.47.0...0.48.0

---

## [0.47.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.47.0) - 2025-12-23

## Breaking Changes

### Code Generation Changes
* RootModel defaults use direct instantiation - RootModel fields with default values now generate `ClassName(value)` instead of `ClassName.model_validate(value)`. This produces cleaner code but changes the generated output (#2714)

* `--strict-nullable` now applies to JSON Schema - The `--strict-nullable` option is no longer OpenAPI-only and has been moved to Field customization options. It now also correctly respects `nullable` on array items (#2713, #2727)

### Custom Template Update Required
* If you use custom Jinja2 templates that check `field.nullable`, you may need to update them. The `nullable` field on JsonSchemaObject now defaults to `None` instead of `False`. Templates should check `field.nullable is True` instead of just `if field.nullable` (#2715)

  Example change:
  ```jinja2
  {# Before #}
  {%- if field.nullable %}...{% endif %}

  {# After #}
  {%- if field.nullable is true %}...{% endif %}
  ```

### Error Handling Changes
* Formatting failures emit warning instead of error - When code formatting fails (e.g., due to black errors), the generator now emits an unformatted output with a warning instead of raising an exception. This allows code generation to succeed even when formatting tools encounter issues (#2737)

## What's Changed
* Require @cli_doc marker for all CLI options by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2712
* fix: respect nullable on array items with --strict-nullable by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2713
* fix: wrap RootModel primitive defaults with default_factory by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2714
* Add --use-default-factory-for-optional-nested-models option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2711
* Fix nullable field access in custom templates with strict_nullable by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2715
* fix: skip non-model types in __change_field_name by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2717
* Add requestBodies scope support for OpenAPI by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2716
* Fix test data backspace escape by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2718
* fix: quote forward references in recursive RootModel generic parameters by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2720
* Add force_exec_validation option to catch runtime errors across Python versions by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2719
* Add validation for extra_args in test helper functions by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2723
* Fix discriminator with allOf without Literal type for Pydantic v2 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2722
* Fix regex_engine config not applied to RootModel generic by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2721
* Fix hostname format with field_constraints to use Field(pattern=...) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2724
* Move --strict-nullable from OpenAPI-only to Field customization by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2727
* Run CLI doc coverage test in CI without --collect-cli-docs by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2728
* Add --use-generic-base-class option for DRY model config by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2726
* Refactor parser base post-processing for DRY and type-safe implementation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2730
* Add --collapse-reuse-models option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2731
* Add --field-type-collision-strategy option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2733
* Revert "Add --field-type-collision-strategy option" by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2734
* Add --no-treat-dot-as-module option for flat output structure by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2732
* Add --field-type-collision-strategy option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2735
* Add --use-standard-primitive-types option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2736
* Emit unformatted output when formatting fails by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2737
* Fix aliasing of builtin type field names by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2738
* Add path filters to optimize CodeRabbit reviews by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2742
* Add --output-date-class option and date-time-local format support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2739
* Fix custom template directory not working for included templates by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2740
* Remove unnecessary model_config from RootModel subclasses by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2741
* Fix incorrect --type-mappings examples in documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2744
* Add Python 3.13 deprecation warning documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2743
* Add admonition support to CLI docs and document --use-default nullable behavior by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2745


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.46.0...0.47.0

---

## [0.46.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.46.0) - 2025-12-20

## Breaking Changes

 ### Python Version
 * Python 3.9 support dropped - Minimum Python version is now 3.10+ (#2692)

 ### Default Behavior Changes
 * Native type hints by default - `list[...]`/`dict[...]` are now used instead of `List[...]`/`Dict[...]`. Use `--no-use-standard-collections` to restore previous behavior (#2699)
 * Union operator by default - `X | Y` syntax is now used instead of `Union[X, Y]`/`Optional[X]`. Use `--no-use-union-operator` to restore previous behavior (#2703)

 ### Code Generation Changes
 * Nullable required fields no longer have default values (Pydantic v2) - Fields marked as both `required` and `nullable` no longer get `= None`. The `pydantic_v2/BaseModel.jinja2` template logic was updated to only assign default values when `field.required` is false. This fixes incorrect behavior where required fields could be omitted (#2520)
 * TypedDict respects enum_field_as_literal setting - TypedDict output now respects user's `--enum-field-as-literal` setting instead of forcing `all`. Added new `--enum-field-as-literal none` option (#2691)
 * prefixItems now generates tuple types - JSON Schema `prefixItems` with matching `minItems`/`maxItems` and no `items` now generates `tuple[T1, T2, ...]` instead of `list[...]`. This applies when the array has a fixed length with heterogeneous types (#2537)


## What's Changed
* feat: Add --use-status-code-in-response-name option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2688
* feat: Add support for number type with time-delta format by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2689
* docs: Add CHANGELOG.md with auto-update workflow by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2690
* feat: Add --enum-field-as-literal none option and respect user settings for TypedDict by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2691
* docs: Clarify default encoding behavior in documentation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2693
* ci: Improve CLI docs generation workflow by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2695
* feat(docs): Group CLI examples by schema type with tabs by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2696
* feat: Add --ignore-enum-constraints option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2694
* Add zensical.toml configuration by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2697
* fix: Make docs generation deterministic by sorting glob results and dict iterations by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2698
* feat: Drop Python 3.9 support, require Python 3.10+  by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2692
* fix: Update zensical dependency version to 0.0.13 for Python 3.10+ by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2700
* feat: Default to native list/dict type hints instead of typing.List/Dict by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2699
* fix: Remove unnecessary pass statement when nested class exists by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2704
* build: Replace pre-commit with prek by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2702
* fix: Improve state management in Imports, DataType, and DataModel classes by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2705
* feat: Default to union operator for type hints by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2703
* fix: handle fork PRs in lint workflow by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2706
* fix: handle fork PRs in readme and cli-docs workflows by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2707
* Nullable required fields should not have default value by @raymondbutcher in https://github.com/koxudaxi/datamodel-code-generator/pull/2520
* Add support for prefixItems to emit tuples by @saulshanabrook in https://github.com/koxudaxi/datamodel-code-generator/pull/2537
* Remove unnecessary flags from --check test by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2708
* fix: update expected files to use modern union type syntax (`str | None`) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2709
* fix: trigger docs build after changelog update by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2710

## New Contributors
* @raymondbutcher made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2520
* @saulshanabrook made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2537

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.45.0...0.46.0

---


## [0.45.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.45.0) - 2025-12-19

## What's Changed
* docs: add cross-links between CLI reference and usage documentation pages by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2678
* Migrate documentation build from MkDocs to Zensical by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2679
* docs: Improve landing page, README, and add FAQ with GitHub issue links by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2680
* docs: Comprehensive documentation improvements with CLI reference enhancements by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2681
* feat: Add documentation and GitHub links to --help output by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2682
* feat: Add official GitHub Action for CI/CD integration by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2683
* feat: Add watch mode for automatic code regeneration with debounce delay by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2686
* feat: Add --enable-command-header option to include command-line in file headers by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2684
* feat: Add --module-split-mode option to generate one file per model (#1170) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2685


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.44.0...0.45.0

---

## [0.44.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.44.0) - 2025-12-18

## What's Changed
* Fix empty dict/list defaults not generating default_factory for Pydantic models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2655
* Add --use-decimal-for-multiple-of option to avoid floating-point precision issues by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2656
* Remove mock remote ref test by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2659
* Skip `from __future__ import annotations` for Python 3.14+ targets (PEP 649) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2658
* Fix enum member names conflicting with builtin type methods by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2660
* Fix field name shadowing check to use issubclass for Pydantic v2 derived types by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2657
* Fix keep_model_order dependency ordering and reduce unnecessary model_rebuild() calls by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2661
* Fix missing __init__.py in intermediate package directories by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2662
* Fix msgspec tag_field conflict with discriminator field definition by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2663
* Fix dataclass field ordering conflict when inheriting from parent with default fields by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2664
* Fix msgspec mutable default values to use default_factory by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2666
* Add compile/exec validation for generated Python code in tests by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2665
* Fix allOf array items partial override to inherit parent item types instead of Any by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2667
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci[bot] in https://github.com/koxudaxi/datamodel-code-generator/pull/2668
* Fix --use-unique-items-as-set to output set literals for default values by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2672
* Fix allOf partial override to inherit parent constraints and add --allof-merge-mode option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2671
* Fix GraphQL parser to handle renamed objects correctly by @siminn-arnorgj in https://github.com/koxudaxi/datamodel-code-generator/pull/2670
* Add auto-generated CLI reference documentation from test cases by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2673
* Fix crash when parsing enum containing only null value by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2674
* Fix allOf with $ref to root model losing constraints by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2676
* Support enum-field-as-literal in GraphQL parser by @siminn-arnorgj in https://github.com/koxudaxi/datamodel-code-generator/pull/2677
* refactor: reduce e2e test duplication with parameterization and enhance CLI docs by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2675


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.43.1...0.44.0

---

## [0.43.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.43.1) - 2025-12-12

## What's Changed
* Add support for x-enumNames extension by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2653
* Fix allOf partial property overrides to inherit parent types instead of Any by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2654


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.43.0...0.43.1

---

## [0.43.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.43.0) - 2025-12-10

## What's Changed
* Fix extra blank line after custom file header with future imports by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2638
* Fix GraphQL enum renaming issue by @siminn-arnorgj in https://github.com/koxudaxi/datamodel-code-generator/pull/2642
* Fix allOf with description generating alias instead of class (Pydantic v2) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2643
* Fix enum default values using full path instead of short name in same module by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2644
* Fix --url option to resolve local fragment refs correctly by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2646
* Fix allOf with single $ref to preserve class inheritance by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2647
* Fix incorrect import when module and class have the same name by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2648
* Fix nullable propagation from $ref schema targets by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2649
* Add --use-frozen-field option for JSON Schema readOnly support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2650
* Add validation error for --use-specialized-enum when target Python version < 3.11 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2651
* Fix discriminator to use enum value instead of model name for single-value enums by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2652

## New Contributors
* @siminn-arnorgj made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2642

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.42.2...0.43.0

---

## [0.42.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.42.2) - 2025-12-08

## What's Changed
* Fix Python 3.9 compatibility regression in _scc.py by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2628
* Fix Python 3.9 compatibility: CI environment names by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2630
* Fix msgspec type hint generation for oneOf/anyOf with null type by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2629
* Fix missing imports for nested references when using --collapse-root-models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2631
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci[bot] in https://github.com/koxudaxi/datamodel-code-generator/pull/2632
* Fix unnecessary underscore suffix for field names in non-Pydantic models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2633
* Fix enum generation from oneOf/anyOf with const values by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2634
* Fix "A Parser can not resolve classes" error when allOf references enum from another schema by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2636
* Fix $ref not merging with additional schema keywords by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2635
* Extract helper methods and reduce code duplication across parsers by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2637


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.42.1...0.42.2

---

## [0.42.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.42.1) - 2025-12-08

## What's Changed
* Add named profile support and --ignore-pyproject option for pyproject.toml configuration by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2619
* Fix _internal module self-importing due to cached path property by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2621
* Add warning when components/schemas is empty but paths exist by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2622
* Fix msgspec discriminated union ClassVar generation and nullable type handling by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2620
* Fix extras lost in oneOf/anyOf structures with --field-include-all-keys by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2623
* Fix msgspec ClassVar generation for discriminator fields without   use_annotated by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2625
* Fix --check mode ignoring pyproject.toml formatter settings by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2626
* Use SerializeAsAny for pydantic v2 models with subclasses by @tobias-bahls in https://github.com/koxudaxi/datamodel-code-generator/pull/2612

## New Contributors
* @tobias-bahls made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2612

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.42.0...0.42.1

---

## [0.42.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.42.0) - 2025-12-08

## What's Changed
* Improve type resolution for inherited fields in allOf with complex schemas by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2614
* Fix circular imports in generated multi-module packages by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2613
* Wrap RootModel default values with type constructors by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2615
* Strict types now enforce field constraints by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2617
* Use default_factory for $ref with default values when using --use-annotated by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2618

## Breaking Changes

### Custom Template Update Required

If you use custom Jinja2 templates, you may need to update them to handle `default_factory` correctly with `--use-annotated`.

A new property `field.has_default_factory_in_field` has been added. Templates should check this property to avoid generating duplicate
default assignments when `Field(default_factory=...)` is used.

Example change in templates:
```jinja2
{# Before #}
{%- if not (field.required or ...) %} = {{ field.represented_default }}{% endif %}

{# After #}
{%- if not field.has_default_factory_in_field and not (field.required or ...) %} = {{ field.represented_default }}{% endif %}
```

Affected built-in templates:
- pydantic/BaseModel.jinja2
- pydantic/BaseModel_root.jinja2
- pydantic_v2/BaseModel.jinja2
- pydantic_v2/RootModel.jinja2


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.41.0...0.42.0

---

## [0.41.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.41.0) - 2025-12-05

## What's Changed
* Fix:  resolve relative $ref correctly when fetching schemas from HTTP URLs by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2600
* Add --read-only-write-only-model-type option for OpenAPI readOnly/writeOnly support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2587
* Add file:// URL protocol support for $ref resolution by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2601
* Fix: Improve reference resolution and handling of duplicate names by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2602
* Prevent invalid relative imports in single-file output for allOf/anyOf schemas by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2604
* Fix single-file treat-dot-as-module by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2603
* allOf ignores $ref when referencing oneOf/anyOf schemas by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2605
* Resolve relative $ref correctly in external path/webhook files by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2606
* Resolve $ref to locally defined $id without network access by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2608
* Correct import generation for dot notation schema names with inheritance by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2607
* Fix import alias if two types are provided (Json schema) by @Killian-fal in https://github.com/koxudaxi/datamodel-code-generator/pull/2611
* Use Enum Members in Discriminators with Safe Imports by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2609

## New Contributors
* @Killian-fal made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2611

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.40.0...0.41.0

---

## [0.40.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.40.0) - 2025-12-03

## What's Changed
* Fix invalid Union syntax when using --collapse-root-models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2594
* Fix enum member names for object values to use title/name/const keys by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2596
* Fix import handling in --collapse-root-models to exclude both Optional and Union by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2597
* Fix default_factory for Union types with dict defaults  by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2595
* Fix RootModel generation order to define referenced types first by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2592
* Fix TypeAlias with circular reference to class generates NameError by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2591
* Fix __future__ import placement with custom file headers by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2589
* Fix multiple types in array not generating Union when object has   properties by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2590
* Add scoped alias support for class-specific field renaming by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2599
* Fix: Handle dots in title when using --use-title-as-name option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2598


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.39.0...0.40.0

---

## [0.39.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.39.0) - 2025-12-02

## What's Changed
* Add --all-exports-scope and --all-exports-collision-strategy options for recursive exports by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2588


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.38.0...0.39.0

---

## [0.38.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.38.0) - 2025-12-02

## What's Changed
* Fix transitive local reference resolution in external schema files by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2577
* Fix crash when parsing JSON Schema with internal references from stdin by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2578
* Fix allOf with multiple refs having same property name generates broken models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2579
* Fix external $ref resolution in paths when components/schemas is missing by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2581
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci[bot] in https://github.com/koxudaxi/datamodel-code-generator/pull/2582
* Fix incorrect relative import path for namespaced schemas referencing subnamespaces by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2580
* Add --generate-cli-command option to generate CLI command from pyproject.toml by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2583
* Add --check option for CI verification of generated files by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2585
* Add --use-all-exports option to generate `__all__` in `__init__.py` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2586
* Fix empty array items to generate List[Any] instead of bare List by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2584


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.37.0...0.38.0

---

## [0.37.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.37.0) - 2025-12-01

## What's Changed
* Add PEP 257 docstrings to modules and test files by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2548
* Strict type annotations for DataType, Reference, and JsonSchemaParser by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2549
* ci: enable pytest-xdist parallel execution (-n auto) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2553
* Add `--generate-pyproject-config` CLI option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2551
* Refactor: Consolidate e2e test helpers and eliminate code duplication by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2552
* Perf: Lazy import inflect module to reduce import time by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2554
* Use time-machine for faster freeze_time by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2555
* Lazy import black and isort for faster test startup by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2556
* Fix: Add pragma no cover for legacy version compatibility code in format.py by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2557
* Improve test coverage by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2558
* Fix --keep-model-order to respect TypeAliasType field dependencies by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2560
* Add --type-mappings option to customize type mappings in JSON schema by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2559
* Restrict freezegun dependency to Python < 3.10 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2561
* Update .gitignore to include coverage files and IDE configurations by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2563
* Remove JetBrains from sponsors section by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2564
* fix: set not nullable not required Struct fields to UnsetType by @CharString in https://github.com/koxudaxi/datamodel-code-generator/pull/2504
* Add support for `webhooks` in `--openapi-scopes` by @HNygard in https://github.com/koxudaxi/datamodel-code-generator/pull/2481
* add dataclass arguments by @ICEPower420 in https://github.com/koxudaxi/datamodel-code-generator/pull/2437
* Preserve Aliased Imports During Cleanup by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2569
* Bugfix-TypeAlias-Rebuild ---> Main by @raj-open in https://github.com/koxudaxi/datamodel-code-generator/pull/2566
* Use TypeAlias instead of TypeAliasType for non-Pydantic v2 models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2562
* Support allOf polymorphism with discriminator in OpenAPI by @zdenecek in https://github.com/koxudaxi/datamodel-code-generator/pull/2530
* Improve reference validation and reserved name handling by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2568
* Fix: enable inline-snapshot update by using assert instead of pytest.fail by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2571
* Add use_attribute_docstrings Support by @voteblake in https://github.com/koxudaxi/datamodel-code-generator/pull/2550
* Fix recursive TypeAlias generation for Python 3.11 (covers mutual alias refs) by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2570
* Add automatic README command help update via GitHub Actions by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2574
* Fix README auto-update workflow to trigger CI with PAT by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2575
* Add --skip-root-model option to skip generating root model by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2572
* Add --reuse-scope option for cross-file model deduplication by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2573

## New Contributors
* @CharString made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2504
* @HNygard made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2481
* @ICEPower420 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2437
* @raj-open made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2566
* @zdenecek made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2530
* @voteblake made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2550

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.36.0...0.37.0

---

## [0.36.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.36.0) - 2025-11-26

## Breaking Changes
* OpenAPI `byte`-formatted string properties for Pydantic v2 are now generated as `bytes` fields that Pydantic automatically decodes from base64-encoded strings at runtime. Code that relied on these fields being plain `str` values (the encoded representation) may need to be updated. by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2511 (closes https://github.com/koxudaxi/datamodel-code-generator/issues/189)

* Enums inferred from OpenAPI / JSON Schema string or integer enums are now generated as specialized `StrEnum` / `IntEnum` subclasses by default when supported by the target Python version. This changes the base class of existing generated enums and can affect comparisons, JSON encoding, and downstream type checks. You can opt out using the `--no-use-specialized-enum` CLI flag or `use_specialized_enum = false` in the configuration file. by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2512 (closes https://github.com/koxudaxi/datamodel-code-generator/issues/1313 and https://github.com/koxudaxi/datamodel-code-generator/issues/2534)

* For some Pydantic v2 collection schemas that previously generated a `RootModel` wrapper (for example the `MyArray` case described in https://github.com/koxudaxi/datamodel-code-generator/issues/1830), the generated code now uses a `TypeAlias` instead of a dedicated model class. Projects that import or subclass such wrapper models may need to adjust to use the alias instead. by @butvinm in https://github.com/koxudaxi/datamodel-code-generator/pull/2505 (closes https://github.com/koxudaxi/datamodel-code-generator/issues/1848, https://github.com/koxudaxi/datamodel-code-generator/issues/2018, https://github.com/koxudaxi/datamodel-code-generator/issues/2427, and https://github.com/koxudaxi/datamodel-code-generator/issues/2487)


## What's Changed
* Add --use-type-alias flag to generate TypeAlias instead of root models by @butvinm in https://github.com/koxudaxi/datamodel-code-generator/pull/2505
* Fix Pydantic v1 runtime support by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2538
* Use subclass enum for GraphQL enums when the relative flag is used by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2514
* Add support for OpenAPI `byte` in Pydantic v2 by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2511
* Add support for specialized enums as StrEnum and IntEnum by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2512
* [Chore] Clean-up `TYPE_CHECKING` blocks by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2539
* Add support for unquoted `null` type by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2542
* Add inline-snapshot test dependency by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2546
* Support isort 7 by @jas4711 in https://github.com/koxudaxi/datamodel-code-generator/pull/2521
* Add inline-snapshot for test expected value management by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2544
* Add --use-inline-field-description option for inline docstring format by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2547


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.35.0...0.36.0

---

## [0.35.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.35.0) - 2025-10-09

## What's Changed
* Add support to Python 3.14 by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2469


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.34.0...0.35.0

---

## [0.34.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.34.0) - 2025-09-28

## What's Changed
* TypedDict: Add support for const fields using Literal by @erandagan in https://github.com/koxudaxi/datamodel-code-generator/pull/2475
* Correct custom CodeFormatter error message by @MrSnapperVibes in https://github.com/koxudaxi/datamodel-code-generator/pull/2489
* dataclass: Add support for const fields using Literal[T] by @ysndr in https://github.com/koxudaxi/datamodel-code-generator/pull/2486
* feat: Add argument to disable the __future__ annotations import by @daviddmd in https://github.com/koxudaxi/datamodel-code-generator/pull/2498
* Fix: Objects with additionalProperties shouldn't be unioned with None by default by @erandagan in https://github.com/koxudaxi/datamodel-code-generator/pull/2493

## New Contributors
* @erandagan made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2475
* @MrSnapperVibes made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2489
* @ysndr made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2486
* @daviddmd made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2498

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.33.0...0.34.0

---

## [0.33.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.33.0) - 2025-08-14

## What's Changed
* Use Pytest `tmp_path` fixture instead of `TemporaryDirectory` by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2463
* Revert default date-time behaviour to respect OpenAPI/JSON Schema specifications by @mueslo in https://github.com/koxudaxi/datamodel-code-generator/pull/2442
* Avoid mixing up configurations of different objects with the same name by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2461
* Fix Pydantic `@model_validator()` usage  for Pydantic 2.12 by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2472
* Run the test suite daily to check breaking changes by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2479
* Automatically infer CSV file type by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2467
* Avoid collapsing models when referencing a forwarding reference by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2465

## New Contributors
* @mueslo made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2442

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.32.0...0.33.0

---

## [0.32.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.32.0) - 2025-07-25

## What's Changed
* modify __typename field to honor `--use-default-kwarg` flag by @rpmcginty in https://github.com/koxudaxi/datamodel-code-generator/pull/2420
* Fix typo in variable name by @eltoder in https://github.com/koxudaxi/datamodel-code-generator/pull/2439
* Send use_non_positive_negative_number_constrained_types to the data type manager by @torarvid in https://github.com/koxudaxi/datamodel-code-generator/pull/2425
* Allow parsing non-string lists for required fields by @HeroGamers in https://github.com/koxudaxi/datamodel-code-generator/pull/2446
* Allow including path parameters in generated models by @MrLoh in https://github.com/koxudaxi/datamodel-code-generator/pull/2445
* Passing in treat_dot_as_module bool to Enum init function by @LukeAtThat in https://github.com/koxudaxi/datamodel-code-generator/pull/2456
* fix: correctly handle multiline comments in Unions by @anor4k in https://github.com/koxudaxi/datamodel-code-generator/pull/2454
* Return Parameter and RequestBody DataTypesare  by @MrLoh in https://github.com/koxudaxi/datamodel-code-generator/pull/2444

## New Contributors
* @rpmcginty made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2420
* @eltoder made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2439
* @torarvid made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2425
* @HeroGamers made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2446
* @MrLoh made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2445
* @LukeAtThat made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2456
* @anor4k made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2454

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.31.2...0.32.0

---

## [0.31.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.31.2) - 2025-06-22

## What's Changed
* fix: prevent code injection through filename in generated headers by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2428


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.31.1...0.31.2

---

## [0.31.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.31.1) - 2025-06-17

## What's Changed
* fix: documentation for --allow-extra-fields by @cosmo-grant in https://github.com/koxudaxi/datamodel-code-generator/pull/2416
* fix: respect `--extra-fields` option in pydantic v2 models by @cosmo-grant in https://github.com/koxudaxi/datamodel-code-generator/pull/2423


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.31.0...0.31.1

---

## [0.31.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.31.0) - 2025-06-12

## What's Changed
* Resolve capitalize-enum-member not working with use-subclass-enum and snake-case-field when typed enum by @kevin-paulson-mindbridge-ai in https://github.com/koxudaxi/datamodel-code-generator/pull/2418
* feat: add `--extra-fields` option to allow, forbid, or ignore extra fields by @cosmo-grant in https://github.com/koxudaxi/datamodel-code-generator/pull/2417
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2415


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.30.2...0.31.0

---

## [0.30.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.30.2) - 2025-06-07

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2393
* Support `coerce_numbers_to_str` in `ConfigDict` by @robotadam in https://github.com/koxudaxi/datamodel-code-generator/pull/2394
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2397
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2402
* fix: Unnecessary _aliased suffix added to models generated from GraphQL union types by @kyo-ago in https://github.com/koxudaxi/datamodel-code-generator/pull/2396
* fix: regression where _deep_merge() mutates list values in passed dictionary by @cosmo-grant in https://github.com/koxudaxi/datamodel-code-generator/pull/2400
* Handle JSON pointer escaped values by @jrnold in https://github.com/koxudaxi/datamodel-code-generator/pull/2401
* fix regex rewrite bug by @minomocca in https://github.com/koxudaxi/datamodel-code-generator/pull/2404
* Add `--frozen-dataclasses` flag to generate frozen dataclasses by @K-dash in https://github.com/koxudaxi/datamodel-code-generator/pull/2408
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2410
* fix generation of discriminated union values with no mapping by @kymckay in https://github.com/koxudaxi/datamodel-code-generator/pull/2412

## New Contributors
* @robotadam made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2394
* @kyo-ago made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2396
* @cosmo-grant made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2400
* @jrnold made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2401
* @minomocca made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2404
* @K-dash made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2408
* @kymckay made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2412

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.30.1...0.30.2

---

## [0.30.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.30.1) - 2025-04-28

## What's Changed
* fix: TypeError: '<' not supported between instances of 'str' and 'NoneType' by @gjcarneiro in https://github.com/koxudaxi/datamodel-code-generator/pull/2380
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2383
* fixes link to templates by @leonlowitzki in https://github.com/koxudaxi/datamodel-code-generator/pull/2382
* capitalise-enum-members not working since v0.28.5 by @kevin-paulson-mindbridge-ai in https://github.com/koxudaxi/datamodel-code-generator/pull/2389

## New Contributors
* @leonlowitzki made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2382
* @kevin-paulson-mindbridge-ai made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2389

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.30.0...0.30.1

---

## [0.30.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.30.0) - 2025-04-17

## What's Changed
* feat: add new option --parent-scoped-naming to avoid name collisions by @gjcarneiro in https://github.com/koxudaxi/datamodel-code-generator/pull/2373


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.29.0...0.30.0

---

## [0.29.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.29.0) - 2025-04-17

## What's Changed
* Fix shadowed import errors by aliasing conflicting symbols in generated models by @sternakt in https://github.com/koxudaxi/datamodel-code-generator/pull/2379
* fix: Pass encoding parameter to parser in init.generate() by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2367
* Bump upper version limit on the inflect library from 6 to 8 by @gothicVI in https://github.com/koxudaxi/datamodel-code-generator/pull/2375
* feat: save memory in pydantic2 by avoiding simple aliasing empty classes by @gjcarneiro in https://github.com/koxudaxi/datamodel-code-generator/pull/2376
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2372
* fix: capitalize_enum_members not recognized in pyproject.toml by @LordFckHelmchen in https://github.com/koxudaxi/datamodel-code-generator/pull/2363
* fix(parser): ignore discriminator in collapsed list fields by @rcarriga in https://github.com/koxudaxi/datamodel-code-generator/pull/2378

## New Contributors
* @LordFckHelmchen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2363
* @rcarriga made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2378

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.28.5...0.29.0

---

## [0.28.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.28.5) - 2025-03-24

## What's Changed
* fix: Fix Union type parsing with recursive None removal by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2342
* Ensure we have a string before trying to strip by @gothicVI in https://github.com/koxudaxi/datamodel-code-generator/pull/2354
* fix: Fix invalid imports for schema files with hyphens and dots by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2343
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2347
* fix: fix field has same name on pydantic v2 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2355
* fix: fix referenced default by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2356
* Fix field aliasing on discriminator fields by @djb7 in https://github.com/koxudaxi/datamodel-code-generator/pull/2349
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2360

## New Contributors
* @gothicVI made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2354
* @djb7 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2349

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.28.4...0.28.5

---

## [0.28.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.28.4) - 2025-03-11

## What's Changed
* feat: add ruff formatters by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2340


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.28.3...0.28.4

---

## [0.28.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.28.3) - 2025-03-10

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2331
* [Chore] Remove Python 3.8 from tox by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2335
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2339
* Fix #2333. Remove not none arg parse defaults. by @ilovelinux in https://github.com/koxudaxi/datamodel-code-generator/pull/2334

## New Contributors
* @ilovelinux made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2335

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.28.2...0.28.3

---

## [0.28.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.28.2) - 2025-02-27

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2328
* Fix import and field name collisions by @butvinm in https://github.com/koxudaxi/datamodel-code-generator/pull/2327

## New Contributors
* @butvinm made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2327

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.28.1...0.28.2

---

## [0.28.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.28.1) - 2025-02-15

## What's Changed
* Graphql --set-default-enum-member by @andrew-womeldorf in https://github.com/koxudaxi/datamodel-code-generator/pull/2323

## New Contributors
* @andrew-womeldorf made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2323

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.28.0...0.28.1

---

## [0.28.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.28.0) - 2025-02-14

## What's Changed
* Drop <3.9 support as run and generation target by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2324


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.27.3...0.28.0

---

## [0.27.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.27.3) - 2025-02-11

## What's Changed
* Reuse extras instead of dependency groups by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2307
* Set line length to 120 charachters by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2310
* Use src layout by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2311
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2316
* YML to YAML by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2317
* Add more ruff checks and use defaults by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2318


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.27.2...0.27.3

---

## [0.27.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.27.2) - 2025-02-07

## What's Changed
* fix: Fix extra dependencies by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2306


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.27.1...0.27.2

---

## [0.27.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.27.1) - 2025-02-06

## What's Changed
* Support isort 6 by @cjwatson in https://github.com/koxudaxi/datamodel-code-generator/pull/2289
* fix: version CLI showing 0.0.0  by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2305

## New Contributors
* @cjwatson made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2289

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.27.0...0.27.1

---

## [0.27.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.27.0) - 2025-02-06

## What's Changed
* Migrate to use uv instead of poetry by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2288
* Add tox configuration file by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2292
* Fix collapse root model when list contains field with constraints #2067 by @dpeachey in https://github.com/koxudaxi/datamodel-code-generator/pull/2293
* Add cloudcoil by @sambhav in https://github.com/koxudaxi/datamodel-code-generator/pull/2291
* fix: tox fix environment failing by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2296
* Migrate mypy to pyright by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2295
* fix: update type-checker config by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2298
* fix: Parser crashes when input contains duplicate schemas at root level by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2301
* fix: merge test coverage before upload by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2299
* setup-trusted-publisher by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2303
* Fix custom package install in CI is not working by @gaborbernat in https://github.com/koxudaxi/datamodel-code-generator/pull/2302

## New Contributors
* @gaborbernat made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2288
* @dpeachey made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2293
* @sambhav made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2291

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.26.5...0.27.0

---

## [0.26.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.26.5) - 2025-01-14

## What's Changed
* typo: Fix 'Allow to' sentence. by @jas4711 in https://github.com/koxudaxi/datamodel-code-generator/pull/2240
* Fix pyproject.toml detection when `[tool.black]` section is omitted by @otonnesen in https://github.com/koxudaxi/datamodel-code-generator/pull/2242
* Update readme by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2258
* Escape null character by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2257
* enum find member quote handling by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2259
* fix Literal imports by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2260

## New Contributors
* @jas4711 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2240
* @otonnesen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2242

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.26.4...0.26.5

---

## [0.26.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.26.4) - 2024-12-15

## What's Changed
* remove poetry-lock in .pre-commit-config.yaml by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2184
* Add --no-alias by @nickyoung-github in https://github.com/koxudaxi/datamodel-code-generator/pull/2183
* fix: Skip empty files by @jackylamhk in https://github.com/koxudaxi/datamodel-code-generator/pull/2157
* fix(parser): custom_template_dir not passed to data_model_type for OpenAPIScope.Parameters by @hambergerpls in https://github.com/koxudaxi/datamodel-code-generator/pull/2166
* feat: add support to msgspec for kw_only=True by @indrat in https://github.com/koxudaxi/datamodel-code-generator/pull/2162
* fix: Preserve class names when generating models from JSON Schema 202… by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2185
* docs: add `uri` as a supported data type by @joscha in https://github.com/koxudaxi/datamodel-code-generator/pull/2217
* Fix OpenAPI test case failure in fresh clone by @ncoghlan in https://github.com/koxudaxi/datamodel-code-generator/pull/2214
* feat: add test for Python3.13 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2219
* Update GitHub Actions to use latest action versions by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2222
* Add support for Python 3.13 in project metadata by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2223
* Default datetime class and python version by @thorwhalen in https://github.com/koxudaxi/datamodel-code-generator/pull/2196
* Avoid sharing extra template state between models by @ncoghlan in https://github.com/koxudaxi/datamodel-code-generator/pull/2215
* fix: OpenAPI 3.1: `required` with `type: [array, null]` by @joscha in https://github.com/koxudaxi/datamodel-code-generator/pull/2216
* feat: support InputFileType.Json and InputFileType.Dict by @XieJiSS in https://github.com/koxudaxi/datamodel-code-generator/pull/2165

## New Contributors
* @nickyoung-github made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2183
* @jackylamhk made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2157
* @hambergerpls made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2166
* @joscha made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2217
* @ncoghlan made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2214
* @thorwhalen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2196
* @XieJiSS made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2165

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.26.3...0.26.4

---

## [0.26.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.26.3) - 2024-11-10

## What's Changed
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2096
* feat: add msgspec support for `--output-datetime-class datetime` by @indrat in https://github.com/koxudaxi/datamodel-code-generator/pull/2124
* Support `use_enum_values` in `ConfigDict` by @nbro10 in https://github.com/koxudaxi/datamodel-code-generator/pull/2134
* [pre-commit.ci] pre-commit autoupdate by @pre-commit-ci in https://github.com/koxudaxi/datamodel-code-generator/pull/2131
* Fix discriminator mapping resolution in schemas with parent-child hierarchy by @sternakt in https://github.com/koxudaxi/datamodel-code-generator/pull/2145
* feat: msgspec discriminated unions by @indrat in https://github.com/koxudaxi/datamodel-code-generator/pull/2081
* Fix content-hash; add pre-commit-check for poetry. by @rafalkrupinski in https://github.com/koxudaxi/datamodel-code-generator/pull/2142

## New Contributors
* @nbro10 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2134
* @sternakt made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2145
* @rafalkrupinski made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2142

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.26.2...0.26.3

---

## [0.26.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.26.2) - 2024-10-17

## What's Changed
* New CLI option --output-datetime-class #1996 by @archetipo in https://github.com/koxudaxi/datamodel-code-generator/pull/2100
* dataclass generator improvements by @anis-campos in https://github.com/koxudaxi/datamodel-code-generator/pull/2102

## New Contributors
* @archetipo made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2100
* @anis-campos made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2102

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.26.1...0.26.2

---

## [0.26.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.26.1) - 2024-09-27

## What's Changed
* feat: support string format: duration for pydantic/msgspec by @indrat in https://github.com/koxudaxi/datamodel-code-generator/pull/2084
* Change ordering of actions by @prmshepherd in https://github.com/koxudaxi/datamodel-code-generator/pull/1961
* Fix an exact import bug with deeper nesting by @AniketDas-Tekky in https://github.com/koxudaxi/datamodel-code-generator/pull/2089

## New Contributors
* @prmshepherd made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1961
* @AniketDas-Tekky made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2089

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.26.0...0.26.1

---

## [0.26.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.26.0) - 2024-09-02

## What's Changed
* Drop support python 3.7 on runtime by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2060
* Change default target python version to 3.8 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2061
* Add command help update script by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2064
* Support union_mode by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2065
* Fix default encoding as_utf-8 on command help by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2066
* Fix --use-annotated for pydantic v2 by @bpsoos in https://github.com/koxudaxi/datamodel-code-generator/pull/2033
* fix missing field descriptions in graphql by @benobytes in https://github.com/koxudaxi/datamodel-code-generator/pull/2074


## Breaking Changes
* Drop support python 3.7 on runtime by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2060
* Change default target python version to 3.8 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/2061

## New Contributors
* @benobytes made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2074

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.9...0.26.0

---

## [0.25.9](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.9) - 2024-08-07

## What's Changed
* Fix merging config and args by @mahdilamb in https://github.com/koxudaxi/datamodel-code-generator/pull/2015
* Fix missing imports for collapsed models by @kmichel-aiven in https://github.com/koxudaxi/datamodel-code-generator/pull/2043
* Don't generate files without model by @kmichel-aiven in https://github.com/koxudaxi/datamodel-code-generator/pull/2044
* Escaping apostophes in mark-down by @ben05allen in https://github.com/koxudaxi/datamodel-code-generator/pull/2047
* Typo: Fix missing whitespace in CLI help by @meliache in https://github.com/koxudaxi/datamodel-code-generator/pull/2053

## New Contributors
* @mahdilamb made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2015
* @ben05allen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2047
* @meliache made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2053

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.8...0.25.9

---

## [0.25.8](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.8) - 2024-07-04

## What's Changed
* feat: new cli option --use-exact-imports by @alpoi-x in https://github.com/koxudaxi/datamodel-code-generator/pull/1983
* patch pydantic v1.10.9 conflict with py3.12 by @luca-knaack-webcom in https://github.com/koxudaxi/datamodel-code-generator/pull/2014
* feature: dots in paths by @luca-knaack-webcom in https://github.com/koxudaxi/datamodel-code-generator/pull/2008
* docs: Update airbyte use case + fix broken link by @natikgadzhi in https://github.com/koxudaxi/datamodel-code-generator/pull/2021
* Fix Missing Imports by @luca-knaack-webcom in https://github.com/koxudaxi/datamodel-code-generator/pull/2009
* 🚑 fixes graphql parser --use-standard-collections --use-union-operator --use-annotated by @bpsoos in https://github.com/koxudaxi/datamodel-code-generator/pull/2016

## New Contributors
* @alpoi-x made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1983
* @natikgadzhi made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2021
* @bpsoos made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/2016

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.7...0.25.8

---

## [0.25.7](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.7) - 2024-06-11

## What's Changed
* Add from_attributes to ConfigDict by @michael2to3 in https://github.com/koxudaxi/datamodel-code-generator/pull/1946
* Fix msgspec template to add field by @ianbuss in https://github.com/koxudaxi/datamodel-code-generator/pull/1942
* Add regex_engine="python-re" if regex uses lookaround by @camillol in https://github.com/koxudaxi/datamodel-code-generator/pull/1945
* Fix broken unittest by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1987
* fix: Fix subschema array items with oneOf showing up as Any type by @jdweav in https://github.com/koxudaxi/datamodel-code-generator/pull/1962
* Fix reuse_models not using the custom_template_dir by @atti92 in https://github.com/koxudaxi/datamodel-code-generator/pull/1954
* Fix alias for superclass with identical name by @kmichel-aiven in https://github.com/koxudaxi/datamodel-code-generator/pull/1981
* feat: support for external referenced discriminators by @luca-knaack-webcom in https://github.com/koxudaxi/datamodel-code-generator/pull/1991
* fix: external references to parent folder by @luca-knaack-webcom in https://github.com/koxudaxi/datamodel-code-generator/pull/1999

## New Contributors
* @michael2to3 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1946
* @ianbuss made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1942
* @camillol made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1945
* @jdweav made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1962
* @kmichel-aiven made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1981
* @luca-knaack-webcom made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1991

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.6...0.25.7

---

## [0.25.6](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.6) - 2024-04-25

## What's Changed
* Fix missing Union by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1905
* fix(ModuleImports): This PR fixes the module import resolver for module of type `BaseClassDataType` by @rshah-evertz in https://github.com/koxudaxi/datamodel-code-generator/pull/1862
* Support http query parameters by @kevin-lithic in https://github.com/koxudaxi/datamodel-code-generator/pull/1911
* feat: add examples to meta fields by @nampereira in https://github.com/koxudaxi/datamodel-code-generator/pull/1899
* Fix Rootmodel template with reuse-model by @atti92 in https://github.com/koxudaxi/datamodel-code-generator/pull/1902
* Support pendulum by @kevin-lithic in https://github.com/koxudaxi/datamodel-code-generator/pull/1914

## New Contributors
* @rshah-evertz made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1862
* @kevin-lithic made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1911
* @nampereira made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1899
* @atti92 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1902

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.5...0.25.6

---

## [0.25.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.5) - 2024-03-16

## What's Changed
* Fix overriden required by @fft001 in https://github.com/koxudaxi/datamodel-code-generator/pull/1868
* Added support for passing pathlib.Path as a format to JSON schema by @brandonsorensen in https://github.com/koxudaxi/datamodel-code-generator/pull/1879
* Make discriminators work with multiple keys pointing to the same schema by @ldej in https://github.com/koxudaxi/datamodel-code-generator/pull/1885

## New Contributors
* @fft001 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1868
* @brandonsorensen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1879
* @ldej made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1885

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.4...0.25.5

---

## [0.25.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.4) - 2024-02-13

## What's Changed
* Fix object instance comparison. Add test. by @jamesbezuk in https://github.com/koxudaxi/datamodel-code-generator/pull/1849
* Added graphql to `--input-file-type` options by @JoeHCQ1 in https://github.com/koxudaxi/datamodel-code-generator/pull/1846
* Add codespell configuration, workflow, pre-commit config and fix few typos by @yarikoptic in https://github.com/koxudaxi/datamodel-code-generator/pull/1842
* has_constraints should return true for falsy values by @ericvandever in https://github.com/koxudaxi/datamodel-code-generator/pull/1844
* Fix black module error when 19.10b0 is installed by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1855

## New Contributors
* @jamesbezuk made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1849
* @JoeHCQ1 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1846
* @yarikoptic made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1842
* @ericvandever made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1844

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.3...0.25.4

---

## [0.25.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.3) - 2024-02-01

## What's Changed
* Enable ability to use custom `JsonSchemaObject` in `JsonSchemaParser` by @WilliamJamieson in https://github.com/koxudaxi/datamodel-code-generator/pull/1783
* Stop modifying behavior of yaml on load by @gluap in https://github.com/koxudaxi/datamodel-code-generator/pull/1826
* Fix bug with oneOf and const #1787 by @shadchin in https://github.com/koxudaxi/datamodel-code-generator/pull/1791
* format: support black >=24 by @airwoodix in https://github.com/koxudaxi/datamodel-code-generator/pull/1829

## New Contributors
* @WilliamJamieson made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1783
* @gluap made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1826
* @shadchin made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1791

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.2...0.25.3

---

## [0.25.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.2) - 2023-12-21

## What's Changed
* Fix original_name validation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1755
* Use const as default by @mmwinther in https://github.com/koxudaxi/datamodel-code-generator/pull/1767
* Support json_schema_extra by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1782
* Improve json_schema_extra to pydanticv2 Field with readOnly/writeOnly  by @mikedavidson-evertz in https://github.com/koxudaxi/datamodel-code-generator/pull/1778
* Fix un-imported literal when generate discriminator by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1765

## New Contributors
* @mikedavidson-evertz made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1778

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.1...0.25.2

---

## [0.25.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.1) - 2023-11-26

## What's Changed
* Fix invalid definition of graphql requirement  by @denisart in https://github.com/koxudaxi/datamodel-code-generator/pull/1741


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.25.0...0.25.1

---

## [0.25.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.25.0) - 2023-11-25

## What's Changed
* Improve collapse_root_models for list by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1700
* Improve one of any of models creation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1682
* Change example to examples in pydantic_v2 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1705
* Enable --set-default-enum-member for dataclasses by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1706
* Fix --use-default of allOf by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1708
* Beta version graphql by @denisart in https://github.com/koxudaxi/datamodel-code-generator/pull/1707
* Add a few tests graphql by @denisart in https://github.com/koxudaxi/datamodel-code-generator/pull/1722
* Add additional imports to cli by @denisart in https://github.com/koxudaxi/datamodel-code-generator/pull/1723
* Fix long description rendering in graphql by @denisart in https://github.com/koxudaxi/datamodel-code-generator/pull/1730
* Add custom formatters by @denisart in https://github.com/koxudaxi/datamodel-code-generator/pull/1733
* with pydantic v2, use pydantic.AwareDatetime instead of datetime by @gjcarneiro in https://github.com/koxudaxi/datamodel-code-generator/pull/1735
* Support discriminators in array items by @mesfahanisimscale in https://github.com/koxudaxi/datamodel-code-generator/pull/1458
* Fix default for annotated field in pydantic v2 by @i404788 in https://github.com/koxudaxi/datamodel-code-generator/pull/1498

## Breaking Changes
* Remove the unneeded `Item` suffix of `anyOf` and `oneOf` model names by https://github.com/koxudaxi/datamodel-code-generator/pull/1682
  * maybe change other model names by the changes
* Change `datetime.datetime` to `pydantic.AwareDatetime` in pydantic v2 by https://github.com/koxudaxi/datamodel-code-generator/pull/1735

## New Contributors
* @denisart made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1707
* @gjcarneiro made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1735
* @mesfahanisimscale made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1458

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.24.2...0.25.0

---

## [0.24.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.24.2) - 2023-11-16

## What's Changed
* Fix join_url bug when httpx 2.4.0 or later by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1699


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.24.1...0.24.2

---

## [0.24.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.24.1) - 2023-11-16

## What's Changed
* Add pyyaml by @mmwinther in https://github.com/koxudaxi/datamodel-code-generator/pull/1698

## New Contributors
* @mmwinther made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1698

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.24.0...0.24.1

---

## [0.24.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.24.0) - 2023-11-16

## What's Changed
* Fix UnionIntFloat json schema generation. by @jboulmier in https://github.com/koxudaxi/datamodel-code-generator/pull/1669
* Move pysnooper to optional by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1672
* use tomllib in 3.11 or later by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1674
* Change --validation option to optional by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1675
* Remove black in lint.sh and format.sh by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1676
* Resolve ref before adding references for allOf items by @pimzero in https://github.com/koxudaxi/datamodel-code-generator/pull/1678
* Change master to main by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1681
* Fix error when JsonSchemaObject is bool with Pydantic v2 by @sbussard-vareto in https://github.com/koxudaxi/datamodel-code-generator/pull/1691

## Breaking Changes
* The version drop  `pysnooper`, `prance`, `openapi-spec-validator` from the default dependencies list.
If you want to use `--debug` and ` --validation`, please add the extra option when you install packages `datamodel-code-generator[debug]` and `datamodel-code-generator[validation]`

## Depreacated
* `--validation` option will be removed in the new future. please use other tools to validate OpenAPI Schema.

## New Contributors
* @jboulmier made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1669
* @pimzero made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1678
* @sbussard-vareto made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1691

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.23.0...0.24.0

---

## [0.23.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.23.0) - 2023-11-08

## What's Changed
* Support $defs for Draft 2019-09  by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1630
* Update openapi-spec-validator max version by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1633
* Fix list default in dataclass by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1632
* Support python 3.12 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1612
* Fix `--remove-special-field-name-prefix` + fields (e.g. enum members) starting with numbers by @lord-haffi in https://github.com/koxudaxi/datamodel-code-generator/pull/1654
* Fix generation of nullable array items by @tfausten in https://github.com/koxudaxi/datamodel-code-generator/pull/1648
* Move nullable logic to openapi parser by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1655
* Add missing space to README.md by @joakimnordling in https://github.com/koxudaxi/datamodel-code-generator/pull/1660
* Improve model naming by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1663
* Fix exponent in minimum by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1664
* Remove constraint on anyurl by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1665
* Improve discriminator by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1666

## New Contributors
* @lord-haffi made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1654
* @tfausten made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1648
* @joakimnordling made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1660

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.22.1...0.23.0

---

## [0.22.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.22.1) - 2023-10-08

## What's Changed
* Ignore broken pydantic version 2.4.0 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1593
* Avoid pydantic ClassVar bug by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1603
* Fix msgspec pattern and optional annotated type by @indrat in https://github.com/koxudaxi/datamodel-code-generator/pull/1606
* Fix missing constr import issue by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1609
* Fix msgspec root import by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1611


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.22.0...0.22.1

---

## [0.22.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.22.0) - 2023-09-23

## What's Changed
* Organize help options by @howardj99 in https://github.com/koxudaxi/datamodel-code-generator/pull/1540
* fix: add type parameters to generic RootModel by @tcrasset in https://github.com/koxudaxi/datamodel-code-generator/pull/1560
* chore: link to contributing guidelines from README.md by @tcrasset in https://github.com/koxudaxi/datamodel-code-generator/pull/1561
* Fix base path to avoid duplicate parts in path when deleting reference by @pedrosmr in https://github.com/koxudaxi/datamodel-code-generator/pull/1550
* Support msgspec output by @indrat in https://github.com/koxudaxi/datamodel-code-generator/pull/1551

## New Contributors
* @howardj99 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1540
* @tcrasset made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1560
* @pedrosmr made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1550
* @indrat made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1551

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.21.5...0.22.0

---

## [0.21.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.21.5) - 2023-09-06

## What's Changed
* Added protect namespace to Pydantic v2 ConfigDict by @willarmiros in https://github.com/koxudaxi/datamodel-code-generator/pull/1489
* Fix pydantic 2.2.1 RootModel cannot have extra_fields error by @i404788 in https://github.com/koxudaxi/datamodel-code-generator/pull/1497
* Add missing default=None by @twoodwark in https://github.com/koxudaxi/datamodel-code-generator/pull/1515
* Fix class Field generated when array with name fields with oneOf inside by @mjperrone in https://github.com/koxudaxi/datamodel-code-generator/pull/1516

## New Contributors
* @willarmiros made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1489
* @twoodwark made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1515
* @mjperrone made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1516

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.21.4...0.21.5

---

## [0.21.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.21.4) - 2023-08-09

## What's Changed
* Update openapi-spec-validator to 0.5.7 by @der-eismann in https://github.com/koxudaxi/datamodel-code-generator/pull/1475
* Fix Pydantic V2 RootModel inheritance by @barreeeiroo in https://github.com/koxudaxi/datamodel-code-generator/pull/1477
* main: fix configuration model validation after CLI args merge by @airwoodix in https://github.com/koxudaxi/datamodel-code-generator/pull/1448
* Fix const for pydantic_v2 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1482
* Unique list is defined as list by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1484
* switch away from deprecated pydantic method by @iliakur in https://github.com/koxudaxi/datamodel-code-generator/pull/1485
* Fix condecimal by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1487
* Add unittest for discriminator by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1488

## New Contributors
* @der-eismann made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1475
* @barreeeiroo made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1477
* @iliakur made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1485

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.21.3...0.21.4

---

## [0.21.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.21.3) - 2023-08-03

## What's Changed
* Give Pydantic V2 its own `dump_resolve_reference_action` to use `model_rebuild` not `update_forward_refs` by @lmmx in https://github.com/koxudaxi/datamodel-code-generator/pull/1468
* fix: Fix regex expression of hostname in pydantic v2 by @xu-cheng in https://github.com/koxudaxi/datamodel-code-generator/pull/1449
* Add `base_class` validation similar to `_validate_base_class` to bare `generate` calls by @kylebebak in https://github.com/koxudaxi/datamodel-code-generator/pull/1453
* Fix issue #1461: Open API parameter models use base class if set by @piercsi in https://github.com/koxudaxi/datamodel-code-generator/pull/1462
* Issues 1454 typeddict not required optional bug fix by @kylebebak in https://github.com/koxudaxi/datamodel-code-generator/pull/1457

## New Contributors
* @lmmx made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1468
* @xu-cheng made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1449
* @kylebebak made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1453
* @piercsi made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1462

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.21.2...0.21.3

---

## [0.21.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.21.2) - 2023-07-20

## What's Changed
* Pre-commit-hooks by @yehoshuadimarsky in https://github.com/koxudaxi/datamodel-code-generator/pull/1416
* feat: add additional imports by @skonik in https://github.com/koxudaxi/datamodel-code-generator/pull/1422
* Add orm_mode to Config(BaseModel)  by @Beaueve in https://github.com/koxudaxi/datamodel-code-generator/pull/1425
* Fix "parent" AttributeError when calling --collapse-root-models by @imankulov in https://github.com/koxudaxi/datamodel-code-generator/pull/1432

## New Contributors
* @yehoshuadimarsky made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1416
* @skonik made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1422
* @Beaueve made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1425
* @imankulov made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1432

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.21.1...0.21.2

---

## [0.21.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.21.1) - 2023-07-06

## What's Changed
* Relax version constraint of prance by @tetsuok in https://github.com/koxudaxi/datamodel-code-generator/pull/1409
* Fix optional field doesn't include `None` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1411

## New Contributors
* @tetsuok made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1409

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.21.0...0.21.1

---

## [0.21.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.21.0) - 2023-07-03

## What's Changed
* pyproject: correct poetry-core package name by @ConnorBaker in https://github.com/koxudaxi/datamodel-code-generator/pull/1374
* Support pydantic v2 in runtime by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1392
* Add pydantic v2 as output model type by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1391
* Add --use-unique-items as set by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1400

## New Contributors
* @ConnorBaker made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1374

# What is the difference between pydantic v1 and v2 output model? 

## Summary
datamodel-code-generator supports Pydantic v1 and v2 as output model type.

Pydantic v2 is a major release with many breaking changes. See the migration guide for more information:
https://docs.pydantic.dev/2.0/migration/

## What's changes in v2 output?
### `__root__` field (a.k.a [Custom Root Types](https://docs.pydantic.dev/1.10/usage/models/#custom-root-types))
`__root__` field (a.k.a [Custom Root Types](https://docs.pydantic.dev/1.10/usage/models/#custom-root-types)) is removed in pydantic v2.
The model is changed to [RootModel](https://docs.pydantic.dev/latest/usage/models/#rootmodel-and-custom-root-types)

### pydantic.Field
https://docs.pydantic.dev/2.0/migration/#changes-to-pydanticfield

- const -> removed
- min_items (use min_length instead)
- max_items (use max_length instead)
- unique_items -> removed and the list type will be replaced by `typing.Set`. this feature is discussed in https://github.com/pydantic/pydantic-core/issues/296
- allow_mutation (use frozen instead)
- regex (use pattern instead)

### Model Config
- `pydantic.Config` -> `pydantic.ConfigDict` 
- allow_mutation —> frozen (inverse value for getting same behavior).
- allow_population_by_field_name → populate_by_name



**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.20.0...0.21.0

---

## [0.20.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.20.0) - 2023-06-06

## What's Changed
* Update documentation by @noddycode in https://github.com/koxudaxi/datamodel-code-generator/pull/1316
* Support TypedDict as output type by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1309
* Remove self attribute from jsonschema root attributes by @rezen in https://github.com/koxudaxi/datamodel-code-generator/pull/1318
* Fix $ref With Path Items by @zach-hamm in https://github.com/koxudaxi/datamodel-code-generator/pull/1323
* Remove keep-runtime-typing on ruff config by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1349
* Update `openapi-spec-validator` to `0.5.2` by @Fokko in https://github.com/koxudaxi/datamodel-code-generator/pull/1343
* Added support for model wise base classes by @senesh-deshan in https://github.com/koxudaxi/datamodel-code-generator/pull/1350
* Fix the custom file header by @Fokko in https://github.com/koxudaxi/datamodel-code-generator/pull/1346

## Breaking Changes
* Eliminate the naming differences of model names and field names by the OS by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1348

Due to differences in file loading order between operating systems, we've added a sorting process when fetching file listings within directories in order to eliminate discrepancies in model and field names. As a result, model names that differ from those generated by existing earlier versions may be produced.

## New Contributors
* @noddycode made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1316
* @rezen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1318
* @zach-hamm made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1323
* @Fokko made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1343
* @senesh-deshan made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1350

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.19.0...0.20.0

---

## [0.19.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.19.0) - 2023-05-10

## What's Changed
* Import Annotated from typing_extensions for Python <= 3.8 by @airwoodix in https://github.com/koxudaxi/datamodel-code-generator/pull/1274
* Fix OpenAPI array response by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1261
* Fix unresolved nested ref in openapi by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1269
* Fix unsorted dataclass field by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1288
* Fix allOf-anyOf by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1291
* Fix null by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1299

## New Contributors
* @airwoodix made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1274

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.18.1...0.19.0

---

## [0.18.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.18.1) - 2023-04-27

## What's Changed
* default_factory field should be non-optional by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1254
* add --use-one-literal-as-default by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1256
* (🎁) Include `py.typed` to mark project as typed by @KotlinIsland in https://github.com/koxudaxi/datamodel-code-generator/pull/1259
* Fix min/max on number fields truncated by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1266
* Add use_operation_id_as_name by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1267
* Add datetime to number and integer by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1268


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.18.0...0.18.1

---

## [0.18.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.18.0) - 2023-04-16

## What's Changed
* Update __all__ to expose needed types by @ShaneMurphy2 in https://github.com/koxudaxi/datamodel-code-generator/pull/1230
* Fix max min round issue by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1235
* Fix strict nullable for default factory by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1236
* Improve union types by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1241
* Support nested all_of by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1242
* (🎁) bump some dependencies by @KotlinIsland in https://github.com/koxudaxi/datamodel-code-generator/pull/1245
* (🎁) log file type when `--input-file-type` is auto. by @KotlinIsland in https://github.com/koxudaxi/datamodel-code-generator/pull/1248
* (🎁) remove typed-ast dependency by @KotlinIsland in https://github.com/koxudaxi/datamodel-code-generator/pull/1246
* (🎁) reference config option to specify input type by @KotlinIsland in https://github.com/koxudaxi/datamodel-code-generator/pull/1250
* (🎁) infer data vs schema when `--input-file-type` is auto by @KotlinIsland in https://github.com/koxudaxi/datamodel-code-generator/pull/1249

## New Contributors
* @ShaneMurphy2 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1230

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.17.2...0.18.0

---

## [0.17.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.17.2) - 2023-03-31

## What's Changed
* Remove union operator error when target-python is 3.9 or early version by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1094
* Add ruff by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1095
* Fix only required anyof oneof by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1104
* Update mypy version to 1.0.0 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1105
* fix mypy version to >=1.0.1,<1.1.0 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1162
* Docs: typo by @KPLauritzen in https://github.com/koxudaxi/datamodel-code-generator/pull/1153
* Fix typo: `docuemnt` -> `document` by @kamyar in https://github.com/koxudaxi/datamodel-code-generator/pull/1179
* feat: add support for custom file header by @Niraj-Kamdar in https://github.com/koxudaxi/datamodel-code-generator/pull/1164
* Exclude fields with default_factory from --use-default-kwarg by @vogre in https://github.com/koxudaxi/datamodel-code-generator/pull/1186
* Bugfix: with deeply nested modules: empty paths did not get an __init__.py file created by @dataway in https://github.com/koxudaxi/datamodel-code-generator/pull/1187
* Fix url $id by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1214
* (🎁) deps: make typed-ast optional by @KotlinIsland in https://github.com/koxudaxi/datamodel-code-generator/pull/1222

## New Contributors
* @KPLauritzen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1153
* @kamyar made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1179
* @Niraj-Kamdar made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1164
* @vogre made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1186
* @dataway made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1187
* @KotlinIsland made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1222

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.17.1...0.17.2

---

## [0.17.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.17.1) - 2023-02-06

## What's Changed
* Change custom template dir structure by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1070
* Support enum as literal in root model by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1073
* Improve duplicate model detection by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1076
* Fix reference same hierarchy directory by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1082
* Fix wrong overwrite field default by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1085
* Fix mro field name on enum by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1069
* OpenAPI - Add support for query parameter model generation by @hambrosia in https://github.com/koxudaxi/datamodel-code-generator/pull/1083
* Support dataclasses.dataclass by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1068

## New Contributors
* @hambrosia made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1083

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.17.0...0.17.1

---

## [0.17.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.17.0) - 2023-01-30

## What's Changed
* Add `--keep-model-order` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1043
* Support openapi `discriminator` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1045
* Fix referenced `patternProperties` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1046
* Support `default_factory` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1047
* Remove duplicate model by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1048
* Fix naming logic for duplicate name model by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1049
* Proposal for adding version metadata to header section by @ghandic in https://github.com/koxudaxi/datamodel-code-generator/pull/1053
* Refactor set-default-enum-member by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1057
* Support list  default enum member by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1058
* Support default object value by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1060
* Fix cli option name --use_non_positive_negative_number_constrained_types by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1064
* Add `--field-extra-keys-without-x-prefix` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1066

## New Contributors
* @ghandic made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1053

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.16.1...0.17.0

---

## [0.16.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.16.1) - 2023-01-22

## What's Changed
* Change default value to None by @JensHeinrich in https://github.com/koxudaxi/datamodel-code-generator/pull/1028
* Support json pointer to array by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1030
* Fix/remove not none arg parse defaults by @JensHeinrich in https://github.com/koxudaxi/datamodel-code-generator/pull/1029
* Add --use-default-kwarg option for better type checker compatibility by @zackyancey in https://github.com/koxudaxi/datamodel-code-generator/pull/1034
* add --remove-special-field-name-prefix by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1033
* Fix snake_case generation by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1037
* Add --disable-warnings by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1038
* Remove dummy field by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1039

## New Contributors
* @JensHeinrich made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1028
* @zackyancey made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1034

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.16.0...0.16.1

---

## [0.16.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.16.0) - 2023-01-16

## What's Changed
* Fix the order of the model having multiple base_class by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/995
* Fix incorrect remove model action by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/997
* Support reference to object properties by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/998
* Fix field constraint number coersion bug by @ninowalker in https://github.com/koxudaxi/datamodel-code-generator/pull/1003
* Fix --collapse-root-models by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1002
* Fix --capitalise-enum-members by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1011
* Override optional all_of field with required by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1012
* Improve anyOf and oneOf detection when anyOf and oneOf parent has proprerties by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/1013

## New Contributors
* @ninowalker made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/1003

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.15.0...0.16.0

---

## [0.15.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.15.0) - 2023-01-04

## Notice
The release has some improvements in model generation.
**The generated model names or the structure will be changed.**

## What's Changed
* Remove unneeded number suffix when the same name model exists in another module by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/973
* Ignore duplicate name field on allOf by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/974
* Improve model deletion by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/976
* Refactor process after parse by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/977
* Support JSONSchema items is boolean by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/979
* Support required in allof item by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/981
* Improve detection additionalProperties in JSONSchema Object by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/982
* Fix nullable object by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/987
* Support const by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/989
* Fix duplicated nested optional by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/990

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.14.1...0.15.0

---

## [0.14.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.14.1) - 2022-12-28

## What's Changed
* Fix deprecation warnings around "copy_on_model_validation" by @Dominic-Walther in https://github.com/koxudaxi/datamodel-code-generator/pull/927
* Fix dev black version for macos by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/941
* Add support for tags and include responses without content by @Aedial in https://github.com/koxudaxi/datamodel-code-generator/pull/924
* Fix indents for multi-line docstrings by @Dominic-Walther in https://github.com/koxudaxi/datamodel-code-generator/pull/938
* Allow to pass extra fields using `--allow-extra-fields` by @fgebhart in https://github.com/koxudaxi/datamodel-code-generator/pull/949
* Fix resolving id by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/963
* fix: template handling of extra template data by @auphofBSF in https://github.com/koxudaxi/datamodel-code-generator/pull/861
* Avoid field name beginning with an underscore by @ronlib in https://github.com/koxudaxi/datamodel-code-generator/pull/962
* Support --special-field-name-prefix option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/966
* Fix allOf with common prefix and $ref by @azatoth in https://github.com/koxudaxi/datamodel-code-generator/pull/968
* Update poetry.lock by @fsecada01 in https://github.com/koxudaxi/datamodel-code-generator/pull/936
* Add collapse root model feature by @i404788 in https://github.com/koxudaxi/datamodel-code-generator/pull/933
* add --capitalise-enum-members option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/970
* Fix no generated enum in array by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/971

## New Contributors
* @Aedial made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/924
* @fgebhart made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/949
* @lgtm-com made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/908
* @auphofBSF made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/861
* @ronlib made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/962
* @azatoth made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/968
* @fsecada01 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/936
* @i404788 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/933

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.14.0...0.14.1

---

## [0.14.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.14.0) - 2022-11-18

## What's Changed
* Drop python3.6 support by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/887
* Support Python 3.11 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/898
* Show help when no input by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/911
* Add docker image by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/919
* Implement field descriptions as docstrings by @Dominic-Walther in https://github.com/koxudaxi/datamodel-code-generator/pull/918
* Fix push docker flow by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/925

## New Contributors
* @Dominic-Walther made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/918

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.13.5...0.14.0

---

## [0.13.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.13.5) - 2022-11-06

## What's Changed
* Fix mro field on enum by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/891
* Fix openapi definitions schema by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/897
* Fix generating import statement code by @antxln in https://github.com/koxudaxi/datamodel-code-generator/pull/893

## New Contributors
* @antxln made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/893

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.13.4...0.13.5

---

## [0.13.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.13.4) - 2022-10-31

## What's Changed
* Fix alias modular default enum member by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/888


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.13.3...0.13.4

---

## [0.13.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.13.3) - 2022-10-27

## What's Changed
* Fix modular default enum member by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/876
* Use format of object if provided by @pn in https://github.com/koxudaxi/datamodel-code-generator/pull/874
* Support union operator `|` by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/884

## New Contributors
* @pn made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/874

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.13.2...0.13.3

---

## [0.13.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.13.2) - 2022-10-17

## What's Changed
* Use default of $ref on enum by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/832
* Fix class name generator by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/841
* Replace exponential in name for FieldnameResolver by @PTank in https://github.com/koxudaxi/datamodel-code-generator/pull/833
* Support discriminators by @bernardoVale in https://github.com/koxudaxi/datamodel-code-generator/pull/838
* add pre-commit for black and isort by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/865
* Support Boolean property by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/872
* fix(format): Fix PythonVersion.has_literal_type for Python 3.10. by @pawelrubin in https://github.com/koxudaxi/datamodel-code-generator/pull/868

## New Contributors
* @PTank made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/833
* @bernardoVale made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/838
* @pre-commit-ci made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/867
* @pawelrubin made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/868

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.13.1...0.13.2

---

## [0.13.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.13.1) - 2022-08-11

## What's Changed
* Added IPv4/IPv6Network support. by @ngaranko in https://github.com/koxudaxi/datamodel-code-generator/pull/789
* added option --use-double-quotes by @nesb1 in https://github.com/koxudaxi/datamodel-code-generator/pull/818
* Fix deep copy max recursion failure - pydantic 1.9.1 by @eyalmor-ent in https://github.com/koxudaxi/datamodel-code-generator/pull/819

## New Contributors
* @ngaranko made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/789
* @nesb1 made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/818
* @eyalmor-ent made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/819

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.13.0...0.13.1

---

## [0.13.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.13.0) - 2022-05-27

## What's Changed
* Fix --snake-case-field breaks class_name by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/777


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.12.3...0.13.0

---

## [0.12.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.12.3) - 2022-05-27

## What's Changed
* Support --original-field-name-delimiter option by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/776


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.12.2...0.12.3

---

## [0.12.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.12.2) - 2022-05-27

## What's Changed
* Support subclass enum by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/771


**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.12.1...0.12.2

---

## [0.12.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.12.1) - 2022-05-19

## What's Changed
* [FIX] inheritance update refs by @jdkent in https://github.com/koxudaxi/datamodel-code-generator/pull/767
* Add Python 3.10 to PythonVersion by @sgaist in https://github.com/koxudaxi/datamodel-code-generator/pull/765

## New Contributors
* @jdkent made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/767
* @sgaist made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/765

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.12.0...0.12.1

---

## [0.12.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.12.0) - 2022-04-18

## What's Changed
* Fix field constraint value by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/745
* Correct typo in GitHub Actions black versions by @lafrenierejm in https://github.com/koxudaxi/datamodel-code-generator/pull/744
* Support unique_items by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/746
* Fix nested Enum by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/747

## New Contributors
* @lafrenierejm made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/744

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.11.20...0.12.0

---

## [0.11.20](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.20) - 2022-03-12

## What's Changed
* no use constr when field-constraints by @linshoK in https://github.com/koxudaxi/datamodel-code-generator/pull/726

## New Contributors
* @linshoK made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/726

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.11.19...0.11.20

---

## [0.11.19](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.19) - 2022-02-08

## What's Changed
* fix booleans literals being converted to int by @koonpeng in https://github.com/koxudaxi/datamodel-code-generator/pull/704
* feat: Add option to disable tls verification in http request by @jtfidje in https://github.com/koxudaxi/datamodel-code-generator/pull/707

## New Contributors
* @koonpeng made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/704
* @jtfidje made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/707

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.11.18...0.11.19

---

## [0.11.18](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.18) - 2022-02-02

## What's Changed
* [Docs] Fix typo by @ijrsvt in https://github.com/koxudaxi/datamodel-code-generator/pull/702
* [Fix] Support Black 22.1.0 by @ijrsvt in https://github.com/koxudaxi/datamodel-code-generator/pull/701

## New Contributors
* @ijrsvt made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/702

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.11.17...0.11.18

---

## [0.11.17](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.17) - 2022-01-23

## What's Changed
* do not convert literal int to string for pydantic 1.9.0 or later by @duesenfranz in https://github.com/koxudaxi/datamodel-code-generator/pull/689

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.11.16...0.11.17

---

## [0.11.16](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.16) - 2022-01-17

## What's Changed
* Fix json type form http by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/637
* Support Python3.10 by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/668
* GitHub Actions: Add Python 3.10 to the testing by @cclauss in https://github.com/koxudaxi/datamodel-code-generator/pull/605
* Use `Non{Positive,Negative}{Float,Int}` in models by @duesenfranz in https://github.com/koxudaxi/datamodel-code-generator/pull/679

## New Contributors
* @cclauss made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/605
* @duesenfranz made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/679

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.11.15...0.11.16

---

## [0.11.15](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.15) - 2021-11-29

## What's Changed
* Fix typed-ast by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/626
* Fix typed_ast dependency with custom mypy by @koxudaxi in https://github.com/koxudaxi/datamodel-code-generator/pull/634
* documented installation via pip by @adaamz in https://github.com/koxudaxi/datamodel-code-generator/pull/620
* Fix typo in argument description by @jacobszpz in https://github.com/koxudaxi/datamodel-code-generator/pull/606
* Fix parsing of absolute reference URLs by @vesajaaskelainen in https://github.com/koxudaxi/datamodel-code-generator/pull/594

## New Contributors
* @adaamz made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/620
* @jacobszpz made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/606
* @vesajaaskelainen made their first contribution in https://github.com/koxudaxi/datamodel-code-generator/pull/594

**Full Changelog**: https://github.com/koxudaxi/datamodel-code-generator/compare/0.11.14...0.11.15

---

## [0.11.14](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.14) - 2021-09-30

- Fix a bug for # field [#558]

---

## [0.11.13](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.13) - 2021-09-15

- Support pydantic 1.5.1 [#537]

---

## [0.11.12](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.12) - 2021-08-27

- ignore broken regex version [#519]
- Support --use-annotated [#516]
- Support --http_headers for authorization [#511]
- Add --use-title-as-name [#510]
- Support patternProperties [#509]
- Fix reuse_model for nested model [#505]
- Improve supporting json_pointer [#503]







---

## [0.11.11](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.11) - 2021-08-12

- Fix version option [#499]

---

## [0.11.10](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.10) - 2021-08-12

- Fix invalid generated code with openapi validator [#496]
- Support wrap_string_literal [#493]
- Use Poetry [#475]

---

## [0.11.9](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.9) - 2021-07-31

- Fix setup.py [#473]
- Support false on additionalProperties [#472] by @reb00ter
- Support jinja2 version3 [#468]
- Support PEP-517 [#467]
- Validate pydantic field name [#465]

## Improve OpenAPI Parser
- Refactor parse_ref [#449] 
- Fix path objects in openapi [#459]
- Fix path parameters [#460]
- Improve resolving response model [#461]
- Improve OpenAPI parser [#462]

Thanks to @reb00ter

---

## [0.11.8](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.8) - 2021-06-11

- set default base class when removed all base class [#448 ]

---

## [0.11.7](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.7) - 2021-06-09

- Fix inline enum only string literal [#445] by @goodoldneon

Thanks to @goodoldneon

---

## [0.11.6](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.6) - 2021-05-28

- Support customTypePath [#436]

---

## [0.2.11+backport-1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.11+backport-1) - 2021-05-29

- backport improve_x_enum_varnames 

---

## [0.11.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.5) - 2021-05-16

- Don't generate enum models that have been swapped by a reused model [#430] by @shnups 
- Pass custom template dir when creating enums [#427] by @shnups 

Thanks to @shnups

---

## [0.11.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.4) - 2021-05-05

- Handle nested nullable enums [#425] by @philipbjorge 

Thanks to @philipbjorge

---

## [0.11.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.3) - 2021-04-29

- Fix #420 [#421] by @goodoldneon 
 (IPv4Address doesn't import from pydantic.validators [#420])

Thanks to @goodoldneon 

---

## [0.11.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.2) - 2021-04-26

- Support field extras keys [#416]

---

## [0.11.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.1) - 2021-04-22

- Fix get_relative_path subfolders with same names [#415] by @siame

Thanks to @siame


---

## [0.11.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.11.0) - 2021-04-21

- Improve parsing additionalProperties [#412]
- Improve parsing complex object [#411] 

breaking change
The detail is in #413

---

## [0.10.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.10.3) - 2021-04-18

- Support complex `oneOf` and `anyOf` [#410]

---

## [0.10.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.10.2) - 2021-04-03

- Improve resolving relative path [#406]
- Refactor parse_enum [#405]

---

## [0.10.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.10.1) - 2021-03-31

- Improve imports in DataType [#403]
- Support self reference array [#402]
- Support allOf with object [#401]
- Improve generating model name [#400]

---

## [0.10.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.10.0) - 2021-03-27

- Support time and idn-email format #397
- Support custom_class_name_generator #396
- Reduce unnecessary downloading #395
- Fix resolving ref with root id #394
- Fix modular generated models #393 
- Refactor module_name #391
- Remove append_result #390
- Remove field name validator #389 
- Fix import style #388
- Fix duplicate field name #386

### breaking change
The detail is in #398

---

## [0.9.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.9.4) - 2021-03-21

- Refactor data_type_manager [#384]
- Fix to parse enum correctly [#383]
- Allow using Literal in python 3.7 via typing_extensions backport [#382] by @yuyupopo 
- Update dependencies [#378]

Thanks to @yuyupopo 

---

## [0.9.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.9.3) - 2021-03-18

- Improve resolving module names [#377]
- Refactor DataModel [#376]
- Improve code style [#375]

---

## [0.9.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.9.2) - 2021-03-11

- Improve typing [#373]
- Fix x-enum-varnames for string [#372]

---

## [0.9.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.9.1) - 2021-03-08

- Escape special characters in regex [#370]
- Support strict types [#369]
- Add --disable-appending-item-suffix [#368]
- Strip constraints on self-reference [#367] 
- Fix custom_root_model [#366]
- Support HTTP URL as an input [#365]

---

## [0.9.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.9.0) - 2021-03-04

- Fix model name which is same imported_name [#364]
- Fix broken update_forward_refs [#363]
- Improve coding style [#362]
- Change all imports return type to iterator[Import] [#361]
- Lazy creating imports and unresolved_types [#360]
- Resolve parent model by data_type [#359]
- Model properties are generated when rendering [#358]
- Refactoring model structure [#354]

breaking change
The detail is in https://github.com/koxudaxi/datamodel-code-generator/issues/357

---

## [0.8.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.8.3) - 2021-02-25

- Support nested json_pointer [#352]

---

## [0.8.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.8.2) - 2021-02-20

- Generate function supports relative input path [#351]
- Support nullable enum [#350]

---

## [0.8.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.8.1) - 2021-02-18

- Fix parsing ref on root model [#346]
- Change regex to raw strings [#345] 

---

## [0.8.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.8.0) - 2021-02-17

- Ignore duplicate object of allOf [#343]
- Improve constrained type in array [#342]
- Improve complex additional properties [#341]
- Add alias attribute on DataType [#340]

### breaking change
The detail is in #344

---

## [0.7.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.7.3) - 2021-02-16

- Support enable_faux_immutability [#338]
- Support generic_container_types [#336]
- Fix oneOf [#335]

---

## [0.7.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.7.2) - 2021-02-09

- Improve strict-nullable [#330]

---

## [0.7.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.7.1) - 2021-02-05

- Remove unused condition [#329]
- Support strict-nullable option [#328]

---

## [0.7.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.7.0) - 2021-01-31

- Fix type in anyof [#326]
- Improve resolving referenced models [#324]
- Fix wrong data type class [#322]

# breaking change
 Change internal interface [https://github.com/koxudaxi/datamodel-code-generator/issues/325]


---

## [0.6.26](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.26) - 2021-01-26

- Fix detecting allOf [#321] 

---

## [0.6.25](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.25) - 2021-01-24

- Fix importing field [#319]
- Improve resolving references [#318]

---

## [0.6.24](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.24) - 2021-01-23

- Support enum in additional properties [#316]
- Fix root_model with additional properties [#315]

---

## [0.6.23](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.23) - 2021-01-21

- Fix remote obj cache [#313]
- Parse enum field as literal [#312] 

---

## [0.6.22](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.22) - 2021-01-19

- Support json pointer [#311]
- Raise model not found exception [#310]

---

## [0.6.21](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.21) - 2021-01-18

- Support multiple type enum [#309]
- Support CSV [#308]
- Support custom encoding [#307]

---

## [0.6.20](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.20) - 2021-01-15

- Support python dictionary [#305]
- Fix parse_ref in one_of [#304[

---

## [0.6.19](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.19) - 2021-01-15

- Fix nested enum [#303]
- Fix similar nested array [#302] 

---

## [0.6.18](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.18) - 2021-01-08

- ignore datetime in yaml [#299]

---

## [0.6.17](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.17) - 2021-01-06

- improve reusing model [#297]

---

## [0.6.16](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.16) - 2020-12-31

- cache jinja2 template [#296]
- improve performance 2 [#295]

---

## [0.6.15](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.15) - 2020-12-28

- Support reuse_models [#294]
- Support Python3.9 [#293]
- Add use-schema-description option [#292] 

---

## [0.6.14](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.14) - 2020-12-27

- Fix file path on windows [#291]
- Improve performance [#290]

---

## [0.6.13](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.13) - 2020-12-25

- Fix array include null [#288]
- Fix resolving base class order [#287]
- Warn with default format for type when not found [#273] by @Liam-Deacon 

Thanks to @Liam-Deacon 

---

## [0.6.12](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.12) - 2020-12-24

- fix invalid field name on enum [#281]
- support circular reference [#280] 

---

## [0.6.11](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.11) - 2020-12-17

- Fix root array [#277]
- Fix detecting file path [#276]

---

## [0.6.10](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.10) - 2020-12-07

- Support nested directory [#275]

---

## [0.6.9](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.9) - 2020-12-02

- support external files in a directory [#272]

---

## [0.6.8](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.8) - 2020-11-29

- fix a condition of importing annotations [#270]
- remove version limit of black [#269] 
- improve $id [#261]

---

## [0.6.7](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.7) - 2020-11-17

- fix external definitions [#265]

---

## [0.6.6](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.6) - 2020-11-14

- support standard collections for type hinting (list, dict)  [#263]
- support python3.9 [#262]

---

## [0.6.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.5) - 2020-11-12

- support $id [#260]
- support root $id  [#259]

---

## [0.6.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.4) - 2020-11-11

- support custom class name [#257]
- ignore subclass enum [#255] 

---

## [0.6.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.3) - 2020-11-09

- fix settings for isort [#254]
- update isort and black [#251]  by @Chilipp 

Thanks to @Chilipp 

---

## [0.6.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.2) - 2020-11-05

- add `--force-optional` [#250] 
- change `use_default_on_required_field` to `apply_default_values_for_required_fields` [#249 ]

---

## [0.6.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.1) - 2020-11-01

- support input_filename [#248]
- support unix-time [#247]

---

## [0.6.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.6.0) - 2020-10-18

- Change parser interface [#241]
- fix handling field constraints [#240]
- refactor parsers [#236]

---

## [0.5.39](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.39) - 2020-10-06

- Fix arrays in additional properties [#234]
- Remove unused imports [#235]

---

## [0.5.38](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.38) - 2020-10-05

- Fix exclusiveMaximum and exclusiveMinimum [#233]

---

## [0.5.37](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.37) - 2020-10-03

- support null and array in type [#226]

---

## [0.5.36](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.36) - 2020-10-02

Fixes typo in import name of condecimal [#230] by @kriberg
Thanks to @kriberg

---

## [0.5.35](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.35) - 2020-09-23

- Use default value even if a field is required [#228]
- Fix nested additional properties [#227]

---

## [0.5.34](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.34) - 2020-09-19

- fix external root jsonschema [#221]

---

## [0.5.33](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.33) - 2020-09-17

- add a option to disable timestamp on file headers [#219]
- add allow_population_by_field_name option [#220]

---

## [0.5.32](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.32) - 2020-09-16

- Fix additional properties [#218]

---

## [0.5.31](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.31) - 2020-09-12

- Fix additional properties [#214]
- Refactor import [#213]
- Fix positive import [#212]

---

## [0.5.30](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.30) - 2020-09-04

- support any [#208]
- support example [#207]

---

## [0.5.29](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.29) - 2020-08-25

- change dependency versions [#202]

---

## [0.5.28](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.28) - 2020-08-21

- change argcomplete lowest version [#201]

---

## [0.5.27](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.27) - 2020-08-16

- Added support of integer in string [#199] by @Forden
Thanks to @Forden

---

## [0.5.26](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.26) - 2020-08-14

- update requirement versions [#198]

---

## [0.5.25](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.25) - 2020-08-13

- Fix schemas path [#196]
- Add uri-reference [#194] by @drsm79 
Thanks to @drsm79 

---

## [0.5.24](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.24) - 2020-08-03

- improve merge of CLI arguments and pyproject options [#191] by @joshbode
Thanks to @joshbode

- ignore type and sort arguments of `Field` [#192]

---

## [0.5.23](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.23) - 2020-08-02

- Support options on pyproject.toml [#190]

---

## [0.5.22](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.22) - 2020-07-30

- add strip-default-none option [#186]

---

## [0.5.21](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.21) - 2020-07-30

- add snake case field option [#185]

---

## [0.5.20](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.20) - 2020-07-27

Fix: #182. Fix yaml support. Improve OAS3  [#183] by @ioggstream

Thanks to @ioggstream

---

## [0.5.19](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.19) - 2020-07-24

- Support remote ref [#179]

---

## [0.5.18](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.18) - 2020-07-23

- Add aliases option to map reserved fields [#181] by @joshbode

Thanks to @joshbode

---

## [0.5.17](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.17) - 2020-07-22

- Fix model names( include fixing duplicate enum names) [#180]

---

## [0.5.16](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.16) - 2020-07-19

- add model resolver [#172]

---

## [0.5.15](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.15) - 2020-07-19

- Implements -Handle double __ in snake to camel function- [#175] by @skrawcz 

Thanks to @skrawcz 

---

## [0.5.14](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.14) - 2020-07-14

- Add option to convert all con* annotations to Field constraint options [#173] by @joshbode 

Thanks to @joshbode 

---

## [0.5.13](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.13) - 2020-06-30

- Fix incorrect optional type on the aliased field [#167]

---

## [0.5.12](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.12) - 2020-06-29

- Space and special characters in keys [#166]

---

## [0.5.11](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.11) - 2020-06-25

- support nested array [#165]

---

## [0.5.10](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.10) - 2020-06-20

- fix default [#161]

---

## [0.5.9](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.9) - 2020-06-19

- fix condition for typed_default [#155]

---

## [0.5.8](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.8) - 2020-06-17

- Support typed default value [#154]

---

## [0.5.7](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.7) - 2020-06-14

- add __str__ on Imports [#152]

---

## [0.5.6](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.6) - 2020-06-13

- support one_of [#147]

---

## [0.5.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.5) - 2020-06-12

- Support enum in array [#149]
- Fix multiple sub-type in List [#150]

---

## [0.5.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.4) - 2020-06-11

- fix `anyof` in array fields [#146]

---

## [0.5.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.3) - 2020-06-11

- dynamic field serialization [#141] by @FlorianLudwig

Thanks to @FlorianLudwig

---

## [0.5.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.2) - 2020-06-05

- support decimal [#137]

---

## [0.5.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.1) - 2020-06-05

- support empty dict on items [#135]
- support hostname [#136]

---

## [0.5.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.5.0) - 2020-06-02

- Breaking Change: Fix invalid python name [#132]
The fixes change the class name of non-Upper Camel to Upper Camel

---

## [0.4.11](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.11) - 2020-05-19

- Fix args of `conint` and `confloat` [#128]

---

## [0.4.10](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.10) - 2020-05-06

- Fix parse errors when property pattern is explicit. [#125] by @mgonzalezperna

Thanks to @mgonzalezperna

---

## [0.4.9](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.9) - 2020-04-22

- Fixed problems, if a name starts with a underscore [#120] by @julian-r

Thanks to @julian-r  

---

## [0.4.8](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.8) - 2020-04-18

- update pydantic version [#119]
- create `generate` function [#118]

---

## [0.4.7](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.7) - 2020-04-14

- Support json and yaml [#115]

---

## [0.4.6](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.6) - 2020-04-06

- fix as a statement on import [#114]

---

## [0.4.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.5) - 2020-04-05

- support as on import statement [#112]
- support empty array on JsonSchema [#113]

---

## [0.4.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.4) - 2020-04-01

- handle edge-case where models map to the __init__.py level of a module [#110] by @joshbode
Thanks to @joshbode

---

## [0.4.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.3) - 2020-03-31

- import version to get full 100% coverage [#109] by @joshbode
Thanks to @joshbode

---

## [0.4.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.2) - 2020-03-30

- Correct population of modular structure [#96] by @joshbode

Thanks to @joshbode

---

## [0.4.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.1) - 2020-03-23

- support empty object as any root object [#106]
- support reserved words as a field [#107]
- change validation to optional [#108]

---

## [0.4.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.4.0) - 2020-03-16

- improve jsonschema [#104]
- support array of type attribute on jsonschema [#103]
- change url-validator [#100]
- support `Field` [#99]
- correct string-normalization to skip-string-normalization #98 by @joshbode
- move lint configuration (black, isort, mypy) to configuration files [#97]  by @joshbode

Thanks to @joshbode

---

## [0.3.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.3.3) - 2020-02-26

- Change numeric constraints to correct mapping [#94] by @surajbarkale

Thanks to @surajbarkale

---

## [0.3.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.3.2) - 2020-02-05

add support for arrays of simple primities to anyOf [#92] by @joshbode

Thanks to @joshbode

---

## [0.3.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.3.1) - 2020-02-03

- Move logic for anyOf/allOf to higher priority [#91] by @joshbode

Thanks to @joshbode

---

## [0.3.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.3.0) - 2020-01-09

- Support JsonSchema [#89]
- Support Remote reference [#87]

---

## [0.2.16](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.16) - 2019-12-13

- Fix types requiring imports in alloff, conint, confloat [#84] by @krezac 

Thanks to @krezac

---

## [0.2.15](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.15) - 2019-12-04

- Support `additionalProperties`  as `Extra.allow` [#83] 

---

## [0.2.14](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.14) - 2019-11-25

- add support for pyproject.toml if present ［#80］by @joshbode
Thanks to @joshbode

---

## [0.2.13](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.13) - 2019-11-22

- Support for Primitve union properties [#79] by @joshbode

Thanks to @joshbode

---

## [0.2.12](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.12) - 2019-11-04

- update dependency versions [#78]

---

## [0.2.11](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.11) - 2019-10-18

- add version option [#75]

---

## [0.2.10](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.10) - 2019-10-18

- support enum alias [#74]

---

## [0.2.9](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.9) - 2019-10-17

- Fix some edge-cases with module references [#73] by @joshbode 

---

## [0.2.8](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.8) - 2019-10-16

- Add support for custom templates and extra template data [#71] by @joshbode
Thanks to @joshbode

---

## [0.2.7](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.7) - 2019-10-15

- add support for object arrays [#70] by @joshbode 
Thanks to @joshbode 

---

## [0.2.6](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.6) - 2019-10-10

- Add missing imports for `constr` and `Dict[str, Any]` [#69] by @joshbode

---

## [0.2.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.5) - 2019-10-09

- add scripts for a test, lint, and format [#68] by @koxudaxi 
- Add support for "modular" schemas [#66] by @joshbode 
- Fix Import path for UUID [#66] by @joshbode 
Thanks to @joshbode

---

## [0.2.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.4) - 2019-09-26

add debug mode as `--debug`

---

## [0.2.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.3) - 2019-09-13

- fix to add `List` on an import statement
- support normalize enum fields 

---

## [0.2.2](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.2) - 2019-09-13

- fix classes order

---

## [0.2.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.1) - 2019-09-13

- support anyOf
- support allOf

---

## [0.2.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.2.0) - 2019-09-05

- support enum
- support forward refs
- support stdin as input file
- target python version
- support duplicate models
- improve to parse array object

---

## [0.1.0](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.1.0) - 2019-08-06

## add features
- custom base model
- null
- create import statements
- string pattern 
- Minimum
- Maximum
- exclusiveMinimum 
- exclusiveMaximum
- multipleOf

---

## [0.0.6](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.0.6) - 2019-07-31

## add supported formats
- email
- uri
- ipv4
- ipv6
- time

---

## [0.0.5](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.0.5) - 2019-07-26

- refactor a parser
- support custom_root_type
- add unittest

---

## [0.0.4](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.0.4) - 2019-07-23

- convert plurals name to singular name for array items

---

## [0.0.3](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.0.3) - 2019-07-23

- fix parsing objects

---

## [0.0.1](https://github.com/koxudaxi/datamodel-code-generator/releases/tag/0.0.1) - 2019-07-23

- Support generate pydantic models from openapi models

Thanks to @joshbode


---

