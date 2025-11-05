from __future__ import annotations

from datamodel_code_generator.model.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.model.strawberry.imports import IMPORT_STRAWBERRY_ID
from datamodel_code_generator.types import DataType, Types


class DataTypeManager(_DataTypeManager):
    def get_data_type(self, types: Types, **kwargs: str | bool | None) -> DataType:
        if types == Types.uuid or (types == Types.string and (kwargs.get("format") == "uuid" or kwargs.get("format__") == "uuid")):
            return DataType.from_import(IMPORT_STRAWBERRY_ID)
        return super().get_data_type(types, **kwargs)
    
    def get_data_type_from_full_path(self, full_path: str, is_custom_type: bool = False) -> DataType:
        # Map GraphQL built-in types to Python types
        graphql_to_python = {
            "String": "str",
            "Int": "int", 
            "Float": "float",
            "Boolean": "bool",
            "ID": "strawberry.ID",
        }
        
        if full_path in graphql_to_python:
            if full_path == "ID":
                return DataType.from_import(IMPORT_STRAWBERRY_ID)
            else:
                return DataType(type=graphql_to_python[full_path])
        
        return super().get_data_type_from_full_path(full_path, is_custom_type)
