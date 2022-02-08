import re
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)
from urllib.parse import ParseResult

from pydantic import BaseModel, Field

from datamodel_code_generator import (
    DefaultPutDict,
    LiteralType,
    OpenAPIScope,
    PythonVersion,
    load_yaml,
    snooper_to_methods,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    get_model_by_path,
    get_special_path,
)
from datamodel_code_generator.reference import snake_to_upper_camel
from datamodel_code_generator.types import DataType, DataTypeManager, StrictTypes

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
    ref: str = Field(..., alias='$ref')


class ExampleObject(BaseModel):
    summary: Optional[str]
    description: Optional[str]
    value: Any
    externalValue: Optional[str]


class MediaObject(BaseModel):
    schema_: Union[ReferenceObject, JsonSchemaObject, None] = Field(
        None, alias='schema'
    )
    example: Any
    examples: Union[str, ReferenceObject, ExampleObject, None]


class ParameterObject(BaseModel):
    name: Optional[str]
    in_: Optional[ParameterLocation] = Field(None, alias='in')
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
    description: Optional[str]
    headers: Dict[str, ParameterObject] = {}
    content: Dict[str, MediaObject] = {}


class Operation(BaseModel):
    tags: List[str] = []
    summary: Optional[str]
    description: Optional[str]
    operationId: Optional[str]
    parameters: List[Union[ReferenceObject, ParameterObject]] = []
    requestBody: Union[ReferenceObject, RequestBodyObject, None]
    responses: Dict[str, Union[ReferenceObject, ResponseObject]] = {}
    deprecated: bool = False


