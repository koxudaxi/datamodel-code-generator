from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import ParseResult

from pydantic import BaseModel, Field

from datamodel_code_generator import load_yaml, snooper_to_methods
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
)
from datamodel_code_generator.reference import snake_to_upper_camel


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
    in_: ParameterLocation = Field(..., alias='in')
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
    parameters: List[Union[ParameterObject, ReferenceObject]] = []
    requestBody: Optional[RequestBodyObject]
    responses: Optional[ResponsesObject]
    deprecated: bool = False


class ComponentsObject(BaseModel):
    schemas: Dict[str, Union[JsonSchemaObject, ReferenceObject]] = {}
    responses: Dict[str, Union[ResponseObject, ReferenceObject]] = {}
    examples: Dict[str, Union[ExampleObject, ReferenceObject]] = {}
    requestBodies: Dict[str, Union[RequestBodyObject, ReferenceObject]] = {}
    headers: Dict[str, Union[HeaderObject, ReferenceObject]] = {}


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(JsonSchemaParser):
    def parse_parameters(self, parameters: ParameterObject, path: List[str]) -> None:
        if parameters.schema_:
            self.parse_item(parameters.name, parameters.schema_, [*path, 'schema'])
        for (
            media_type,
            media_obj,
        ) in parameters.content.items():  # type: str, MediaObject
            if isinstance(media_obj.schema_, JsonSchemaObject):
                self.parse_item(parameters.name, media_obj.schema_, [*path, media_type])

    def parse_request_body(
        self, name: str, request_body: RequestBodyObject, path: List[str],
    ) -> None:
        for (
            media_type,
            media_obj,
        ) in request_body.content.items():  # type: str, MediaObject
            if isinstance(media_obj.schema_, JsonSchemaObject):
                self.parse_item(name, media_obj.schema_, [*path, media_type])

    @classmethod
    def _get_request_body_name(cls, path_name: str, method: str) -> str:
        camel_path_name = snake_to_upper_camel(path_name[1:].replace("/", "_"))
        return f'{camel_path_name}{method.capitalize()}Request'

    def parse_operation(self, raw_operation: Operation, path: List[str],) -> None:
        operation = Operation.parse_obj(raw_operation)
        for parameters in operation.parameters:
            if isinstance(parameters, ParameterObject):
                self.parse_parameters(parameters=parameters, path=[*path, 'parameters'])
        if operation.requestBody:
            self.parse_request_body(
                name=self._get_request_body_name(*path[-2:]),
                request_body=operation.requestBody,
                path=[*path, 'requestBody'],
            )

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
                paths: Dict[str, Dict[str, Any]] = specification.get('paths', {})
                for path_name, methods in paths.items():
                    for method, raw_operation in methods.items():
                        self.parse_operation(
                            raw_operation, [*path_parts, '#/paths', path_name, method],
                        )
