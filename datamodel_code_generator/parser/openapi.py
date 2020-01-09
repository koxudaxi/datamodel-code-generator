from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Set, Tuple, Type

from datamodel_code_generator import PythonVersion, snooper_to_methods
from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.parser.base import get_singular_name
from datamodel_code_generator.parser.jsonschema import (
    JsonSchemaObject,
    JsonSchemaParser,
    json_schema_data_formats,
)
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
