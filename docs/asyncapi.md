# 📡 Generate from AsyncAPI

Generate Python models from AsyncAPI 2.x and 3.x documents.

## 🚀 Quick Start

```bash
datamodel-codegen \
    --input asyncapi.yaml \
    --input-file-type asyncapi \
    --output-model-type pydantic_v2.BaseModel \
    --output model.py
```

## 📝 Example

**asyncapi.yaml**
```yaml
asyncapi: 3.0.0
info:
  title: User events
  version: 1.0.0
channels:
  userSignedUp:
    messages:
      userSignedUp:
        payload:
          $ref: '#/components/schemas/UserSignedUp'
components:
  schemas:
    UserSignedUp:
      type: object
      required:
        - id
        - email
      properties:
        id:
          type: string
        email:
          type: string
          format: email
```

**✨ Generated model.py**
```python
from __future__ import annotations

from pydantic import BaseModel, EmailStr


class UserSignedUp(BaseModel):
    id: str
    email: EmailStr
```

## Supported AsyncAPI Versions

The AsyncAPI parser supports documents with `asyncapi` versions in the 2.x and 3.x families.

| Version | Schema behavior |
|---------|-----------------|
| 2.x | Message `schemaFormat` is applied to the message payload. AsyncAPI Schema Objects are handled with OpenAPI 3.0-compatible schema features. |
| 3.x | `payload`, `headers`, and `components.schemas` may be AsyncAPI Schema Objects, Reference Objects, or Multi Format Schema Objects. AsyncAPI Schema Objects are handled with OpenAPI 3.1-compatible schema features. |

Use `--schema-version auto` to detect the version from the `asyncapi` field, or pass
`--schema-version 2.0` / `--schema-version 3.0` to select a version explicitly.

## Model Generation Scope

datamodel-code-generator generates data models from schema-bearing fields. It does not generate clients, servers, protocol adapters, or runtime message validators.

The AsyncAPI parser extracts schemas from:

| AsyncAPI location | Generated models |
|-------------------|------------------|
| `components.schemas` | Reusable schema models |
| `components.messages[*].payload` and `headers` | Reusable message payload/header models |
| `channels[*].publish.message`, `subscribe.message`, and `messages[*]` | Channel message payload/header models |
| `operations[*].messages` and `operations[*].reply.messages` | Operation request/reply message payload/header models |
| `components.operations[*].messages` and `reply.messages` | Reusable operation message payload/header models |
| `message.traits[*].headers` and `components.messageTraits[*].headers` | Header models when the message itself does not define `headers` |
| Local and external Reference Objects | Resolved before model generation |

Protocol bindings are tolerated and their references are resolved when they lead to the schema-bearing objects above. Binding-specific configuration is treated as transport metadata and is not emitted as Python models.

## Schema Formats

AsyncAPI 3.x Multi Format Schema Objects are unwrapped through `schemaFormat` before model generation.
AsyncAPI 2.x message-level `schemaFormat` is applied to the message payload.

Supported embedded schema formats are:

| `schemaFormat` family | Behavior |
|-----------------------|----------|
| `application/vnd.aai.asyncapi...` or omitted | Parsed as an AsyncAPI Schema Object |
| `application/schema+json` / `application/schema+yaml` | Parsed with the JSON Schema/OpenAPI schema stack |
| `application/vnd.oai.openapi...` | Parsed with the OpenAPI schema stack |
| `application/vnd.apache.avro...` | Converted with the Avro parser, then generated as Python models |
| `application/vnd.google.protobuf` | Converted with the Protocol Buffers parser, then generated as Python models |

RAML, XML Schema, and custom embedded `schemaFormat` values inside an AsyncAPI document are rejected with an explicit error instead of producing partial or misleading models. Use the dedicated top-level `xmlschema` or other input types for those schema files.

Embedded Protocol Buffers schemas support inline `.proto` source strings. Use the top-level `protobuf` input type for multi-file `.proto` schemas that depend on local imports.

## Limitations

The AsyncAPI input type is for model generation from message payloads, headers, and reusable schemas. It does not:

- validate complete AsyncAPI documents;
- apply protocol binding semantics;
- generate producer/consumer code;
- enforce runtime message validation;
- merge multiple traits that define the same `headers` property.

## 📖 See Also

- 🖥️ [CLI Reference](cli-reference/index.md) - Complete CLI options reference
- 📋 [Generate from JSON Schema](jsonschema.md) - JSON Schema input documentation
- 📘 [Generate from OpenAPI](openapi.md) - OpenAPI schema behavior
- 🪶 [Generate from Apache Avro Schema](avro.md) - Avro schema input documentation
