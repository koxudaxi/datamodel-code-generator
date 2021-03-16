from typing import ClassVar, Optional

from datamodel_code_generator.model.base import DataModelFieldBase, DataModel


class SchematicsModelField(DataModelFieldBase):

    @property
    def schematics_type(self) -> Optional[str]:
        data_type = self.data_type.full_name
        if not data_type:
            return None
        elif self.nullable is not None:
            if self.nullable:
                return f'{data_type}(required=False)'
            return f'{data_type}(required=True)'
        elif self.required:
            return f'{data_type}(required=True)'
        return f'{data_type}(required=False)'


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'schematics/BaseModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'schematics.BaseModel'
