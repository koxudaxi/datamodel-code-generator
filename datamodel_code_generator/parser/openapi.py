from typing import Callable, Dict, List, Optional, Set, Tuple, Type, Union

from datamodel_code_generator import PythonVersion
from datamodel_code_generator.format import format_code
from datamodel_code_generator.imports import (
    IMPORT_ANNOTATIONS,
    IMPORT_LIST,
    IMPORT_OPTIONAL,
)
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.parser.base import (  # resolve_references,
    ClassNames,
    JsonSchemaObject,
    Parser,
    dump_templates,
    get_singular_name,
    sort_data_models,
)
from prance import BaseParser

from ..model.base import DataModel, DataModelField


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
                any_of_item_names.add(singular_name, ref=True, version_compatible=True)
        return any_of_item_names

    def parse_all_of(self, name: str, obj: JsonSchemaObject) -> ClassNames:
        all_of_name = ClassNames(self.target_python_version)
        if not obj.allOf:  # pragma: no cover
            return all_of_name
        fields: List[DataModelField] = []
        all_of_item_names: ClassNames = ClassNames(self.target_python_version)
        base_classes: ClassNames = ClassNames(self.target_python_version)
        for all_of_item in obj.allOf:
            if all_of_item.ref:  # $ref
                base_classes.add(
                    all_of_item.ref_object_name, ref=True, version_compatible=True
                )

            else:
                fields_, class_names = self.parse_object_fields(all_of_item)
                fields.extend(fields_)
                all_of_item_names.extend(class_names)

        if base_classes.class_names:
            base_class_names: List[str] = base_classes.class_names
        else:
            base_class_names = [self.base_class] if self.base_class else []

        data_model_type = self.data_model_type(
            name,
            fields=fields,
            base_classes=base_class_names,
            auto_import=False,
            reference_classes=all_of_item_names.unresolved_class_names
            + base_class_names,
        )
        all_of_item_names.extend(base_classes)
        self.append_result(data_model_type)

        all_of_name.add(name, ref=True, version_compatible=True)
        return all_of_name

    def parse_object_fields(
        self, obj: JsonSchemaObject
    ) -> Tuple[List[DataModelField], ClassNames]:
        requires: Set[str] = set(obj.required or [])
        fields: List[DataModelField] = []
        field_types: Union[List[str], str]
        field_all_class_names: ClassNames = ClassNames(self.target_python_version)
        for field_name, filed in obj.properties.items():  # type: ignore
            field_class_names: ClassNames = ClassNames(self.target_python_version)
            if filed.ref:
                field_class_names.add(
                    filed.ref_object_name, ref=True, version_compatible=True
                )
                field_types = field_class_names.get_types()
            elif filed.is_array:
                class_name = self.get_class_name(field_name)
                array_fields, array_field_classes = self.parse_array_fields(
                    class_name, filed
                )
                field_types = array_fields[0].type_hint
                field_class_names = array_field_classes
            elif filed.is_object:
                class_name = self.get_class_name(field_name)
                self.parse_object(class_name, filed)
                field_class_names.add(class_name, ref=True, version_compatible=True)
                field_types = field_class_names.get_types()
            elif filed.enum:
                self.parse_enum(field_name, filed)
                field_class_names.add(
                    self.results[-1].name, ref=True, version_compatible=True
                )
                field_types = field_class_names.get_types()
            elif filed.anyOf:
                any_of_item_names = self.parse_any_of(field_name, filed)
                field_types = any_of_item_names.get_types()
                field_all_class_names.extend(any_of_item_names)
            elif filed.allOf:
                all_of_item_names = self.parse_all_of(field_name, filed)
                field_types = all_of_item_names.get_types()
                field_all_class_names.extend(all_of_item_names)
            else:
                data_type = self.get_data_type(filed)
                self.imports.append(data_type.import_)
                field_types = data_type.type_hint
            required: bool = field_name in requires
            if not required:
                self.imports.append(IMPORT_OPTIONAL)
            fields.append(
                self.data_model_field_type(
                    name=field_name,
                    types=field_types,
                    required=required,
                    base_classes=[self.base_class] if self.base_class else [],
                )
            )
            field_all_class_names.extend(field_class_names)
        return fields, field_all_class_names

    def parse_object(self, name: str, obj: JsonSchemaObject) -> None:
        fields, field_all_class_names = self.parse_object_fields(obj)
        data_model_type = self.data_model_type(
            name,
            fields=fields,
            base_classes=[self.base_class] if self.base_class else [],
            reference_classes=field_all_class_names.unresolved_class_names,
        )
        self.append_result(data_model_type)

    def parse_array_fields(
        self, name: str, obj: JsonSchemaObject
    ) -> Tuple[List[DataModelField], ClassNames]:
        if isinstance(obj.items, JsonSchemaObject):
            items: List[JsonSchemaObject] = [obj.items]
        else:
            items = obj.items  # type: ignore
        item_obj_names: ClassNames = ClassNames(self.target_python_version)
        is_union: bool = False
        for item in items:
            if item.ref:
                item_obj_names.add(
                    item.ref_object_name, ref=True, version_compatible=True
                )
            elif isinstance(item, JsonSchemaObject) and item.properties:
                singular_name = get_singular_name(name)
                self.parse_object(singular_name, item)
                item_obj_names.add(singular_name, ref=True, version_compatible=True)
            elif item.anyOf:
                any_of_item_names = self.parse_any_of(name, item)
                for type_ in any_of_item_names.get_types():
                    item_obj_names.add(type_)
                item_obj_names.add_unresolved_name(name)
                is_union = True
            elif item.allOf:
                singular_name = get_singular_name(name)
                all_of_item_names = self.parse_all_of(singular_name, item)
                for type_ in all_of_item_names.get_types():
                    item_obj_names.add(type_)
                item_obj_names.add_unresolved_name(singular_name)
            else:
                data_type = self.get_data_type(item)
                item_obj_names.add(data_type.type_hint)
                self.imports.append(data_type.import_)
        self.imports.append(IMPORT_LIST)
        field = DataModelField(
            types=item_obj_names.get_types(),
            required=True,
            is_list=True,
            is_union=is_union,
        )
        return [field], item_obj_names

    def parse_array(self, name: str, obj: JsonSchemaObject) -> None:
        fields, item_obj_names = self.parse_array_fields(name, obj)
        data_model_root = self.data_model_root_type(
            name,
            fields,
            base_classes=[self.base_class] if self.base_class else [],
            imports=[IMPORT_LIST],
            reference_classes=item_obj_names.unresolved_class_names,
        )

        self.append_result(data_model_root)

    def parse_root_type(self, name: str, obj: JsonSchemaObject) -> None:
        reference_classes: List[str] = []
        if obj.type:
            data_type = self.get_data_type(obj)
            self.imports.append(data_type.import_)
            if obj.nullable:
                self.imports.append(IMPORT_OPTIONAL)
            types: Union[str, List[str]] = data_type.type_hint
        elif obj.anyOf:
            any_of_item_names = self.parse_any_of(name, obj)
            types = any_of_item_names.get_types()
        else:
            obj_names: ClassNames = ClassNames(self.target_python_version)
            obj_names.add(obj.ref_object_name, ref=True, version_compatible=True)
            reference_classes.append(obj.ref_object_name)
            types = obj_names.get_types()
        data_model_root_type = self.data_model_root_type(
            name,
            [self.data_model_field_type(types=types, required=not obj.nullable)],
            base_classes=[self.base_class] if self.base_class else [],
            reference_classes=reference_classes,
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
