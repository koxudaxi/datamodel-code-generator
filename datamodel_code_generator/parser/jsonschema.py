import enum as _enum
import sys
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Generator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)
from warnings import warn

from pydantic import BaseModel, Field, root_validator, validator

from datamodel_code_generator import (
    InvalidClassNameError,
    cached_property,
    load_yaml,
    snooper_to_methods,
)
from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.parser import LiteralType

from ..imports import IMPORT_LITERAL, Import
from ..model import pydantic as pydantic_model
from ..parser.base import Parser
from ..reference import is_url
from ..types import DataType, DataTypeManager, Types


def get_model_by_path(schema: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    if not keys:
        return schema
    elif len(keys) == 1:
        return schema.get(keys[0], {})
    return get_model_by_path(schema[keys[0]], keys[1:])


json_schema_data_formats: Dict[str, Dict[str, Types]] = {
    'integer': {
        'int32': Types.int32,
        'int64': Types.int64,
        'default': Types.integer,
        'unix-time': Types.int64,
    },
    'number': {
        'float': Types.float,
        'double': Types.double,
        'decimal': Types.decimal,
        'time': Types.time,
        'default': Types.number,
    },
    'string': {
        'default': Types.string,
        'byte': Types.byte,  # base64 encoded string
        'binary': Types.binary,
        'date': Types.date,
        'date-time': Types.date_time,
        'password': Types.password,
        'email': Types.email,
        'uuid': Types.uuid,
        'uuid1': Types.uuid1,
        'uuid2': Types.uuid2,
        'uuid3': Types.uuid3,
        'uuid4': Types.uuid4,
        'uuid5': Types.uuid5,
        'uri': Types.uri,
        'uri-reference': Types.string,
        'hostname': Types.hostname,
        'ipv4': Types.ipv4,
        'ipv6': Types.ipv6,
        'decimal': Types.decimal,
        'integer': Types.integer,
    },
    'boolean': {'default': Types.boolean},
    'object': {'default': Types.object},
    'null': {'default': Types.null},
    'array': {'default': Types.array},
}


class JSONReference(_enum.Enum):
    LOCAL = 'LOCAL'
    REMOTE = 'REMOTE'
    URL = 'URL'


class JsonSchemaObject(BaseModel):
    __constraint_fields__: Set[str] = {
        'exclusiveMinimum',
        'minimum',
        'exclusiveMaximum',
        'maximum',
        'multipleOf',
        'minItems',
        'maxItems',
        'minLength',
        'maxLength',
        'pattern',
    }

    @root_validator(pre=True)
    def validate_exclusive_maximum_and_exclusive_minimum(
        cls, values: Dict[str, Any]
    ) -> Any:
        exclusive_maximum: Union[float, bool, None] = values.get('exclusiveMaximum')
        exclusive_minimum: Union[float, bool, None] = values.get('exclusiveMinimum')

        if exclusive_maximum is True:
            values['exclusiveMaximum'] = values['maximum']
            del values['maximum']
        elif exclusive_maximum is False:
            del values['exclusiveMaximum']
        if exclusive_minimum is True:
            values['exclusiveMinimum'] = values['minimum']
            del values['minimum']
        elif exclusive_minimum is False:
            del values['exclusiveMinimum']
        return values

    @validator('ref')
    def validate_ref(cls, value: Any) -> Any:
        if isinstance(value, str) and '#' in value:
            if '#/' in value or value[0] == '#' or value[-1] == '#':
                return value
            return value.replace('#', '#/')
        return value

    items: Union[List['JsonSchemaObject'], 'JsonSchemaObject', None]
    uniqueItem: Optional[bool]
    type: Union[str, List[str], None]
    format: Optional[str]
    pattern: Optional[str]
    minLength: Optional[int]
    maxLength: Optional[int]
    minimum: Optional[float]
    maximum: Optional[float]
    minItems: Optional[int]
    maxItems: Optional[int]
    multipleOf: Optional[float]
    exclusiveMaximum: Union[float, bool, None]
    exclusiveMinimum: Union[float, bool, None]
    additionalProperties: Union['JsonSchemaObject', bool, None]
    oneOf: List['JsonSchemaObject'] = []
    anyOf: List['JsonSchemaObject'] = []
    allOf: List['JsonSchemaObject'] = []
    enum: List[Any] = []
    writeOnly: Optional[bool]
    properties: Optional[Dict[str, 'JsonSchemaObject']]
    required: List[str] = []
    ref: Optional[str] = Field(default=None, alias='$ref')
    nullable: Optional[bool] = False
    x_enum_varnames: List[str] = Field(default=[], alias='x-enum-varnames')
    description: Optional[str]
    title: Optional[str]
    example: Any
    examples: Any
    default: Any
    id: Optional[str] = Field(default=None, alias='$id')

    class Config:
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)

    @cached_property
    def is_object(self) -> bool:
        return (
            self.properties is not None
            or self.type == 'object'
            and not self.allOf
            and not self.oneOf
            and not self.anyOf
        )

    @cached_property
    def is_array(self) -> bool:
        return self.items is not None or self.type == 'array'

    @cached_property
    def ref_object_name(self) -> str:  # pragma: no cover
        return self.ref.rsplit('/', 1)[-1]  # type: ignore

    @validator('items', pre=True)
    def validate_items(cls, values: Any) -> Any:
        # this condition expects empty dict
        return values or None

    @cached_property
    def has_default(self) -> bool:
        return 'default' in self.__fields_set__

    @cached_property
    def has_constraint(self) -> bool:
        return bool(self.__constraint_fields__ & self.__fields_set__)

    @cached_property
    def ref_type(self) -> Optional[JSONReference]:
        if self.ref:
            if self.ref[0] == '#':
                return JSONReference.LOCAL
            elif is_url(self.ref):
                return JSONReference.URL
            return JSONReference.REMOTE
        return None  # pragma: no cover


