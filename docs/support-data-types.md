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
- enum
- allOf (as Multiple inheritance)
- anyOf (as Union)
- oneOf (as Union)
- $ref ([http extra](../#http-extra-option) is required when resolving $ref for remote files.)
- $id (for [JSONSchema](https://json-schema.org/understanding-json-schema/structuring.html#the-id-property))
