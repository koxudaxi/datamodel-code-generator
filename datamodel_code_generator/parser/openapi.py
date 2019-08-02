from typing import Dict, Iterator, List, Set, Type, Union

import inflect
from datamodel_code_generator.parser.base import Parser, get_data_type, JsonSchemaObject
from prance import BaseParser, ResolvingParser

from ..model.base import DataModel, DataModelField, TemplateBase

inflect_engine = inflect.engine()


def dump_templates(templates: Union[TemplateBase, List[TemplateBase]]) -> str:
    if isinstance(templates, TemplateBase):
        templates = [templates]
    return '\n\n\n'.join(str(m) for m in templates)


class OpenAPIParser(Parser):
    def __init__(
        self,
        data_model_type: Type[DataModel],
        data_model_root_type: Type[DataModel],
        data_model_field_type: Type[DataModelField] = DataModelField,
        filename: str = 'api.yaml',
    ):
        self.base_parser = BaseParser(filename, backend='openapi-spec-validator')
        self.resolving_parser = ResolvingParser(
            filename, backend='openapi-spec-validator'
        )
        super().__init__(
            data_model_type, data_model_root_type, data_model_field_type, filename
        )

    def parse_object(self, name: str, obj: JsonSchemaObject) -> Iterator[TemplateBase]:
        requires: Set[str] = set(obj.required or [])
        d_list: List[DataModelField] = []
        for field_name, filed in obj.properties.items():  # type: str, JsonSchemaObject
            if filed.is_array:
                yield from self.parse_array(field_name, filed)
            d_list.append(
                self.data_model_field_type(
                    name=field_name,
                    type_hint=get_data_type(filed).type_hint,
                    required=field_name in requires,
                )
            )
        yield self.data_model_type(name, fields=d_list)

    def parse_array(self, name: str, obj: JsonSchemaObject) -> Iterator[TemplateBase]:
        # continue
        if isinstance(obj.items, JsonSchemaObject):
            items: List[JsonSchemaObject] = [obj.items]
        else:
            items = obj.items
        items_obj_name: List[str] = []
        for item in items:
            if item.ref:
                items_obj_name.append(item.ref.split('/')[-1])
            elif isinstance(item, JsonSchemaObject) and item.properties:
                singular_name: str = inflect_engine.singular_noun(name)
                yield from self.parse_object(singular_name, item)
                items_obj_name.append(singular_name)
            else:
                data_type = get_data_type(obj).type_hint
                items_obj_name.append(data_type)
        yield self.data_model_root_type(name, [DataModelField(type_hint=', '.join(items_obj_name))])

    def parse_root_type(self, name: str, obj: JsonSchemaObject) -> Iterator[TemplateBase]:
        yield self.data_model_root_type(
            name,
            [
                DataModelField(
                    type_hint=get_data_type(obj).type_hint
                )
            ],
        )

    def parse(self) -> str:
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
        return dump_templates(templates)
