from typing import Any, List, Optional

from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.types import DataType, Types


class Enum(DataModel):
    TEMPLATE_FILE_PATH = 'Enum.jinja2'
    BASE_CLASS = 'enum.Enum'

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
    ):
        super().__init__(name=name, fields=fields, decorators=decorators)

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        raise NotImplementedError
