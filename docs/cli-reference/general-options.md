# ⚙️ General Options

## 📋 Options

| Option | Description |
|--------|-------------|
| [`--all-exports-collision-strategy`](#all-exports-collision-strategy) | Handle name collisions when exporting recursive module hiera... |
| [`--all-exports-scope`](#all-exports-scope) | Generate __all__ exports for child modules in __init__.py fi... |
| [`--check`](#check) | Verify generated code matches existing output without modify... |
| [`--disable-warnings`](#disable-warnings) | Suppress warning messages during code generation. |
| [`--generate-cli-command`](#generate-cli-command) | Generate CLI command from pyproject.toml configuration. |
| [`--generate-prompt`](#generate-prompt) | Generate a prompt for consulting LLMs about CLI options. |
| [`--generate-pyproject-config`](#generate-pyproject-config) | Generate pyproject.toml configuration from CLI arguments. |
| [`--http-headers`](#http-headers) | Fetch schema from URL with custom HTTP headers. |
| [`--http-ignore-tls`](#http-ignore-tls) | Disable TLS certificate verification for HTTPS requests. |
| [`--http-query-parameters`](#http-query-parameters) | Add query parameters to HTTP requests for remote schemas. |
| [`--ignore-pyproject`](#ignore-pyproject) | Ignore pyproject.toml configuration file. |
| [`--module-split-mode`](#module-split-mode) | Split generated models into separate files, one per model cl... |
| [`--shared-module-name`](#shared-module-name) | Customize the name of the shared module for deduplicated mod... |
| [`--watch`](#watch) | Watch mode cannot be used with --check mode. |
| [`--watch-delay`](#watch-delay) | Watch mode starts file watcher and handles clean exit. |

---

## `--all-exports-collision-strategy` {#all-exports-collision-strategy}

Handle name collisions when exporting recursive module hierarchies.

The `--all-exports-collision-strategy` flag determines how to resolve naming conflicts
when using `--all-exports-scope=recursive`. The 'minimal-prefix' strategy adds the
minimum module path prefix needed to disambiguate colliding names, while 'full-prefix'
uses the complete module path. Requires `--all-exports-scope=recursive`.

**Related:** [`--all-exports-scope`](general-options.md#all-exports-scope)

**See also:** [Module Structure and Exports](../module-exports.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --all-exports-scope recursive --all-exports-collision-strategy minimal-prefix # (1)!
    ```

    1. :material-arrow-left: `--all-exports-collision-strategy` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```yaml
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Modular Swagger Petstore
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
                    $ref: "#/components/schemas/collections.Pets"
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
                    $ref: "#/components/schemas/collections.Pets"
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
        models.Species:
          type: string
          enum:
            - dog
            - cat
            - snake
        models.Pet:
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
            species:
              $ref: '#/components/schemas/models.Species'
        models.User:
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
        collections.Pets:
          type: array
          items:
            $ref: "#/components/schemas/models.Pet"
        collections.Users:
          type: array
          items:
            $ref: "#/components/schemas/models.User"
        optional:
          type: string
        Id:
          type: string
        collections.Rules:
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
        collections.apis:
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
              stage:
                type: string
                enum: [
                  "test",
                  "dev",
                  "stg",
                  "prod"
                ]
        models.Event:
          type: object
          properties:
            name:
              anyOf:
                - type: string
                - type: number
                - type: integer
                - type: boolean
                - type: object
                - type: array
                  items:
                    type: string
        Result:
          type: object
          properties:
            event:
              $ref: '#/components/schemas/models.Event'
        foo.bar.Thing:
          properties:
            attributes:
              type: object
        foo.bar.Thang:
          properties:
            attributes:
              type: array
              items:
                type: object
        foo.bar.Clone:
          allOf:
            - $ref: '#/components/schemas/foo.bar.Thing'
            - type: object
              properties:
                others:
                  type: object
                  properties:
                     name:
                       type: string
    
        foo.Tea:
          properties:
            flavour:
              type: string
            id:
              $ref: '#/components/schemas/Id'
        Source:
          properties:
            country:
              type: string
        foo.Cocoa:
          properties:
            quality:
              type: integer
        bar.Field:
          type: string
          example: green
        woo.boo.Chocolate:
          properties:
            flavour:
              type: string
            source:
              $ref: '#/components/schemas/Source'
            cocoa:
              $ref: '#/components/schemas/foo.Cocoa'
            field:
              $ref: '#/components/schemas/bar.Field'
        differentTea:
          type: object
          properties:
            foo:
              $ref: '#/components/schemas/foo.Tea'
            nested:
              $ref: '#/components/schemas/nested.foo.Tea'
        nested.foo.Tea:
          properties:
            flavour:
              type: string
            id:
              $ref: '#/components/schemas/Id'
            self:
              $ref: '#/components/schemas/nested.foo.Tea'
            optional:
              type: array
              items:
                $ref: '#/components/schemas/optional'
        nested.foo.TeaClone:
          properties:
            flavour:
              type: string
            id:
              $ref: '#/components/schemas/Id'
            self:
              $ref: '#/components/schemas/nested.foo.Tea'
            optional:
              type: array
              items:
                $ref: '#/components/schemas/optional'
        nested.foo.List:
          type: array
          items:
            $ref: '#/components/schemas/nested.foo.Tea'
    ```

    **Output:**

    ```python
    # __init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from ._internal import DifferentTea, Error, Id, Optional, Result, Source
    
    __all__ = ["DifferentTea", "Error", "Id", "Optional", "Result", "Source"]
    
    # _internal.py
    # generated by datamodel-codegen:
    #   filename:  _internal
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    from . import models
    
    
    class Optional(BaseModel):
        __root__: str
    
    
    class Id(BaseModel):
        __root__: str
    
    
    class Error(BaseModel):
        code: int
        message: str
    
    
    class Result(BaseModel):
        event: models.Event | None = None
    
    
    class Source(BaseModel):
        country: str | None = None
    
    
    class DifferentTea(BaseModel):
        foo: Tea | None = None
        nested: Tea_1 | None = None
    
    
    class Tea(BaseModel):
        flavour: str | None = None
        id: Id | None = None
    
    
    class Cocoa(BaseModel):
        quality: int | None = None
    
    
    class Tea_1(BaseModel):
        flavour: str | None = None
        id: Id | None = None
        self: Tea_1 | None = None
        optional: list[Optional] | None = None
    
    
    class TeaClone(BaseModel):
        flavour: str | None = None
        id: Id | None = None
        self: Tea_1 | None = None
        optional: list[Optional] | None = None
    
    
    class List(BaseModel):
        __root__: list[Tea_1]
    
    
    Tea_1.update_forward_refs()
    
    # bar.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from pydantic import BaseModel, Field
    
    
    class FieldModel(BaseModel):
        __root__: str = Field(..., example='green')
    
    # collections.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from enum import Enum
    
    from pydantic import AnyUrl, BaseModel, Field
    
    from . import models
    
    
    class Pets(BaseModel):
        __root__: list[models.Pet]
    
    
    class Users(BaseModel):
        __root__: list[models.User]
    
    
    class Rules(BaseModel):
        __root__: list[str]
    
    
    class Stage(Enum):
        test = 'test'
        dev = 'dev'
        stg = 'stg'
        prod = 'prod'
    
    
    class Api(BaseModel):
        apiKey: str | None = Field(
            None, description='To be used as a dataset parameter value'
        )
        apiVersionNumber: str | None = Field(
            None, description='To be used as a version parameter value'
        )
        apiUrl: AnyUrl | None = Field(
            None, description="The URL describing the dataset's fields"
        )
        apiDocumentationUrl: AnyUrl | None = Field(
            None, description='A URL to the API console for each API'
        )
        stage: Stage | None = None
    
    
    class Apis(BaseModel):
        __root__: list[Api]
    
    # foo/__init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from .._internal import Cocoa, Tea
    
    __all__ = ["Cocoa", "Tea"]
    
    # foo/bar.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from typing import Any
    
    from pydantic import BaseModel
    
    
    class Thing(BaseModel):
        attributes: dict[str, Any] | None = None
    
    
    class Thang(BaseModel):
        attributes: list[dict[str, Any]] | None = None
    
    
    class Others(BaseModel):
        name: str | None = None
    
    
    class Clone(Thing):
        others: Others | None = None
    
    # models.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import Any
    
    from pydantic import BaseModel
    
    
    class Species(Enum):
        dog = 'dog'
        cat = 'cat'
        snake = 'snake'
    
    
    class Pet(BaseModel):
        id: int
        name: str
        tag: str | None = None
        species: Species | None = None
    
    
    class User(BaseModel):
        id: int
        name: str
        tag: str | None = None
    
    
    class Event(BaseModel):
        name: str | float | int | bool | dict[str, Any] | list[str] | None = None
    
    # nested/__init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    # nested/foo.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from .._internal import List
    from .._internal import Tea_1 as Tea
    from .._internal import TeaClone
    
    __all__ = ["List", "Tea", "TeaClone"]
    
    # woo/__init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from .boo import Chocolate
    
    __all__ = [
        "Chocolate",
    ]
    
    # woo/boo.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    from .. import bar
    from .._internal import Cocoa, Source
    
    
    class Chocolate(BaseModel):
        flavour: str | None = None
        source: Source | None = None
        cocoa: Cocoa | None = None
        field: bar.FieldModel | None = None
    ```

---

## `--all-exports-scope` {#all-exports-scope}

Generate __all__ exports for child modules in __init__.py files.

The `--all-exports-scope=children` flag adds __all__ to each __init__.py containing
exports from direct child modules. This improves IDE autocomplete and explicit exports.
Use 'recursive' to include all descendant exports with collision handling.

**Related:** [`--all-exports-collision-strategy`](general-options.md#all-exports-collision-strategy)

**See also:** [Module Structure and Exports](../module-exports.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --all-exports-scope children # (1)!
    ```

    1. :material-arrow-left: `--all-exports-scope` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```yaml
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Modular Swagger Petstore
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
                    $ref: "#/components/schemas/collections.Pets"
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
                    $ref: "#/components/schemas/collections.Pets"
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
        models.Species:
          type: string
          enum:
            - dog
            - cat
            - snake
        models.Pet:
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
            species:
              $ref: '#/components/schemas/models.Species'
        models.User:
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
        collections.Pets:
          type: array
          items:
            $ref: "#/components/schemas/models.Pet"
        collections.Users:
          type: array
          items:
            $ref: "#/components/schemas/models.User"
        optional:
          type: string
        Id:
          type: string
        collections.Rules:
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
        collections.apis:
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
              stage:
                type: string
                enum: [
                  "test",
                  "dev",
                  "stg",
                  "prod"
                ]
        models.Event:
          type: object
          properties:
            name:
              anyOf:
                - type: string
                - type: number
                - type: integer
                - type: boolean
                - type: object
                - type: array
                  items:
                    type: string
        Result:
          type: object
          properties:
            event:
              $ref: '#/components/schemas/models.Event'
        foo.bar.Thing:
          properties:
            attributes:
              type: object
        foo.bar.Thang:
          properties:
            attributes:
              type: array
              items:
                type: object
        foo.bar.Clone:
          allOf:
            - $ref: '#/components/schemas/foo.bar.Thing'
            - type: object
              properties:
                others:
                  type: object
                  properties:
                     name:
                       type: string
    
        foo.Tea:
          properties:
            flavour:
              type: string
            id:
              $ref: '#/components/schemas/Id'
        Source:
          properties:
            country:
              type: string
        foo.Cocoa:
          properties:
            quality:
              type: integer
        bar.Field:
          type: string
          example: green
        woo.boo.Chocolate:
          properties:
            flavour:
              type: string
            source:
              $ref: '#/components/schemas/Source'
            cocoa:
              $ref: '#/components/schemas/foo.Cocoa'
            field:
              $ref: '#/components/schemas/bar.Field'
        differentTea:
          type: object
          properties:
            foo:
              $ref: '#/components/schemas/foo.Tea'
            nested:
              $ref: '#/components/schemas/nested.foo.Tea'
        nested.foo.Tea:
          properties:
            flavour:
              type: string
            id:
              $ref: '#/components/schemas/Id'
            self:
              $ref: '#/components/schemas/nested.foo.Tea'
            optional:
              type: array
              items:
                $ref: '#/components/schemas/optional'
        nested.foo.TeaClone:
          properties:
            flavour:
              type: string
            id:
              $ref: '#/components/schemas/Id'
            self:
              $ref: '#/components/schemas/nested.foo.Tea'
            optional:
              type: array
              items:
                $ref: '#/components/schemas/optional'
        nested.foo.List:
          type: array
          items:
            $ref: '#/components/schemas/nested.foo.Tea'
    ```

    **Output:**

    ```python
    # __init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from ._internal import DifferentTea, Error, Id, Optional, Result, Source
    
    __all__ = ["DifferentTea", "Error", "Id", "Optional", "Result", "Source"]
    
    # _internal.py
    # generated by datamodel-codegen:
    #   filename:  _internal
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    from . import models
    
    
    class Optional(BaseModel):
        __root__: str
    
    
    class Id(BaseModel):
        __root__: str
    
    
    class Error(BaseModel):
        code: int
        message: str
    
    
    class Result(BaseModel):
        event: models.Event | None = None
    
    
    class Source(BaseModel):
        country: str | None = None
    
    
    class DifferentTea(BaseModel):
        foo: Tea | None = None
        nested: Tea_1 | None = None
    
    
    class Tea(BaseModel):
        flavour: str | None = None
        id: Id | None = None
    
    
    class Cocoa(BaseModel):
        quality: int | None = None
    
    
    class Tea_1(BaseModel):
        flavour: str | None = None
        id: Id | None = None
        self: Tea_1 | None = None
        optional: list[Optional] | None = None
    
    
    class TeaClone(BaseModel):
        flavour: str | None = None
        id: Id | None = None
        self: Tea_1 | None = None
        optional: list[Optional] | None = None
    
    
    class List(BaseModel):
        __root__: list[Tea_1]
    
    
    Tea_1.update_forward_refs()
    
    # bar.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from pydantic import BaseModel, Field
    
    
    class FieldModel(BaseModel):
        __root__: str = Field(..., example='green')
    
    # collections.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from enum import Enum
    
    from pydantic import AnyUrl, BaseModel, Field
    
    from . import models
    
    
    class Pets(BaseModel):
        __root__: list[models.Pet]
    
    
    class Users(BaseModel):
        __root__: list[models.User]
    
    
    class Rules(BaseModel):
        __root__: list[str]
    
    
    class Stage(Enum):
        test = 'test'
        dev = 'dev'
        stg = 'stg'
        prod = 'prod'
    
    
    class Api(BaseModel):
        apiKey: str | None = Field(
            None, description='To be used as a dataset parameter value'
        )
        apiVersionNumber: str | None = Field(
            None, description='To be used as a version parameter value'
        )
        apiUrl: AnyUrl | None = Field(
            None, description="The URL describing the dataset's fields"
        )
        apiDocumentationUrl: AnyUrl | None = Field(
            None, description='A URL to the API console for each API'
        )
        stage: Stage | None = None
    
    
    class Apis(BaseModel):
        __root__: list[Api]
    
    # foo/__init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from .._internal import Cocoa, Tea
    
    __all__ = ["Cocoa", "Tea"]
    
    # foo/bar.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from typing import Any
    
    from pydantic import BaseModel
    
    
    class Thing(BaseModel):
        attributes: dict[str, Any] | None = None
    
    
    class Thang(BaseModel):
        attributes: list[dict[str, Any]] | None = None
    
    
    class Others(BaseModel):
        name: str | None = None
    
    
    class Clone(Thing):
        others: Others | None = None
    
    # models.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from enum import Enum
    from typing import Any
    
    from pydantic import BaseModel
    
    
    class Species(Enum):
        dog = 'dog'
        cat = 'cat'
        snake = 'snake'
    
    
    class Pet(BaseModel):
        id: int
        name: str
        tag: str | None = None
        species: Species | None = None
    
    
    class User(BaseModel):
        id: int
        name: str
        tag: str | None = None
    
    
    class Event(BaseModel):
        name: str | float | int | bool | dict[str, Any] | list[str] | None = None
    
    # nested/__init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    # nested/foo.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from .._internal import List
    from .._internal import Tea_1 as Tea
    from .._internal import TeaClone
    
    __all__ = ["List", "Tea", "TeaClone"]
    
    # woo/__init__.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from .boo import Chocolate
    
    __all__ = [
        "Chocolate",
    ]
    
    # woo/boo.py
    # generated by datamodel-codegen:
    #   filename:  modular.yaml
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    from .. import bar
    from .._internal import Cocoa, Source
    
    
    class Chocolate(BaseModel):
        flavour: str | None = None
        source: Source | None = None
        cocoa: Cocoa | None = None
        field: bar.FieldModel | None = None
    ```

---

## `--check` {#check}

Verify generated code matches existing output without modifying files.

The `--check` flag compares the generated output with existing files and exits with
a non-zero status if they differ. Useful for CI/CD validation to ensure schemas
and generated code stay in sync. Works with both single files and directory outputs.

**See also:** [CI/CD Integration](../ci-cd.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --disable-timestamp --check # (1)!
    ```

    1. :material-arrow-left: `--check` - the option documented here

??? example "Examples"

    **Input Schema:**

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

    **Output:**

    ```python
    # generated by datamodel-codegen:
    #   filename:  person.json
    
    from __future__ import annotations
    
    from typing import Any
    
    from pydantic import BaseModel, Field, conint
    
    
    class Person(BaseModel):
        firstName: str | None = Field(None, description="The person's first name.")
        lastName: str | None = Field(None, description="The person's last name.")
        age: conint(ge=0) | None = Field(
            None, description='Age in years which must be equal to or greater than zero.'
        )
        friends: list[Any] | None = None
        comment: None = None
    ```

---

## `--disable-warnings` {#disable-warnings}

Suppress warning messages during code generation.

The --disable-warnings option silences all warning messages that the generator
might emit during processing (e.g., about unsupported features, ambiguous schemas,
or potential issues). Useful for clean output in CI/CD pipelines.

**See also:** [Model Reuse and Deduplication](../model-reuse.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --disable-warnings # (1)!
    ```

    1. :material-arrow-left: `--disable-warnings` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Pet",
      "allOf": [
        {
          "$ref": "#/definitions/Home"
        },
        {
          "$ref": "#/definitions/Kind"
        },
        {
          "$ref": "#/definitions/Id"
        },
        {
          "type": "object",
          "properties": {
            "name": {
              "type": "string"
            }
          }
        }
      ],
      "type": [
        "object"
      ],
      "properties": {
        "name": {
          "type": "string"
        },
        "age": {
          "type": "integer"
        }
      },
      "definitions": {
        "Home": {
          "type": "object",
          "properties": {
            "address": {
              "type": "string"
            },
            "zip": {
              "type": "string"
            }
          }
        },
        "Kind": {
          "type": "object",
          "properties": {
            "description": {
              "type": "string"
            }
          }
        },
        "Id": {
          "type": "object",
          "properties": {
            "id": {
              "type": "integer"
            }
          }
        }
      }
    }
    ```

    **Output:**

    ```python
    # generated by datamodel-codegen:
    #   filename:  all_of_with_object.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    
    class Home(BaseModel):
        address: str | None = None
        zip: str | None = None
    
    
    class Kind(BaseModel):
        description: str | None = None
    
    
    class Id(BaseModel):
        id: int | None = None
    
    
    class Pet(Home, Kind, Id):
        name: str | None = None
        age: int | None = None
    ```

---

## `--generate-cli-command` {#generate-cli-command}

Generate CLI command from pyproject.toml configuration.

The `--generate-cli-command` flag reads your pyproject.toml configuration
and outputs the equivalent CLI command. This is useful for debugging
configuration issues or sharing commands with others.

**See also:** [pyproject.toml Configuration](../pyproject_toml.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --generate-cli-command # (1)!
    ```

    1. :material-arrow-left: `--generate-cli-command` - the option documented here

??? example "Examples"

    **Configuration (pyproject.toml):**

    ```toml
    [tool.datamodel-codegen]
    input = "schema.yaml"
    output = "model.py"
    ```

    **Output:**

    ```
    datamodel-codegen --input schema.yaml --output model.py
    ```

---

## `--generate-prompt` {#generate-prompt}

Generate a prompt for consulting LLMs about CLI options.

The `--generate-prompt` flag outputs a formatted prompt containing:
- Current CLI options
- Options organized by category with descriptions
- Full help text

This prompt can be copied to ChatGPT, Claude, or other LLMs to get
recommendations for appropriate CLI options.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --generate-prompt # (1)!
    ```

    1. :material-arrow-left: `--generate-prompt` - the option documented here

!!! info "Piping to CLI LLM Tools"

    You can pipe the generated prompt directly to CLI-based LLM tools:

    **Claude Code (Anthropic CLI):**
    ```bash
    datamodel-codegen --generate-prompt "How do I generate strict types?" | claude
    ```

    **Codex (OpenAI CLI):**
    ```bash
    datamodel-codegen --generate-prompt "Best options for Pydantic v2?" | codex
    ```

!!! info "Copying to Clipboard"

    Copy the prompt to clipboard for use with web-based LLM chats (ChatGPT, Claude, etc.):

    **macOS:**
    ```bash
    datamodel-codegen --generate-prompt | pbcopy
    ```

    **Linux (X11):**
    ```bash
    datamodel-codegen --generate-prompt | xclip -selection clipboard
    ```

    **Linux (Wayland):**
    ```bash
    datamodel-codegen --generate-prompt | wl-copy
    ```

    **Windows (PowerShell):**
    ```powershell
    datamodel-codegen --generate-prompt | Set-Clipboard
    ```

    **WSL2:**
    ```bash
    datamodel-codegen --generate-prompt | clip.exe
    ```

    After copying, paste into ChatGPT, Claude web, or any other LLM chat interface.

??? example "Examples"

    **Output:**

    ```
    # datamodel-code-generator CLI Options Consultation
    
    ## Current CLI Options
    
    ```
    (No options specified)
    ```
    
    ## Options by Category
    
    ### Base Options
    - `--encoding`: Specify character encoding for input and output files.
    - `--input`: Specify the input schema file path.
    - `--input-file-type`: Specify the input file type for code generation.
    - `--output`: Specify the destination path for generated Python code.
    - `--url`: Fetch schema from URL with custom HTTP headers.
    
    ### Typing Customization
    - `--allof-merge-mode`: Merge constraints from root model references in allOf schemas.
    - `--disable-future-imports`: Prevent automatic addition of __future__ imports in generated code.
    - `--enum-field-as-literal`: Convert all enum fields to Literal types instead of Enum classes.
    - `--ignore-enum-constraints`: Ignore enum constraints and use base string type instead of Enum classes.
    - `--no-use-specialized-enum`: Disable specialized Enum classes for Python 3.11+ code generation.
    - `--no-use-standard-collections`
    - `--no-use-union-operator`
    - `--output-date-class`: Specify date class type for date schema fields.
    - `--output-datetime-class`: Specify datetime class type for date-time schema fields.
    - `--strict-types`: Enable strict type validation for specified Python types.
    - `--type-mappings`: Override default type mappings for schema formats.
    - `--type-overrides`: Replace schema model types with custom Python types via JSON mapping.
    - `--use-annotated`: Test GraphQL annotated types with standard collections and union operator.
    - `--use-decimal-for-multiple-of`: Generate Decimal types for fields with multipleOf constraint.
    - `--use-generic-container-types`: Use typing.Dict/List instead of dict/list for container types.
    - `--use-non-positive-negative-number-constrained-types`: Use NonPositive/NonNegative types for number constraints.
    - `--use-pendulum`: Use pendulum types for date/time fields instead of datetime module.
    - `--use-root-model-type-alias`: Generate RootModel as type alias format for better mypy support (issue #1903).
    - `--use-standard-primitive-types`: Use Python standard library types for string formats instead of str.
    - `--use-tuple-for-fixed-items`: Generate tuple types for arrays with items array syntax.
    - `--use-type-alias`: Use TypeAlias instead of root models for type definitions (experimental).
    - `--use-unique-items-as-set`: Generate set types for arrays with uniqueItems constraint.
    
    ### Field Customization
    - `--aliases`: Test GraphQL annotated types with field aliases.
    - `--capitalize-enum-members`: Capitalize enum member names to UPPER_CASE format.
    - `--empty-enum-field-name`: Name for empty string enum field values.
    - `--extra-fields`: Configure how generated models handle extra fields not defined in schema.
    - `--field-constraints`: Generate Field() with validation constraints from schema.
    - `--field-extra-keys`: Include specific extra keys in Field() definitions.
    - `--field-extra-keys-without-x-prefix`: Include schema extension keys in Field() without requiring 'x-' prefix.
    - `--field-include-all-keys`: Include all schema keys in Field() json_schema_extra.
    - `--field-type-collision-strategy`: Rename type class instead of field when names collide (Pydantic v2 only).
    - `--no-alias`: Disable Field alias generation for non-Python-safe property names.
    - `--original-field-name-delimiter`: Specify delimiter for original field names when using snake-case conversion.
    - `--remove-special-field-name-prefix`: Remove the special prefix from field names.
    - `--set-default-enum-member`: Set the first enum member as the default value for enum fields.
    - `--snake-case-field`: Convert field names to snake_case format.
    - `--special-field-name-prefix`: Prefix to add to special field names (like reserved keywords).
    - `--use-attribute-docstrings`: Generate field descriptions as attribute docstrings instead of Field descriptions.
    - `--use-enum-values-in-discriminator`: Use enum values in discriminator mappings for union types.
    - `--use-field-description`: Include schema descriptions as Field docstrings.
    - `--use-inline-field-description`: Add field descriptions as inline comments.
    - `--use-schema-description`: Use schema description as class docstring.
    - `--use-title-as-name`: Use schema title as the generated class name.
    
    ### Model Customization
    - `--allow-extra-fields`: Allow extra fields in generated Pydantic models (extra='allow').
    - `--allow-population-by-field-name`: Allow Pydantic model population by field name (not just alias).
    - `--base-class`: Specify a custom base class for generated models.
    - `--base-class-map`: Test --base-class-map option for model-specific base classes.
    - `--class-name`: Override the auto-generated class name with a custom name.
    - `--collapse-reuse-models`: Collapse duplicate models by replacing references instead of inheritance.
    - `--collapse-root-models`: Inline root model definitions instead of creating separate wrapper classes.
    - `--dataclass-arguments`: Customize dataclass decorator arguments via JSON dictionary.
    - `--enable-faux-immutability`: Enable faux immutability in Pydantic v1 models (allow_mutation=False).
    - `--force-optional`: Force all fields to be Optional regardless of required status.
    - `--frozen-dataclasses`: Generate frozen dataclasses with optional keyword-only fields.
    - `--keep-model-order`: Keep model definition order as specified in schema.
    - `--keyword-only`: Generate dataclasses with keyword-only fields (Python 3.10+).
    - `--output-model-type`: Generate models from GraphQL with different output model types.
    - `--parent-scoped-naming`: Namespace models by their parent scope to avoid naming conflicts.
    - `--reuse-model`: Reuse identical model definitions instead of generating duplicates.
    - `--reuse-scope`: Scope for model reuse detection (root or tree).
    - `--skip-root-model`: Skip generation of root model when schema contains nested definitions.
    - `--strict-nullable`: Treat default field as a non-nullable field.
    - `--strip-default-none`: Remove fields with None as default value from generated models.
    - `--target-pydantic-version`: Target Pydantic version for generated code compatibility.
    - `--target-python-version`: Target Python version for generated code syntax and imports.
    - `--union-mode`: Union mode for combining anyOf/oneOf schemas (smart or left_to_right).
    - `--use-default`: Use default values from schema in generated models.
    - `--use-default-factory-for-optional-nested-models`: Generate default_factory for optional nested model fields.
    - `--use-default-kwarg`: Use default= keyword argument instead of positional argument for fields with defaults.
    - `--use-frozen-field`: Generate frozen (immutable) field definitions for readOnly properties.
    - `--use-generic-base-class`: Generate a shared base class with model configuration to avoid repetition (DRY).
    - `--use-one-literal-as-default`: Use single literal value as default when enum has only one option.
    - `--use-serialize-as-any`: Wrap fields with subtypes in Pydantic's SerializeAsAny.
    - `--use-subclass-enum`: Generate typed Enum subclasses for enums with specific field types.
    
    ### Template Customization
    - `--additional-imports`: Add custom imports to generated output files.
    - `--custom-file-header`: Add custom header text to the generated file.
    - `--custom-file-header-path`: Add custom header content from file to generated code.
    - `--custom-formatters`: Apply custom Python code formatters to generated output.
    - `--custom-formatters-kwargs`: Pass custom arguments to custom formatters via JSON file.
    - `--custom-template-dir`: Use custom Jinja2 templates for model generation.
    - `--disable-appending-item-suffix`: Disable appending 'Item' suffix to array item types.
    - `--disable-timestamp`: Disable timestamp in generated file header for reproducible output.
    - `--enable-command-header`: Include command-line options in file header for reproducibility.
    - `--enable-version-header`: Include tool version information in file header.
    - `--extra-template-data`: Pass custom template variables from JSON file for code generation.
    - `--formatters`: Specify code formatters to apply to generated output.
    - `--no-treat-dot-as-module`: Keep dots in schema names as underscores for flat output.
    - `--use-double-quotes`: Use double quotes for string literals in generated code.
    - `--use-exact-imports`: Import exact types instead of modules.
    - `--wrap-string-literal`: Wrap long string literals across multiple lines.
    
    ### OpenAPI-only Options
    - `--include-path-parameters`: Include OpenAPI path parameters in generated parameter models.
    - `--openapi-scopes`: Specify OpenAPI scopes to generate (schemas, paths, parameters).
    - `--read-only-write-only-model-type`: Generate separate request and response models for readOnly/writeOnly fields.
    - `--use-operation-id-as-name`: Use OpenAPI operationId as the generated function/class name.
    - `--use-status-code-in-response-name`: Include HTTP status code in response model names.
    - `--validation`: Enable validation constraints (deprecated, use --field-constraints).
    
    ### General Options
    - `--all-exports-collision-strategy`: Handle name collisions when exporting recursive module hierarchies.
    - `--all-exports-scope`: Generate __all__ exports for child modules in __init__.py files.
    - `--check`: Verify generated code matches existing output without modifying files.
    - `--disable-warnings`: Suppress warning messages during code generation.
    - `--generate-cli-command`: Generate CLI command from pyproject.toml configuration.
    - `--generate-prompt`: Generate a prompt for consulting LLMs about CLI options.
    - `--generate-pyproject-config`: Generate pyproject.toml configuration from CLI arguments.
    - `--http-headers`: Fetch schema from URL with custom HTTP headers.
    - `--http-ignore-tls`: Disable TLS certificate verification for HTTPS requests.
    - `--http-query-parameters`: Add query parameters to HTTP requests for remote schemas.
    - `--ignore-pyproject`: Ignore pyproject.toml configuration file.
    - `--module-split-mode`: Split generated models into separate files, one per model class.
    - `--shared-module-name`: Customize the name of the shared module for deduplicated models.
    - `--watch`: Watch mode cannot be used with --check mode.
    - `--watch-delay`: Watch mode starts file watcher and handles clean exit.
    
    ## All Available Options (Full Help)
    
    ```
    usage: 
      datamodel-codegen [options]
    
    Generate Python data models from schema definitions or structured data
    
    For detailed usage, see: https://koxudaxi.github.io/datamodel-code-generator
    
    [36;1mOptions[0m:
      --additional-imports ADDITIONAL_IMPORTS
                            Custom imports for output (delimited list input). For
                            example "datetime.date,datetime.datetime"
      --custom-formatters CUSTOM_FORMATTERS
                            List of modules with custom formatter (delimited list
                            input).
      --formatters {black,isort,ruff-check,ruff-format} [{black,isort,ruff-check,ruff-format} ...]
                            Formatters for output (default: [black, isort])
      --http-headers HTTP_HEADER [HTTP_HEADER ...]
                            Set headers in HTTP requests to the remote host.
                            (example: "Authorization: Basic dXNlcjpwYXNz")
      --http-ignore-tls     Disable verification of the remote host's TLS
                            certificate
      --http-query-parameters HTTP_QUERY_PARAMETERS [HTTP_QUERY_PARAMETERS ...]
                            Set query parameters in HTTP requests to the remote
                            host. (example: "ref=branch")
      --input INPUT         Input file/directory (default: stdin)
      --input-file-type {auto,openapi,jsonschema,json,yaml,dict,csv,graphql}
                            Input file type (default: auto)
      --output OUTPUT       Output file (default: stdout)
      --output-model-type {pydantic.BaseModel,pydantic_v2.BaseModel,pydantic_v2.dataclass,dataclasses.dataclass,typing.TypedDict,msgspec.Struct}
                            Output model type (default: pydantic.BaseModel)
      --url URL             Input file URL. `--input` is ignored when `--url` is
                            used
    
    [36;1mTyping customization[0m:
      --allof-merge-mode {constraints,all,none}
                            Mode for field merging in allOf schemas.
                            'constraints': merge only constraints (minItems,
                            maxItems, pattern, etc.) from parent (default). 'all':
                            merge constraints plus annotations (default, examples)
                            from parent. 'none': do not merge any fields from
                            parent properties.
      --base-class BASE_CLASS
                            Base Class (default: pydantic.BaseModel)
      --base-class-map BASE_CLASS_MAP
                            Model-specific base class mapping (JSON). Example:
                            '{"MyModel": "custom.BaseA", "OtherModel":
                            "custom.BaseB"}'. Priority: base-class-map >
                            customBasePath (in schema) > base-class.
      --disable-future-imports
                            Disable __future__ imports
      --enum-field-as-literal {all,one,none}
                            Parse enum field as literal. all: all enum field type
                            are Literal. one: field type is Literal when an enum
                            has only one possible value. none: always use Enum
                            class (never convert to Literal)
      --field-constraints   Use field constraints and not con* annotations
      --ignore-enum-constraints
                            Ignore enum constraints and use the base type (e.g.,
                            str, int) instead of generating Enum classes
      --set-default-enum-member
                            Set enum members as default values for enum field
      --strict-types {str,bytes,int,float,bool} [{str,bytes,int,float,bool} ...]
                            Use strict types
      --type-mappings TYPE_MAPPINGS [TYPE_MAPPINGS ...]
                            Override default type mappings. Format:
                            "type+format=target" (e.g., "string+binary=string" to
                            map binary format to string type) or "format=target"
                            (e.g., "binary=string"). Can be specified multiple
                            times.
      --type-overrides TYPE_OVERRIDES
                            Replace schema model types with custom Python types.
                            Format: JSON object mapping model names to Python
                            import paths. Model-level: '{"CustomType":
                            "my_app.types.MyType"}' replaces all references.
                            Scoped: '{"User.field": "my_app.Type"}' replaces
                            specific field only.
      --use-annotated       Use typing.Annotated for Field(). Also, `--field-
                            constraints` option will be enabled.
      --use-decimal-for-multiple-of
                            Use condecimal instead of confloat for float/number
                            fields with multipleOf constraint (Pydantic only).
                            Avoids floating-point precision issues in validation.
      --use-enum-values-in-discriminator
                            Use enum member literals in discriminator fields
                            instead of string literals
      --use-generic-container-types
                            Use generic container types for type hinting
                            (typing.Sequence, typing.Mapping). If `--use-standard-
                            collections` option is set, then import from
                            collections.abc instead of typing
      --use-non-positive-negative-number-constrained-types
                            Use the Non{Positive,Negative}{FloatInt} types instead
                            of the corresponding con* constrained types.
      --use-one-literal-as-default
                            Use one literal as default value for one literal field
      --use-root-model-type-alias
                            Use type alias format for RootModel (e.g., Foo =
                            RootModel[Bar]) instead of class inheritance (Pydantic
                            v2 only)
      --use-serialize-as-any
                            Use pydantic.SerializeAsAny for fields with types that
                            have subtypes (Pydantic v2 only)
      --use-specialized-enum, --no-use-specialized-enum
                            Use specialized Enum class (StrEnum, IntEnum).
                            Requires --target-python-version 3.11+
      --use-standard-collections, --no-use-standard-collections
                            Use standard collections for type hinting (list,
                            dict). Default: enabled
      --use-subclass-enum   Define generic Enum class as subclass with field type
                            when enum has type (int, float, bytes, str)
      --use-tuple-for-fixed-items
                            Generate tuple types for arrays with items array
                            syntax when minItems equals maxItems equals items
                            length
      --use-type-alias      Use TypeAlias instead of root models (experimental)
      --use-union-operator, --no-use-union-operator
                            Use | operator for Union type (PEP 604). Default:
                            enabled
      --use-unique-items-as-set
                            define field type as `set` when the field attribute
                            has `uniqueItems`
    
    [36;1mField customization[0m:
      --capitalise-enum-members, --capitalize-enum-members
                            Capitalize field names on enum
      --empty-enum-field-name EMPTY_ENUM_FIELD_NAME
                            Set field name when enum value is empty (default: `_`)
      --field-extra-keys FIELD_EXTRA_KEYS [FIELD_EXTRA_KEYS ...]
                            Add extra keys to field parameters
      --field-extra-keys-without-x-prefix FIELD_EXTRA_KEYS_WITHOUT_X_PREFIX [FIELD_EXTRA_KEYS_WITHOUT_X_PREFIX ...]
                            Add extra keys with `x-` prefix to field parameters.
                            The extra keys are stripped of the `x-` prefix.
      --field-include-all-keys
                            Add all keys to field parameters
      --field-type-collision-strategy {rename-field,rename-type}
                            Strategy for handling field name and type name
                            collisions (Pydantic v2 only). 'rename-field': rename
                            field with suffix and add alias (default). 'rename-
                            type': rename type class with suffix to preserve field
                            name.
      --force-optional      Force optional for required fields
      --no-alias            Do not add a field alias. E.g., if --snake-case-field
                            is used along with a base class, which has an
                            alias_generator
      --original-field-name-delimiter ORIGINAL_FIELD_NAME_DELIMITER
                            Set delimiter to convert to snake case. This option
                            only can be used with --snake-case-field (default: `_`
                            )
      --remove-special-field-name-prefix
                            Remove field name prefix if it has a special meaning
                            e.g. underscores
      --snake-case-field    Change camel-case field name to snake-case
      --special-field-name-prefix SPECIAL_FIELD_NAME_PREFIX
                            Set field name prefix when first character can't be
                            used as Python field name (default: `field`)
      --strict-nullable     Treat default field as a non-nullable field
      --strip-default-none  Strip default None on fields
      --union-mode {smart,left_to_right}
                            Union mode for only pydantic v2 field
      --use-attribute-docstrings
                            Set use_attribute_docstrings=True in Pydantic v2
                            ConfigDict
      --use-default         Use default value even if a field is required
      --use-default-factory-for-optional-nested-models
                            Use default_factory for optional nested model fields
                            instead of None default. E.g., `field: Model | None =
                            Field(default_factory=Model)` instead of `field: Model
                            | None = None`
      --use-default-kwarg   Use `default=` instead of a positional argument for
                            Fields that have default values.
      --use-field-description
                            Use schema description to populate field docstring
      --use-frozen-field    Use Field(frozen=True) for readOnly fields (Pydantic
                            v2) or Field(allow_mutation=False) (Pydantic v1)
      --use-inline-field-description
                            Use schema description to populate field docstring as
                            inline docstring
    
    [36;1mModel customization[0m:
      --all-exports-collision-strategy {error,minimal-prefix,full-prefix}
                            Strategy for name collisions when using --all-exports-
                            scope=recursive. 'error': raise an error (default).
                            'minimal-prefix': add module prefix only to colliding
                            names. 'full-prefix': add full module path prefix to
                            colliding names.
      --all-exports-scope {children,recursive}
                            Generate __all__ in __init__.py with re-exports.
                            'children': export from direct child modules only.
                            'recursive': export from all descendant modules.
      --allow-extra-fields  Deprecated: Allow passing extra fields. This flag is
                            deprecated. Use `--extra-fields=allow` instead.
      --allow-population-by-field-name
                            Allow population by field name
      --class-name CLASS_NAME
                            Set class name of root model
      --collapse-reuse-models
                            When used with --reuse-model, collapse duplicate
                            models by replacing references instead of creating
                            empty inheritance subclasses. This eliminates 'class
                            Foo(Bar): pass' patterns
      --collapse-root-models
                            Models generated with a root-type field will be merged
                            into the models using that root-type model
      --dataclass-arguments DATACLASS_ARGUMENTS
                            Custom dataclass arguments as a JSON dictionary, e.g.
                            '{"frozen": true, "kw_only": true}'. Overrides
                            --frozen-dataclasses and similar flags.
      --disable-appending-item-suffix
                            Disable appending `Item` suffix to model name in an
                            array
      --disable-timestamp   Disable timestamp on file headers
      --enable-command-header
                            Enable command-line options on file headers for
                            reproducibility
      --enable-faux-immutability
                            Enable faux immutability
      --enable-version-header
                            Enable package version on file headers
      --extra-fields {allow,ignore,forbid}
                            Set the generated models to allow, forbid, or ignore
                            extra fields.
      --frozen-dataclasses  Generate frozen dataclasses (dataclass(frozen=True)).
                            Only applies to dataclass output.
      --keep-model-order    Keep generated models' order
      --keyword-only        Defined models as keyword only (for example
                            dataclass(kw_only=True)).
      --module-split-mode {single}
                            Split generated models into separate files. 'single':
                            generate one file per model class.
      --output-date-class {date,PastDate,FutureDate}
                            Choose Date class between PastDate, FutureDate or
                            date. (Pydantic v2 only) Each output model has its
                            default mapping.
      --output-datetime-class {datetime,AwareDatetime,NaiveDatetime,PastDatetime,FutureDatetime}
                            Choose Datetime class between AwareDatetime,
                            NaiveDatetime, PastDatetime, FutureDatetime or
                            datetime. Each output model has its default mapping
                            (for example pydantic: datetime, dataclass: str, ...)
      --parent-scoped-naming
                            Set name of models defined inline from the parent
                            model
      --reuse-model         Reuse models on the field when a module has the model
                            with the same content
      --reuse-scope {module,tree}
                            Scope for model reuse deduplication: module (per-file,
                            default) or tree (cross-file with shared module). Only
                            effective when --reuse-model is set.
      --shared-module-name SHARED_MODULE_NAME
                            Name of the shared module for --reuse-scope=tree
                            (default: "shared"). Use this option if your schema
                            has a file named "shared".
      --skip-root-model     Skip generating the model for the root schema element
      --target-pydantic-version {2,2.11}
                            Target Pydantic version for generated code. '2':
                            Pydantic 2.0+ compatible (default, uses
                            populate_by_name). '2.11': Pydantic 2.11+ (uses
                            validate_by_name).
      --target-python-version {3.10,3.11,3.12,3.13,3.14}
                            target python version
      --treat-dot-as-module, --no-treat-dot-as-module
                            Treat dotted schema names as module paths, creating
                            nested directory structures (e.g., 'foo.bar.Model'
                            becomes 'foo/bar.py'). Use --no-treat-dot-as-module to
                            keep dots in names as underscores for single-file
                            output.
      --use-exact-imports   import exact types instead of modules, for example:
                            "from .foo import Bar" instead of "from . import foo"
                            with "foo.Bar"
      --use-generic-base-class
                            Generate a shared base class with model configuration
                            (e.g., extra='forbid') instead of repeating the
                            configuration in each model. Keeps code DRY.
      --use-pendulum        use pendulum instead of datetime
      --use-schema-description
                            Use schema description to populate class docstring
      --use-standard-primitive-types
                            Use Python standard library types for string formats
                            (UUID, IPv4Address, etc.) instead of str. Affects
                            dataclass, msgspec, TypedDict output. Pydantic already
                            uses these types by default.
      --use-title-as-name   use titles as class names of models
    
    [36;1mTemplate customization[0m:
      --aliases ALIASES     Alias mapping file (JSON) for renaming fields.
                            Supports hierarchical formats: Flat: {'field':
                            'alias'} applies to all occurrences. Scoped:
                            {'ClassName.field': 'alias'} applies to specific
                            class. Priority: scoped > flat. Example: {'User.name':
                            'user_name', 'Address.name': 'addr_name', 'id': 'id_'}
      --custom-file-header CUSTOM_FILE_HEADER
                            Custom file header
      --custom-file-header-path CUSTOM_FILE_HEADER_PATH
                            Custom file header file path
      --custom-formatters-kwargs CUSTOM_FORMATTERS_KWARGS
                            A file with kwargs for custom formatters.
      --custom-template-dir CUSTOM_TEMPLATE_DIR
                            Custom template directory
      --encoding ENCODING   The encoding of input and output (default: UTF-8)
      --extra-template-data EXTRA_TEMPLATE_DATA
                            Extra template data for output models. Input is
                            supposed to be a json/yaml file. For OpenAPI and
                            Jsonschema the keys are the spec path of the object,
                            or the name of the object if you want to apply the
                            template data to multiple objects with the same name.
                            If you are using another input file type (e.g.
                            GraphQL), the key is the name of the object. The value
                            is a dictionary of the template data to add.
      --use-double-quotes   Model generated with double quotes. Single quotes or
                            your black config skip_string_normalization value will
                            be used without this option.
      --wrap-string-literal
                            Wrap string literal by using black `experimental-
                            string-processing` option (require black 20.8b0 or
                            later)
    
    [36;1mOpenAPI-only options[0m:
      --include-path-parameters
                            Include path parameters in generated parameter models
                            in addition to query parameters (Only OpenAPI)
      --openapi-scopes {schemas,paths,tags,parameters,webhooks,requestbodies} [{schemas,paths,tags,parameters,webhooks,requestbodies} ...]
                            Scopes of OpenAPI model generation (default: schemas)
      --read-only-write-only-model-type {request-response,all}
                            Model generation for readOnly/writeOnly fields:
                            'request-response' = Request/Response models only (no
                            base model), 'all' = Base + Request + Response models.
      --use-operation-id-as-name
                            use operation id of OpenAPI as class names of models
      --use-status-code-in-response-name
                            Include HTTP status code in response model names
                            (e.g., ResourceGetResponse200,
                            ResourceGetResponseDefault)
      --validation          Deprecated: Enable validation (Only OpenAPI). this
                            option is deprecated. it will be removed in future
                            releases
    
    [36;1mGeneral options[0m:
      --check               Verify generated files are up-to-date without
                            modifying them. Exits with code 1 if differences
                            found, 0 if up-to-date. Useful for CI to ensure
                            generated code is committed.
      --debug               show debug message (require "debug". `$ pip install
                            'datamodel-code-generator[debug]'`)
      --disable-warnings    disable warnings
      --generate-cli-command
                            Generate CLI command from pyproject.toml configuration
                            and exit
      --generate-prompt [QUESTION]
                            Generate a prompt for consulting LLMs about CLI
                            options. Optionally provide your question as an
                            argument.
      --generate-pyproject-config
                            Generate pyproject.toml configuration from the
                            provided CLI arguments and exit
      --ignore-pyproject    Ignore pyproject.toml configuration
      --no-color            disable colorized output
      --profile PROFILE     Use a named profile from pyproject.toml
                            [tool.datamodel-codegen.profiles.<name>]
      --version             show version
      --watch               Watch input file(s) for changes and regenerate output
                            automatically
      --watch-delay WATCH_DELAY
                            Debounce delay in seconds for watch mode (default:
                            0.5)
      -h, --help            show this help message and exit
    
    Documentation: https://koxudaxi.github.io/datamodel-code-generator
    GitHub: https://github.com/koxudaxi/datamodel-code-generator
    
    ```
    
    ## Instructions
    
    Based on the above information, please help with the question or suggest
    appropriate CLI options for the use case. Consider:
    
    1. The current options already set
    2. Option descriptions and their purposes
    3. Potential conflicts between options
    4. Best practices for the target output format
    ```

---

## `--generate-pyproject-config` {#generate-pyproject-config}

Generate pyproject.toml configuration from CLI arguments.

The `--generate-pyproject-config` flag outputs a pyproject.toml configuration
snippet based on the provided CLI arguments. This is useful for converting
a working CLI command into a reusable configuration file.

**See also:** [pyproject.toml Configuration](../pyproject_toml.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --generate-pyproject-config --input schema.yaml --output model.py # (1)!
    ```

    1. :material-arrow-left: `--generate-pyproject-config` - the option documented here

??? example "Examples"

    **Output:**

    ```
    [tool.datamodel-codegen]
    input = "schema.yaml"
    output = "model.py"
    ```

---

## `--http-headers` {#http-headers}

Fetch schema from URL with custom HTTP headers.

The `--url` flag specifies a remote URL to fetch the schema from instead of
a local file. The `--http-headers` flag adds custom HTTP headers to the request,
useful for authentication (e.g., Bearer tokens) or custom API requirements.
Format: `HeaderName:HeaderValue`.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --url https://api.example.com/schema.json --http-headers "Authorization:Bearer token" # (1)!
    ```

    1. :material-arrow-left: `--http-headers` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Pet",
      "type": "object",
      "properties": {
        "id": {
          "type": "integer"
        },
        "name": {
          "type": "string"
        },
        "tag": {
          "type": "string"
        }
      }
    }
    ```

    **Output:**

    ```python
    # generated by datamodel-codegen:
    #   filename:  https://api.example.com/schema.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    
    class Pet(BaseModel):
        id: int | None = None
        name: str | None = None
        tag: str | None = None
    ```

---

## `--http-ignore-tls` {#http-ignore-tls}

Disable TLS certificate verification for HTTPS requests.

The `--http-ignore-tls` flag disables SSL/TLS certificate verification
when fetching schemas from HTTPS URLs. This is useful for development
environments with self-signed certificates. Not recommended for production.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --url https://api.example.com/schema.json --http-ignore-tls # (1)!
    ```

    1. :material-arrow-left: `--http-ignore-tls` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Pet",
      "type": "object",
      "properties": {
        "id": {
          "type": "integer"
        },
        "name": {
          "type": "string"
        },
        "tag": {
          "type": "string"
        }
      }
    }
    ```

    **Output:**

    ```python
    # generated by datamodel-codegen:
    #   filename:  https://api.example.com/schema.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    
    class Pet(BaseModel):
        id: int | None = None
        name: str | None = None
        tag: str | None = None
    ```

---

## `--http-query-parameters` {#http-query-parameters}

Add query parameters to HTTP requests for remote schemas.

The `--http-query-parameters` flag adds query parameters to HTTP requests
when fetching schemas from URLs. Useful for APIs that require version
or format parameters. Format: `key=value`. Multiple parameters can be
specified: `--http-query-parameters version=v2 format=json`.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --url https://api.example.com/schema.json --http-query-parameters version=v2 format=json # (1)!
    ```

    1. :material-arrow-left: `--http-query-parameters` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Pet",
      "type": "object",
      "properties": {
        "id": {
          "type": "integer"
        },
        "name": {
          "type": "string"
        },
        "tag": {
          "type": "string"
        }
      }
    }
    ```

    **Output:**

    ```python
    # generated by datamodel-codegen:
    #   filename:  https://api.example.com/schema.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    
    class Pet(BaseModel):
        id: int | None = None
        name: str | None = None
        tag: str | None = None
    ```

---

## `--ignore-pyproject` {#ignore-pyproject}

Ignore pyproject.toml configuration file.

The `--ignore-pyproject` flag tells datamodel-codegen to ignore any
[tool.datamodel-codegen] configuration in pyproject.toml. This is useful
when you want to override project defaults with CLI arguments, or when
testing without project configuration.

**See also:** [pyproject.toml Configuration](../pyproject_toml.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --ignore-pyproject # (1)!
    ```

    1. :material-arrow-left: `--ignore-pyproject` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "firstName": {"type": "string"},
        "lastName": {"type": "string"}
      }
    }
    ```

    **Output:**

    === "With Option"

        ```python
        # generated by datamodel-codegen:
        #   filename:  schema.json
        
        from __future__ import annotations
        
        from pydantic import BaseModel
        
        
        class Model(BaseModel):
            firstName: str | None = None
            lastName: str | None = None
        ```

    === "Without Option"

        ```python
        # generated by datamodel-codegen:
        #   filename:  schema.json
        
        from __future__ import annotations
        
        from pydantic import BaseModel, Field
        
        
        class Model(BaseModel):
            first_name: str | None = Field(None, alias='firstName')
            last_name: str | None = Field(None, alias='lastName')
        ```

---

## `--module-split-mode` {#module-split-mode}

Split generated models into separate files, one per model class.

The `--module-split-mode=single` flag generates each model class in its own file,
named after the class in snake_case. Use with `--all-exports-scope=recursive` to
create an __init__.py that re-exports all models for convenient imports.

**Related:** [`--all-exports-scope`](general-options.md#all-exports-scope), [`--use-exact-imports`](template-customization.md#use-exact-imports)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --module-split-mode single --all-exports-scope recursive --use-exact-imports # (1)!
    ```

    1. :material-arrow-left: `--module-split-mode` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "definitions": {
        "User": {
          "type": "object",
          "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"}
          }
        },
        "Order": {
          "type": "object",
          "properties": {
            "id": {"type": "integer"},
            "user": {"$ref": "#/definitions/User"}
          }
        }
      }
    }
    ```

    **Output:**

    ```python
    # __init__.py
    # generated by datamodel-codegen:
    #   filename:  input.json
    
    from __future__ import annotations
    
    from .model import Model
    from .order import Order
    from .user import User
    
    __all__ = [
        "Model",
        "Order",
        "User",
    ]
    
    # model.py
    # generated by datamodel-codegen:
    #   filename:  input.json
    
    from __future__ import annotations
    
    from typing import Any
    
    from pydantic import BaseModel
    
    
    class Model(BaseModel):
        __root__: Any
    
    # order.py
    # generated by datamodel-codegen:
    #   filename:  input.json
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    from .user import User
    
    
    class Order(BaseModel):
        id: int | None = None
        user: User | None = None
    
    # user.py
    # generated by datamodel-codegen:
    #   filename:  input.json
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    
    class User(BaseModel):
        id: int | None = None
        name: str | None = None
    ```

---

## `--shared-module-name` {#shared-module-name}

Customize the name of the shared module for deduplicated models.

The `--shared-module-name` flag sets the name of the shared module created
when using `--reuse-model` with `--reuse-scope=tree`. This module contains
deduplicated models that are referenced from multiple files. Default is
`shared`. Use this if your schema already has a file named `shared`.

Note: This option only affects modular output with tree-level model reuse.

**See also:** [Model Reuse and Deduplication](../model-reuse.md)

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --shared-module-name my_shared # (1)!
    ```

    1. :material-arrow-left: `--shared-module-name` - the option documented here

??? example "Examples"

    **Input Schema:**

    ```json
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Pet",
      "type": "object",
      "properties": {
        "id": {
          "type": "integer"
        },
        "name": {
          "type": "string"
        },
        "tag": {
          "type": "string"
        }
      }
    }
    ```

    **Output:**

    ```python
    # generated by datamodel-codegen:
    #   filename:  pet_simple.json
    #   timestamp: 2019-07-26T00:00:00+00:00
    
    from __future__ import annotations
    
    from pydantic import BaseModel
    
    
    class Pet(BaseModel):
        id: int | None = None
        name: str | None = None
        tag: str | None = None
    ```

---

## `--watch` {#watch}

Watch mode cannot be used with --check mode.

The `--watch` flag enables file watching for automatic regeneration.
It cannot be combined with `--check` since check mode requires a single
comparison, not continuous watching.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --watch --check # (1)!
    ```

    1. :material-arrow-left: `--watch` - the option documented here

??? example "Examples"

    === "JSON Schema"

        **Input Schema:**

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

        **Output:**

        ```
        Error: --watch and --check cannot be used together
        ```

    === "unknown"

        **Output:**

        ```
        Error: --watch requires --input file path
        ```

---

## `--watch-delay` {#watch-delay}

Watch mode starts file watcher and handles clean exit.

The `--watch` flag starts a file watcher that monitors the input file
or directory for changes. The `--watch-delay` option sets the debounce
delay in seconds (default: 0.5) to prevent multiple regenerations for
rapid file changes. Press Ctrl+C to stop watching.

!!! tip "Usage"

    ```bash
    datamodel-codegen --input schema.json --watch --watch-delay 1.5 # (1)!
    ```

    1. :material-arrow-left: `--watch-delay` - the option documented here

??? example "Examples"

    **Input Schema:**

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

    **Output:**

    ```
    Watching
    ```

---

