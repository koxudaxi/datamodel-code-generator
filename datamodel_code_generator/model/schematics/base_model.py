from typing import ClassVar, Optional, Any, Tuple

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.base import DataModelFieldBase, DataModel
from datamodel_code_generator.model.schematics.imports import IMPORT_MODEL, IMPORT_LIST
from datamodel_code_generator.types import chain_as_tuple


class SchematicsModelField(DataModelFieldBase):

    @property
    def serialized_name(self) -> str:
        return self.name

    @property
    def imports(self) -> Tuple[Import, ...]:
        imports_ = (IMPORT_LIST,) if self.data_type.is_list else ()
        if self.is_model_type:
            imports_ = chain_as_tuple(imports_, (IMPORT_MODEL,))
        return chain_as_tuple(self.data_type.all_imports, imports_)

    @property
    def is_model_type(self) -> bool:
        return self.data_type.reference if self.data_type.reference is not None \
            else len(self.data_type.data_types) > 0 and self.data_type.data_types[-1].reference is not None

    @property
    def model_name(self) -> Optional[str]:
        return self.data_type.reference.name if self.data_type.reference is not None \
            else len(self.data_type.data_types) > 0 and self.data_type.data_types[-1].reference.name

    @property
    def is_required(self) -> bool:
        return self.nullable is not None and self.nullable or self.required

    @property
    def is_list(self) -> bool:
        return self.data_type.is_list

    @property
    def schematics_type(self) -> Optional[str]:
        return self.model_name if self.is_model_type else self.data_type.full_name

    @property
    def inline_value(self) -> str:
        if self.is_list and not self.is_model_type:
            assembled_string = f"ListType({self.schematics_type}"
        elif self.is_list and self.is_model_type:
            assembled_string = f"ListType(ModelType({self.schematics_type})"
        elif self.is_model_type:
            assembled_string = f"ModelType({self.schematics_type}"
        else:
            assembled_string = f"{self.schematics_type}("

        assembled_string += ")"
        return assembled_string


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'schematics/BaseModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'schematics.BaseModel'

    @property
    def imports(self) -> Tuple[Import, ...]:
        return chain_as_tuple(
            (i for f in self.fields for i in f.imports), self._additional_imports
        )
