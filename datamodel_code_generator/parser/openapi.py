from typing import Dict, Iterator, List, Optional, Set, Type, Union

import black
import inflect
from datamodel_code_generator.parser.base import (
    JsonSchemaObject,
    Parser,
    get_data_type,
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
    if upper_camel_name == field_name:
        upper_camel_name += '_'
    return upper_camel_name


class OpenAPIParser(Parser):
    def __init__(
        self,
        data_model_type: Type[DataModel],
        data_model_root_type: Type[DataModel],
        data_model_field_type: Type[DataModelField] = DataModelField,
        filename: Optional[str] = None,
        base_class: Optional[str] = None,
    ):
        self.base_parser = (
            BaseParser(filename, backend='openapi-spec-validator') if filename else None
        )
        self.resolving_parser = (
            ResolvingParser(filename, backend='openapi-spec-validator')
            if filename
            else None
        )

        super().__init__(
            data_model_type,
            data_model_root_type,
            data_model_field_type,
            filename,
            base_class,
        )

    def parse_object(self, name: str, obj: JsonSchemaObject) -> Iterator[TemplateBase]:
        requires: Set[str] = set(obj.required or [])
        fields: List[DataModelField] = []
        for field_name, filed in obj.properties.items():  # type: ignore
            if filed.is_array or filed.is_object:
                class_name = create_class_name(field_name)
                if filed.is_array:
                    yield from self.parse_array(class_name, filed)
                else:
                    yield from self.parse_object(class_name, filed)
                field_type_hint: str = class_name
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
        yield data_model_type

    def parse_array(self, name: str, obj: JsonSchemaObject) -> Iterator[TemplateBase]:
        if isinstance(obj.items, JsonSchemaObject):
            items: List[JsonSchemaObject] = [obj.items]
        else:
            items = obj.items  # type: ignore
        items_obj_name: List[str] = []
        for item in items:
            if item.ref:
                items_obj_name.append(item.ref.split('/')[-1])
            elif isinstance(item, JsonSchemaObject) and item.properties:
                singular_name = inflect_engine.singular_noun(name)
                if singular_name is False:
                    singular_name = f'{name}Item'
                yield from self.parse_object(singular_name, item)
                items_obj_name.append(singular_name)
            else:
                data_type = get_data_type(item, self.data_model_type)
                items_obj_name.append(data_type.type_hint)
                self.imports.append(data_type.import_)
        support_types = f', '.join(items_obj_name)
        self.imports.append(IMPORT_LIST)
        yield self.data_model_root_type(
            name,
            [DataModelField(type_hint=f'List[{support_types}]', required=True)],
            base_class=self.base_class,
        )

    def parse_root_type(
        self, name: str, obj: JsonSchemaObject
    ) -> Iterator[TemplateBase]:
        data_type = get_data_type(obj, self.data_model_type)
        self.imports.append(data_type.import_)
        if obj.nullable:
            self.imports.append(IMPORT_OPTIONAL)
        data_model_root_type = self.data_model_root_type(
            name,
            [
                self.data_model_field_type(
                    type_hint=data_type.type_hint, required=not obj.nullable
                )
            ],
            base_class=self.base_class,
        )
        self.imports.append(data_model_root_type.imports)
        yield data_model_root_type

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
            else:
                templates.extend(self.parse_root_type(obj_name, obj))

        result: str = ''
        if with_import:
            result += f'{self.imports.dump()}\n\n\n'
        result += dump_templates(templates)
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
