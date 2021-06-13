import re
from collections import defaultdict
from enum import Enum
from typing import Any, DefaultDict, Dict, List, Optional, Pattern, Union
from urllib.parse import ParseResult

from pydantic import BaseModel, Field

from datamodel_code_generator import load_yaml, snooper_to_methods
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    get_special_path,
)
from datamodel_code_generator.reference import snake_to_upper_camel
from datamodel_code_generator.types import DataType

RE_APPLICATION_JSON_PATTERN: Pattern[str] = re.compile(r'^application/.*json$')

OPERATION_NAMES: List[str] = [
    "get",
    "put",
    "post",
    "delete",
    "patch",
    "head",
    "options",
    "trace",
]


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


class Operation(BaseModel):
    tags: List[str] = []
    summary: Optional[str]
    description: Optional[str]
    operationId: Optional[str]
    parameters: List[Union[ParameterObject, ReferenceObject]] = []
    requestBody: Optional[RequestBodyObject]
    responses: Dict[str, Union[ResponseObject, ReferenceObject]] = {}
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

    def parse_schema(
        self, name: str, obj: JsonSchemaObject, path: List[str],
    ) -> DataType:
        if obj.is_array:
            data_type: DataType = self.parse_array(name, obj, path)
        elif obj.allOf:
            data_type = self.parse_all_of(name, obj, path)
        elif obj.oneOf:
            data_type = self.parse_root_type(name, obj, path)
        elif obj.is_object:
            data_type = self.parse_object(name, obj, path)
        elif obj.enum:
            data_type = self.parse_enum(name, obj, path)
        else:
            data_type = self.get_data_type(obj)
        self.parse_ref(obj, path)
        return data_type

    def parse_request_body(
        self, name: str, request_body: RequestBodyObject, path: List[str],
    ) -> None:
        for (
            media_type,
            media_obj,
        ) in request_body.content.items():  # type: str, MediaObject
            if isinstance(media_obj.schema_, JsonSchemaObject):
                self.parse_schema(name, media_obj.schema_, [*path, media_type])

    def parse_responses(
        self,
        name: str,
        responses: Dict[str, Union[ResponseObject, ReferenceObject]],
        path: List[str],
    ) -> Dict[str, Dict[str, DataType]]:
        data_types: DefaultDict[str, Dict[str, DataType]] = defaultdict(dict)
        for status_code, detail in responses.items():
            if isinstance(detail, ReferenceObject):
                if not detail.ref:
                    continue
                ref_body = self._get_ref_body(
                    self.model_resolver.resolve_ref(detail.ref)
                )
                content = ref_body.get("content", {})
            else:
                content = detail.content
            for content_type, obj in content.items():
                object_schema = obj.schema_
                if not object_schema:
                    continue
                if isinstance(object_schema, JsonSchemaObject):
                    data_types[status_code][content_type] = self.parse_schema(
                        name, object_schema, [*path, status_code, content_type]
                    )
                else:
                    data_types[status_code][content_type] = self.get_ref_data_type(
                        object_schema.ref
                    )

        return data_types

    @classmethod
    def _get_model_name(cls, path_name: str, method: str, suffix: str) -> str:
        camel_path_name = snake_to_upper_camel(path_name.replace('/', '_'))
        return f'{camel_path_name}{method.capitalize()}{suffix}'

    def parse_operation(
        self,
        raw_operation: Dict[str, Any],
        parent_parameters: List[Dict[str, Any]],
        path: List[str],
    ) -> None:
        if parent_parameters:
            if 'parameters' in raw_operation:
                raw_operation['parameters'].extend(parent_parameters)
            else:
                raw_operation['parameters'] = parent_parameters
        operation = Operation.parse_obj(raw_operation)
        for parameters in operation.parameters:
            if isinstance(parameters, ParameterObject):
                self.parse_parameters(parameters=parameters, path=[*path, 'parameters'])
        path_name, method = path[-2:]
        if operation.requestBody:
            self.parse_request_body(
                name=self._get_model_name(path_name, method, suffix='Request'),
                request_body=operation.requestBody,
                path=[*path, 'requestBody'],
            )
        if operation.responses:
            self.parse_responses(
                name=self._get_model_name(path_name, method, suffix='Response'),
                responses=operation.responses,
                path=[*path, 'responses'],
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
                parameters: List[Dict[str, Any]] = [
                    self._get_ref_body(p['$ref']) if '$ref' in p else p  # type: ignore
                    for p in paths.get('parameters', [])
                    if isinstance(p, dict)
                ]
                paths_path = [*path_parts, '#/paths']
                for path_name, methods in paths.items():
                    relative_path_name = path_name[1:]
                    if relative_path_name:
                        path = [*paths_path, relative_path_name]
                    else:
                        path = get_special_path('root', paths_path)
                    for operation_name, raw_operation in methods.items():
                        if operation_name in OPERATION_NAMES:
                            self.parse_operation(
                                raw_operation, parameters, [*path, operation_name],
                            )
