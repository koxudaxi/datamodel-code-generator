# Schema Version Support

This document describes the JSON Schema and OpenAPI versions supported by datamodel-code-generator.

## Overview

datamodel-code-generator supports multiple versions of JSON Schema and OpenAPI specifications. By default, the tool operates in **Lenient mode**, accepting all features regardless of version declarations. This ensures maximum compatibility with real-world schemas that often mix features from different versions.

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
3. **Fallback**: Draft 7 (most widely used)

## OpenAPI Version Support

### Supported Versions

| Version | Spec URL | JSON Schema Base |
|---------|----------|------------------|
| 3.0.x | [spec.openapis.org/oas/v3.0.3](https://spec.openapis.org/oas/v3.0.3) | Draft 5 (subset) |
| 3.1.x | [spec.openapis.org/oas/v3.1.0](https://spec.openapis.org/oas/v3.1.0) | 2020-12 (full) |

> **Note**: OpenAPI 2.0 (Swagger) support is limited. We recommend converting to OpenAPI 3.0+.

### Feature Compatibility Matrix

| Feature | OAS 3.0 | OAS 3.1 |
|---------|---------|---------|
| **Schema Base** | JSON Schema Draft 5 (subset) | JSON Schema 2020-12 (full) |
| **Definitions Path** | `#/components/schemas` | `#/components/schemas` |
| **Nullable** |
| `nullable: true` keyword | Yes | Deprecated |
| Null in type array | - | Yes |
| Type as array | - | Yes |
| **Array Features** |
| prefixItems | - | Yes |
| **Boolean Schemas** | - | Yes |
| **OpenAPI Specific** |
| discriminator | Yes | Yes |
| binary format | Yes | Yes |
| password format | Yes | Yes |
| webhooks | - | Yes |

### Version Detection

datamodel-code-generator detects the OpenAPI version from the `openapi` field:

- `openapi: "3.0.x"` -> OpenAPI 3.0
- `openapi: "3.1.x"` -> OpenAPI 3.1
- No `openapi` field -> Fallback to OpenAPI 3.1

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
| `contains` | Draft 6 | ❌ Not Supported | Array contains at least one matching item |
| `deprecated` | 2019-09 | ⚠️ Partial | Marks schema elements as deprecated |
| `if/then/else` | Draft 7 | ❌ Not Supported | Conditional schema validation |
| `contentMediaType/contentEncoding` | Draft 7 | ❌ Not Supported | Content type and encoding hints for strings |
| `$anchor` | 2019-09 | ❌ Not Supported | Location-independent schema references |
| `$vocabulary` | 2019-09 | ❌ Not Supported | Vocabulary declarations for meta-schemas |
| `unevaluatedProperties` | 2019-09 | ❌ Not Supported | Additional properties not evaluated by subschemas |
| `unevaluatedItems` | 2019-09 | ❌ Not Supported | Additional items not evaluated by subschemas |
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
| `xml` | OAS 3.0 | ❌ Not Supported | XML serialization metadata (name, namespace, prefix) |
| `externalDocs` | OAS 3.0 | ❌ Not Supported | Reference to external documentation |
| `links` | OAS 3.0 | ❌ Not Supported | Links between operations |
| `callbacks` | OAS 3.0 | ❌ Not Supported | Callback definitions for webhooks |
| `securitySchemes` | OAS 3.0 | ❌ Not Supported | API security mechanism definitions |
<!-- END AUTO-GENERATED SUPPORTED FEATURES -->

## Data Format Support

### Common Formats (JSON Schema + OpenAPI)

| Type | Format | Python Type |
|------|--------|-------------|
| integer | int32 | `int` |
| integer | int64 | `int` |
| number | float | `float` |
| number | double | `float` |
| number | decimal | `Decimal` |
| string | date | `date` |
| string | date-time | `datetime` |
| string | time | `time` |
| string | duration | `timedelta` |
| string | email | `EmailStr` |
| string | uri | `AnyUrl` |
| string | uuid | `UUID` |
| string | byte | `bytes` (base64) |
| string | ipv4 | `IPv4Address` |
| string | ipv6 | `IPv6Address` |
| string | hostname | `str` |

### OpenAPI-Only Formats

| Type | Format | Python Type | Notes |
|------|--------|-------------|-------|
| string | binary | `bytes` | File content |
| string | password | `SecretStr` | Sensitive data |

## Limitations and Known Issues

### JSON Schema - Unsupported Features

| Feature | Introduced | Status | Notes |
|---------|------------|--------|-------|
| `$anchor` | 2019-09 | ❌ Not supported | Use `$ref` with `$id` instead |
| `$recursiveRef` / `$recursiveAnchor` | 2019-09 | ✅ Supported | Statically resolved to self-reference |
| `$dynamicRef` / `$dynamicAnchor` | 2020-12 | ✅ Supported | Statically resolved to self-reference |
| `unevaluatedProperties` | 2019-09 | ❌ Not supported | Use `additionalProperties` instead |
| `unevaluatedItems` | 2019-09 | ❌ Not supported | Use `additionalItems` instead |
| `contentMediaType` | Draft 7 | ❌ Not supported | Content type hints ignored |
| `contentEncoding` | Draft 7 | ❌ Not supported | Encoding hints ignored |
| `contentSchema` | 2019-09 | ❌ Not supported | Nested content schema ignored |
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
| `webhooks` | OAS 3.1 | ❌ Not supported | Top-level webhooks ignored |
| `security` definitions | OAS 2.0+ | ❌ Not supported | Security schemes not generated |
| `servers` | OAS 3.0 | ❌ Not supported | Server configuration ignored |
| `externalDocs` | OAS 2.0+ | ❌ Not supported | External documentation links ignored |
| `xml` | OAS 2.0+ | ❌ Not supported | XML serialization hints ignored |
| Request body `required` | OAS 3.0 | ⚠️ Partial | Affects field optionality |
| Header/Cookie parameters | OAS 3.0 | ⚠️ Partial | Generated but not validated |

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
