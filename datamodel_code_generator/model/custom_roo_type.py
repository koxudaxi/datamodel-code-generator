from datamodel_code_generator.model.base import TemplateBase


class CustomRootType(TemplateBase):
    def __init__(self, name: str, _type: str):
        self.name = name
        self.type = _type
        super().__init__(template_file_path='pydantic/BaseModel_root.jinja2')

    def render(self) -> str:
        return self._render(class_name=self.name, _type=self.type)
