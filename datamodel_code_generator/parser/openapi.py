from typing import Callable, Dict, List, Optional, Set, Tuple, Type

from datamodel_code_generator import PythonVersion, snooper_to_methods
from datamodel_code_generator.format import format_code
from datamodel_code_generator.imports import IMPORT_ANNOTATIONS
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.parser.base import (
    JsonSchemaObject,
    Parser,
    dump_templates,
    get_singular_name,
    sort_data_models,
)
from datamodel_code_generator.types import DataType
from prance import BaseParser

from ..model.base import DataModel, DataModelField


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(Parser):
    def __init__(
        self,
        data_model_type: Type[DataModel],
        data_model_root_type: Type[DataModel],
        data_model_field_type: Type[DataModelField] = DataModelField,
        filename: Optional[str] = None,
        base_class: Optional[str] = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        text: Optional[str] = None,
        result: Optional[List[DataModel]] = None,
        dump_resolve_reference_action: Optional[Callable[[List[str]], str]] = None,
    ):
        self.base_parser = (
            BaseParser(filename, text, backend='openapi-spec-validator')
            if filename or text
            else None
        )

        super().__init__(
            data_model_type,
            data_model_root_type,
            data_model_field_type,
            filename,
            base_class,
            target_python_version,
            text,
            result,
            dump_resolve_reference_action,
        )

    def parse_any_of(self, name: str, obj: JsonSchemaObject) -> List[DataType]:
        any_of_data_types: List[DataType] = []
        for any_of_item in obj.anyOf:
            if any_of_item.ref:  # $ref
                any_of_data_types.append(
                    self.data_type(
                        type=any_of_item.ref_object_name,
                        ref=True,
                        version_compatible=True,
                    )
                )
            else:
                singular_name = get_singular_name(name)
                self.parse_object(singular_name, any_of_item)
                any_of_data_types.append(
                    self.data_type(
                        type=singular_name, ref=True, version_compatible=True
                    )
                )
        return any_of_data_types

    def parse_all_of(self, name: str, obj: JsonSchemaObject) -> List[DataType]:
        fields: List[DataModelField] = []
        base_classes: List[DataType] = []
        for all_of_item in obj.allOf:
            if all_of_item.ref:  # $ref
                base_classes.append(
                    self.data_type(
                        type=all_of_item.ref_object_name,
                        ref=True,
                        version_compatible=True,
                    )
                )

            else:
                fields_ = self.parse_object_fields(all_of_item)
                fields.extend(fields_)

        data_model_type = self.data_model_type(
            name,
            fields=fields,
            base_classes=[b.type for b in base_classes],
            auto_import=False,
            custom_base_class=self.base_class,
        )
        self.append_result(data_model_type)

        return [self.data_type(type=name, ref=True, version_compatible=True)]

    def parse_object_fields(self, obj: JsonSchemaObject) -> List[DataModelField]:
        requires: Set[str] = set(obj.required or [])
        fields: List[DataModelField] = []

        for field_name, filed in obj.properties.items():  # type: ignore
            is_list = False
            field_types: List[DataType]
            if filed.ref:
                field_types = [
                    self.data_type(
                        type=filed.ref_object_name, ref=True, version_compatible=True
                    )
                ]
            elif filed.is_array:
                class_name = self.get_class_name(field_name)
                array_fields, array_field_classes = self.parse_array_fields(
                    class_name, filed
                )
                field_types = array_fields[0].data_types
                is_list = True
            elif filed.is_object:
                class_name = self.get_class_name(field_name)
                self.parse_object(class_name, filed)
                field_types = [
                    self.data_type(type=class_name, ref=True, version_compatible=True)
                ]
            elif filed.enum:
                enum = self.parse_enum(field_name, filed)
                field_types = [
                    self.data_type(type=enum.name, ref=True, version_compatible=True)
                ]
            elif filed.anyOf:
                field_types = self.parse_any_of(field_name, filed)
            elif filed.allOf:
                field_types = self.parse_all_of(field_name, filed)
            else:
                data_type = self.get_data_type(filed)
                field_types = [data_type]
            required: bool = field_name in requires
            fields.append(
                self.data_model_field_type(
                    name=field_name,
                    data_types=field_types,
                    required=required,
                    is_list=is_list,
                )
            )
        return fields

    def parse_object(self, name: str, obj: JsonSchemaObject) -> None:
        fields = self.parse_object_fields(obj)
        data_model_type = self.data_model_type(
            name, fields=fields, custom_base_class=self.base_class
        )
        self.append_result(data_model_type)

    def parse_array_fields(
        self, name: str, obj: JsonSchemaObject
    ) -> Tuple[List[DataModelField], List[DataType]]:
        if isinstance(obj.items, JsonSchemaObject):
            items: List[JsonSchemaObject] = [obj.items]
        else:
            items = obj.items  # type: ignore
        item_obj_data_types: List[DataType] = []
        is_union: bool = False
        for item in items:
            if item.ref:
                item_obj_data_types.append(
                    self.data_type(
                        type=item.ref_object_name, ref=True, version_compatible=True
                    )
                )
            elif isinstance(item, JsonSchemaObject) and item.properties:
                singular_name = get_singular_name(name)
                self.parse_object(singular_name, item)
                item_obj_data_types.append(
                    self.data_type(
                        type=singular_name, ref=True, version_compatible=True
                    )
                )
            elif item.anyOf:
                item_obj_data_types.extend(self.parse_any_of(name, item))
                is_union = True
            elif item.allOf:
                singular_name = get_singular_name(name)
                item_obj_data_types.extend(self.parse_all_of(singular_name, item))
            else:
                item_obj_data_types.append(self.get_data_type(item))

        field = self.data_model_field_type(
            data_types=item_obj_data_types,
            required=True,
            is_list=True,
            is_union=is_union,
        )
        return [field], item_obj_data_types

    def parse_array(self, name: str, obj: JsonSchemaObject) -> None:
        fields, item_obj_names = self.parse_array_fields(name, obj)
        data_model_root = self.data_model_root_type(
            name, fields, custom_base_class=self.base_class
        )

        self.append_result(data_model_root)

    def parse_root_type(self, name: str, obj: JsonSchemaObject) -> None:
        if obj.type:
            types: List[DataType] = [self.get_data_type(obj)]
        elif obj.anyOf:
            types = self.parse_any_of(name, obj)
        else:
            types = [
                self.data_type(
                    type=obj.ref_object_name, ref=True, version_compatible=True
                )
            ]

        data_model_root_type = self.data_model_root_type(
            name,
            [self.data_model_field_type(data_types=types, required=not obj.nullable)],
            custom_base_class=self.base_class,
        )
        self.append_result(data_model_root_type)

    def parse_enum(self, name: str, obj: JsonSchemaObject) -> DataModel:
        enum_fields = []

        for enum_part in obj.enum:  # type: ignore
            if obj.type == 'string':
                default = f"'{enum_part}'"
                field_name = enum_part
            else:
                default = enum_part
                field_name = f'{obj.type}_{enum_part}'
            enum_fields.append(
                self.data_model_field_type(name=field_name, default=default)
            )

        enum = Enum(self.get_class_name(name), fields=enum_fields)
        self.append_result(enum)
        return enum

    def parse(
        self, with_import: Optional[bool] = True, format_: Optional[bool] = True
    ) -> str:
        for obj_name, raw_obj in self.base_parser.specification['components'][
            'schemas'
        ].items():  # type: str, Dict
            obj = JsonSchemaObject.parse_obj(raw_obj)
            if obj.is_object:
                self.parse_object(obj_name, obj)
            elif obj.is_array:
                self.parse_array(obj_name, obj)
            elif obj.enum:
                self.parse_enum(obj_name, obj)
            elif obj.allOf:
                self.parse_all_of(obj_name, obj)
            else:
                self.parse_root_type(obj_name, obj)

        result: str = ''
        if with_import:
            if self.target_python_version == PythonVersion.PY_37:
                self.imports.append(IMPORT_ANNOTATIONS)
            result += f'{self.imports.dump()}\n\n\n'

        _, sorted_data_models, require_update_action_models = sort_data_models(
            self.results
        )

        result += dump_templates(list(sorted_data_models.values()))
        if self.dump_resolve_reference_action:
            result += f'\n\n{self.dump_resolve_reference_action(require_update_action_models)}'

        if format_:
            result = format_code(result, self.target_python_version)

        return result
