# datamodel-code-generator

This code generator creates pydantic model from an openapi file.

[![Build Status](https://travis-ci.org/koxudaxi/datamodel-code-generator.svg?branch=master)](https://travis-ci.org/koxudaxi/datamodel-code-generator)
[![PyPI version](https://badge.fury.io/py/datamodel-code-generator.svg)](https://badge.fury.io/py/datamodel-code-generator)
[![codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/branch/master/graph/badge.svg)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)


## This project is an experimental phase.


## Supported file formats
- OpenAPI 3 (yaml/json)


## Implemented list
### OpenAPI 3
#### DataType
- string (include patter/minLength/maxLenght)
- number (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
- integer (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
- boolean
- array
- object

##### String Fromat 
- date
- datetime
- password
- email
- uuid (uuid1/uuid2/uuid3/uuid4/uuid5)
- ipv4
- ipv6
#### Other schema
- enum
- allOf (as Multiple inheritance)
- anyOf (as Union)
- $ref (only one file)


## Installation

To install `datamodel-code-generator`:
```sh
$ pip install datamodel-code-generator
```

## Usage

The `datamodel-codegen` command:
```
usage: datamodel-codegen [-h] [--input INPUT] [--output OUTPUT]
                         [--base-class BASE_CLASS]
                         [--custom-template-dir CUSTOM_TEMPLATE_DIR]
                         [--extra-template-data EXTRA_TEMPLATE_DATA]
                         [--target-python-version {3.6,3.7}] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Open API YAML file (default: stdin)
  --output OUTPUT       Output file (default: stdout)
  --base-class BASE_CLASS
                        Base Class (default: pydantic.BaseModel)
  --custom-template-dir CUSTOM_TEMPLATE_DIR
                        Custom Template Directory
  --extra-template-data EXTRA_TEMPLATE_DATA
                        Extra Template Data
  --target-python-version {3.6,3.7}
                        target python version (default: 3.7)
  --debug               show debug message
```

## Example

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
#   timestamp: 2019-09-26T01:04:25+00:00

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, UrlStr


class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet]


class Error(BaseModel):
    code: int
    message: str


class api(BaseModel):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None
    apiUrl: Optional[UrlStr] = None
    apiDocumentationUrl: Optional[UrlStr] = None


class apis(BaseModel):
    __root__: List[api]
```

## Development

Install the package in editable mode:

```sh
$ git clone git@github.com:koxudaxi/datamodel-code-generator.git
$ pip install -e datamodel-code-generator
```

## PyPi 

[https://pypi.org/project/datamodel-code-generator](https://pypi.org/project/datamodel-code-generator)

## Source Code

[https://github.com/koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator)

## Documentation

[https://koxudaxi.github.io/datamodel-code-generator](https://koxudaxi.github.io/datamodel-code-generator)

## License

datamodel-code-generator is released under the MIT License. http://www.opensource.org/licenses/mit-license
