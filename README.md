# datamodel-code-generator

This code generator creates [pydantic](https://docs.pydantic.dev/) model and [dataclasses.dataclass](https://docs.python.org/3/library/dataclasses.html) from an openapi file and others.

[![Build Status](https://github.com/koxudaxi/datamodel-code-generator/workflows/Test/badge.svg)](https://github.com/koxudaxi/datamodel-code-generator/actions?query=workflow%3ATest)
[![PyPI version](https://badge.fury.io/py/datamodel-code-generator.svg)](https://pypi.python.org/pypi/datamodel-code-generator)
[![Downloads](https://pepy.tech/badge/datamodel-code-generator/month)](https://pepy.tech/project/datamodel-code-generator)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/datamodel-code-generator)](https://pypi.python.org/pypi/datamodel-code-generator)
[![codecov](https://codecov.io/gh/koxudaxi/datamodel-code-generator/branch/master/graph/badge.svg)](https://codecov.io/gh/koxudaxi/datamodel-code-generator)
![license](https://img.shields.io/github/license/koxudaxi/datamodel-code-generator.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## Help
See [documentation](https://koxudaxi.github.io/datamodel-code-generator) for more details.

## Sponsors
[![JetBrains](https://avatars.githubusercontent.com/u/60931315?s=200&v=4)](https://github.com/JetBrainsOfficial)

## Quick Installation

To install `datamodel-code-generator`:
```bash
$ pip install datamodel-code-generator
```

## Simple usage
You can generate models from a local file.
```bash
$ datamodel-codegen --input api.yaml --output model.py
```

<details>
<summary>api.yaml</summary>

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

</details>

<details>
<summary>model.py</summary>

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
</details>

## Which project uses it?
These OSS use datamodel-code-generator to generate many models. We can learn about use-cases from these projects.
- [Netflix/consoleme](https://github.com/Netflix/consoleme)
  - *[How do I generate models from the Swagger specification?](https://github.com/Netflix/consoleme/blob/master/docs/gitbook/faq.md#how-do-i-generate-models-from-the-swagger-specification)*
- [DataDog/integrations-core](https://github.com/DataDog/integrations-core)
  - *[Config models](https://github.com/DataDog/integrations-core/blob/master/docs/developer/meta/config-models.md)*
- [awslabs/aws-lambda-powertools-python](https://github.com/awslabs/aws-lambda-powertools-python)
  - *Not used. But, introduced [advanced-use-cases](https://awslabs.github.io/aws-lambda-powertools-python/2.6.0/utilities/parser/#advanced-use-cases) in the official document*
- [open-metadata/OpenMetadata](https://github.com/open-metadata/OpenMetadata)
  - [Makefile](https://github.com/open-metadata/OpenMetadata/blob/main/Makefile)
- [airbytehq/airbyte](https://github.com/airbytehq/airbyte)
  - *[code-generator/Dockerfile](https://github.com/airbytehq/airbyte/blob/master/tools/code-generator/Dockerfile)*
- [IBM/compliance-trestle](https://github.com/IBM/compliance-trestle)
  - *[Building the models from the OSCAL schemas.](https://github.com/IBM/compliance-trestle/blob/develop/docs/contributing/website.md#building-the-models-from-the-oscal-schemas)*
- [SeldonIO/MLServer](https://github.com/SeldonIO/MLServer)
  - *[generate-types.sh](https://github.com/SeldonIO/MLServer/blob/master/hack/generate-types.sh)*
## Supported input types
-  OpenAPI 3 (YAML/JSON, [OpenAPI Data Type](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#data-types))
-  JSON Schema ([JSON Schema Core](http://json-schema.org/draft/2019-09/json-schema-validation.html)/[JSON Schema Validation](http://json-schema.org/draft/2019-09/json-schema-validation.html))
-  JSON/YAML/CSV Data (it will be converted to JSON Schema)
-  Python dictionary (it will be converted to JSON Schema)

## Supported output types
- [pydantic](https://docs.pydantic.dev/).BaseModel
- [dataclasses.dataclass](https://docs.python.org/3/library/dataclasses.html)

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

### Docker Image
The docker image is in [Docker Hub](https://hub.docker.com/r/koxudaxi/datamodel-code-generator)
```bash
$ docker pull koxudaxi/datamodel-code-generator
```

## Advanced Uses
You can genearte models from a URL.
```bash
$ datamodel-codegen --url https://<INPUT FILE URL> --output model.py
```
This method needs  [http extra option](#http-extra-option)


## All Command Options

The `datamodel-codegen` command:
```bash
usage: datamodel-codegen [-h] [--input INPUT] [--url URL]
                         [--http-headers HTTP_HEADER [HTTP_HEADER ...]]
                         [--http-ignore-tls]
                         [--input-file-type {auto,openapi,jsonschema,json,yaml,dict,csv}]
                         [--output-model-type {pydantic.BaseModel,dataclasses.dataclass}]
                         [--openapi-scopes {schemas,paths,tags,parameters} [{schemas,paths,tags,parameters} ...]]
                         [--output OUTPUT] [--base-class BASE_CLASS]
                         [--field-constraints] [--use-annotated]
                         [--use-non-positive-negative-number-constrained-types]
                         [--field-extra-keys FIELD_EXTRA_KEYS [FIELD_EXTRA_KEYS ...]]
                         [--field-include-all-keys]
                         [--field-extra-keys-without-x-prefix FIELD_EXTRA_KEYS_WITHOUT_X_PREFIX [FIELD_EXTRA_KEYS_WITHOUT_X_PREFIX ...]] 
                         [--snake-case-field]
                         [--original-field-name-delimiter ORIGINAL_FIELD_NAME_DELIMITER]
                         [--strip-default-none]
                         [--disable-appending-item-suffix]
                         [--allow-population-by-field-name]
                         [--allow-extra-fields] [--enable-faux-immutability]
                         [--use-default] [--force-optional]
                         [--strict-nullable]
                         [--strict-types {str,bytes,int,float,bool} [{str,bytes,int,float,bool} ...]]
                         [--disable-timestamp] [--use-standard-collections]
                         [--use-generic-container-types]
                         [--use-union-operator] [--use-schema-description]
                         [--use-field-description] [--use-default-kwarg]
                         [--reuse-model] [--keep-model-order]
                         [--collapse-root-models]
                         [--enum-field-as-literal {all,one}]
                         [--set-default-enum-member]
                         [--empty-enum-field-name EMPTY_ENUM_FIELD_NAME]
                         [--capitalise-enum-members]
                         [--special-field-name-prefix SPECIAL_FIELD_NAME_PREFIX]
                         [--remove-special-field-name-prefix]
                         [--use-subclass-enum] [--class-name CLASS_NAME]
                         [--use-title-as-name]
                         [--custom-template-dir CUSTOM_TEMPLATE_DIR]
                         [--extra-template-data EXTRA_TEMPLATE_DATA]
                         [--aliases ALIASES]
                         [--target-python-version {3.6,3.7,3.8,3.9,3.10,3.11}]
                         [--wrap-string-literal] [--validation]
                         [--use-double-quotes] [--encoding ENCODING] [--debug]
                         [--disable-warnings] [--version]

options:
  -h, --help            show this help message and exit
  --input INPUT         Input file/directory (default: stdin)
  --url URL             Input file URL. `--input` is ignored when `--url` is
                        used
  --http-headers HTTP_HEADER [HTTP_HEADER ...]
                        Set headers in HTTP requests to the remote host.
                        (example: "Authorization: Basic dXNlcjpwYXNz")
  --http-ignore-tls     Disable verification of the remote host's TLS
                        certificate
  --input-file-type {auto,openapi,jsonschema,json,yaml,dict,csv}
                        Input file type (default: auto)
  --output-model-type {pydantic.BaseModel,dataclasses.dataclass}
                        Output model type (default: pydantic.BaseModel)
  --openapi-scopes {schemas,paths,tags,parameters} [{schemas,paths,tags,parameters} ...]
                        Scopes of OpenAPI model generation (default: schemas)
  --output OUTPUT       Output file (default: stdout)
  --base-class BASE_CLASS
                        Base Class (default: pydantic.BaseModel)
  --field-constraints   Use field constraints and not con* annotations
  --use-annotated       Use typing.Annotated for Field(). Also, `--field-
                        constraints` option will be enabled.
  --use-non-positive-negative-number-constrained-types
                        Use the Non{Positive,Negative}{FloatInt} types instead
                        of the corresponding con* constrained types.
  --field-extra-keys FIELD_EXTRA_KEYS [FIELD_EXTRA_KEYS ...]
                        Add extra keys to field parameters
  --field-include-all-keys
                        Add all keys to field parameters
  --field-extra-keys-without-x-prefix
                        Add extra keys with `x-` prefix to field parameters.
                        The extra keys are stripped of the `x-` prefix.
  --snake-case-field    Change camel-case field name to snake-case
  --original-field-name-delimiter ORIGINAL_FIELD_NAME_DELIMITER
                        Set delimiter to convert to snake case. This option
                        only can be used with --snake-case-field (default: `_`
                        )
  --strip-default-none  Strip default None on fields
  --disable-appending-item-suffix
                        Disable appending `Item` suffix to model name in an
                        array
  --allow-population-by-field-name
                        Allow population by field name
  --allow-extra-fields  Allow to pass extra fields, if this flag is not
                        passed, extra fields are forbidden.
  --enable-faux-immutability
                        Enable faux immutability
  --use-default         Use default value even if a field is required
  --force-optional      Force optional for required fields
  --strict-nullable     Treat default field as a non-nullable field (Only
                        OpenAPI)
  --strict-types {str,bytes,int,float,bool} [{str,bytes,int,float,bool} ...]
                        Use strict types
  --disable-timestamp   Disable timestamp on file headers
  --use-standard-collections
                        Use standard collections for type hinting (list, dict)
  --use-generic-container-types
                        Use generic container types for type hinting
                        (typing.Sequence, typing.Mapping). If `--use-standard-
                        collections` option is set, then import from
                        collections.abc instead of typing
  --use-union-operator  Use | operator for Union type (PEP 604).
  --use-schema-description
                        Use schema description to populate class docstring
  --use-field-description
                        Use schema description to populate field docstring
  --use-default-kwarg   Use `default=` instead of a positional argument for
                        Fields that have default values.
  --reuse-model         Re-use models on the field when a module has the model
                        with the same content
  --keep-model-order    Keep generated models' order
  --collapse-root-models
                        Models generated with a root-type field will be
                        mergedinto the models using that root-type model
  --enum-field-as-literal {all,one}
                        Parse enum field as literal. all: all enum field type
                        are Literal. one: field type is Literal when an enum
                        has only one possible value
  --set-default-enum-member
                        Set enum members as default values for enum field
  --empty-enum-field-name EMPTY_ENUM_FIELD_NAME
                        Set field name when enum value is empty (default: `_`)
  --capitalise-enum-members
                        Capitalize field names on enum
  --special-field-name-prefix SPECIAL_FIELD_NAME_PREFIX
                        Set field name prefix when first character can't be
                        used as Python field name (default: `field`)
  --remove-special-field-name-prefix
                        Remove field name prefix when first character can't be
                        used as Python field name
  --use-subclass-enum   Define Enum class as subclass with field type when
                        enum has type (int, float, bytes, str)
  --class-name CLASS_NAME
                        Set class name of root model
  --use-title-as-name   use titles as class names of models
  --custom-template-dir CUSTOM_TEMPLATE_DIR
                        Custom template directory
  --extra-template-data EXTRA_TEMPLATE_DATA
                        Extra template data
  --aliases ALIASES     Alias mapping file
  --target-python-version {3.6,3.7,3.8,3.9,3.10,3.11}
                        target python version (default: 3.7)
  --wrap-string-literal
                        Wrap string literal by using black `experimental-
                        string-processing` option (require black 20.8b0 or
                        later)
  --validation          Enable validation (Only OpenAPI)
  --use-double-quotes   Model generated with double quotes. Single quotes or
                        your black config skip_string_normalization value will
                        be used without this option.
  --encoding ENCODING   The encoding of input and output (default: cp1252)
  --debug               show debug message
  --disable-warnings    disable warnings
  --version             show version
```


## Implemented list
### OpenAPI 3 and JsonSchema
#### DataType
-  string (include patter/minLength/maxLenght)
-  number (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
-  integer (include maximum/exclusiveMaximum/minimum/exclusiveMinimum/multipleOf/le/ge)
-  boolean
-  array
-  object

##### String Format
-  date
-  datetime
-  time
-  password
-  email
-  idn-email
-  uuid (uuid1/uuid2/uuid3/uuid4/uuid5)
-  ipv4
-  ipv6
-  ipv4-network
-  ipv6-network
-  hostname
-  decimal

#### Other schema
-  enum (as enum.Enum or typing.Literal)
-  allOf (as Multiple inheritance)
-  anyOf (as typing.Union)
-  oneOf (as typing.Union)
-  $ref ([http extra](#http-extra-option) is required when resolving $ref for remote files.)
-  $id (for [JSONSchema](https://json-schema.org/understanding-json-schema/structuring.html#the-id-property))


## Related projects
### fastapi-code-generator
This code generator creates [FastAPI](https://github.com/tiangolo/fastapi) app from an openapi file.

[https://github.com/koxudaxi/fastapi-code-generator](https://github.com/koxudaxi/fastapi-code-generator)

### pydantic-pycharm-plugin
[A JetBrains PyCharm plugin](https://plugins.jetbrains.com/plugin/12861-pydantic) for [`pydantic`](https://github.com/samuelcolvin/pydantic).

[https://github.com/koxudaxi/pydantic-pycharm-plugin](https://github.com/koxudaxi/pydantic-pycharm-plugin)

## PyPi

[https://pypi.org/project/datamodel-code-generator](https://pypi.org/project/datamodel-code-generator)

## License

datamodel-code-generator is released under the MIT License. http://www.opensource.org/licenses/mit-license
