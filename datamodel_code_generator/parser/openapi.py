from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple, Type, Union

import black
import inflect
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.parser.base import (
    JsonSchemaObject,
    Parser,
    get_data_type,
    resolve_references,
    snake_to_upper_camel,
)
from datamodel_code_generator.types import Import
from isort import SortImports
from prance import BaseParser, ResolvingParser

from ..model.base import DataModel, DataModelField, TemplateBase

inflect_engine = inflect.engine()

IMPORT_LIST = Import(import_='List', from_='typing')
IMPORT_OPTIONAL = Import(import_='Optional', from_='typing')


def dump_templates(templates: Union[TemplateBase, List[TemplateBase]]) -> str:
    if isinstance(templates, TemplateBase):
        templates = [templates]
    return '\n\n\n'.join(str(m) for m in templates)


def create_class_name(field_name: str) -> str:
    upper_camel_name = snake_to_upper_camel(field_name)
    return upper_camel_name


class OpenAPIParser(Parser):
    def __init__(
        self,
        data_model_type: Type[DataModel],
        data_model_root_type: Type[DataModel],
        data_model_field_type: Type[DataModelField] = DataModelField,
        filename: Optional[str] = None,
        base_class: Optional[str] = None,
        target_python_version: str = '3.7',
        text: Optional[str] = None,
        dump_resolve_reference_action: Optional[Callable[[List[str]], str]] = None,
    ):
        self.base_parser = (
            BaseParser(filename, text, backend='openapi-spec-validator')
            if filename or text
            else None
        )
        self.resolving_parser = (
            ResolvingParser(filename, text, backend='openapi-spec-validator')
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
            dump_resolve_reference_action,
        )

    def parse_object(self, name: str, obj: JsonSchemaObject) -> Iterator[TemplateBase]:
        requires: Set[str] = set(obj.required or [])
        fields: List[DataModelField] = []
        field_class_names: Set[str] = set()
        for field_name, filed in obj.properties.items():  # type: ignore
            if filed.ref:
                self.add_unresolved_classes(name, filed.ref_object_name)
                field_type_hint = self.get_type_name(filed.ref_object_name)
            elif filed.is_array or filed.is_object:
                class_name = create_class_name(field_name)
                if filed.is_array:
                    models = list(self.parse_array(class_name, filed))
                    yield from models[:-1]
                    root_model = models[-1]
                    field_type_hint: str = root_model.fields[  # type: ignore
                        0
                    ].type_hint
                    if class_name in self.unresolved_classes:  # pragma: no cover
                        field_class_names = (
                            field_class_names | self.unresolved_classes.pop(class_name)
                        )
                else:
                    yield from self.parse_object(class_name, filed)
                    field_class_names.add(class_name)
                    field_type_hint = self.get_type_name(class_name)
            elif filed.enum:
                enum_name = self.get_type_name(field_name)
                field_type_hint, enum = self.parse_enum(enum_name, filed)
                yield enum
            else:
                data_type = get_data_type(filed, self.data_model_type)
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
        data_model_type = self.data_model_type(
            name, fields=fields, base_class=self.base_class
        )
        self.imports.append(data_model_type.imports)
        self.created_model_names.add(name)
        self.add_unresolved_classes(name, list(field_class_names))
        yield data_model_type

    def parse_array(self, name: str, obj: JsonSchemaObject) -> Iterator[TemplateBase]:
        if isinstance(obj.items, JsonSchemaObject):
            items: List[JsonSchemaObject] = [obj.items]
        else:
            items = obj.items  # type: ignore
        items_obj_name: List[str] = []
        reference_obj_class: List[str] = []
        for item in items:
            if item.ref:
                class_name = self.get_type_name(item.ref_object_name)
                items_obj_name.append(class_name)
                reference_obj_class.append(class_name)
            elif isinstance(item, JsonSchemaObject) and item.properties:
                singular_name = inflect_engine.singular_noun(name)
                if singular_name is False:
                    singular_name = f'{name}Item'
                yield from self.parse_object(singular_name, item)
                items_obj_name.append(self.get_type_name(singular_name))
                print(singular_name)
            else:
                data_type = get_data_type(item, self.data_model_type)
                items_obj_name.append(data_type.type_hint)
                self.imports.append(data_type.import_)
        if items_obj_name:
            if reference_obj_class:
                self.add_unresolved_classes(name, reference_obj_class)
            support_types = ', '.join(items_obj_name)
            type_hint: str = f'List[{support_types}]'
        else:
            type_hint = 'List'
        self.imports.append(IMPORT_LIST)
        self.created_model_names.add(name)
        yield self.data_model_root_type(
            name,
            [DataModelField(type_hint=type_hint, required=True)],
            base_class=self.base_class,
        )

    def parse_root_type(
        self, name: str, obj: JsonSchemaObject
    ) -> Iterator[TemplateBase]:
        if obj.type:
            data_type = get_data_type(obj, self.data_model_type)
            self.imports.append(data_type.import_)
            if obj.nullable:
                self.imports.append(IMPORT_OPTIONAL)
            type_hint: str = data_type.type_hint
        else:
            self.add_unresolved_classes(name, obj.ref_object_name)
            type_hint = self.get_type_name(obj.ref_object_name)
        data_model_root_type = self.data_model_root_type(
            name,
            [
                self.data_model_field_type(
                    type_hint=type_hint, required=not obj.nullable
                )
            ],
            base_class=self.base_class,
        )
        self.imports.append(data_model_root_type.imports)
        self.created_model_names.add(name)
        yield data_model_root_type

    def parse_enum(self, name: str, obj: JsonSchemaObject) -> Tuple[str, TemplateBase]:
        enum_fields = []

        for enum_part in obj.enum:  # type: ignore
            if obj.type == 'string':
                default = f"'{enum_part}'"
            else:
                default = enum_part
            if obj.type == 'string':
                field_name = enum_part
            else:
                field_name = f'{obj.type}_{enum_part}'
            enum_fields.append(
                self.data_model_field_type(name=field_name, default=default)
            )
        enum_name = name
        count = 1
        while enum_name in self.created_model_names:
            enum_name = f'{name}_{count}'
            count += 1
        enum_name = create_class_name(enum_name)
        self.imports.append(Import(import_='Enum', from_='enum'))
        self.created_model_names.add(enum_name)
        return enum_name, Enum(enum_name, fields=enum_fields)

    def parse(
        self, with_import: Optional[bool] = True, format_: Optional[bool] = True
    ) -> str:
        templates: List[TemplateBase] = []
        for obj_name, raw_obj in self.base_parser.specification['components'][
            'schemas'
        ].items():  # type: str, Dict
            obj = JsonSchemaObject.parse_obj(raw_obj)
            if obj.is_object:
                templates.extend(self.parse_object(obj_name, obj))
            elif obj.is_array:
                templates.extend(self.parse_array(obj_name, obj))
            elif obj.enum:
                templates.append(self.parse_enum(obj_name, obj)[1])
            else:
                templates.extend(self.parse_root_type(obj_name, obj))

        result: str = ''
        if with_import:
            if self.target_python_version == '3.7':
                self.imports.append(Import(from_='__future__', import_='annotations'))
            result += f'{self.imports.dump()}\n\n\n'
        result += dump_templates(templates)
        if self.dump_resolve_reference_action:
            resolved_references, _ = resolve_references(
                list(self.created_model_names), self.unresolved_classes
            )
            result += f'\n\n{self.dump_resolve_reference_action(list(self.unresolved_classes))}'
        if format_:
            result = black.format_str(
                result,
                mode=black.FileMode(
                    target_versions={black.TargetVersion.PY36},
                    string_normalization=False,
                ),
            )
            result = SortImports(file_contents=result).output

        return result
