from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple, Type

from datamodel_code_generator import PythonVersion
from datamodel_code_generator.format import format_code
from datamodel_code_generator.imports import (
    IMPORT_ANNOTATIONS,
    IMPORT_LIST,
    IMPORT_OPTIONAL,
)
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.parser.base import (
    ClassNames,
    JsonSchemaObject,
    Parser,
    dump_templates,
    get_singular_name,
    resolve_references,
)
from prance import BaseParser

from ..model.base import DataModel, DataModelField, TemplateBase


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

    def parse_any_of(self, name: str, obj: JsonSchemaObject) -> ClassNames:
        any_of_item_names: ClassNames = ClassNames(self.target_python_version)
        if not obj.anyOf:  # pragma: no cover
            return any_of_item_names
        for any_of_item in obj.anyOf:
            if any_of_item.ref:  # $ref
                any_of_item_names.add(
                    any_of_item.ref_object_name, ref=True, version_compatible=True
                )
            else:
                singular_name = get_singular_name(name)
                self.parse_object(singular_name, any_of_item)
                any_of_item_names.add(singular_name, version_compatible=True)
        return any_of_item_names

    def parse_object(self, name: str, obj: JsonSchemaObject) -> None:
        requires: Set[str] = set(obj.required or [])
        fields: List[DataModelField] = []
        unresolved_class_names: List[str] = []
        for field_name, filed in obj.properties.items():  # type: ignore
            field_class_names: ClassNames = ClassNames(self.target_python_version)
            if filed.ref:
                field_class_names.add(filed.ref_object_name, version_compatible=True)
                field_type_hint = field_class_names.get_type()
            elif filed.is_array:
                class_name = self.get_class_name(field_name)
                array_field, array_field_classes = self.parse_array_field(class_name, filed)
                field_type_hint: str = array_field.type_hint
                field_class_names = array_field_classes
            elif filed.is_object:
                class_name = self.get_class_name(field_name)
                self.parse_object(class_name, filed)
                field_class_names.add(class_name, version_compatible=True)
                field_type_hint = field_class_names.get_type()
            elif filed.enum:
                self.parse_enum(field_name, filed)
                field_class_names.add(self.result[-1].name, version_compatible=True)
                field_type_hint = field_class_names.get_type()
            elif filed.anyOf:
                any_of_item_names = self.parse_any_of(field_name, filed)
                field_type_hint = any_of_item_names.get_union_type()
                unresolved_class_names.extend(any_of_item_names.unresolved_class_names)
            else:
                data_type = self.get_data_type(filed)
                self.imports.append(data_type.import_)
                field_type_hint = data_type.type_hint
            required: bool = field_name in requires
            if not required:
                self.imports.append(IMPORT_OPTIONAL)
            fields.append(
                self.data_model_field_type(
                    name=field_name,
                    type_hint=field_type_hint,
                    required=required,
                    base_class=self.base_class,
                )
            )
            unresolved_class_names.extend(field_class_names.unresolved_class_names)
        data_model_type = self.data_model_type(
            name, fields=fields, base_class=self.base_class
        )
        self.add_unresolved_classes(name, unresolved_class_names)
        self.append_result(data_model_type)

    def _parse_array(self, name: str, obj: JsonSchemaObject) -> Tuple[DataModel, ClassNames]:
        if isinstance(obj.items, JsonSchemaObject):
            items: List[JsonSchemaObject] = [obj.items]
        else:
            items = obj.items  # type: ignore
        item_obj_names: ClassNames = ClassNames(self.target_python_version)
        for item in items:
            if item.ref:
                item_obj_names.add(
                    item.ref_object_name, ref=True, version_compatible=True
                )
            elif isinstance(item, JsonSchemaObject) and item.properties:
                singular_name = get_singular_name(name)
                self.parse_object(singular_name, item)
                item_obj_names.add(singular_name, version_compatible=True)
            elif item.anyOf:
                any_of_item_names = self.parse_any_of(name, item)
                item_obj_names.add(any_of_item_names.get_union_type())
            else:
                data_type = self.get_data_type(item)
                item_obj_names.add(data_type.type_hint)
                self.imports.append(data_type.import_)
        data_model_root = self.data_model_root_type(
            name,
            [
                DataModelField(
                    type_hint=item_obj_names.get_list_type(), required=True
                )
            ],
            base_class=self.base_class,
            imports=[IMPORT_LIST],
        )

        return data_model_root, item_obj_names

    def parse_array_field(self, name: str, obj: JsonSchemaObject) -> Tuple[DataModelField, ClassNames]:
        data_model_root, item_obj_names = self._parse_array(name, obj)
        return data_model_root.fields[0], item_obj_names

    def parse_array(self, name: str, obj: JsonSchemaObject) -> None:
        data_model_root, item_obj_names = self._parse_array(name, obj)
        self.add_unresolved_classes(name, item_obj_names.unresolved_class_names)
        self.append_result(data_model_root)

    def parse_root_type(self, name: str, obj: JsonSchemaObject) -> None:
        if obj.type:
            data_type = self.get_data_type(obj)
            self.imports.append(data_type.import_)
            if obj.nullable:
                self.imports.append(IMPORT_OPTIONAL)
            type_hint: str = data_type.type_hint
        elif obj.anyOf:
            any_of_item_names = self.parse_any_of(name, obj)
            type_hint = any_of_item_names.get_union_type()
        else:
            obj_names: ClassNames = ClassNames(self.target_python_version)
            obj_names.add(obj.ref_object_name, ref=True, version_compatible=True)
            self.add_unresolved_classes(name, obj.ref_object_name)
            type_hint = obj_names.get_type()
        data_model_root_type = self.data_model_root_type(
            name,
            [
                self.data_model_field_type(
                    type_hint=type_hint, required=not obj.nullable
                )
            ],
            base_class=self.base_class,
        )
        self.append_result(data_model_root_type)

    def parse_enum(self, name: str, obj: JsonSchemaObject) -> None:
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

        enum_name = self.get_class_name(name)
        self.append_result(Enum(enum_name, fields=enum_fields))

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
            else:
                self.parse_root_type(obj_name, obj)

        result: str = ''
        if with_import:
            if self.target_python_version == PythonVersion.PY_37:
                self.imports.append(IMPORT_ANNOTATIONS)
            result += f'{self.imports.dump()}\n\n\n'
        result += dump_templates(self.result)
        if self.dump_resolve_reference_action:
            resolved_references, _ = resolve_references(
                list(self.created_model_names), self.unresolved_classes
            )
            result += f'\n\n{self.dump_resolve_reference_action(list(self.unresolved_classes))}'
        if format_:
            result = format_code(result, self.target_python_version)

        return result