class ComponentsObject(BaseModel):
    schemas: Dict[str, Union[ReferenceObject, JsonSchemaObject]] = {}
    responses: Dict[str, Union[ReferenceObject, ResponseObject]] = {}
    examples: Dict[str, Union[ReferenceObject, ExampleObject]] = {}
    requestBodies: Dict[str, Union[ReferenceObject, RequestBodyObject]] = {}
    headers: Dict[str, Union[ReferenceObject, HeaderObject]] = {}


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(JsonSchemaParser):
    def __init__(
        self,
        source: Union[str, Path, List[Path], ParseResult],
        *,
        data_model_type: Type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: Type[DataModel] = pydantic_model.CustomRootType,
        data_type_manager_type: Type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: Type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        dump_resolve_reference_action: Optional[Callable[[Iterable[str]], str]] = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Optional[Mapping[str, str]] = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: Optional[str] = None,
        use_standard_collections: bool = False,
        base_path: Optional[Path] = None,
        use_schema_description: bool = False,
        reuse_model: bool = False,
        encoding: str = 'utf-8',
        enum_field_as_literal: Optional[LiteralType] = None,
        set_default_enum_member: bool = False,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: Optional[DefaultPutDict[str, str]] = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Optional[Sequence[StrictTypes]] = None,
        empty_enum_field_name: Optional[str] = None,
        custom_class_name_generator: Optional[Callable[[str], str]] = None,
        field_extra_keys: Optional[Set[str]] = None,
        field_include_all_keys: bool = False,
        openapi_scopes: Optional[List[OpenAPIScope]] = None,
        wrap_string_literal: Optional[bool] = False,
        use_title_as_name: bool = False,
        http_headers: Optional[Sequence[Tuple[str, str]]] = None,
        http_ignore_tls: bool = False,
        use_annotated: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
    ):
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_type_manager_type=data_type_manager_type,
            data_model_field_type=data_model_field_type,
            base_class=base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            target_python_version=target_python_version,
            dump_resolve_reference_action=dump_resolve_reference_action,
            validation=validation,
            field_constraints=field_constraints,
            snake_case_field=snake_case_field,
            strip_default_none=strip_default_none,
            aliases=aliases,
            allow_population_by_field_name=allow_population_by_field_name,
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            force_optional_for_required_fields=force_optional_for_required_fields,
            class_name=class_name,
            use_standard_collections=use_standard_collections,
            base_path=base_path,
            use_schema_description=use_schema_description,
            reuse_model=reuse_model,
            encoding=encoding,
            enum_field_as_literal=enum_field_as_literal,
            set_default_enum_member=set_default_enum_member,
            strict_nullable=strict_nullable,
            use_generic_container_types=use_generic_container_types,
            enable_faux_immutability=enable_faux_immutability,
            remote_text_cache=remote_text_cache,
            disable_appending_item_suffix=disable_appending_item_suffix,
            strict_types=strict_types,
            empty_enum_field_name=empty_enum_field_name,
            custom_class_name_generator=custom_class_name_generator,
            field_extra_keys=field_extra_keys,
            field_include_all_keys=field_include_all_keys,
            wrap_string_literal=wrap_string_literal,
            use_title_as_name=use_title_as_name,
            http_headers=http_headers,
            http_ignore_tls=http_ignore_tls,
            use_annotated=use_annotated,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
        )
        self.open_api_scopes: List[OpenAPIScope] = openapi_scopes or [
            OpenAPIScope.Schemas
        ]

    def get_ref_model(self, ref: str) -> Dict[str, Any]:
        ref_file, ref_path = self.model_resolver.resolve_ref(ref).split('#', 1)
        if ref_file:
            ref_body = self._get_ref_body(ref_file)
        else:  # pragma: no cover
            ref_body = self.raw_obj
        return get_model_by_path(ref_body, ref_path.split('/')[1:])

    def parse_parameters(self, parameters: ParameterObject, path: List[str]) -> None:
        if parameters.name and parameters.schema_:  # pragma: no cover
            self.parse_item(parameters.name, parameters.schema_, [*path, 'schema'])
        for (
            media_type,
            media_obj,
        ) in parameters.content.items():  # type: str, MediaObject
            if parameters.name and isinstance(  # pragma: no cover
                media_obj.schema_, JsonSchemaObject
            ):  # pragma: no cover
                self.parse_item(parameters.name, media_obj.schema_, [*path, media_type])

    def parse_schema(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: List[str],
    ) -> DataType:
        if obj.is_array:
            data_type: DataType = self.parse_array_fields(
                name, obj, [*path, name], False
            ).data_type
            # TODO: The List model is not created by this method. Some scenarios may necessitate it.
        elif obj.allOf:  # pragma: no cover
            data_type = self.parse_all_of(name, obj, path)
        elif obj.oneOf:  # pragma: no cover
            data_type = self.parse_root_type(name, obj, path)
        elif obj.is_object:
            data_type = self.parse_object(name, obj, path)
        elif obj.enum:  # pragma: no cover
            data_type = self.parse_enum(name, obj, path)
        elif obj.ref:  # pragma: no cover
            data_type = self.get_ref_data_type(obj.ref)
        else:
            data_type = self.get_data_type(obj)
        self.parse_ref(obj, path)
        return data_type

    def parse_request_body(
        self,
        name: str,
        request_body: RequestBodyObject,
        path: List[str],
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
        responses: Dict[str, Union[ReferenceObject, ResponseObject]],
        path: List[str],
    ) -> Dict[str, Dict[str, DataType]]:
        data_types: DefaultDict[str, Dict[str, DataType]] = defaultdict(dict)
        for status_code, detail in responses.items():
            if isinstance(detail, ReferenceObject):
                if not detail.ref:  # pragma: no cover
                    continue
                ref_model = self.get_ref_model(detail.ref)
                content = {
                    k: MediaObject.parse_obj(v)
                    for k, v in ref_model.get("content", {}).items()
                }
            else:
                content = detail.content
            for content_type, obj in content.items():

                object_schema = obj.schema_
                if not object_schema:  # pragma: no cover
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
        path: List[str],
    ) -> None:
        operation = Operation.parse_obj(raw_operation)
        for parameters in operation.parameters:
            if isinstance(parameters, ReferenceObject):
                ref_parameter = self.get_ref_model(parameters.ref)
                parameters = ParameterObject.parse_obj(ref_parameter)
            self.parse_parameters(parameters=parameters, path=[*path, 'parameters'])
        path_name, method = path[-2:]
        if operation.requestBody:
            if isinstance(operation.requestBody, ReferenceObject):
                ref_model = self.get_ref_model(operation.requestBody.ref)
                request_body = RequestBodyObject.parse_obj(ref_model)
            else:
                request_body = operation.requestBody
            self.parse_request_body(
                name=self._get_model_name(path_name, method, suffix='Request'),
                request_body=request_body,
                path=[*path, 'requestBody'],
            )
        self.parse_responses(
            name=self._get_model_name(path_name, method, suffix='Response'),
            responses=operation.responses,
            path=[*path, 'responses'],
        )

    def parse_raw(self) -> None:
        for source in self.iter_source:
            if self.validation:
                from prance import BaseParser

                BaseParser(
                    spec_string=source.text,
                    backend='openapi-spec-validator',
                    encoding=self.encoding,
                )
            specification: Dict[str, Any] = load_yaml(source.text)
            self.raw_obj = specification
            schemas: Dict[Any, Any] = specification.get('components', {}).get(
                'schemas', {}
            )
            security: Optional[List[Dict[str, List[str]]]] = specification.get(
                'security'
            )
            if isinstance(self.source, ParseResult):
                path_parts: List[str] = self.get_url_path_parts(self.source)
            else:
                path_parts = list(source.path.parts)
            with self.model_resolver.current_root_context(path_parts):
                if OpenAPIScope.Schemas in self.open_api_scopes:
                    for (
                        obj_name,
                        raw_obj,
                    ) in schemas.items():  # type: str, Dict[Any, Any]
                        self.parse_raw_obj(
                            obj_name,
                            raw_obj,
                            [*path_parts, '#/components', 'schemas', obj_name],
                        )
                if OpenAPIScope.Paths in self.open_api_scopes:
                    paths: Dict[str, Dict[str, Any]] = specification.get('paths', {})
                    parameters: List[Dict[str, Any]] = [
                        self._get_ref_body(p['$ref']) if '$ref' in p else p  # type: ignore
                        for p in paths.get('parameters', [])
                        if isinstance(p, dict)
                    ]
                    paths_path = [*path_parts, '#/paths']
                    for path_name, methods in paths.items():

                        paths_parameters = parameters[:]
                        if 'parameters' in methods:
                            paths_parameters.extend(methods['parameters'])
                        relative_path_name = path_name[1:]
                        if relative_path_name:
                            path = [*paths_path, relative_path_name]
                        else:  # pragma: no cover
                            path = get_special_path('root', paths_path)
                        for operation_name, raw_operation in methods.items():
                            if operation_name not in OPERATION_NAMES:
                                continue
                            if paths_parameters:
                                if 'parameters' in raw_operation:  # pragma: no cover
                                    raw_operation['parameters'].extend(paths_parameters)
                                else:
                                    raw_operation['parameters'] = paths_parameters
                            if security is not None and 'security' not in raw_operation:
                                raw_operation['security'] = security
                            self.parse_operation(
                                raw_operation,
                                [*path, operation_name],
                            )
