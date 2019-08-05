from typing import Any, List, Optional

from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.model.pydantic.types import get_data_type, type_map
from datamodel_code_generator.types import DataType, Types


class DataClass(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/dataclass.jinja2'
    FROM_ = 'pydantic.dataclasses'
    IMPORT_ = 'pydantic.dataclasses.dataclass'
    DATA_TYPE_MAP = type_map

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_class: Optional[str] = None,
    ):

        super().__init__(name, fields, decorators, base_class)

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        return get_data_type(types, **kwargs)
