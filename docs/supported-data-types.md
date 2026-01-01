# 📚 Supported Input Formats

This code generator supports the following input formats:

- OpenAPI 3 (YAML/JSON, [OpenAPI Data Type](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#data-types));
- JSON Schema ([JSON Schema Core](http://json-schema.org/draft/2019-09/json-schema-validation.html) /[JSON Schema Validation](http://json-schema.org/draft/2019-09/json-schema-validation.html));
- JSON/YAML Data (it will be converted to JSON Schema);
- Python dictionary (it will be converted to JSON Schema);
- GraphQL schema ([GraphQL Schemas and Types](https://graphql.org/learn/schema/));

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
- path
- uuid (uuid1/uuid2/uuid3/uuid4/uuid5)
- ulid (requires [`python-ulid`](https://github.com/mdomke/python-ulid))
- ipv4
- ipv6
- hostname
- decimal
- uri

### 🔗 Other schema
- enum (as enum.Enum or typing.Literal)
- allOf (as Multiple inheritance)
- anyOf (as typing.Union)
- oneOf (as typing.Union)
- $ref ([http extra](index.md#http-extra-option) is required when resolving $ref for remote files.)
- $id (for [JSONSchema](https://json-schema.org/understanding-json-schema/structuring.html#id))
