from datamodel_code_generator.model.base import TemplateBase


class Alias(TemplateBase):
    def __init__(self, name: str, _type: str):
        self.name = name
        self.type = _type
        super().__init__(template_file_name='alias.mako')

    def render(self) -> str:
        return self._render(name=self.name, _type=self.type)
