from typing import ClassVar, Optional

from datamodel_code_generator.model.base import DataModelFieldBase, DataModel


class SchematicsModelField(DataModelFieldBase):

    @property
    def schematics_type(self) -> Optional[str]:

        data_type_name = None

        if self.data_type.is_list:
            data_types = self.data_type.data_types
            if self.data_type.is_list and len(data_types) > 0:
                data_type_name = f'ListType(ModelType({data_types[-1].reference.name}), '
        elif self.data_type.reference is not None:
            data_type_name = f'ModelType({self.data_type.reference.name}, '
        else:
            data_type_name = f'{self.data_type.full_name}('

        is_required = self.nullable is not None and self.nullable or self.required
        schematic_args = f'required={"True" if is_required else "False"}, serialized_name="{self.name}")'
        full_type = f'{data_type_name}{schematic_args}'
        return full_type


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'schematics/BaseModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'schematics.BaseModel'
