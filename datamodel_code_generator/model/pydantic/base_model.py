from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Set, Union

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic.types import get_data_type
from datamodel_code_generator.types import DataType, Types


class DataModelField(DataModelFieldBase):
    _FIELDS_KEYS: Set[str] = {'alias', 'example', 'examples', 'description', 'title'}
    field: Optional[str] = None

    def get_valid_argument(self, value: Any) -> Union[str, List[Any], Dict[Any, Any]]:
        if isinstance(value, str):
            return repr(value)
        elif isinstance(value, list):
            return [self.get_valid_argument(i) for i in value]
        elif isinstance(value, dict):
            return {
                self.get_valid_argument(k): self.get_valid_argument(v)
                for k, v in value.items()
            }
        return value

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)
        field_arguments = [
            f"{k}={self.get_valid_argument(v)}"
            for k, v in self.dict(include=self._FIELDS_KEYS).items()
            if v is not None
        ]
        if field_arguments:
            self.field = f'Field({"..." if self.required else self.get_valid_argument(self.default)}, {",".join(field_arguments)})'


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel.jinja2'
    BASE_CLASS = 'pydantic.BaseModel'

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[str]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Any]] = None,
        auto_import: bool = True,
        reference_classes: Optional[List[str]] = None,
        imports: Optional[List[Import]] = None,
    ):

        super().__init__(
            name=name,
            fields=fields,  # type: ignore
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            auto_import=auto_import,
            reference_classes=reference_classes,
            imports=imports,
        )

        config_parameters: Dict[str, Any] = {}

        if 'additionalProperties' in self.extra_template_data:
            config_parameters['extra'] = 'Extra.allow'
            self.imports.append(Import(from_='pydantic', import_='Extra'))

        if config_parameters:
            from datamodel_code_generator.model.pydantic import Config

            self.extra_template_data['config'] = Config.parse_obj(config_parameters)

        for field in fields:
            if field.field:
                self.imports.append(Import(from_='pydantic', import_='Field'))

    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        return get_data_type(types, **kwargs)
