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

## ✅ Implemented data types and features

### 📊 Data Types
- string (supported keywords: pattern/minLength/maxLength)
- number (supported keywords: maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf)
- integer (supported keywords: maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf)
- boolean
- array
- object

### 📝 String Formats
- date
- datetime
- time
- password
- email (requires [`email-validator`](https://github.com/JoshData/python-email-validator))
- idn-email (requires [`email-validator`](https://github.com/JoshData/python-email-validator))
- idn-hostname
- path
- uuid (uuid1/uuid2/uuid3/uuid4/uuid5)
- ulid (requires [`python-ulid`](https://github.com/mdomke/python-ulid))
- ipv4
- ipv4-network
- ipv6
- ipv6-network
- hostname
- decimal
- uri
- uri-reference
- uri-template
- iri
- iri-reference
- json-pointer
- relative-json-pointer
- regex

### 🔗 Other schema
- enum (as enum.Enum or typing.Literal)
- allOf (as Multiple inheritance)
- anyOf (as typing.Union)
- oneOf (as typing.Union)
- $ref ([http extra](index.md#http-extra-option) is required when resolving $ref for remote files.)
- $id (for [JSONSchema](https://json-schema.org/understanding-json-schema/structuring.html#id))
