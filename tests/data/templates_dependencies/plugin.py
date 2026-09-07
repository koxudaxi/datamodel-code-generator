"""External model implementations exercising the public parser extension API."""
from pathlib import Path

from datamodel_code_generator.model.pydantic_v2 import BaseModel


class AdaptedModel(BaseModel):
    @staticmethod
    def CUSTOM_TEMPLATE_ADAPTER(template):
        source = Path(template.filename).with_name("adapted.jinja2").read_text()
        return template.environment.from_string(source)


class DefaultDirectoryModel(AdaptedModel):
    def __init__(self, *args, **kwargs):
        kwargs["custom_template_dir"] = Path(__file__).parent / "default_templates"
        super().__init__(*args, **kwargs)


class AbsoluteTemplateModel(BaseModel):
    TEMPLATE_FILE_PATH = str(Path(__file__).with_name("standalone.jinja2"))
    CUSTOM_TEMPLATE_ADAPTER = None


class SplitTemplateModel(BaseModel):
    def __init__(self, *args, **kwargs):
        self.TEMPLATE_FILE_PATH = str(
            kwargs["custom_template_dir"].parent / "split" / kwargs["reference"].name / "BaseModel.jinja2"
        )
        super().__init__(*args, **kwargs)


class SplitAdaptedModel(SplitTemplateModel):
    CUSTOM_TEMPLATE_ADAPTER = staticmethod(AdaptedModel.CUSTOM_TEMPLATE_ADAPTER)
