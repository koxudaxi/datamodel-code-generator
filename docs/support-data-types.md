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
- $ref (exclude URL Reference)
