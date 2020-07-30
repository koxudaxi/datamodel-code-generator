# datamodel-code-generator

This code generator creates pydantic model from an openapi file and others.

[![Build Status](https://travis-ci.org/koxudaxi/datamodel-code-generator.svg?branch=master)](https://travis-ci.org/koxudaxi/datamodel-code-generator)
[![PyPI version](https://badge.fury.io/py/datamodel-code-generator.svg)](https://pypi.python.org/pypi/datamodel-code-generator)
[![Downloads](https://pepy.tech/badge/datamodel-code-generator/month)](https://pepy.tech/project/datamodel-code-generator/month)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/datamodel-code-generator)](https://pypi.python.org/pypi/datamodel-code-generator)
[![codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/branch/master/graph/badge.svg)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)
![license](https://img.shields.io/github/license/koxudaxi/datamodel-code-generator.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Help
See [documentation](https://koxudaxi.github.io/datamodel-code-generator) for more details.


## Supported source types
- OpenAPI 3 (YAML/JSON)
- JSON Schema
- JSON/YAML Data (it will be converted to JSON Schema)

## Implemented list
### OpenAPI 3 and JsonSchema
#### DataType
- string (include patter/minLength/maxLenght)
- number (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
- integer (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
- boolean
- array
- object

##### String Format 
- date
- datetime
- password
- email
- uuid (uuid1/uuid2/uuid3/uuid4/uuid5)
- ipv4
- ipv6
- hostname
- decimal

#### Other schema
- enum
- allOf (as Multiple inheritance)
- anyOf (as Union)
- oneOf (as Union)
- $ref ([http extra](#http-extra-option) is required when resolving $ref for remote files.)


## Installation

To install `datamodel-code-generator`:
```bash
$ pip install datamodel-code-generator
```

### `http` extra option
If you want to resolve `$ref` for remote files then you should specify `http` extra option.
```bash
$ pip install datamodel-code-generator[http]
```

## Usage

The `datamodel-codegen` command:
```
usage: datamodel-codegen [-h] [--input INPUT]
                         [--input-file-type {auto,openapi,jsonschema,json,yaml}]
                         [--output OUTPUT] [--base-class BASE_CLASS]
                         [--field-constraints] [--snake-case-field]
                         [--strip-default-none]
                         [--custom-template-dir CUSTOM_TEMPLATE_DIR]
                         [--extra-template-data EXTRA_TEMPLATE_DATA]
                         [--aliases ALIASES]
                         [--target-python-version {3.6,3.7}] [--validation]
                         [--debug] [--version]

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Input file (default: stdin)
  --input-file-type {auto,openapi,jsonschema,json,yaml}
                        Input file type (default: auto)
  --output OUTPUT       Output file (default: stdout)
  --base-class BASE_CLASS
                        Base Class (default: pydantic.BaseModel)
  --field-constraints   Use field constraints and not con* annotations
  --snake-case-field    Change camel-case field name to snake-case
  --strip-default-none  Strip default None on fields
  --custom-template-dir CUSTOM_TEMPLATE_DIR
                        Custom template directory
  --extra-template-data EXTRA_TEMPLATE_DATA
                        Extra template data
  --aliases ALIASES     Alias mapping file
  --target-python-version {3.6,3.7}
                        target python version (default: 3.7)
  --validation          Enable validation (Only OpenAPI)
  --debug               show debug message
  --version             show version
```

## Example
### OpenAPI
```sh
$ datamodel-codegen --input api.yaml --output model.py
```

<details>
<summary>api.yaml</summary>
<pre>
<code>
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
        name:
          type: string
        tag:
          type: string
    Pets:
      type: array
      items:
        $ref: "#/components/schemas/Pet"
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
            description: "The URL describing the dataset's fields"
          apiDocumentationUrl:
            type: string
            format: uri
            description: A URL to the API console for each API
```
</code>
</pre>
</details>

`model.py`:
```python
# generated by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2020-06-02T05:28:24+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import AnyUrl, BaseModel, Field


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


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
```


## PyPi 

[https://pypi.org/project/datamodel-code-generator](https://pypi.org/project/datamodel-code-generator)

## License

datamodel-code-generator is released under the MIT License. http://www.opensource.org/licenses/mit-license


## This project is an experimental phase.
