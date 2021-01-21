# Target Source files
- OpenAPI 3 (YAML/JSON, [OpenAPI Data Type](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#data-types))
- JSON Schema ([JSON Schema Core](http://json-schema.org/draft/2019-09/json-schema-validation.html) /[JSON Schema Validation](http://json-schema.org/draft/2019-09/json-schema-validation.html))
- JSON/YAML Data (it will be converted to JSON Schema)
- Python dictionary (it will be converted to JSON Schema)

# Implemented list

This codegen supports major data types to OpenAPI/JSON Schema

## OpenAPI 3 and JsonSchema
### DataType
- string (include patter/minLength/maxLenght)
- number (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
- integer (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
- boolean
- array
- object

#### String Format 
- date
- datetime
- password
- email
- uuid (uuid1/uuid2/uuid3/uuid4/uuid5)
- ipv4
- ipv6
- hostname
- decimal

### Other schema
- enum (as enum.Enum or typing.Literal)
- allOf (as Multiple inheritance)
- anyOf (as typing.Union)
- oneOf (as typing.Union)
- $ref ([http extra](../#http-extra-option) is required when resolving $ref for remote files.)
- $id (for [JSONSchema](https://json-schema.org/understanding-json-schema/structuring.html#the-id-property))
