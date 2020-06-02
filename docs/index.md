# datamodel-code-generator

This code generator creates pydantic model from an openapi file and others.

[![Build Status](https://travis-ci.org/koxudaxi/datamodel-code-generator.svg?branch=master)](https://travis-ci.org/koxudaxi/datamodel-code-generator)
[![PyPI version](https://badge.fury.io/py/datamodel-code-generator.svg)](https://pypi.python.org/pypi/datamodel-code-generator)
[![Downloads](https://pepy.tech/badge/datamodel-code-generator/month)](https://pepy.tech/project/datamodel-code-generator/month)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/datamodel-code-generator)](https://pypi.python.org/pypi/datamodel-code-generator)
[![codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/branch/master/graph/badge.svg)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)
![license](https://img.shields.io/github/license/koxudaxi/datamodel-code-generator.svg)


## Supported source types
- OpenAPI 3 (YAML/JSON)
- JSON Schema
- JSON/YAML Data (it will be converted to JSON Schema)

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
                         [--validation Enable validation (Only OpenAPI)]
                         [--version]

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Input file (default: stdin)
  --input-file-type {auto,openapi,jsonscehma,json,yaml}
  --output OUTPUT       Output file (default: stdout)
  --base-class BASE_CLASS
                        Base Class (default: pydantic.BaseModel)
  --custom-template-dir CUSTOM_TEMPLATE_DIR
                        Custom Template Directory
  --extra-template-data EXTRA_TEMPLATE_DATA
                        Extra Template Data
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

## Source Code

[https://github.com/koxudaxi/datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator)

## License

datamodel-code-generator is released under the MIT License. http://www.opensource.org/licenses/mit-license

## This project is an experimental phase.
