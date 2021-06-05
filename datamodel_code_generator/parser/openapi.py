from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import ParseResult

from pydantic import BaseModel, Field

from datamodel_code_generator import load_yaml, snooper_to_methods
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
)


class ParameterLocation(Enum):
    query = 'query'
    header = 'header'
    path = 'path'
    cookie = 'cookie'


class ReferenceObject(BaseModel):
    ref: str = Field(default=None, alias='$ref')


class ExampleObject(BaseModel):
    summary: Optional[str]
    description: Optional[str]
    value: Any
    externalValue: Optional[str]


class MediaObject(BaseModel):
    schema_: Union[JsonSchemaObject, ReferenceObject, None] = Field(
        None, alias='schema'
    )
    example: Any
    examples: Union[str, ReferenceObject, ExampleObject, None]


class ParameterObject(BaseModel):
    name: str
    in_: ParameterLocation
    description: Optional[str]
    required: bool = False
    deprecated: bool = False
    schema_: Optional[JsonSchemaObject] = Field(None, alias='schema')
    example: Any
    examples: Union[str, ReferenceObject, ExampleObject, None]
    content: Dict[str, MediaObject] = {}


class HeaderObject(BaseModel):
    description: Optional[str]
    required: bool = False
    deprecated: bool = False
    schema_: Optional[JsonSchemaObject] = Field(None, alias='schema')
    example: Any
    examples: Union[str, ReferenceObject, ExampleObject, None]
    content: Dict[str, MediaObject] = {}


class RequestBodyObject(BaseModel):
    description: Optional[str]
    content: Dict[str, MediaObject] = {}
    required: bool = False


class ResponseObject(BaseModel):
    description: str
    headers: Dict[str, ParameterObject] = {}
    content: Dict[str, MediaObject] = {}


class ResponsesObject(BaseModel):
    default: Union[HeaderObject, ReferenceObject, None]


class Operation(BaseModel):
    tags: List[str] = []
    summary: Optional[str]
    description: Optional[str]
    operationId: Optional[str]
    parameters: List[Union[ParameterObject, ReferenceObject]]
    requestBody: ResponsesObject
    deprecated: bool = False


class ComponentsObject(BaseModel):
    schemas: Dict[str, Union[JsonSchemaObject, ReferenceObject]] = {}
    responses: Dict[str, Union[ResponseObject, ReferenceObject]] = {}
    examples: Dict[str, Union[ExampleObject, ReferenceObject]] = {}
    requestBodies: Dict[str, Union[RequestBodyObject, ReferenceObject]] = {}
    headers: Dict[str, Union[HeaderObject, ReferenceObject]] = {}


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(JsonSchemaParser):
    def parse_raw(self) -> None:
        for source in self.iter_source:
            if self.validation:
                from prance import BaseParser

                base_parser = BaseParser(
                    spec_string=source.text, backend='openapi-spec-validator'
                )
                specification: Dict[str, Any] = base_parser.specification
            else:
                specification = load_yaml(source.text)
            self.raw_obj = specification
            schemas: Dict[Any, Any] = specification.get('components', {}).get(
                'schemas', {}
            )
            if isinstance(self.source, ParseResult):
                path_parts: List[str] = self.get_url_path_parts(self.source)
            else:
                path_parts = list(source.path.parts)
            with self.model_resolver.current_root_context(path_parts):
                for obj_name, raw_obj in schemas.items():  # type: str, Dict[Any, Any]
                    self.parse_raw_obj(
                        obj_name,
                        raw_obj,
                        [*path_parts, '#/components', 'schemas', obj_name],
                    )
