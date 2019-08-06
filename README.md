# datamodel-code-generator

This code generator creates pydantic mode from an openapi file.

[![Build Status](https://travis-ci.org/koxudaxi/datamodel-code-generator.svg?branch=master)](https://travis-ci.org/koxudaxi/datamodel-code-generator)
[![PyPI version](https://badge.fury.io/py/datamodel-code-generator.svg)](https://badge.fury.io/py/datamodel-code-generator)
[![codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/branch/master/graph/badge.svg)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)


## This project is an experimental phase.

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

optional arguments:
  -h, --help            show this help message and exit
  --input INPUT         Open API YAML file
  --output OUTPUT       Output file
  --base-class BASE_CLASS
                        Base Class
```

## Example

```sh
$ datamodel-codegen --input api.yaml --output model.py
```


`api.yaml`:
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

`model.py`:
```python
# generated by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2019-07-23T14:23:18+00:00

from typing import List, Optional

from pydantic import BaseModel



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
