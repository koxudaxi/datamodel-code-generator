# Field Customization

## Options

| Option | Description |
|--------|-------------|
| [`--aliases`](#aliases) | Apply custom field and class name aliases from JSON file. |
| [`--capitalize-enum-members`](#capitalize-enum-members) | Capitalize enum member names to UPPER_CASE format. |
| [`--empty-enum-field-name`](#empty-enum-field-name) | Name for empty string enum field values. |
| [`--extra-fields`](#extra-fields) | Configure how generated models handle extra fields not defin... |
| [`--field-constraints`](#field-constraints) | Generate Field() with validation constraints from schema. |
| [`--field-extra-keys`](#field-extra-keys) | Include specific extra keys in Field() definitions. |
| [`--field-extra-keys-without-x-prefix`](#field-extra-keys-without-x-prefix) | Include specified schema extension keys in Field() without r... |
| [`--field-include-all-keys`](#field-include-all-keys) | Include all schema keys in Field() json_schema_extra. |
| [`--no-alias`](#no-alias) | Disable Field alias generation for non-Python-safe property ... |
| [`--original-field-name-delimiter`](#original-field-name-delimiter) | Specify delimiter for original field names when using snake-... |
| [`--remove-special-field-name-prefix`](#remove-special-field-name-prefix) | Remove the special prefix from field names. |
| [`--set-default-enum-member`](#set-default-enum-member) | Set the first enum member as the default value for enum fiel... |
| [`--snake-case-field`](#snake-case-field) | Convert field names to snake_case format. |
| [`--special-field-name-prefix`](#special-field-name-prefix) | Prefix to add to special field names (like reserved keywords... |
| [`--use-attribute-docstrings`](#use-attribute-docstrings) | Generate field descriptions as attribute docstrings instead ... |
| [`--use-enum-values-in-discriminator`](#use-enum-values-in-discriminator) | Use enum values in discriminator mappings for union types. |
| [`--use-field-description`](#use-field-description) | Include schema descriptions as Field docstrings. |
| [`--use-inline-field-description`](#use-inline-field-description) | Add field descriptions as inline comments. |
| [`--use-schema-description`](#use-schema-description) | Use schema description as class docstring. |
| [`--use-title-as-name`](#use-title-as-name) | Use schema title as the generated class name. |

---

## `--aliases` {#aliases}

Apply custom field and class name aliases from JSON file.

The `--aliases` option allows renaming fields and classes via a JSON mapping file,
providing fine-grained control over generated names independent of schema definitions.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --aliases openapi/aliases.json --target-python 3.9 # (1)!
    ```

    1. :material-arrow-left: `--aliases` - the option documented here

??? example "Input Schema"

    ```yaml
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Swagger Petstore
      license:
        name: MIT
    servers:
      - url: http://petstore.swagger.io/v1
    paths:
      /pets:
        get:
          summary: List all pets
          operationId: listPets
          tags:
            - pets
          parameters:
            - name: limit
              in: query
              description: How many items to return at one time (max 100)
              required: false
              schema:
                type: integer
                format: int32
          responses:
            '200':
              description: A paged array of pets
              headers:
                x-next:
                  description: A link to the next page of responses
                  schema:
                    type: string
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
        post:
          summary: Create a pet
          operationId: createPets
          tags:
            - pets
          responses:
            '201':
              description: Null response
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          operationId: showPetById
          tags:
            - pets
          parameters:
            - name: petId
              in: path
              required: true
              description: The id of the pet to retrieve
              schema:
                type: string
          responses:
            '200':
              description: Expected response to a valid request
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
        x-amazon-apigateway-integration:
          uri:
            Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
          passthroughBehavior: when_no_templates
          httpMethod: POST
          type: aws_proxy
    components:
      schemas:
        Pet:
          required:
            - id
            - name
          properties:
            id:
              type: integer
              format: int64
              default: 1
            name:
              type: string
            tag:
              type: string
        Pets:
          type: array
          items:
            $ref: "#/components/schemas/Pet"
        Users:
          type: array
          items:
            required:
              - id
              - name
            properties:
              id:
                type: integer
                format: int64
              name:
                type: string
              tag:
                type: string
        Id:
          type: string
        Rules:
          type: array
          items:
            type: string
        Error:
          description: error result
          required:
            - code
            - message
          properties:
            code:
              type: integer
              format: int32
            message:
              type: string
        apis:
          type: array
          items:
            type: object
            properties:
              apiKey:
                type: string
                description: To be used as a dataset parameter value
              apiVersionNumber:
                type: string
                description: To be used as a version parameter value
              apiUrl:
                type: string
                format: uri
                description: "The URL describing the dataset's fields"
              apiDocumentationUrl:
                type: string
                format: uri
                description: A URL to the API console for each API
        Event:
          type: object
          description: Event object
          properties:
            name:
              type: string
        Result:
            type: object
            properties:
              event:
                $ref: '#/components/schemas/Event'
    ```

??? example "Output"

    === "Pydantic v1"

        ```python
        # generated by datamodel-codegen:
        #   filename:  api.yaml
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import List, Optional
        
        from pydantic import AnyUrl, BaseModel, Field
        
        
        class Pet(BaseModel):
            id_: int = Field(..., alias='id')
            name_: str = Field(..., alias='name')
            tag: Optional[str] = None
        
        
        class Pets(BaseModel):
            __root__: List[Pet]
        
        
        class User(BaseModel):
            id_: int = Field(..., alias='id')
            name_: str = Field(..., alias='name')
            tag: Optional[str] = None
        
        
        class Users(BaseModel):
            __root__: List[User]
        
        
        class Id(BaseModel):
            __root__: str
        
        
        class Rules(BaseModel):
            __root__: List[str]
        
        
        class Error(BaseModel):
            code: int
            message: str
        
        
        class Api(BaseModel):
            apiKey: Optional[str] = Field(
                None, description='To be used as a dataset parameter value'
            )
            apiVersionNumber: Optional[str] = Field(
                None, description='To be used as a version parameter value'
            )
            apiUrl: Optional[AnyUrl] = Field(
                None, description="The URL describing the dataset's fields"
            )
            apiDocumentationUrl: Optional[AnyUrl] = Field(
                None, description='A URL to the API console for each API'
            )
        
        
        class Apis(BaseModel):
            __root__: List[Api]
        
        
        class Event(BaseModel):
            name_: Optional[str] = Field(None, alias='name')
        
        
        class Result(BaseModel):
            event: Optional[Event] = None
        ```

    === "msgspec"

        ```python
        # generated by datamodel-codegen:
        #   filename:  api.yaml
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import Annotated, List, Union
        
        from msgspec import UNSET, Meta, Struct, UnsetType, field
        from typing_extensions import TypeAlias
        
        
        class Pet(Struct):
            id_: int = field(name='id')
            name_: str = field(name='name')
            tag: Union[str, UnsetType] = UNSET
        
        
        Pets: TypeAlias = List[Pet]
        
        
        class User(Struct):
            id_: int = field(name='id')
            name_: str = field(name='name')
            tag: Union[str, UnsetType] = UNSET
        
        
        Users: TypeAlias = List[User]
        
        
        Id: TypeAlias = str
        
        
        Rules: TypeAlias = List[str]
        
        
        class Error(Struct):
            code: int
            message: str
        
        
        class Api(Struct):
            apiKey: Union[
                Annotated[str, Meta(description='To be used as a dataset parameter value')],
                UnsetType,
            ] = UNSET
            apiVersionNumber: Union[
                Annotated[str, Meta(description='To be used as a version parameter value')],
                UnsetType,
            ] = UNSET
            apiUrl: Union[
                Annotated[str, Meta(description="The URL describing the dataset's fields")],
                UnsetType,
            ] = UNSET
            apiDocumentationUrl: Union[
                Annotated[str, Meta(description='A URL to the API console for each API')],
                UnsetType,
            ] = UNSET
        
        
        Apis: TypeAlias = List[Api]
        
        
        class Event(Struct):
            name_: Union[str, UnsetType] = field(name='name', default=UNSET)
        
        
        class Result(Struct):
            event: Union[Event, UnsetType] = UNSET
        ```

---

## `--capitalize-enum-members` {#capitalize-enum-members}

Capitalize enum member names to UPPER_CASE format.

The `--capitalize-enum-members` flag converts enum member names to
UPPER_CASE format (e.g., `active` becomes `ACTIVE`), following Python
naming conventions for constants.

**Related:** [`--snake-case-field`](field-customization.md#snake-case-field)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --capitalize-enum-members # (1)!
    ```

    1. :material-arrow-left: `--capitalize-enum-members` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "string",
      "enum": [
        "snake_case",
        "CAP_CASE",
        "CamelCase",
        "UPPERCASE"
      ]
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  many_case_enum.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    
    
    class Model(Enum):
        SNAKE_CASE = 'snake_case'
        CAP_CASE = 'CAP_CASE'
        CAMEL_CASE = 'CamelCase'
        UPPERCASE = 'UPPERCASE'
    ```

---

## `--empty-enum-field-name` {#empty-enum-field-name}

Name for empty string enum field values.

The `--empty-enum-field-name` flag configures the code generation behavior.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --empty-enum-field-name empty # (1)!
    ```

    1. :material-arrow-left: `--empty-enum-field-name` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "string",
      "enum": [
        true,
        false,
        "",
        "\n",
        "\r\n",
        "\t",
        "\b",
        null,
        "\\"
      ]
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  special_enum.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import Optional
    
    from pydantic import BaseModel
    
    
    class ModelEnum(Enum):
        True_ = True
        False_ = False
        empty = ''
        field_ = '\n'
        field__ = '\r\n'
        field__1 = '\t'
        field__2 = '\b'
        field__3 = '\\'
    
    
    class Model(BaseModel):
        __root__: Optional[ModelEnum] = None
    ```

---

## `--extra-fields` {#extra-fields}

Configure how generated models handle extra fields not defined in schema.

The `--extra-fields` flag sets the generated models to allow, forbid, or
ignore extra fields. With `--extra-fields allow`, models will accept and
store fields not defined in the schema. Options: allow, ignore, forbid.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --extra-fields allow # (1)!
    ```

    1. :material-arrow-left: `--extra-fields` - the option documented here

??? example "Input Schema"

    ```graphql
    type Person {
        id: ID!
        name: String!
        height: Int
        mass: Int
        hair_color: String
        skin_color: String
        eye_color: String
        birth_year: String
        gender: String
    
        # Relationships
        homeworld_id: ID
        homeworld: Planet
        species: [Species!]!
        species_ids: [ID!]!
        films: [Film!]!
        films_ids: [ID!]!
        starships: [Starship!]!
        starships_ids: [ID!]!
        vehicles: [Vehicle!]!
        vehicles_ids: [ID!]!
    }
    
    type Planet {
        id: ID!
        name: String!
        rotation_period: String
        orbital_period: String
        diameter: String
        climate: String
        gravity: String
        terrain: String
        surface_water: String
        population: String
    
        # Relationships
        residents: [Person!]!
        residents_ids: [ID!]!
        films: [Film!]!
        films_ids: [ID!]!
    }
    
    type Species {
        id: ID!
        name: String!
        classification: String
        designation: String
        average_height: String
        skin_colors: String
        hair_colors: String
        eye_colors: String
        average_lifespan: String
        language: String
    
        # Relationships
        people: [Person!]!
        people_ids: [ID!]!
        films: [Film!]!
        films_ids: [ID!]!
    }
    
    type Vehicle {
        id: ID!
        name: String!
        model: String
        manufacturer: String
        cost_in_credits: String
        length: String
        max_atmosphering_speed: String
        crew: String
        passengers: String
        cargo_capacity: String
        consumables: String
        vehicle_class: String
    
        # Relationships
        pilots: [Person!]!
        pilots_ids: [ID!]!
        films: [Film!]!
        films_ids: [ID!]!
    }
    
    type Starship {
        id: ID!
        name: String!
        model: String
        manufacturer: String
        cost_in_credits: String
        length: String
        max_atmosphering_speed: String
        crew: String
        passengers: String
        cargo_capacity: String
        consumables: String
        hyperdrive_rating: String
        MGLT: String
        starship_class: String
    
        # Relationships
        pilots: [Person!]!
        pilots_ids: [ID!]!
        films: [Film!]!
        films_ids: [ID!]!
    }
    
    type Film {
      id: ID!
      title: String!
      episode_id: Int!
      opening_crawl: String!
      director: String!
      producer: String
      release_date: String!
    
      # Relationships
      characters: [Person!]!
      characters_ids: [ID!]!
      planets: [Planet!]!
      planets_ids: [ID!]!
      starships: [Starship!]!
      starships_ids: [ID!]!
      vehicles: [Vehicle!]!
      vehicles_ids: [ID!]!
      species: [Species!]!
      species_ids: [ID!]!
    }
    
    type Query {
      planet(id: ID!): Planet
      listPlanets(page: Int): [Planet!]!
      person(id: ID!): Person
      listPeople(page: Int): [Person!]!
      species(id: ID!): Species
      listSpecies(page: Int): [Species!]!
      film(id: ID!): Film
      listFilms(page: Int): [Film!]!
      starship(id: ID!): Starship
      listStarships(page: Int): [Starship!]!
      vehicle(id: ID!): Vehicle
      listVehicles(page: Int): [Vehicle!]!
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  simple-star-wars.graphql
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from typing import List, Literal, Optional
    
    from pydantic import BaseModel, Extra, Field
    from typing_extensions import TypeAlias
    
    Boolean: TypeAlias = bool
    """
    The `Boolean` scalar type represents `true` or `false`.
    """
    
    
    ID: TypeAlias = str
    """
    The `ID` scalar type represents a unique identifier, often used to refetch an object or as key for a cache. The ID type appears in a JSON response as a String; however, it is not intended to be human-readable. When expected as an input type, any string (such as `"4"`) or integer (such as `4`) input value will be accepted as an ID.
    """
    
    
    Int: TypeAlias = int
    """
    The `Int` scalar type represents non-fractional signed whole numeric values. Int can represent values between -(2^31) and 2^31 - 1.
    """
    
    
    String: TypeAlias = str
    """
    The `String` scalar type represents textual data, represented as UTF-8 character sequences. The String type is most often used by GraphQL to represent free-form human-readable text.
    """
    
    
    class Film(BaseModel):
        class Config:
            extra = Extra.allow
    
        characters: List[Person]
        characters_ids: List[ID]
        director: String
        episode_id: Int
        id: ID
        opening_crawl: String
        planets: List[Planet]
        planets_ids: List[ID]
        producer: Optional[String] = None
        release_date: String
        species: List[Species]
        species_ids: List[ID]
        starships: List[Starship]
        starships_ids: List[ID]
        title: String
        vehicles: List[Vehicle]
        vehicles_ids: List[ID]
        typename__: Optional[Literal['Film']] = Field('Film', alias='__typename')
    
    
    class Person(BaseModel):
        class Config:
            extra = Extra.allow
    
        birth_year: Optional[String] = None
        eye_color: Optional[String] = None
        films: List[Film]
        films_ids: List[ID]
        gender: Optional[String] = None
        hair_color: Optional[String] = None
        height: Optional[Int] = None
        homeworld: Optional[Planet] = None
        homeworld_id: Optional[ID] = None
        id: ID
        mass: Optional[Int] = None
        name: String
        skin_color: Optional[String] = None
        species: List[Species]
        species_ids: List[ID]
        starships: List[Starship]
        starships_ids: List[ID]
        vehicles: List[Vehicle]
        vehicles_ids: List[ID]
        typename__: Optional[Literal['Person']] = Field('Person', alias='__typename')
    
    
    class Planet(BaseModel):
        class Config:
            extra = Extra.allow
    
        climate: Optional[String] = None
        diameter: Optional[String] = None
        films: List[Film]
        films_ids: List[ID]
        gravity: Optional[String] = None
        id: ID
        name: String
        orbital_period: Optional[String] = None
        population: Optional[String] = None
        residents: List[Person]
        residents_ids: List[ID]
        rotation_period: Optional[String] = None
        surface_water: Optional[String] = None
        terrain: Optional[String] = None
        typename__: Optional[Literal['Planet']] = Field('Planet', alias='__typename')
    
    
    class Species(BaseModel):
        class Config:
            extra = Extra.allow
    
        average_height: Optional[String] = None
        average_lifespan: Optional[String] = None
        classification: Optional[String] = None
        designation: Optional[String] = None
        eye_colors: Optional[String] = None
        films: List[Film]
        films_ids: List[ID]
        hair_colors: Optional[String] = None
        id: ID
        language: Optional[String] = None
        name: String
        people: List[Person]
        people_ids: List[ID]
        skin_colors: Optional[String] = None
        typename__: Optional[Literal['Species']] = Field('Species', alias='__typename')
    
    
    class Starship(BaseModel):
        class Config:
            extra = Extra.allow
    
        MGLT: Optional[String] = None
        cargo_capacity: Optional[String] = None
        consumables: Optional[String] = None
        cost_in_credits: Optional[String] = None
        crew: Optional[String] = None
        films: List[Film]
        films_ids: List[ID]
        hyperdrive_rating: Optional[String] = None
        id: ID
        length: Optional[String] = None
        manufacturer: Optional[String] = None
        max_atmosphering_speed: Optional[String] = None
        model: Optional[String] = None
        name: String
        passengers: Optional[String] = None
        pilots: List[Person]
        pilots_ids: List[ID]
        starship_class: Optional[String] = None
        typename__: Optional[Literal['Starship']] = Field('Starship', alias='__typename')
    
    
    class Vehicle(BaseModel):
        class Config:
            extra = Extra.allow
    
        cargo_capacity: Optional[String] = None
        consumables: Optional[String] = None
        cost_in_credits: Optional[String] = None
        crew: Optional[String] = None
        films: List[Film]
        films_ids: List[ID]
        id: ID
        length: Optional[String] = None
        manufacturer: Optional[String] = None
        max_atmosphering_speed: Optional[String] = None
        model: Optional[String] = None
        name: String
        passengers: Optional[String] = None
        pilots: List[Person]
        pilots_ids: List[ID]
        vehicle_class: Optional[String] = None
        typename__: Optional[Literal['Vehicle']] = Field('Vehicle', alias='__typename')
    
    
    Film.update_forward_refs()
    Person.update_forward_refs()
    ```

---

## `--field-constraints` {#field-constraints}

Generate Field() with validation constraints from schema.

The `--field-constraints` flag generates Pydantic Field() definitions with
validation constraints (min/max length, pattern, etc.) from the schema.
Output differs between Pydantic v1 and v2 due to API changes.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --field-constraints # (1)!
    ```

    1. :material-arrow-left: `--field-constraints` - the option documented here

??? example "Input Schema"

    ```yaml
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Swagger Petstore
      license:
        name: MIT
    servers:
      - url: http://petstore.swagger.io/v1
    paths:
      /pets:
        get:
          summary: List all pets
          operationId: listPets
          tags:
            - pets
          parameters:
            - name: limit
              in: query
              description: How many items to return at one time (max 100)
              required: false
              schema:
                type: integer
                format: int32
                minimum: 0
                maximum: 100
          responses:
            '200':
              description: A paged array of pets
              headers:
                x-next:
                  description: A link to the next page of responses
                  schema:
                    type: string
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
        post:
          summary: Create a pet
          operationId: createPets
          tags:
            - pets
          responses:
            '201':
              description: Null response
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          operationId: showPetById
          tags:
            - pets
          parameters:
            - name: petId
              in: path
              required: true
              description: The id of the pet to retrieve
              schema:
                type: string
          responses:
            '200':
              description: Expected response to a valid request
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
        x-amazon-apigateway-integration:
          uri:
            Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
          passthroughBehavior: when_no_templates
          httpMethod: POST
          type: aws_proxy
    components:
      schemas:
        Pet:
          required:
            - id
            - name
          properties:
            id:
              type: integer
              format: int64
              minimum: 0
              maximum: 9223372036854775807
            name:
              type: string
              maxLength: 256
            tag:
              type: string
              maxLength: 64
        Pets:
          type: array
          items:
            $ref: "#/components/schemas/Pet"
          maxItems: 10
          minItems: 1
          uniqueItems: true
        UID:
          type: integer
          minimum: 0
        Users:
          type: array
          items:
            required:
              - id
              - name
              - uid
            properties:
              id:
                type: integer
                format: int64
                minimum: 0
              name:
                type: string
                maxLength: 256
              tag:
                type: string
                maxLength: 64
              uid:
                $ref: '#/components/schemas/UID'
              phones:
                type: array
                items:
                  type: string
                  minLength: 3
                maxItems: 10
              fax:
                type: array
                items:
                  type: string
                  minLength: 3
              height:
                type:
                  - integer
                  - number
                minimum: 1
                maximum: 300
              weight:
                type:
                  - number
                  - integer
                minimum: 1.0
                maximum: 1000.0
              age:
                type: integer
                minimum: 0.0
                maximum: 200.0
                exclusiveMinimum: true
              rating:
                type: number
                minimum: 0
                exclusiveMinimum: True
                maximum: 5
    
        Id:
          type: string
        Rules:
          type: array
          items:
            type: string
        Error:
          required:
            - code
            - message
          properties:
            code:
              type: integer
              format: int32
            message:
              type: string
        apis:
          type: array
          items:
            type: object
            properties:
              apiKey:
                type: string
                description: To be used as a dataset parameter value
              apiVersionNumber:
                type: string
                description: To be used as a version parameter value
              apiUrl:
                type: string
                format: uri
                minLength: 1
                description: "The URL describing the dataset's fields"
              apiDocumentationUrl:
                type: string
                format: uri
                description: A URL to the API console for each API
        Event:
          type: object
          properties:
            name:
              type: string
        Result:
            type: object
            properties:
              event:
                $ref: '#/components/schemas/Event'
    ```

??? example "Output"

    === "Pydantic v1"

        ```python
        # generated by datamodel-codegen:
        #   filename:  api_constrained.yaml
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import List, Optional, Union
        
        from pydantic import AnyUrl, BaseModel, Field
        
        
        class Pet(BaseModel):
            id: int = Field(..., ge=0, le=9223372036854775807)
            name: str = Field(..., max_length=256)
            tag: Optional[str] = Field(None, max_length=64)
        
        
        class Pets(BaseModel):
            __root__: List[Pet] = Field(..., max_items=10, min_items=1, unique_items=True)
        
        
        class UID(BaseModel):
            __root__: int = Field(..., ge=0)
        
        
        class Phone(BaseModel):
            __root__: str = Field(..., min_length=3)
        
        
        class FaxItem(BaseModel):
            __root__: str = Field(..., min_length=3)
        
        
        class User(BaseModel):
            id: int = Field(..., ge=0)
            name: str = Field(..., max_length=256)
            tag: Optional[str] = Field(None, max_length=64)
            uid: UID
            phones: Optional[List[Phone]] = Field(None, max_items=10)
            fax: Optional[List[FaxItem]] = None
            height: Optional[Union[int, float]] = Field(None, ge=1.0, le=300.0)
            weight: Optional[Union[float, int]] = Field(None, ge=1.0, le=1000.0)
            age: Optional[int] = Field(None, gt=0, le=200)
            rating: Optional[float] = Field(None, gt=0.0, le=5.0)
        
        
        class Users(BaseModel):
            __root__: List[User]
        
        
        class Id(BaseModel):
            __root__: str
        
        
        class Rules(BaseModel):
            __root__: List[str]
        
        
        class Error(BaseModel):
            code: int
            message: str
        
        
        class Api(BaseModel):
            apiKey: Optional[str] = Field(
                None, description='To be used as a dataset parameter value'
            )
            apiVersionNumber: Optional[str] = Field(
                None, description='To be used as a version parameter value'
            )
            apiUrl: Optional[AnyUrl] = Field(
                None, description="The URL describing the dataset's fields"
            )
            apiDocumentationUrl: Optional[AnyUrl] = Field(
                None, description='A URL to the API console for each API'
            )
        
        
        class Apis(BaseModel):
            __root__: List[Api]
        
        
        class Event(BaseModel):
            name: Optional[str] = None
        
        
        class Result(BaseModel):
            event: Optional[Event] = None
        ```

    === "Pydantic v2"

        ```python
        # generated by datamodel-codegen:
        #   filename:  api_constrained.yaml
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import List, Optional, Union
        
        from pydantic import AnyUrl, BaseModel, Field, RootModel
        
        
        class Pet(BaseModel):
            id: int = Field(..., ge=0, le=9223372036854775807)
            name: str = Field(..., max_length=256)
            tag: Optional[str] = Field(None, max_length=64)
        
        
        class Pets(RootModel[List[Pet]]):
            root: List[Pet] = Field(..., max_length=10, min_length=1)
        
        
        class UID(RootModel[int]):
            root: int = Field(..., ge=0)
        
        
        class Phone(RootModel[str]):
            root: str = Field(..., min_length=3)
        
        
        class FaxItem(RootModel[str]):
            root: str = Field(..., min_length=3)
        
        
        class User(BaseModel):
            id: int = Field(..., ge=0)
            name: str = Field(..., max_length=256)
            tag: Optional[str] = Field(None, max_length=64)
            uid: UID
            phones: Optional[List[Phone]] = Field(None, max_length=10)
            fax: Optional[List[FaxItem]] = None
            height: Optional[Union[int, float]] = Field(None, ge=1.0, le=300.0)
            weight: Optional[Union[float, int]] = Field(None, ge=1.0, le=1000.0)
            age: Optional[int] = Field(None, gt=0, le=200)
            rating: Optional[float] = Field(None, gt=0.0, le=5.0)
        
        
        class Users(RootModel[List[User]]):
            root: List[User]
        
        
        class Id(RootModel[str]):
            root: str
        
        
        class Rules(RootModel[List[str]]):
            root: List[str]
        
        
        class Error(BaseModel):
            code: int
            message: str
        
        
        class Api(BaseModel):
            apiKey: Optional[str] = Field(
                None, description='To be used as a dataset parameter value'
            )
            apiVersionNumber: Optional[str] = Field(
                None, description='To be used as a version parameter value'
            )
            apiUrl: Optional[AnyUrl] = Field(
                None, description="The URL describing the dataset's fields"
            )
            apiDocumentationUrl: Optional[AnyUrl] = Field(
                None, description='A URL to the API console for each API'
            )
        
        
        class Apis(RootModel[List[Api]]):
            root: List[Api]
        
        
        class Event(BaseModel):
            name: Optional[str] = None
        
        
        class Result(BaseModel):
            event: Optional[Event] = None
        ```

---

## `--field-extra-keys` {#field-extra-keys}

Include specific extra keys in Field() definitions.

The `--field-extra-keys` flag configures the code generation behavior.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --field-extra-keys key2 --field-extra-keys-without-x-prefix x-repr # (1)!
    ```

    1. :material-arrow-left: `--field-extra-keys` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Extras",
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "normal key",
          "key1": 123,
          "key2": 456,
          "$exclude": 123,
          "invalid-key-1": "abc",
          "-invalid+key_2": "efg",
          "$comment": "comment",
          "$id": "#name",
          "register": "hij",
          "schema": "klm",
          "x-repr": true,
          "x-abc": true,
          "example": "example",
          "readOnly": true
        },
        "age": {
          "type": "integer",
          "example": 12,
          "writeOnly": true,
          "examples": [
            13,
            20
          ]
        }
      }
    }
    ```

??? example "Output"

    === "Pydantic v1"

        ```python
        # generated by datamodel-codegen:
        #   filename:  extras.json
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import Optional
        
        from pydantic import BaseModel, Field
        
        
        class Extras(BaseModel):
            name: Optional[str] = Field(
                None,
                description='normal key',
                example='example',
                invalid_key_1='abc',
                key2=456,
                repr=True,
            )
            age: Optional[int] = Field(None, example=12, examples=[13, 20])
        ```

    === "Pydantic v2"

        ```python
        # generated by datamodel-codegen:
        #   filename:  extras.json
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import Optional
        
        from pydantic import BaseModel, Field
        
        
        class Extras(BaseModel):
            name: Optional[str] = Field(
                None,
                description='normal key',
                examples=['example'],
                json_schema_extra={'key2': 456, 'invalid-key-1': 'abc'},
                repr=True,
            )
            age: Optional[int] = Field(
                None, examples=[13, 20], json_schema_extra={'example': 12}
            )
        ```

---

## `--field-extra-keys-without-x-prefix` {#field-extra-keys-without-x-prefix}

Include specified schema extension keys in Field() without requiring 'x-' prefix.

The --field-extra-keys-without-x-prefix option allows you to specify custom
schema extension keys that should be included in Pydantic Field() extras without
the 'x-' prefix requirement. For example, 'x-repr' in the schema becomes 'repr'
in Field(). This is useful for custom schema extensions and vendor-specific metadata.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --field-include-all-keys --field-extra-keys-without-x-prefix x-repr # (1)!
    ```

    1. :material-arrow-left: `--field-extra-keys-without-x-prefix` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Extras",
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "normal key",
          "key1": 123,
          "key2": 456,
          "$exclude": 123,
          "invalid-key-1": "abc",
          "-invalid+key_2": "efg",
          "$comment": "comment",
          "$id": "#name",
          "register": "hij",
          "schema": "klm",
          "x-repr": true,
          "x-abc": true,
          "example": "example",
          "readOnly": true
        },
        "age": {
          "type": "integer",
          "example": 12,
          "writeOnly": true,
          "examples": [
            13,
            20
          ]
        }
      }
    }
    ```

??? example "Output"

    === "Pydantic v1"

        ```python
        # generated by datamodel-codegen:
        #   filename:  extras.json
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import Optional
        
        from pydantic import BaseModel, Field
        
        
        class Extras(BaseModel):
            name: Optional[str] = Field(
                None,
                description='normal key',
                example='example',
                field_comment='comment',
                field_exclude=123,
                field_invalid_key_2='efg',
                invalid_key_1='abc',
                key1=123,
                key2=456,
                readOnly=True,
                register_='hij',
                repr=True,
                schema_='klm',
                x_abc=True,
            )
            age: Optional[int] = Field(None, example=12, examples=[13, 20], writeOnly=True)
        ```

    === "Pydantic v2"

        ```python
        # generated by datamodel-codegen:
        #   filename:  extras.json
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import Optional
        
        from pydantic import BaseModel, Field
        
        
        class Extras(BaseModel):
            name: Optional[str] = Field(
                None,
                description='normal key',
                examples=['example'],
                json_schema_extra={
                    'key1': 123,
                    'key2': 456,
                    '$exclude': 123,
                    'invalid-key-1': 'abc',
                    '-invalid+key_2': 'efg',
                    '$comment': 'comment',
                    'register': 'hij',
                    'schema': 'klm',
                    'x-abc': True,
                    'readOnly': True,
                },
                repr=True,
            )
            age: Optional[int] = Field(
                None, examples=[13, 20], json_schema_extra={'example': 12, 'writeOnly': True}
            )
        ```

---

## `--field-include-all-keys` {#field-include-all-keys}

Include all schema keys in Field() json_schema_extra.

The `--field-include-all-keys` flag configures the code generation behavior.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --field-include-all-keys # (1)!
    ```

    1. :material-arrow-left: `--field-include-all-keys` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Person",
      "type": "object",
      "properties": {
        "firstName": {
          "type": "string",
          "description": "The person's first name."
        },
        "lastName": {
          "type": ["string", "null"],
          "description": "The person's last name."
        },
        "age": {
          "description": "Age in years which must be equal to or greater than zero.",
          "type": "integer",
          "minimum": 0
        },
        "friends": {
          "type": "array"
        },
        "comment": {
          "type": "null"
        }
      }
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  person.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from typing import Any, List, Optional
    
    from pydantic import BaseModel, Field, conint
    
    
    class Person(BaseModel):
        firstName: Optional[str] = Field(None, description="The person's first name.")
        lastName: Optional[str] = Field(None, description="The person's last name.")
        age: Optional[conint(ge=0)] = Field(
            None, description='Age in years which must be equal to or greater than zero.'
        )
        friends: Optional[List[Any]] = None
        comment: None = None
    ```

---

## `--no-alias` {#no-alias}

Disable Field alias generation for non-Python-safe property names.

The `--no-alias` flag disables automatic alias generation when JSON property
names contain characters invalid in Python (like hyphens). Without this flag,
fields are renamed to Python-safe names with `Field(alias='original-name')`.
With this flag, only Python-safe names are used without aliases.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --no-alias # (1)!
    ```

    1. :material-arrow-left: `--no-alias` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Person",
      "type": "object",
      "properties": {
        "first-name": {
          "type": "string"
        },
        "last-name": {
          "type": "string"
        },
        "email_address": {
          "type": "string"
        }
      },
      "required": ["first-name", "last-name"]
    }
    ```

??? example "Output"

    === "With Option"

        ```python
        # generated by datamodel-codegen:
        #   filename:  no_alias.json
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import Optional
        
        from pydantic import BaseModel
        
        
        class Person(BaseModel):
            first_name: str
            last_name: str
            email_address: Optional[str] = None
        ```

    === "Without Option"

        ```python
        # generated by datamodel-codegen:
        #   filename:  no_alias.json
        #   timestamp: 2019-07-26T00:00:00+00:00
        
        from __future__ import annotations
        
        from typing import Optional
        
        from pydantic import BaseModel, Field
        
        
        class Person(BaseModel):
            first_name: str = Field(..., alias='first-name')
            last_name: str = Field(..., alias='last-name')
            email_address: Optional[str] = None
        ```

---

## `--original-field-name-delimiter` {#original-field-name-delimiter}

Specify delimiter for original field names when using snake-case conversion.

The `--original-field-name-delimiter` option works with `--snake-case-field` to specify
the delimiter used in original field names. This is useful when field names contain
delimiters like spaces or hyphens that should be treated as word boundaries during
snake_case conversion.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --snake-case-field --original-field-name-delimiter " " # (1)!
    ```

    1. :material-arrow-left: `--original-field-name-delimiter` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "SpaceIF": {
          "$ref": "#/definitions/SpaceIF"
        }
      },
      "definitions": {
        "SpaceIF": {
          "type": "string",
          "enum": [
            "Space Field"
          ]
        }
      }
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  space_field_enum.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import Optional
    
    from pydantic import BaseModel, Field
    
    
    class SpaceIF(Enum):
        space_field = 'Space Field'
    
    
    class Model(BaseModel):
        space_if: Optional[SpaceIF] = Field(None, alias='SpaceIF')
    ```

---

## `--remove-special-field-name-prefix` {#remove-special-field-name-prefix}

Remove the special prefix from field names.

The `--remove-special-field-name-prefix` flag configures the code generation behavior.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --remove-special-field-name-prefix # (1)!
    ```

    1. :material-arrow-left: `--remove-special-field-name-prefix` - the option documented here

??? example "Input Schema"

    ```json
    {
        "$id": "schema_v2.json",
        "$schema": "http://json-schema.org/schema#",
    
        "type": "object",
        "properties": {
            "@id": {
                "type": "string",
                "format": "uri",
                "pattern": "^http.*$",
                "title": "Id must be presesnt and must be a URI"
            },
            "@type": { "type": "string" },
            "@+!type": { "type": "string" },
            "@-!type": { "type": "string" },
            "profile": { "type": "string" }
        },
        "required": ["@id", "@type"]
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  special_prefix_model.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from typing import Optional
    
    from pydantic import AnyUrl, BaseModel, Field
    
    
    class Model(BaseModel):
        id: AnyUrl = Field(..., alias='@id', title='Id must be presesnt and must be a URI')
        type: str = Field(..., alias='@type')
        type_1: Optional[str] = Field(None, alias='@+!type')
        type_2: Optional[str] = Field(None, alias='@-!type')
        profile: Optional[str] = None
    ```

---

## `--set-default-enum-member` {#set-default-enum-member}

Set the first enum member as the default value for enum fields.

The `--set-default-enum-member` flag configures the code generation behavior.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --reuse-model --set-default-enum-member # (1)!
    ```

    1. :material-arrow-left: `--set-default-enum-member` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema",
      "title": "User",
      "type": "object",
      "properties": {
        "name": {
          "type": "string"
        },
        "animal": {
          "type": "string",
          "enum": [
            "dog",
            "cat",
            "snake"
          ],
          "default": "dog"
        },
        "pet": {
          "type": "string",
          "enum": [
            "dog",
            "cat",
            "snake"
          ],
          "default": "cat"
        },
        "redistribute": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "static",
              "connected"
            ]
          }
        }
      },
      "definitions": {
        "redistribute": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "static",
              "connected"
            ]
          },
          "description": "Redistribute type for routes."
        }
      }
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  duplicate_enum.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import List, Optional
    
    from pydantic import BaseModel, Field
    
    
    class Animal(Enum):
        dog = 'dog'
        cat = 'cat'
        snake = 'snake'
    
    
    class RedistributeEnum(Enum):
        static = 'static'
        connected = 'connected'
    
    
    class User(BaseModel):
        name: Optional[str] = None
        animal: Optional[Animal] = Animal.dog
        pet: Optional[Animal] = Animal.cat
        redistribute: Optional[List[RedistributeEnum]] = None
    
    
    class Redistribute(BaseModel):
        __root__: List[RedistributeEnum] = Field(
            ..., description='Redistribute type for routes.'
        )
    ```

---

## `--snake-case-field` {#snake-case-field}

Convert field names to snake_case format.

The `--snake-case-field` flag converts camelCase or PascalCase field names
to snake_case format in the generated Python code, following Python naming
conventions (PEP 8).

**Related:** [`--capitalize-enum-members`](field-customization.md#capitalize-enum-members)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --snake-case-field # (1)!
    ```

    1. :material-arrow-left: `--snake-case-field` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "InvalidEnum",
      "type": "string",
      "enum": [
        "1 value",
        " space",
        "*- special",
        "schema",
        "MRO",
        "mro"
      ]
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  invalid_enum_name.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    
    
    class InvalidEnum(Enum):
        field_1_value = '1 value'
        field_space = ' space'
        field___special = '*- special'
        schema = 'schema'
        mro_1 = 'MRO'
        mro_ = 'mro'
    ```

---

## `--special-field-name-prefix` {#special-field-name-prefix}

Prefix to add to special field names (like reserved keywords).

The `--special-field-name-prefix` flag configures the code generation behavior.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --special-field-name-prefix special # (1)!
    ```

    1. :material-arrow-left: `--special-field-name-prefix` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "string",
      "enum": [
        true,
        false,
        "",
        "\n",
        "\r\n",
        "\t",
        "\b",
        null,
        "\\"
      ]
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  special_enum.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import Optional
    
    from pydantic import BaseModel
    
    
    class ModelEnum(Enum):
        True_ = True
        False_ = False
        special_ = ''
        special__1 = '\n'
        special__ = '\r\n'
        special__2 = '\t'
        special__3 = '\b'
        special__4 = '\\'
    
    
    class Model(BaseModel):
        __root__: Optional[ModelEnum] = None
    ```

---

## `--use-attribute-docstrings` {#use-attribute-docstrings}

Generate field descriptions as attribute docstrings instead of Field descriptions.

The `--use-attribute-docstrings` flag places field descriptions in Python docstring
format (PEP 224 attribute docstrings) rather than in Field(..., description=...).
This provides better IDE support for hovering over attributes. Requires
`--use-field-description` to be enabled.

**Related:** [`--use-field-description`](field-customization.md#use-field-description)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --output-model-type pydantic_v2.BaseModel --use-field-description --use-attribute-docstrings # (1)!
    ```

    1. :material-arrow-left: `--use-attribute-docstrings` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "title": "Person",
      "properties": {
        "name": {
          "type": "string",
          "description": "The person's full name"
        },
        "age": {
          "type": "integer",
          "description": "The person's age in years"
        }
      },
      "required": ["name"]
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  use_attribute_docstrings_test.json
    #   timestamp: 1985-10-26T08:21:00+00:00
    
    from __future__ import annotations
    
    from typing import Optional
    
    from pydantic import BaseModel, ConfigDict
    
    
    class Person(BaseModel):
        model_config = ConfigDict(
            use_attribute_docstrings=True,
        )
        name: str
        """
        The person's full name
        """
        age: Optional[int] = None
        """
        The person's age in years
        """
    ```

---

## `--use-enum-values-in-discriminator` {#use-enum-values-in-discriminator}

Use enum values in discriminator mappings for union types.

The `--use-enum-values-in-discriminator` flag configures the code generation behavior.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --use-enum-values-in-discriminator --output-model-type pydantic_v2.BaseModel # (1)!
    ```

    1. :material-arrow-left: `--use-enum-values-in-discriminator` - the option documented here

??? example "Input Schema"

    ```yaml
    openapi: "3.0.0"
    components:
      schemas:
        Request:
          oneOf:
            - $ref: '#/components/schemas/RequestV1'
            - $ref: '#/components/schemas/RequestV2'
          discriminator:
            propertyName: version
            mapping:
              v1: '#/components/schemas/RequestV1'
              v2: '#/components/schemas/RequestV2'
    
        RequestVersionEnum:
          type: string
          description: this is not included!
          title: no title!
          enum:
            - v1
            - v2
        RequestBase:
          properties:
            version:
              $ref: '#/components/schemas/RequestVersionEnum'
          required:
            - version
    
        RequestV1:
          allOf:
            - $ref: '#/components/schemas/RequestBase'
          properties:
            request_id:
              type: string
              title: test title
              description: there is description
          required:
            - request_id
        RequestV2:
          allOf:
            - $ref: '#/components/schemas/RequestBase'
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  discriminator_enum.yaml
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import Literal, Union
    
    from pydantic import BaseModel, Field, RootModel
    
    
    class RequestVersionEnum(Enum):
        v1 = 'v1'
        v2 = 'v2'
    
    
    class RequestBase(BaseModel):
        version: RequestVersionEnum
    
    
    class RequestV1(RequestBase):
        request_id: str = Field(..., description='there is description', title='test title')
        version: Literal[RequestVersionEnum.v1]
    
    
    class RequestV2(RequestBase):
        version: Literal[RequestVersionEnum.v2]
    
    
    class Request(RootModel[Union[RequestV1, RequestV2]]):
        root: Union[RequestV1, RequestV2] = Field(..., discriminator='version')
    ```

---

## `--use-field-description` {#use-field-description}

Include schema descriptions as Field docstrings.

The `--use-field-description` flag extracts the `description` property from
schema fields and includes them as docstrings or Field descriptions in the
generated models, preserving documentation from the original schema.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --use-type-alias --use-field-description # (1)!
    ```

    1. :material-arrow-left: `--use-field-description` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "definitions": {
        "SimpleString": {
          "type": "string"
        },
        "UnionType": {
          "anyOf": [
            {"type": "string"},
            {"type": "integer"}
          ]
        },
        "ArrayType": {
          "type": "array",
          "items": {"type": "string"}
        },
        "AnnotatedType": {
          "title": "MyAnnotatedType",
          "description": "An annotated union type",
          "anyOf": [
            {"type": "string"},
            {"type": "boolean"}
          ]
        },
        "ModelWithTypeAliasField": {
          "type": "object",
          "properties": {
            "simple_field": {"$ref": "#/definitions/SimpleString"},
            "union_field": {"$ref": "#/definitions/UnionType"},
            "array_field": {"$ref": "#/definitions/ArrayType"},
            "annotated_field": {"$ref": "#/definitions/AnnotatedType"}
          }
        }
      }
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  type_alias.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from typing import Annotated, Any, List, Optional, Union
    
    from pydantic import BaseModel, Field
    from typing_extensions import TypeAlias
    
    Model: TypeAlias = Any
    
    
    SimpleString: TypeAlias = str
    
    
    UnionType: TypeAlias = Union[str, int]
    
    
    ArrayType: TypeAlias = List[str]
    
    
    AnnotatedType: TypeAlias = Annotated[
        Union[str, bool], Field(..., title='MyAnnotatedType')
    ]
    """
    An annotated union type
    """
    
    
    class ModelWithTypeAliasField(BaseModel):
        simple_field: Optional[SimpleString] = None
        union_field: Optional[UnionType] = None
        array_field: Optional[ArrayType] = None
        annotated_field: Optional[AnnotatedType] = None
    ```

---

## `--use-inline-field-description` {#use-inline-field-description}

Add field descriptions as inline comments.

The `--use-inline-field-description` flag adds the `description` property from
schema fields as inline comments after each field definition. This provides
documentation without using Field() wrappers.

**Related:** [`--use-field-description`](field-customization.md#use-field-description), [`--use-schema-description`](field-customization.md#use-schema-description)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --use-inline-field-description # (1)!
    ```

    1. :material-arrow-left: `--use-inline-field-description` - the option documented here

??? example "Input Schema"

    ```yaml
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Swagger Petstore
      license:
        name: MIT
    servers:
      - url: http://petstore.swagger.io/v1
    paths:
      /pets:
        get:
          summary: List all pets
          operationId: listPets
          tags:
            - pets
          parameters:
            - name: limit
              in: query
              description: How many items to return at one time (max 100)
              required: false
              schema:
                type: integer
                format: int32
          responses:
            '200':
              description: A paged array of pets
              headers:
                x-next:
                  description: A link to the next page of responses
                  schema:
                    type: string
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
        post:
          summary: Create a pet
          operationId: createPets
          tags:
            - pets
          responses:
            '201':
              description: Null response
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          operationId: showPetById
          tags:
            - pets
          parameters:
            - name: petId
              in: path
              required: true
              description: The id of the pet to retrieve
              schema:
                type: string
          responses:
            '200':
              description: Expected response to a valid request
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
        x-amazon-apigateway-integration:
          uri:
            Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
          passthroughBehavior: when_no_templates
          httpMethod: POST
          type: aws_proxy
    components:
      schemas:
        Pet:
          required:
            - id
            - name
          properties:
            id:
              type: integer
              format: int64
              default: 1
            name:
              type: string
            tag:
              type: string
        Pets:
          type: array
          items:
            $ref: "#/components/schemas/Pet"
        Users:
          type: array
          items:
            required:
              - id
              - name
            properties:
              id:
                type: integer
                format: int64
              name:
                type: string
              tag:
                type: string
        Id:
          type: string
        Rules:
          type: array
          items:
            type: string
        Error:
          description: "error result.\nNow with multi-line docstrings."
          required:
            - code
            - message
          properties:
            code:
              type: integer
              format: int32
            message:
              type: string
        apis:
          type: array
          items:
            type: object
            properties:
              apiKey:
                type: string
                description: "To be used as a dataset parameter value.\nNow also with multi-line docstrings."
              apiVersionNumber:
                type: string
                description: To be used as a version parameter value
              apiUrl:
                type: string
                format: uri
                description: "The URL describing the dataset's fields"
              apiDocumentationUrl:
                type: string
                format: uri
                description: A URL to the API console for each API
        Event:
          type: object
          description: Event object
          properties:
            name:
              type: string
        Result:
            type: object
            properties:
              event:
                $ref: '#/components/schemas/Event'
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  api_multiline_docstrings.yaml
    #   timestamp: 2022-11-11T00:00:00+00:00
    
    from __future__ import annotations
    
    from typing import List, Optional
    
    from pydantic import AnyUrl, BaseModel, Field
    
    
    class Pet(BaseModel):
        id: int
        name: str
        tag: Optional[str] = None
    
    
    class Pets(BaseModel):
        __root__: List[Pet]
    
    
    class User(BaseModel):
        id: int
        name: str
        tag: Optional[str] = None
    
    
    class Users(BaseModel):
        __root__: List[User]
    
    
    class Id(BaseModel):
        __root__: str
    
    
    class Rules(BaseModel):
        __root__: List[str]
    
    
    class Error(BaseModel):
        code: int
        message: str
    
    
    class Api(BaseModel):
        apiKey: Optional[str] = Field(
            None,
            description='To be used as a dataset parameter value.\nNow also with multi-line docstrings.',
        )
        """
        To be used as a dataset parameter value.
        Now also with multi-line docstrings.
        """
    
        apiVersionNumber: Optional[str] = Field(
            None, description='To be used as a version parameter value'
        )
        """To be used as a version parameter value"""
    
        apiUrl: Optional[AnyUrl] = Field(
            None, description="The URL describing the dataset's fields"
        )
        """The URL describing the dataset's fields"""
    
        apiDocumentationUrl: Optional[AnyUrl] = Field(
            None, description='A URL to the API console for each API'
        )
        """A URL to the API console for each API"""
    
    
    class Apis(BaseModel):
        __root__: List[Api]
    
    
    class Event(BaseModel):
        name: Optional[str] = None
    
    
    class Result(BaseModel):
        event: Optional[Event] = None
    ```

---

## `--use-schema-description` {#use-schema-description}

Use schema description as class docstring.

The `--use-schema-description` flag extracts the `description` property from
schema definitions and adds it as a docstring to the generated class. This is
useful for preserving documentation from your schema in the generated code.

**Related:** [`--use-field-description`](field-customization.md#use-field-description), [`--use-inline-field-description`](field-customization.md#use-inline-field-description)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --use-schema-description # (1)!
    ```

    1. :material-arrow-left: `--use-schema-description` - the option documented here

??? example "Input Schema"

    ```yaml
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Swagger Petstore
      license:
        name: MIT
    servers:
      - url: http://petstore.swagger.io/v1
    paths:
      /pets:
        get:
          summary: List all pets
          operationId: listPets
          tags:
            - pets
          parameters:
            - name: limit
              in: query
              description: How many items to return at one time (max 100)
              required: false
              schema:
                type: integer
                format: int32
          responses:
            '200':
              description: A paged array of pets
              headers:
                x-next:
                  description: A link to the next page of responses
                  schema:
                    type: string
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
        post:
          summary: Create a pet
          operationId: createPets
          tags:
            - pets
          responses:
            '201':
              description: Null response
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
                    x-amazon-apigateway-integration:
                      uri:
                        Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
                      passthroughBehavior: when_no_templates
                      httpMethod: POST
                      type: aws_proxy
      /pets/{petId}:
        get:
          summary: Info for a specific pet
          operationId: showPetById
          tags:
            - pets
          parameters:
            - name: petId
              in: path
              required: true
              description: The id of the pet to retrieve
              schema:
                type: string
          responses:
            '200':
              description: Expected response to a valid request
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Pets"
            default:
              description: unexpected error
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Error"
        x-amazon-apigateway-integration:
          uri:
            Fn::Sub: arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${PythonVersionFunction.Arn}/invocations
          passthroughBehavior: when_no_templates
          httpMethod: POST
          type: aws_proxy
    components:
      schemas:
        Pet:
          required:
            - id
            - name
          properties:
            id:
              type: integer
              format: int64
              default: 1
            name:
              type: string
            tag:
              type: string
        Pets:
          type: array
          items:
            $ref: "#/components/schemas/Pet"
        Users:
          type: array
          items:
            required:
              - id
              - name
            properties:
              id:
                type: integer
                format: int64
              name:
                type: string
              tag:
                type: string
        Id:
          type: string
        Rules:
          type: array
          items:
            type: string
        Error:
          description: "error result.\nNow with multi-line docstrings."
          required:
            - code
            - message
          properties:
            code:
              type: integer
              format: int32
            message:
              type: string
        apis:
          type: array
          items:
            type: object
            properties:
              apiKey:
                type: string
                description: "To be used as a dataset parameter value.\nNow also with multi-line docstrings."
              apiVersionNumber:
                type: string
                description: To be used as a version parameter value
              apiUrl:
                type: string
                format: uri
                description: "The URL describing the dataset's fields"
              apiDocumentationUrl:
                type: string
                format: uri
                description: A URL to the API console for each API
        Event:
          type: object
          description: Event object
          properties:
            name:
              type: string
        Result:
            type: object
            properties:
              event:
                $ref: '#/components/schemas/Event'
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  api_multiline_docstrings.yaml
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from typing import List, Optional
    
    from pydantic import AnyUrl, BaseModel, Field
    
    
    class Pet(BaseModel):
        id: int
        name: str
        tag: Optional[str] = None
    
    
    class Pets(BaseModel):
        __root__: List[Pet]
    
    
    class User(BaseModel):
        id: int
        name: str
        tag: Optional[str] = None
    
    
    class Users(BaseModel):
        __root__: List[User]
    
    
    class Id(BaseModel):
        __root__: str
    
    
    class Rules(BaseModel):
        __root__: List[str]
    
    
    class Error(BaseModel):
        """
        error result.
        Now with multi-line docstrings.
        """
    
        code: int
        message: str
    
    
    class Api(BaseModel):
        apiKey: Optional[str] = Field(
            None,
            description='To be used as a dataset parameter value.\nNow also with multi-line docstrings.',
        )
        apiVersionNumber: Optional[str] = Field(
            None, description='To be used as a version parameter value'
        )
        apiUrl: Optional[AnyUrl] = Field(
            None, description="The URL describing the dataset's fields"
        )
        apiDocumentationUrl: Optional[AnyUrl] = Field(
            None, description='A URL to the API console for each API'
        )
    
    
    class Apis(BaseModel):
        __root__: List[Api]
    
    
    class Event(BaseModel):
        """
        Event object
        """
    
        name: Optional[str] = None
    
    
    class Result(BaseModel):
        event: Optional[Event] = None
    ```

---

## `--use-title-as-name` {#use-title-as-name}

Use schema title as the generated class name.

The `--use-title-as-name` flag uses the `title` property from the schema
as the class name instead of deriving it from the property name or path.
This is useful when schemas have descriptive titles that should be preserved.

**Related:** [`--class-name`](model-customization.md#class-name)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --use-title-as-name # (1)!
    ```

    1. :material-arrow-left: `--use-title-as-name` - the option documented here

??? example "Input Schema"

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "definitions": {
        "ProcessingStatus": {
          "title": "Processing Status Title",
          "enum": [
            "COMPLETED",
            "PENDING",
            "FAILED"
          ],
          "type": "string",
          "description": "The processing status"
        },
        "kind": {
          "type": "string"
        },
        "ExtendedProcessingTask": {
          "title": "Extended Processing Task Title",
          "oneOf": [
            {
              "$ref": "#"
            },
            {
              "type": "object",
              "title": "NestedCommentTitle",
              "properties": {
                "comment": {
                  "type": "string"
                }
              }
            }
          ]
        },
        "ExtendedProcessingTasks": {
          "title": "Extended Processing Tasks Title",
          "type": "array",
          "items": [
            {
              "$ref": "#/definitions/ExtendedProcessingTask"
            }
          ]
        },
        "ProcessingTask": {
          "title": "Processing Task Title",
          "type": "object",
          "properties": {
            "processing_status_union": {
              "title": "Processing Status Union Title",
              "oneOf": [
                {
                  "title": "Processing Status Detail",
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "integer"
                    },
                    "description": {
                      "type": "string"
                    }
                  }
                },
                {
                  "$ref": "#/definitions/ExtendedProcessingTask"
                },
                {
                  "$ref": "#/definitions/ProcessingStatus"
                }
              ],
              "default": "COMPLETED"
            },
            "processing_status": {
              "$ref": "#/definitions/ProcessingStatus",
              "default": "COMPLETED"
            },
            "name": {
              "type": "string"
            },
            "kind": {
              "$ref": "#/definitions/kind"
            }
          }
        }
      },
      "title": "Processing Tasks Title",
      "type": "array",
          "items": [
            {
              "$ref": "#/definitions/ProcessingTask"
            }
          ]
    }
    ```

??? example "Output"

    ```python
    # generated by datamodel-codegen:
    #   filename:  titles.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import List, Optional, Union
    
    from pydantic import BaseModel, Field
    
    
    class ProcessingStatusTitle(Enum):
        COMPLETED = 'COMPLETED'
        PENDING = 'PENDING'
        FAILED = 'FAILED'
    
    
    class Kind(BaseModel):
        __root__: str
    
    
    class NestedCommentTitle(BaseModel):
        comment: Optional[str] = None
    
    
    class ProcessingStatusDetail(BaseModel):
        id: Optional[int] = None
        description: Optional[str] = None
    
    
    class ProcessingTasksTitle(BaseModel):
        __root__: List[ProcessingTaskTitle] = Field(..., title='Processing Tasks Title')
    
    
    class ExtendedProcessingTask(BaseModel):
        __root__: Union[ProcessingTasksTitle, NestedCommentTitle] = Field(
            ..., title='Extended Processing Task Title'
        )
    
    
    class ExtendedProcessingTasksTitle(BaseModel):
        __root__: List[ExtendedProcessingTask] = Field(
            ..., title='Extended Processing Tasks Title'
        )
    
    
    class ProcessingTaskTitle(BaseModel):
        processing_status_union: Optional[
            Union[ProcessingStatusDetail, ExtendedProcessingTask, ProcessingStatusTitle]
        ] = Field('COMPLETED', title='Processing Status Union Title')
        processing_status: Optional[ProcessingStatusTitle] = 'COMPLETED'
        name: Optional[str] = None
        kind: Optional[Kind] = None
    
    
    ProcessingTasksTitle.update_forward_refs()
    ```

---

