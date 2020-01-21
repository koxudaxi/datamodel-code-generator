from typing import Dict

from datamodel_code_generator import snooper_to_methods
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from prance import BaseParser


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(JsonSchemaParser):
    def parse_raw(self) -> None:
        base_parser = BaseParser(
            spec_string=self.text, backend='openapi-spec-validator'
        )

        for obj_name, raw_obj in base_parser.specification['components'][
            'schemas'
        ].items():  # type: str, Dict
            self.parse_raw_obj(obj_name, raw_obj)
