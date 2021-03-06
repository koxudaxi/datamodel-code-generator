from datamodel_code_generator.model.pydantic.base_model import BaseModel


class CustomRootType(BaseModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel_root.jinja2'
    BASE_CLASS = 'pydantic.BaseModel'
