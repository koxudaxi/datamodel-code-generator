# Schema Version Support

This document describes the JSON Schema, OpenAPI, AsyncAPI, Apache Avro, XML Schema, and Protocol Buffers versions supported by datamodel-code-generator.

## Overview

datamodel-code-generator supports multiple schema formats including JSON Schema, OpenAPI, AsyncAPI, Apache Avro, XML Schema, and Protocol Buffers. By default, the tool operates in **Lenient mode**, accepting all features regardless of version declarations for formats that carry version information. This ensures maximum compatibility with real-world schemas that often mix features from different versions.

## JSON Schema Version Support

### Supported Versions

| Version | Spec URL | Notes |
|---------|----------|-------|
| Draft 4 | [json-schema.org/draft-04](https://json-schema.org/draft-04/json-schema-core) | `id`, `definitions` |
| Draft 6 | [json-schema.org/draft-06](https://json-schema.org/draft-06/json-schema-release-notes) | `$id`, const, boolean schemas |
| Draft 7 | [json-schema.org/draft-07](https://json-schema.org/draft-07/json-schema-release-notes) | if/then/else, readOnly/writeOnly |
| 2019-09 | [json-schema.org/draft/2019-09](https://json-schema.org/draft/2019-09/release-notes) | `$defs`, `$anchor`, `$recursiveRef`/`$recursiveAnchor` |
| 2020-12 | [json-schema.org/draft/2020-12](https://json-schema.org/draft/2020-12/release-notes) | `prefixItems`, null in type arrays, `$dynamicRef`/`$dynamicAnchor` |

### Feature Compatibility Matrix

| Feature | Draft 4 | Draft 6 | Draft 7 | 2019-09 | 2020-12 |
|---------|---------|---------|---------|---------|---------|
| **ID/Reference** |
| ID field | `id` | `$id` | `$id` | `$id` | `$id` |
| Definitions key | `definitions` | `definitions` | `definitions` | `$defs`* | `$defs` |
| **Type Features** |
| Boolean schemas | - | Yes | Yes | Yes | Yes |
| Null in type array | - | - | - | - | Yes |
| const | - | Yes | Yes | Yes | Yes |
| **Numeric Constraints** |
| exclusiveMinimum (number) | - (boolean) | Yes | Yes | Yes | Yes |
| exclusiveMaximum (number) | - (boolean) | Yes | Yes | Yes | Yes |
| **Array Features** |
| prefixItems | - | - | - | - | Yes |
| items (as array/tuple) | Yes | Yes | Yes | Yes | - (single only) |
| contains | - | Yes | Yes | Yes | Yes |
| **Conditional** |
| if/then/else | - | - | Yes | Yes | Yes |
| **Recursive/Dynamic References** | | | | | |
| `$recursiveRef` / `$recursiveAnchor` | - | - | - | Yes | - |
| `$dynamicRef` / `$dynamicAnchor` | - | - | - | - | Yes |
| **Metadata** |
| readOnly | - | - | Yes | Yes | Yes |
| writeOnly | - | - | Yes | Yes | Yes |

*2019-09 supports both `definitions` and `$defs` for backward compatibility.

### Version Detection

datamodel-code-generator automatically detects the JSON Schema version:

1. **Explicit `$schema` field**: If present, the version is detected from the URL pattern
2. **Heuristics**: If no `$schema`, presence of `$defs` suggests 2020-12, `definitions` suggests Draft 7
3. **Fallback**: Draft 7 (backward-compatible default)

## OpenAPI Version Support

### Supported Versions

| Version | Spec URL | JSON Schema Base |
|---------|----------|------------------|
| 3.0.x | [spec.openapis.org/oas/v3.0.3](https://spec.openapis.org/oas/v3.0.3) | Draft 5 (subset) |
| 3.1.x | [spec.openapis.org/oas/v3.1.0](https://spec.openapis.org/oas/v3.1.0) | 2020-12 (full) |
| 3.2.x | [spec.openapis.org/oas/v3.2.0](https://spec.openapis.org/oas/v3.2.0) | 2020-12 (full) |

> **Note**: OpenAPI 2.0 (Swagger) support is limited. We recommend converting to OpenAPI 3.0+.

### Feature Compatibility Matrix

| Feature | OAS 3.0 | OAS 3.1 | OAS 3.2 |
|---------|---------|---------|---------|
| **Schema Base** | JSON Schema Draft 5 (subset) | JSON Schema 2020-12 (full) | JSON Schema 2020-12 (full) |
| **Definitions Path** | `#/components/schemas` | `#/components/schemas` | `#/components/schemas` |
| **Nullable** | | | |
| `nullable: true` keyword | Yes | Deprecated | Deprecated |
| Null in type array | - | Yes | Yes |
| Type as array | - | Yes | Yes |
| **Array Features** | | | |
| prefixItems | - | Yes | Yes |
| **Boolean Schemas** | - | Yes | Yes |
| **OpenAPI Specific** | | | |
| discriminator | Yes | Yes | Yes |
| binary format | Yes | Yes | Yes |
| password format | Yes | Yes | Yes |
| webhooks | - | Yes | Yes |

### Version Detection

datamodel-code-generator detects the OpenAPI version from the `openapi` field:

- `openapi: "3.0.x"` -> OpenAPI 3.0
- `openapi: "3.1.x"` -> OpenAPI 3.1
- `openapi: "3.2.x"` -> OpenAPI 3.2
- No `openapi` field -> Fallback to OpenAPI 3.1

## AsyncAPI Version Support

AsyncAPI documents are supported with `--input-file-type asyncapi`. The parser generates models from schema-bearing message payloads, headers, and reusable schemas.

### Supported Versions

| Version | Schema behavior |
|---------|-----------------|
| 2.x | Message `schemaFormat` is applied to `payload`; default schemas use OpenAPI 3.0-compatible features |
| 3.x | `payload`, `headers`, and `components.schemas` may use Schema Object, Reference Object, or Multi Format Schema Object; default schemas use OpenAPI 3.1-compatible features |

### Supported Schema Locations

| Location | Status | Notes |
|----------|--------|-------|
| `components.schemas` | ✅ Supported | Reusable schemas are generated even when not referenced |
| `components.messages[*].payload` / `headers` | ✅ Supported | Includes local and external references |
| Channel `publish` / `subscribe` messages | ✅ Supported | AsyncAPI 2.x channel operation messages |
| Channel `messages` | ✅ Supported | AsyncAPI 3.x channel messages |
| Operation `messages` / `reply.messages` | ✅ Supported | Includes reusable `components.operations` |
| Message trait `headers` | ✅ Supported | Used when the target message does not define `headers` |
| Protocol bindings | ⚠️ Tolerated | Binding configuration is transport metadata and is not emitted as models |

### Embedded Schema Formats

| `schemaFormat` family | Status | Notes |
|-----------------------|--------|-------|
| AsyncAPI Schema Object | ✅ Supported | Default when omitted |
| JSON Schema | ✅ Supported | `application/schema+json` and `application/schema+yaml` |
| OpenAPI Schema Object | ✅ Supported | `application/vnd.oai.openapi...` |
| Apache Avro | ✅ Supported | `application/vnd.apache.avro...` |
| Protocol Buffers | ✅ Supported | `application/vnd.google.protobuf`; inline source and local imports are resolved |
| XML Schema | ✅ Supported | `application/xml`, `text/xml`, `application/xsd+xml`, `application/xml+schema`, `application/xml-schema` |
| RAML and custom formats | ❌ Explicit error | Use a dedicated top-level input type where available |

### Version Detection

datamodel-code-generator detects the AsyncAPI version from the `asyncapi` field:

- `asyncapi: "2.x.y"` -> AsyncAPI 2.x
- `asyncapi: "3.x.y"` -> AsyncAPI 3.x
- Unknown versions fall back to the 3.x schema behavior unless `--schema-version` is set explicitly

## MCP Tool Schema Profile Support

MCP tool schema profile documents are supported with `--input-file-type mcp-tools`. This input type is experimental and converts MCP tool `inputSchema` and `outputSchema` entries into JSON Schema definitions before model generation.

Supported source shapes include:

- `tools/list` JSON-RPC responses with `result.tools`;
- MCP server definitions with a top-level `tools` array;
- single tool definitions or arrays of tool definitions;
- JSON Schema documents whose `$defs` or `definitions` values are tool definitions.

Each generated definition is named from the tool `name` plus `Input` or `Output`, for example `SearchInput`, `SearchOutput`, and `CreateIssueInput`.

## Protocol Buffers Version Support

### Supported Versions

| Version | Spec URL | Notes |
|---------|----------|-------|
| proto2 | [protobuf.dev/reference/protobuf/proto2-spec](https://protobuf.dev/reference/protobuf/proto2-spec/) | `required`, `optional`, `repeated`, defaults, extensions |
| proto3 | [protobuf.dev/reference/protobuf/proto3-spec](https://protobuf.dev/reference/protobuf/proto3-spec/) | implicit field defaults, `optional`, maps, services |
| edition 2023 | [protobuf.dev/editions](https://protobuf.dev/programming-guides/editions/) | Supported by the bundled `protoc` runtime |

### Version Detection

datamodel-code-generator detects Protocol Buffers syntax from each compiled `.proto` descriptor:

- `syntax = "proto3";` -> proto3
- `syntax = "proto2";` or no syntax declaration -> proto2
- `edition = "2023";` -> edition 2023
- `--schema-version proto2`, `--schema-version proto3`, or `--schema-version 2023` can override
  auto-detection

## Apache Avro Schema Support

JSON-encoded Apache Avro schemas are supported with `--input-file-type avro`. The parser accepts `.avsc` files and Avro schema JSON.

### Supported Schema Forms

| Avro construct | Status | Notes |
|----------------|--------|-------|
| Primitive types | ✅ Supported | `null`, `boolean`, `int`, `long`, `float`, `double`, `bytes`, `string` |
| `record` | ✅ Supported | Generates Python model classes |
| `enum` | ✅ Supported | Generates enum classes |
| `array` | ✅ Supported | Generates list fields or root list models |
| `map` | ✅ Supported | Generates dict fields or root dict models |
| `fixed` | ✅ Supported | Generates fixed-length binary string models |
| `union` | ✅ Supported | Generates union types; nullable unions become optional fields |
| Named type resolution | ✅ Supported | Handles `name`, `namespace`, fullnames, nested named types, and references |
| Record field metadata | ✅ Supported | Preserves `doc`, `default`, `aliases`, and `order` where applicable |
| Logical types | ✅ Supported | Maps current Avro logical types to Python-friendly formats where possible |

### Logical Types

| Avro logical type | Python-oriented format |
|-------------------|------------------------|
| `decimal`, `big-decimal` | Decimal |
| `uuid` | UUID |
| `date` | Date |
| `time-millis`, `time-micros` | Time |
| `timestamp-millis`, `timestamp-micros`, `timestamp-nanos` | Date-time |
| `local-timestamp-millis`, `local-timestamp-micros`, `local-timestamp-nanos` | Local date-time |
| `duration` | Timedelta/duration |

### Version Detection

Apache Avro schemas do not include an in-schema version marker equivalent to JSON Schema's `$schema`, OpenAPI's `openapi`, or XML Schema versioning attributes. For that reason, `--schema-version` does not select an Avro specification version. The Avro parser follows the currently implemented Apache Avro schema rules and logical types.

### Avro Limitations

datamodel-code-generator generates Python model definitions from Avro schemas. It does not implement Avro runtime validation, binary encoding, decoding, or serialization.

<!-- BEGIN AUTO-GENERATED SUPPORTED FEATURES -->
### Supported Features (from code)

The following features are tracked in the codebase with their implementation status:

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
<!-- END AUTO-GENERATED SUPPORTED FEATURES -->

## Data Format Support

<!-- BEGIN AUTO-GENERATED DATA FORMAT SUPPORT -->
### Data Format Support (from code)

The tables below are generated from the schema format registry and the default Pydantic v2 type mapping.

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
<!-- END AUTO-GENERATED DATA FORMAT SUPPORT -->

## Limitations and Known Issues

### JSON Schema - Unsupported Features

| Feature | Introduced | Status | Notes |
|---------|------------|--------|-------|
| `contains` | Draft 6 | ⚠️ Partial | Count constraints are modeled when `contains` matches every item |
| `unevaluatedProperties` | 2019-09 | ⚠️ Partial | Boolean values and schema-valued extra allowance are modeled |
| `unevaluatedItems` | 2019-09 | ⚠️ Partial | Boolean values and schema-valued array item types are modeled |
| `contentMediaType` | Draft 7 | ⚠️ Partial | Preserved as schema metadata |
| `contentEncoding` | Draft 7 | ⚠️ Partial | Preserved as schema metadata |
| `contentSchema` | 2019-09 | ⚠️ Partial | Preserved as schema metadata |
| `$vocabulary` | 2019-09 | ❌ Not supported | Vocabulary declarations ignored |
| `$comment` | Draft 7 | ⚠️ Ignored | Comments not preserved in output |
| `deprecated` | 2019-09 | ⚠️ Partial | Recognized but not enforced |
| `examples` (array) | Draft 6 | ⚠️ Partial | Only first example used for Field default |
| Recursive `$ref` | Draft 4+ | ⚠️ Partial | Supported with `ForwardRef`, may require manual adjustment |
| `propertyNames` | Draft 6 | ✅ Supported | Dict key type constraints via pattern, enum, or $ref |
| `dependentRequired` | 2019-09 | ❌ Not supported | Dependent requirements ignored |
| `dependentSchemas` | 2019-09 | ❌ Not supported | Dependent schemas ignored |

### OpenAPI - Unsupported Features

| Feature | Introduced | Status | Notes |
|---------|------------|--------|-------|
| OpenAPI 2.0 (Swagger) | OAS 2.0 | ⚠️ Limited | Recommend converting to 3.0+ |
| `$ref` sibling keywords | OAS 3.0 | ❌ Not supported | 3.0 spec limitation (fixed in 3.1) |
| `links` | OAS 3.0 | ❌ Not supported | Runtime linking not applicable |
| `callbacks` | OAS 3.0 | ❌ Not supported | Webhook callbacks ignored |
| `webhooks` | OAS 3.1 | ✅ Supported | Generated when included in `--openapi-scopes` |
| `security` definitions | OAS 2.0+ | ❌ Not supported | Security schemes not generated |
| `servers` | OAS 3.0 | ❌ Not supported | Server configuration ignored |
| `externalDocs` | OAS 2.0+ | ⚠️ Partial | Preserved as schema metadata |
| `xml` | OAS 2.0+ | ⚠️ Partial | Preserved as schema metadata |
| Request body `required` | OAS 3.0 | ⚠️ Partial | Affects field optionality |
| Header/Cookie parameters | OAS 3.0 | ⚠️ Partial | Generated but not validated |

### Apache Avro - Unsupported Features

| Feature | Status | Notes |
|---------|--------|-------|
| Runtime validation | ❌ Not supported | Generated models are Python models, not an Avro validator |
| Avro binary serialization | ❌ Not supported | Encoding and decoding are outside model generation scope |
| Avro container files | ❌ Not supported | Input is schema JSON / `.avsc`, not Avro data files |

### GraphQL - Unsupported Features

| Feature | Spec | Status | Notes |
|---------|------|--------|-------|
| Directives | Core | ❌ Not supported | Custom directives ignored |
| Subscriptions | Core | ❌ Not supported | Only Query/Mutation types |
| Custom scalars | Core | ⚠️ Partial | Mapped to `Any` by default |
| Interfaces inheritance | Core | ⚠️ Partial | Flattened to concrete types |
| Federation directives | Apollo | ❌ Not supported | Apollo Federation not supported |
| Input unions | Proposal | ❌ Not supported | Not yet in GraphQL spec |

### Legend

- ✅ Fully supported
- ⚠️ Partial support or limitations
- ❌ Not supported

### Mixed Version Schemas

Real-world schemas often mix features from different versions. datamodel-code-generator handles this in **Lenient mode** (default):

- Features from all versions are accepted
- No warnings for version mismatches
- Maximum compatibility with existing schemas

In **Strict mode** (`--schema-version-mode strict`), warnings are emitted for version-incompatible features.

## See Also

- [Supported Data Types](./supported-data-types.md) - Complete data type support
- [JSON Schema Guide](./jsonschema.md) - JSON Schema usage examples
- [OpenAPI Guide](./openapi.md) - OpenAPI usage examples
- [AsyncAPI Guide](./asyncapi.md) - AsyncAPI usage examples
- [Apache Avro Guide](./avro.md) - Avro schema usage examples
- [Protocol Buffers / gRPC Guide](./protobuf.md) - Protocol Buffers schema usage examples
