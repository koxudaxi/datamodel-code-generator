from collections import ChainMap
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Mapping, Optional, Set

from pydantic import Field

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import (
    ConstraintsBase,
    DataModel,
    DataModelFieldBase,
)
from datamodel_code_generator.model.pydantic.imports import IMPORT_EXTRA, IMPORT_FIELD


class Constraints(ConstraintsBase):

    gt: Optional[float] = Field(None, alias='exclusiveMinimum')
    ge: Optional[float] = Field(None, alias='minimum')
    lt: Optional[float] = Field(None, alias='exclusiveMaximum')
    le: Optional[float] = Field(None, alias='maximum')
    multiple_of: Optional[float] = Field(None, alias='multipleOf')
    min_items: Optional[int] = Field(None, alias='minItems')
    max_items: Optional[int] = Field(None, alias='maxItems')
    min_length: Optional[int] = Field(None, alias='minLength')
    max_length: Optional[int] = Field(None, alias='maxLength')
    regex: Optional[str] = Field(None, alias='pattern')


class DataModelField(DataModelFieldBase):
    _FIELDS_KEYS: Set[str] = {'alias', 'example', 'examples', 'description', 'title'}

    constraints: Optional[Constraints] = None

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
        data: Mapping[str, Any] = self.dict(include=self._FIELDS_KEYS)
        if self.constraints is not None:
            data = ChainMap(data, self.constraints.dict())
        field_arguments = sorted(
            f"{k}={repr(v)}" for k, v in data.items() if v is not None
        )
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
        path: Optional[Path] = None,
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
            path=path,
        )

        config_parameters: Dict[str, Any] = {}

        if 'additionalProperties' in self.extra_template_data:
            config_parameters['extra'] = 'Extra.allow'
            self.imports.append(IMPORT_EXTRA)

        if self.extra_template_data.get('allow_population_by_field_name'):
            config_parameters['allow_population_by_field_name'] = True

        if config_parameters:
            from datamodel_code_generator.model.pydantic import Config

            self.extra_template_data['config'] = Config.parse_obj(config_parameters)

        for field in fields:
            if field.field:
                self.imports.append(IMPORT_FIELD)
