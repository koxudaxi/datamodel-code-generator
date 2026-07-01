# 📚 Supported Input Formats

This code generator supports the following input formats:

- OpenAPI 3.0/3.1/3.2 (YAML/JSON, [OpenAPI Data Types](https://spec.openapis.org/oas/v3.2.0.html#data-types)); OpenAPI 2.0 (Swagger) has limited support.
- [AsyncAPI](asyncapi.md) 2.x/3.x (YAML/JSON).
- JSON Schema ([JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core.html) / [JSON Schema Validation](https://json-schema.org/draft/2020-12/json-schema-validation.html)).
- Apache Avro schema (`.avsc`, [Apache Avro](avro.md)).
- [XML Schema](xmlschema.md) (XSD).
- Protocol Buffers / gRPC (`.proto`, [Protocol Buffers / gRPC](protobuf.md)).
- GraphQL schema ([GraphQL Schemas and Types](https://graphql.org/learn/schema/)).
- MCP tool schemas (`--input-file-type mcp-tools`, [MCP Tool Schemas](mcp-tools.md)).
- JSON / YAML / CSV data (converted to JSON Schema before model generation).
- Python dictionary (converted to JSON Schema before model generation).
- Existing Python types via [`--input-model`](python-model.md): Pydantic models, dataclasses, Pydantic dataclasses, TypedDict, and dict schemas.

Use `--input-file-type auto` (the default) for common files, or set an explicit
type when a file extension is ambiguous. For example, YAML can contain either an
OpenAPI/JSON Schema document or raw sample data, so use `jsonschema`, `openapi`,
or `yaml` depending on the intended input.

## 📘 OpenAPI 3 and JSON Schema {#openapi-3-and-json-schema}

Below are the data types and features recognized by datamodel-code-generator for OpenAPI 3 and JSON Schema.

<!-- BEGIN AUTO-GENERATED SCHEMA FEATURE SUPPORT -->
### Schema Feature Support (from code)

The JSON Schema and OpenAPI feature matrix below is generated from the same code metadata used by the schema version support page.

#### JSON Schema Features

| Feature | Introduced | Status | Description |
|---------|------------|--------|-------------|
| `Null in type array` | 2020-12 | ✅ Supported | Allows `type: ['string', 'null']` syntax for nullable types |
| `$defs` | 2019-09 | ✅ Supported | Uses `$defs` instead of `definitions` for schema definitions |
| `prefixItems` | 2020-12 | ✅ Supported | Tuple validation using `prefixItems` keyword |
| `Boolean schemas` | Draft 6 | ✅ Supported | Allows `true` and `false` as valid schemas |
| `$id` | Draft 6 | ✅ Supported | Schema identifier field (`id` in Draft 4, `$id` in Draft 6+) |
| `definitions/$defs` | Draft 4 | ✅ Supported | Key for reusable schema definitions |
| `exclusiveMinimum/Maximum as number` | Draft 6 | ✅ Supported | Numeric `exclusiveMinimum`/`exclusiveMaximum` (boolean in Draft 4) |
| `readOnly/writeOnly` | Draft 7 | ✅ Supported | Field visibility hints for read-only and write-only properties |
| `const` | Draft 6 | ✅ Supported | Single constant value constraint |
| `propertyNames` | Draft 6 | ✅ Supported | Dict key type constraints via pattern, enum, or $ref |
| `contains` | Draft 6 | ⚠️ Partial | Count constraints are modeled when contains matches every item; general schema-valued contains is not supported |
| `deprecated` | 2019-09 | ⚠️ Partial | Marks schema elements as deprecated |
| `if/then/else` | Draft 7 | ❌ Not Supported | Conditional schema validation |
| `contentMediaType/contentEncoding` | Draft 7 | ⚠️ Partial | Content type and encoding hints for strings |
| `contentSchema` | 2019-09 | ⚠️ Partial | Schema for decoded string content |
| `$anchor` | 2019-09 | ✅ Supported | Location-independent schema references |
| `$vocabulary` | 2019-09 | ❌ Not Supported | Vocabulary declarations for meta-schemas |
| `unevaluatedProperties` | 2019-09 | ⚠️ Partial | Additional properties not evaluated by subschemas |
| `unevaluatedItems` | 2019-09 | ⚠️ Partial | Additional items not evaluated by subschemas |
| `dependentRequired` | 2019-09 | ❌ Not Supported | Conditional property requirements |
| `dependentSchemas` | 2019-09 | ❌ Not Supported | Conditional schema application based on property presence |
| `$recursiveRef/$recursiveAnchor` | 2019-09 | ✅ Supported | Recursive reference resolution via anchors |
| `$dynamicRef/$dynamicAnchor` | 2020-12 | ✅ Supported | Dynamic reference resolution across schemas |

#### OpenAPI-Specific Features

| Feature | Introduced | Status | Description |
|---------|------------|--------|-------------|
| `nullable` | OAS 3.0 | ✅ Supported | Uses `nullable: true` for nullable types (deprecated in 3.1) |
| `discriminator` | OAS 3.0 | ✅ Supported | Polymorphism support via `discriminator` keyword |
| `webhooks` | OAS 3.1 | ✅ Supported | Top-level webhooks object for incoming events |
| `$ref with sibling keywords` | OAS 3.1 | ⚠️ Partial | $ref can coexist with description, summary (no allOf workaround) |
| `itemSchema` | OAS 3.2 | ✅ Supported | Media Type Object item schema for sequential media |
| `$self` | OAS 3.2 | ✅ Supported | Root document URI for relative and absolute reference resolution |
| `querystring` | OAS 3.2 | ✅ Supported | Query string parameter object without a parameter name |
| `xml` | OAS 3.0 | ⚠️ Partial | XML serialization metadata (name, namespace, prefix) |
| `externalDocs` | OAS 3.0 | ⚠️ Partial | Reference to external documentation |
| `links` | OAS 3.0 | ❌ Not Supported | Links between operations |
| `callbacks` | OAS 3.0 | ❌ Not Supported | Callback definitions for webhooks |
| `securitySchemes` | OAS 3.0 | ❌ Not Supported | API security mechanism definitions |
<!-- END AUTO-GENERATED SCHEMA FEATURE SUPPORT -->

## ✅ Implemented data types and features

<!-- BEGIN AUTO-GENERATED DATA TYPE SUPPORT -->
### Implemented Data Types and Formats

The schema type, format, and default Pydantic v2 type columns below are generated from the parser's schema format registry and the default Pydantic v2 type mapping; keyword and note columns document supplemental schema details.

#### Schema Data Types

| Schema Type | Default Pydantic v2 Type | Supported Keywords |
|-------------|--------------------------|--------------------|
| `integer` | `int` | maximum, exclusiveMaximum, minimum, exclusiveMinimum, multipleOf |
| `number` | `float` | maximum, exclusiveMaximum, minimum, exclusiveMinimum, multipleOf |
| `string` | `str` | pattern, minLength, maxLength |
| `boolean` | `bool` | - |
| `object` | `Dict[str, Any]` | properties, required, additionalProperties, patternProperties |
| `null` | `None` | - |
| `array` | `List[Any]` | items, prefixItems, minItems, maxItems, uniqueItems |

#### Common Formats (JSON Schema + OpenAPI)

| Schema Type | Format | Default Pydantic v2 Type | Notes |
|-------------|--------|--------------------------|-------|
| `integer` | `default` (no `format`) | `int` | - |
| `integer` | `int32` | `int` | - |
| `integer` | `int64` | `int` | - |
| `integer` | `date-time` | `AwareDatetime` | - |
| `integer` | `unix-time` | `int` | - |
| `integer` | `unixtime` | `int` | - |
| `number` | `default` (no `format`) | `float` | - |
| `number` | `float` | `float` | - |
| `number` | `double` | `float` | - |
| `number` | `decimal` | `Decimal` | - |
| `number` | `date-time` | `AwareDatetime` | - |
| `number` | `time` | `time` | - |
| `number` | `time-delta` | `timedelta` | - |
| `number` | `unixtime` | `int` | - |
| `string` | `default` (no `format`) | `str` | - |
| `string` | `byte` | `Base64Str` | Base64 encoded string |
| `string` | `date` | `date` | - |
| `string` | `date-time` | `AwareDatetime` | - |
| `string` | `timestamp with time zone` | `AwareDatetime` | - |
| `string` | `date-time-local` | `NaiveDatetime` | - |
| `string` | `duration` | `timedelta` | - |
| `string` | `time` | `time` | - |
| `string` | `time-local` | `time` | - |
| `string` | `path` | `Path` | - |
| `string` | `email` | `EmailStr` | Requires email-validator |
| `string` | `idn-email` | `EmailStr` | Requires email-validator |
| `string` | `idn-hostname` | `str` | - |
| `string` | `iri` | `str` | - |
| `string` | `iri-reference` | `str` | - |
| `string` | `uuid` | `UUID` | - |
| `string` | `uuid1` | `UUID1` | - |
| `string` | `uuid2` | `UUID` | - |
| `string` | `uuid3` | `UUID3` | - |
| `string` | `uuid4` | `UUID4` | - |
| `string` | `uuid5` | `UUID5` | - |
| `string` | `uri` | `AnyUrl` | - |
| `string` | `uri-reference` | `str` | - |
| `string` | `uri-template` | `str` | - |
| `string` | `json-pointer` | `str` | - |
| `string` | `relative-json-pointer` | `str` | - |
| `string` | `regex` | `str` | - |
| `string` | `hostname` | `str` | - |
| `string` | `ipv4` | `IPv4Address` | - |
| `string` | `ipv4-network` | `IPv4Network` | - |
| `string` | `ipv6` | `IPv6Address` | - |
| `string` | `ipv6-network` | `IPv6Network` | - |
| `string` | `decimal` | `Decimal` | - |
| `string` | `integer` | `int` | - |
| `string` | `unixtime` | `int` | - |
| `string` | `ulid` | `ULID` | Requires python-ulid |
| `boolean` | `default` (no `format`) | `bool` | - |
| `object` | `default` (no `format`) | `Dict[str, Any]` | - |
| `null` | `default` (no `format`) | `None` | - |
| `array` | `default` (no `format`) | `List[Any]` | - |

#### OpenAPI-Only Formats

| Schema Type | Format | Default Pydantic v2 Type | Notes |
|-------------|--------|--------------------------|-------|
| `string` | `binary` | `bytes` | File content |
| `string` | `password` | `SecretStr` | - |
<!-- END AUTO-GENERATED DATA TYPE SUPPORT -->

### 🔗 Other schema
- enum (as enum.Enum or typing.Literal)
- allOf (as Multiple inheritance)
- anyOf (as typing.Union)
- oneOf (as typing.Union)
- $ref ([http extra](index.md#http-extra-option) is required when resolving $ref for remote files.)
- $id (for [JSONSchema](https://json-schema.org/understanding-json-schema/structuring.html#id))
