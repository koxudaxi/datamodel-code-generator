from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Set, Union

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic.types import get_data_type
from datamodel_code_generator.types import DataType, Types


class DataModelField(DataModelFieldBase):
    _FIELDS_KEYS: Set[str] = {'alias', 'example', 'examples', 'description', 'title'}

    def __init__(self, **values: Any) -> None:
        super().__init__(**values)

    @property
    def method(self) -> Optional[str]:
        return self.validator

    @property
    def validator(self) -> Optional[str]:
        return None
        # TODO refactor this method for other validation logic
        # from datamodel_code_generator.model.pydantic import VALIDATOR_TEMPLATE
        #
        # return VALIDATOR_TEMPLATE.render(
        #     field_name=self.name, types=','.join([t.type_hint for t in self.data_types])
        # )

    @property
    def field(self) -> Optional[str]:
        """for backwards compatibility"""
        result = str(self)
        if result == "":
            return None

        return result

    def __str__(self) -> str:
        field_arguments = [
            f"{k}={repr(v)}"
            for k, v in self.dict(include=self._FIELDS_KEYS).items()
            if v is not None
        ]
        if not field_arguments:
            return ""

        value_arg = "..." if self.required else repr(self.default)
        kwargs = ",".join(field_arguments)
        return f'Field({value_arg}, {kwargs})'


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

        methods: List[str] = [field.method for field in fields if field.method]

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
            methods=methods,
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
