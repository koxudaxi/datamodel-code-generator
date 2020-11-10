from typing import Any, Dict, Optional

import yaml

from datamodel_code_generator import snooper_to_methods
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser


@snooper_to_methods(max_variable_length=None)
class OpenAPIParser(JsonSchemaParser):
    def parse_raw(self) -> None:
        for source in self.iter_source:
            if self.validation:
                from prance import BaseParser

                base_parser = BaseParser(
                    spec_string=source.text, backend='openapi-spec-validator'
                )
                specification: Dict[str, Any] = base_parser.specification
            else:
                specification = yaml.safe_load(source.text)
            self.raw_obj = specification
            schemas: Optional[Dict[Any, Any]] = specification.get('components', {}).get(
                'schemas'
            )
            if not schemas:  # pragma: no cover
                continue
            self.model_resolver.set_current_root(list(source.path.parts))
            for obj_name, raw_obj in schemas.items():  # type: str, Dict[Any, Any]
                self.parse_raw_obj(
                    obj_name, raw_obj, ['components', 'schemas', obj_name]
                )
