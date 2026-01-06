# Supported Schema Formats and Versions

This document details the schema formats and versions supported by datamodel-code-generator, including version-specific features and behaviors.

## Supported Versions

### JSON Schema

| Version | $schema URI Pattern | Status |
|---------|---------------------|--------|
| Draft 4 | `draft-04` | Supported |
| Draft 6 | `draft-06` | Supported |
| Draft 7 | `draft-07` | Supported (Default) |
| Draft 2019-09 | `2019-09` | Supported |
| Draft 2020-12 | `2020-12` | Supported |

### OpenAPI

| Version | openapi Field | Status |
|---------|---------------|--------|
| 3.0.x | `3.0.*` | Supported |
| 3.1.x | `3.1.*` | Supported (Default) |

## Version Detection

The parser automatically detects schema versions using the following priority:

1. **Explicit `$schema` field** (JSON Schema) or **`openapi` field** (OpenAPI)
2. **Heuristic detection** based on keywords:
   - `$defs` present: Draft 2020-12 (also valid in 2019-09)
   - `definitions` present: Draft 7
3. **Fallback**: Draft 7 for JSON Schema, 3.1 for OpenAPI

### Manual Override

Use CLI options to override automatic detection:

```bash
# Specify JSON Schema version
datamodel-codegen --input schema.json --schema-version draft-07

# Specify OpenAPI version
datamodel-codegen --input openapi.yaml --schema-version 3.0
```

## Feature Compatibility by Version

### JSON Schema Features

| Feature | Draft 4 | Draft 6 | Draft 7 | 2019-09 | 2020-12 |
|---------|---------|---------|---------|---------|---------|
| `null` in type array | - | - | - | - | Yes |
| `$defs` (vs `definitions`) | - | - | - | Yes | Yes |
| `prefixItems` (vs items array) | - | - | - | - | Yes |
| Boolean schemas | - | Yes | Yes | Yes | Yes |
| `$id` (vs `id`) | - | Yes | Yes | Yes | Yes |
| Numeric `exclusiveMinimum/Maximum` | - | Yes | Yes | Yes | Yes |

### OpenAPI Features

| Feature | 3.0.x | 3.1.x |
|---------|-------|-------|
| `nullable` keyword | Yes | Deprecated |
| `null` in type array | - | Yes |
| Discriminator | Yes | Yes |
| `$defs` support | - | Yes |

## Data Type Formats

### Common Formats (All Versions)

| Type | Format | Python Type |
|------|--------|-------------|
| `integer` | `int32` | `int` |
| `integer` | `int64` | `int` |
| `number` | `float` | `float` |
| `number` | `double` | `float` |
| `number` | `decimal` | `Decimal` |
| `string` | `date` | `date` |
| `string` | `date-time` | `datetime` |
| `string` | `time` | `time` |
| `string` | `duration` | `timedelta` |
| `string` | `email` | `EmailStr` |
| `string` | `uri` | `AnyUrl` |
| `string` | `uuid` | `UUID` |
| `string` | `uuid1`-`uuid5` | `UUID1`-`UUID5` |
| `string` | `hostname` | `str` |
| `string` | `ipv4` | `IPv4Address` |
| `string` | `ipv6` | `IPv6Address` |
| `string` | `byte` | `bytes` |
| `string` | `path` | `Path` |

### OpenAPI-Only Formats

These formats are only valid in OpenAPI specifications:

| Type | Format | Python Type |
|------|--------|-------------|
| `string` | `binary` | `bytes` |
| `string` | `password` | `SecretStr` |

## Version Modes

### Lenient Mode (Default)

- Accepts all features regardless of declared version
- No warnings for version mismatches
- Recommended for most use cases

### Strict Mode

Enable with `--schema-version-mode strict`:

- Warns when features don't match the declared/detected version
- Useful for schema validation and compliance checking

```bash
# Enable strict mode
datamodel-codegen --input schema.json --schema-version-mode strict
```

**Strict mode warnings include:**

| Feature | JSON Schema Warning | OpenAPI Warning |
|---------|---------------------|-----------------|
| `null` in type array | Draft 4/6/7 (not supported) | 3.0 (use nullable instead) |
| `nullable` keyword | Always (OpenAPI extension) | 3.1 (deprecated) |
| `binary` format | Always (OpenAPI extension) | Never (valid) |
| `password` format | Always (OpenAPI extension) | Never (valid) |
| `prefixItems` | Before Draft 2020-12 | - |
| Items as array | Draft 2020-12 (use prefixItems) | - |
| Boolean schema | Draft 4 (not supported) | - |
| Numeric exclusiveMin/Max | Draft 4 (use boolean) | 3.0 (use boolean) |
| Boolean exclusiveMin/Max | Draft 6+ (use numeric) | 3.1 (use numeric) |

## Limitations

### JSON Schema

- `$dynamicRef`/`$dynamicAnchor` (Draft 2020-12): Not fully supported
- Complex `if`/`then`/`else` patterns: Limited support
- `unevaluatedProperties`/`unevaluatedItems`: Not supported

### OpenAPI

- Callbacks: Not supported
- Links: Not supported
- Security schemes: Parsed but not used for model generation

## Migration Guide

### From OpenAPI 3.0 to 3.1

1. Replace `nullable: true` with `type: ["string", "null"]`
2. Replace `definitions` with `$defs`
3. Update `exclusiveMinimum`/`exclusiveMaximum` from boolean to numeric values

### From JSON Schema Draft 7 to 2020-12

1. Replace `definitions` with `$defs`
2. Replace items array with `prefixItems`
3. Update `id` to `$id`

## See Also

### JSON Schema Specifications

- [JSON Schema Home](https://json-schema.org/)
- [Draft 4](https://json-schema.org/specification-links#draft-4)
- [Draft 6](https://json-schema.org/specification-links#draft-6)
- [Draft 7](https://json-schema.org/specification-links#draft-7)
- [Draft 2019-09](https://json-schema.org/specification-links#2019-09-formerly-known-as-draft-8)
- [Draft 2020-12](https://json-schema.org/specification-links#2020-12)

### OpenAPI Specifications

- [OpenAPI Initiative](https://www.openapis.org/)
- [OpenAPI 3.0.3](https://spec.openapis.org/oas/v3.0.3)
- [OpenAPI 3.1.0](https://spec.openapis.org/oas/v3.1.0)

### datamodel-code-generator

- [CLI Reference](cli-reference/index.md)
- [GitHub Repository](https://github.com/koxudaxi/datamodel-code-generator)
