from typing import Any, Dict

from datamodel_code_generator import load_json_or_yaml, snooper_to_methods
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(JsonSchemaParser):
    def parse_raw(self) -> None:
        if self.validation:
            from prance import BaseParser

            base_parser = BaseParser(
                spec_string=self.text, backend='openapi-spec-validator'
            )
            components: Dict[str, Any] = base_parser.specification['components']
        else:
            components = load_json_or_yaml(self.text)['components']  # type: ignore

        for obj_name, raw_obj in components[
            'schemas'
        ].items():  # type: str, Dict[Any, Any]
            self.parse_raw_obj(obj_name, raw_obj)
