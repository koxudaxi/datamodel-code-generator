from typing import List, Optional

from datamodel_code_generator.model import DataModel, DataModelField


class DataClass(DataModel):
    TEMPLATE_FILE_PATH = 'dataclass.jinja2'

    def __init__(self, name: str, fields: List[DataModelField],
                 decorators: Optional[List[str]] = None, base_class: Optional[str] = None):
        super().__init__(name, fields, decorators, base_class)