JsonSchemaObject.update_forward_refs()


@snooper_to_methods(max_variable_length=None)
class JsonSchemaParser(Parser):
    def __init__(
        self,
        source: Union[str, Path, List[Path]],
        *,
        data_model_type: Type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: Type[DataModel] = pydantic_model.CustomRootType,
        data_type_manager_type: Type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: Type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        dump_resolve_reference_action: Optional[Callable[[List[str]], str]] = None,
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
        )

        self.remote_object_cache: Dict[str, Dict[str, Any]] = {}
        self.raw_obj: Dict[Any, Any] = {}
        self._root_id: Optional[str] = None
        self._root_id_base_path: Optional[str] = None
        self.reserved_refs: DefaultDict[Tuple[str], Set[str]] = defaultdict(set)

    @property
    def root_id(self) -> Optional[str]:
        return self._root_id

    @root_id.setter
    def root_id(self, value: Optional[str]) -> None:
        self._root_id = value
        if value and '/' in value:
            self._root_id_base_path = value.rsplit('/', 1)[0]
        else:
            self._root_id_base_path = None

        self.model_resolver.set_root_id_base_path(self.root_id_base_path)

    @property
    def root_id_base_path(self) -> Optional[str]:
        return self._root_id_base_path

    def should_parse_enum_as_literal(self, obj: JsonSchemaObject) -> bool:
        return self.enum_field_as_literal == LiteralType.All or (
            self.enum_field_as_literal == LiteralType.One and len(obj.enum) == 1
        )

    def get_data_type(self, obj: JsonSchemaObject) -> DataType:
        if obj.type is None:
            return self.data_type_manager.get_data_type(Types.any)

        def _get_data_type(type_: str, format__: str) -> DataType:
            data_formats: Optional[Types] = json_schema_data_formats[type_].get(
                format__
            )
            if data_formats is None:
                warn(
                    "format of {!r} not understood for {!r} - using default"
                    "".format(format__, type_)
                )
                data_formats = json_schema_data_formats[type_]['default']
            return self.data_type_manager.get_data_type(
                data_formats, **obj.dict() if not self.field_constraints else {},
            )

        if isinstance(obj.type, list):
            return self.data_type(
                data_types=[
                    _get_data_type(t, 'default') for t in obj.type if t != 'null'
                ],
                is_optional='null' in obj.type,
            )
        return _get_data_type(obj.type, obj.format or 'default')

    def get_ref_data_type(self, ref: str) -> DataType:
        reference = self.model_resolver.add_ref(ref)
        return self.data_type.from_reference(reference)

    def set_additional_properties(self, name: str, obj: JsonSchemaObject) -> None:
        if obj.additionalProperties:
            # TODO check additional property types.
            self.extra_template_data[name][
                'additionalProperties'
            ] = obj.additionalProperties

    def set_title(self, name: str, obj: JsonSchemaObject) -> None:
        if obj.title:
            self.extra_template_data[name]['title'] = obj.title

    def parse_list_item(
        self, name: str, target_items: List[JsonSchemaObject], path: List[str]
    ) -> DataType:
        data_types: List[DataType] = []
        for index, item in enumerate(target_items):
            if item.ref:  # $ref
                data_types.append(self.get_ref_data_type(item.ref))
            elif not any(v for k, v in vars(item).items() if k != 'type'):
                # trivial types
                data_types.append(self.get_data_type(item))
            elif (
                item.is_array
                and isinstance(item.items, JsonSchemaObject)
                and not any(v for k, v in vars(item.items).items() if k != 'type')
            ):
                # trivial item types
                data_types.append(
                    self.data_type(
                        data_types=[self.get_data_type(item.items)], is_list=True,
                    )
                )
            else:
                data_types.append(
                    self.data_type.from_model_name(
                        self.parse_object(
                            name, item, [*path, str(index)], singular_name=True,
                        ).name,
                    )
                )
        return self.data_type(data_types=data_types)

    def parse_any_of(
        self, name: str, obj: JsonSchemaObject, path: List[str]
    ) -> DataType:
        return self.parse_list_item(name, obj.anyOf, path)

    def parse_one_of(
        self, name: str, obj: JsonSchemaObject, path: List[str]
    ) -> DataType:
        return self.parse_list_item(name, obj.oneOf, path)

    def parse_all_of(
        self, name: str, obj: JsonSchemaObject, path: List[str]
    ) -> DataType:
        fields: List[DataModelFieldBase] = []
        base_classes: List[DataType] = []
        if len(obj.allOf) == 1:
            single_obj = obj.allOf[0]
            if single_obj.ref and single_obj.ref_type == JSONReference.LOCAL:
                if get_model_by_path(self.raw_obj, single_obj.ref[2:].split('/')).get(
                    'enum'
                ):
                    return self.get_ref_data_type(single_obj.ref)
        for all_of_item in obj.allOf:
            if all_of_item.ref:  # $ref
                base_classes.append(self.get_ref_data_type(all_of_item.ref))
            else:
                fields.extend(self.parse_object_fields(all_of_item, path))
        class_name = self.model_resolver.add(
            path, name, class_name=True, unique=True, loaded=True
        ).name
        self.set_additional_properties(class_name, obj)
        data_model_type = self.data_model_type(
            class_name,
            fields=fields,
            base_classes=[b.type_hint for b in base_classes],
            auto_import=False,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description if self.use_schema_description else None,
        )
        # add imports for the fields
        for f in fields:
            data_model_type.imports.extend(f.imports)
        self.append_result(data_model_type)

        return self.data_type.from_model_name(class_name)

    def parse_object_fields(
        self, obj: JsonSchemaObject, path: List[str]
    ) -> List[DataModelFieldBase]:
        properties: Dict[str, JsonSchemaObject] = (
            {} if obj.properties is None else obj.properties
        )
        requires: Set[str] = {*()} if obj.required is None else {*obj.required}
        fields: List[DataModelFieldBase] = []

        for field_name, field in properties.items():
            field_type: DataType
            original_field_name: str = field_name
            constraints: Optional[Mapping[str, Any]] = None
            field_name, alias = self.model_resolver.get_valid_field_name_and_alias(
                field_name
            )
            if field.ref:
                field_type = self.get_ref_data_type(field.ref)
            elif field.is_array:
                array_field = self.parse_array_fields(
                    field_name, field, [*path, field_name]
                )
                field_type = array_field.data_type
                constraints = field.dict()
            elif field.anyOf:
                field_type = self.parse_any_of(field_name, field, [*path, field_name])
            elif field.oneOf:
                field_type = self.parse_one_of(field_name, field, [*path, field_name])
            elif field.allOf:
                field_type = self.parse_all_of(field_name, field, [*path, field_name])
            elif field.is_object:
                if field.properties:
                    field_type = self.data_type.from_model_name(
                        self.parse_object(field_name, field, [*path, field_name]).name
                    )

                elif isinstance(field.additionalProperties, JsonSchemaObject):
                    unresolved_type: Optional[str]
                    imports_: List[Import] = []
                    field_class_name = self.model_resolver.add(
                        [*path, field_name], field_name, class_name=True
                    ).name

                    # TODO: supports other type
                    if (
                        isinstance(field.additionalProperties.items, JsonSchemaObject)
                        and field.additionalProperties.items.ref
                    ):
                        unresolved_type = self.model_resolver.add_ref(
                            field.additionalProperties.items.ref,
                        ).name
                        additional_properties_type = self.data_type.from_model_name(
                            unresolved_type, is_list=True
                        ).type_hint
                    elif field.additionalProperties.is_array:
                        additional_properties_type = unresolved_type = self.parse_array(
                            field_class_name,
                            field.additionalProperties,
                            [*path, field_name],
                        ).name
                    elif field.additionalProperties.is_object:
                        additional_properties_type = (
                            unresolved_type
                        ) = self.parse_object(
                            field_class_name,
                            field.additionalProperties,
                            [*path, field_name],
                            additional_properties=None
                            if field.additionalProperties.ref
                            else field,
                        ).name
                    elif field.additionalProperties.enum:
                        if self.should_parse_enum_as_literal(
                            field.additionalProperties
                        ):
                            additional_properties_type = self.data_type.create_literal(
                                field.additionalProperties.enum
                            ).type_hint
                            unresolved_type = None
                            imports_.append(IMPORT_LITERAL)
                        else:
                            additional_properties_type = (
                                unresolved_type
                            ) = self.parse_enum(
                                field_class_name,
                                field.additionalProperties,
                                [*path, field_name],
                            ).name

                    else:
                        additional_properties_type = (
                            unresolved_type
                        ) = self.parse_root_type(
                            field_class_name,
                            field.additionalProperties,
                            [*path, field_name],
                            additional_properties=None
                            if field.additionalProperties.ref
                            else field,
                        ).name
                    self.parse_ref(
                        field.additionalProperties, [*path, field_name],
                    )
                    field_type = self.data_type(
                        type=additional_properties_type,
                        is_dict=True,
                        unresolved_types={unresolved_type}
                        if unresolved_type
                        else {*()},
                        imports_=imports_,
                    )

                else:
                    field_type = self.data_type_manager.get_data_type(Types.object)
            elif field.enum:
                if self.should_parse_enum_as_literal(field):
                    field_type = self.data_type_manager.data_type.create_literal(
                        field.enum
                    )
                else:
                    enum = self.parse_enum(field_name, field, [*path, field_name])
                    field_type = self.data_type.from_model_name(enum.name)
            else:
                field_type = self.get_data_type(field)
                if self.field_constraints:
                    constraints = field.dict()
            if self.force_optional_for_required_fields or (
                self.apply_default_values_for_required_fields and field.has_default
            ):
                required: bool = False
            else:
                required = original_field_name in requires
            fields.append(
                self.data_model_field_type(
                    name=field_name,
                    example=field.example,
                    examples=field.examples,
                    description=field.description,
                    default=field.default,
                    title=field.title,
                    data_type=field_type,
                    required=required,
                    alias=alias,
                    constraints=constraints,
                )
            )
        return fields

    def parse_object(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: List[str],
        singular_name: bool = False,
        unique: bool = True,
        additional_properties: Optional[JsonSchemaObject] = None,
    ) -> DataModel:
        if not unique:  # pragma: no cover
            warn(
                f'{self.__class__.__name__}.parse_object() ignore `unique` argument.'
                f'An object name must be unique.'
                f'This argument will be removed in a future version'
            )
        class_name = self.model_resolver.add(
            path,
            name,
            class_name=True,
            singular_name=singular_name,
            unique=True,
            loaded=True,
        ).name
        self.set_title(class_name, obj)
        self.set_additional_properties(class_name, additional_properties or obj)
        data_model_type = self.data_model_type(
            class_name,
            fields=self.parse_object_fields(obj, path),
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description if self.use_schema_description else None,
        )
        self.append_result(data_model_type)
        return data_model_type

    def parse_array_fields(
        self, name: str, obj: JsonSchemaObject, path: List[str]
    ) -> DataModelFieldBase:
        if isinstance(obj.items, JsonSchemaObject):
            items = [obj.items]
        else:
            items = obj.items or []
        item_obj_data_types: List[DataType] = []
        for index, item in enumerate(items):
            field_path = [*path, str(index)]
            if item.has_constraint:
                model = self.model_resolver.add(
                    field_path, name, class_name=True, singular_name=True, unique=True,
                )
                item_obj_data_types.append(
                    self.data_type.from_model_name(
                        self.parse_root_type(model.name, item, field_path,).name
                    )
                )
            elif item.ref:
                item_obj_data_types.append(self.get_ref_data_type(item.ref))
            elif isinstance(item, JsonSchemaObject) and item.properties:
                item_obj_data_types.append(
                    self.data_type.from_model_name(
                        self.parse_object(
                            name, item, field_path, singular_name=True,
                        ).name,
                    )
                )
            elif item.anyOf:
                item_obj_data_types.append(self.parse_any_of(name, item, field_path))
            elif item.allOf:
                item_obj_data_types.append(
                    self.parse_all_of(
                        self.model_resolver.add(
                            field_path, name, singular_name=True
                        ).name,
                        item,
                        field_path,
                    )
                )
            elif item.enum:
                item_obj_data_types.append(
                    self.data_type_manager.data_type.create_literal(item.enum)
                    if self.should_parse_enum_as_literal(item)
                    else self.data_type.from_model_name(
                        self.parse_enum(
                            name, item, field_path, singular_name=True
                        ).name,
                    )
                )
            elif item.is_array:
                array_field = self.parse_array_fields(
                    self.model_resolver.add(field_path, name, class_name=True).name,
                    item,
                    field_path,
                )
                item_obj_data_types.append(array_field.data_type)
            else:
                item_obj_data_types.append(self.get_data_type(item))
        if self.force_optional_for_required_fields:
            required: bool = False
        else:
            required = not obj.nullable and not (
                obj.has_default and self.apply_default_values_for_required_fields
            )
        field = self.data_model_field_type(
            data_type=self.data_type(data_types=item_obj_data_types, is_list=True,),
            example=obj.example,
            examples=obj.examples,
            default=obj.default,
            description=obj.description,
            title=obj.title,
            required=required,
            constraints=obj.dict(),
        )
        return field

    def parse_array(
        self, name: str, obj: JsonSchemaObject, path: List[str]
    ) -> DataModel:
        field = self.parse_array_fields(name, obj, [*path, name])
        self.model_resolver.add(path, name, loaded=True)
        data_model_root = self.data_model_root_type(
            name,
            [field],
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description if self.use_schema_description else None,
        )

        self.append_result(data_model_root)
        return data_model_root

    def parse_root_type(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: List[str],
        additional_properties: Optional[JsonSchemaObject] = None,
    ) -> DataModel:
        if obj.type:
            data_type: DataType = self.get_data_type(obj)
        elif obj.anyOf:
            data_type = self.parse_any_of(name, obj, [*path, name])
        elif obj.ref:
            data_type = self.get_ref_data_type(obj.ref)
        else:
            data_type = self.data_type_manager.get_data_type(Types.any)
        if self.force_optional_for_required_fields:
            required: bool = False
        else:
            required = not obj.nullable and not (
                obj.has_default and self.apply_default_values_for_required_fields
            )
        self.model_resolver.add(path, name, loaded=True)
        self.set_title(name, obj)
        self.set_additional_properties(name, additional_properties or obj)
        data_model_root_type = self.data_model_root_type(
            name,
            [
                self.data_model_field_type(
                    data_type=data_type,
                    description=obj.description,
                    example=obj.example,
                    examples=obj.examples,
                    default=obj.default,
                    required=required,
                    constraints=obj.dict() if self.field_constraints else {},
                )
            ],
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
        )
        self.append_result(data_model_root_type)
        return data_model_root_type

    def parse_enum(
        self,
        name: str,
        obj: JsonSchemaObject,
        path: List[str],
        singular_name: bool = False,
        unique: bool = True,
    ) -> DataModel:
        if not unique:  # pragma: no cover
            warn(
                f'{self.__class__.__name__}.parse_enum() ignore `unique` argument.'
                f'An object name must be unique.'
                f'This argument will be removed in a future version'
            )
        enum_fields: List[DataModelFieldBase] = []

        for i, enum_part in enumerate(obj.enum):
            if obj.type == 'string' or isinstance(enum_part, str):
                default = f"'{enum_part}'"
                field_name = enum_part
            else:
                default = enum_part
                if obj.x_enum_varnames:
                    field_name = obj.x_enum_varnames[i]
                else:
                    prefix = (
                        obj.type
                        if isinstance(obj.type, str)
                        else type(enum_part).__name__
                    )
                    field_name = f'{prefix}_{enum_part}'
            enum_fields.append(
                self.data_model_field_type(
                    name=self.model_resolver.get_valid_name(field_name),
                    default=default,
                    data_type=self.data_type_manager.get_data_type(Types.any),
                    required=True,
                )
            )
        enum_name = self.model_resolver.add(
            path,
            name,
            class_name=True,
            singular_name=singular_name,
            singular_name_suffix='Enum',
            unique=True,
            loaded=True,
        ).name
        enum = Enum(
            enum_name,
            fields=enum_fields,
            path=self.current_source_path,
            description=obj.description if self.use_schema_description else None,
        )
        self.append_result(enum)
        return enum

    def _get_ref_body(self, ref: str) -> Dict[Any, Any]:
        if is_url(ref):
            return self._get_ref_body_from_url(ref)
        return self._get_ref_body_from_remote(ref)

    def _get_ref_body_from_url(self, ref: str) -> Dict[Any, Any]:
        cached_ref_body: Optional[Dict[str, Any]] = self.remote_object_cache.get(ref)
        if cached_ref_body:
            return cached_ref_body

        # URL Reference – $ref: 'http://path/to/your/resource' Uses the whole document located on the different server.
        try:
            import httpx
        except ImportError:  # pragma: no cover
            raise Exception(
                f'Please run $pip install datamodel-code-generator[http] to resolve URL Reference ref={ref}'
            )
        raw_body: str = httpx.get(ref).text
        # yaml loader can parse json data.
        ref_body = load_yaml(raw_body)
        self.remote_object_cache[ref] = ref_body
        return ref_body

    def _get_ref_body_from_remote(self, ref: str) -> Dict[Any, Any]:
        # Remote Reference – $ref: 'document.json' Uses the whole document located on the same server and in
        # the same location. TODO treat edge case
        if self.current_source_path and len(self.current_source_path.parts) > 1:
            full_path = self.base_path / self.current_source_path.parent / ref
        else:
            full_path = self.base_path / ref

        ref_full_path = str(full_path)

        cached_ref_body: Optional[Dict[str, Any]] = self.remote_object_cache.get(
            ref_full_path
        )
        if cached_ref_body:
            return cached_ref_body

        # yaml loader can parse json data.
        with full_path.open(encoding=self.encoding) as f:
            ref_body = load_yaml(f)
        self.remote_object_cache[ref_full_path] = ref_body
        return ref_body

    def parse_ref(self, obj: JsonSchemaObject, path: List[str]) -> None:
        if obj.ref:
            reference = self.model_resolver.get(obj.ref)
            if not reference or not reference.loaded:
                # https://swagger.io/docs/specification/using-ref/
                if obj.ref_type == JSONReference.LOCAL:
                    # Local Reference – $ref: '#/definitions/myElement'
                    self.reserved_refs[tuple(self.model_resolver.current_root)].add(obj.ref)  # type: ignore
                elif self.model_resolver.is_after_load(obj.ref):
                    self.reserved_refs[tuple(obj.ref.split('#')[0].split('/'))].add(obj.ref)  # type: ignore
                else:
                    if obj.ref_type == JSONReference.REMOTE and self.root_id_base_path:
                        ref = f'{self.root_id_base_path}/{obj.ref}'
                    else:
                        ref = obj.ref
                    if self.model_resolver.is_external_ref(ref):
                        relative_path, object_path = ref.split('#/')
                    elif self.model_resolver.is_external_root_ref(ref):
                        relative_path, object_path = ref[:-1], ''
                    else:
                        relative_path, object_path = ref, ''

                    models = self._get_ref_body(relative_path)
                    model_name = self.model_resolver.add_ref(obj.ref).name
                    if obj.ref_type == JSONReference.REMOTE:
                        previous_base_path: Optional[Path] = self.base_path
                        self.base_path = (self.base_path / relative_path).parent
                    else:
                        previous_base_path = None
                    relative_paths = relative_path.split('/')
                    self._parse_file(
                        models,
                        model_name,
                        relative_paths,
                        object_path.split('/') if object_path else None,
                    )
                    if previous_base_path:
                        self.base_path = previous_base_path
                    self.model_resolver.add_ref(
                        ref, actual_module_name=''
                    ).loaded = True

        if obj.items:
            if isinstance(obj.items, JsonSchemaObject):
                self.parse_ref(obj.items, path)
            else:
                for item in obj.items:
                    self.parse_ref(item, path)
        if isinstance(obj.additionalProperties, JsonSchemaObject):
            self.parse_ref(obj.additionalProperties, path)
        for item in obj.anyOf:
            self.parse_ref(item, path)
        for item in obj.allOf:
            self.parse_ref(item, path)
        for item in obj.oneOf:
            self.parse_ref(item, path)
        if obj.properties:
            for value in obj.properties.values():
                self.parse_ref(value, path)

    def parse_id(self, obj: JsonSchemaObject, path: List[str]) -> None:
        if obj.id:
            self.model_resolver.add_id(obj.id, path)
        if obj.items:
            if isinstance(obj.items, JsonSchemaObject):
                self.parse_id(obj.items, path)
            else:
                for item in obj.items:
                    self.parse_id(item, path)
        if isinstance(obj.additionalProperties, JsonSchemaObject):  # pragma: no cover
            self.parse_id(obj.additionalProperties, path)
        for item in obj.anyOf:  # pragma: no cover
            self.parse_id(item, path)  # pragma: no cover
        for item in obj.allOf:
            self.parse_id(item, path)  # pragma: no cover
        if obj.properties:
            for value in obj.properties.values():
                self.parse_id(value, path)

    @contextmanager
    def root_id_context(self, root_raw: Dict[str, Any]) -> Generator[None, None, None]:
        root_id: Optional[str] = root_raw.get('$id')
        previous_root_id: Optional[str] = self.root_id
        if root_id:
            try:
                self._get_ref_body(root_id)
            except Exception as e:
                print(f'Parse $id failed. $id={root_id}\n {str(e)}', file=sys.stderr)
                self.root_id = None
            else:
                self.root_id = root_id
        else:
            self.root_id = None
        yield
        self.root_id = previous_root_id

    def parse_raw_obj(self, name: str, raw: Dict[str, Any], path: List[str],) -> None:
        self.parse_obj(name, JsonSchemaObject.parse_obj(raw), path)

    def parse_obj(self, name: str, obj: JsonSchemaObject, path: List[str],) -> None:
        name = self.model_resolver.add(path, name, class_name=True).name
        if obj.is_object:
            self.parse_object(name, obj, path)
        elif obj.is_array:
            self.parse_array(name, obj, path)
        elif obj.enum:
            self.parse_enum(name, obj, path)
        elif obj.allOf:
            self.parse_all_of(name, obj, path)
        else:
            self.parse_root_type(name, obj, path)
        self.parse_ref(obj, path)

    def parse_raw(self) -> None:
        if isinstance(self.source, list) or (
            isinstance(self.source, Path) and self.source.is_dir()
        ):
            self.current_source_path = Path()
            self.model_resolver.after_load_files = {
                s.path.as_posix() for s in self.iter_source
            }

        for source in self.iter_source:
            path_parts = list(source.path.parts)
            if self.current_source_path is not None:
                self.current_source_path = source.path
            with self.model_resolver.current_root_context(path_parts):
                self.raw_obj = load_yaml(source.text)
                if self.class_name:
                    obj_name = self.class_name
                else:
                    # backward compatible
                    obj_name = self.raw_obj.get('title', 'Model')
                    if not self.model_resolver.validate_name(obj_name):
                        raise InvalidClassNameError(obj_name)
                self._parse_file(self.raw_obj, obj_name, path_parts)

        # resolve unparsed json pointer
        for source in self.iter_source:
            path_parts = list(source.path.parts)
            reserved_refs = self.reserved_refs.get(tuple(path_parts))  # type: ignore
            if not reserved_refs:
                continue
            if self.current_source_path is not None:
                self.current_source_path = source.path

            with self.model_resolver.current_root_context(path_parts):
                for reserved_ref in sorted(reserved_refs):
                    if self.model_resolver.add_ref(reserved_ref).loaded:
                        continue
                    file_path, model_path = reserved_ref.split('#', 1)
                    valid_path_parts = [p for p in model_path.split('/') if p]
                    if (
                        len(valid_path_parts) == 1
                        and self.model_resolver.add_ref(f'{file_path}#').loaded
                    ):  # pragma: no cover
                        continue
                    # for root model
                    self.raw_obj = load_yaml(source.text)
                    self.parse_json_pointer(self.raw_obj, reserved_ref, path_parts)

    def parse_json_pointer(
        self, raw: Dict[str, Any], ref: str, path_parts: List[str]
    ) -> None:
        path = ref.split('#', 1)[-1]
        if path[0] == '/':  # pragma: no cover
            path = path[1:]
        object_paths = path.split('/')
        models = get_model_by_path(raw, object_paths)
        model_name = object_paths[-1]

        self.parse_raw_obj(
            model_name, models, [*path_parts, f'#/{object_paths[0]}', *object_paths[1:]]
        )

    def _parse_file(
        self,
        raw: Dict[str, Any],
        obj_name: str,
        path_parts: List[str],
        object_paths: Optional[List[str]] = None,
    ) -> None:
        if object_paths:
            path = [*path_parts, f'#/{object_paths[0]}', *object_paths[1:]]
        else:
            path = path_parts
        reference = self.model_resolver.get(path)
        if reference and reference.loaded:
            return
        with self.model_resolver.current_root_context(path_parts):
            obj_name = self.model_resolver.add(path, obj_name, unique=False).name
            with self.root_id_context(raw):

                # parse $id before parsing $ref
                root_obj = JsonSchemaObject.parse_obj(raw)
                self.parse_id(root_obj, path_parts)
                definitions = raw.get('definitions', {})
                for key, model in definitions.items():
                    obj = JsonSchemaObject.parse_obj(model)
                    self.parse_id(obj, [*path_parts, '#/definitions', key])

                if object_paths:
                    models = get_model_by_path(raw, object_paths)
                    model_name = object_paths[-1]
                    self.parse_obj(model_name, JsonSchemaObject.parse_obj(models), path)
                else:
                    self.parse_obj(obj_name, root_obj, path_parts)
                for key, model in definitions.items():
                    path = [*path_parts, '#/definitions', key]
                    reference = self.model_resolver.get(path)
                    if not reference or not reference.loaded:
                        self.parse_raw_obj(key, model, path)
