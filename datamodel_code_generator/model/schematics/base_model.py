from typing import ClassVar

from datamodel_code_generator.model.base import DataModelFieldBase, DataModel


class SchematicsModelField(DataModelFieldBase):

    @property
    def type_hint(self) -> str:
        return ''

    @property
    def schematics_type(self) -> str:
        return ''

        # if not type_hint:
        #     return OPTIONAL
        # elif self.nullable is not None:
        #     if self.nullable:
        #         return f'{OPTIONAL}[{type_hint}]'
        #     return type_hint
        # elif self.required:
        #     return type_hint
        # return f'{OPTIONAL}[{type_hint}]'


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'schematics/BaseModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'schematics.BaseModel'
