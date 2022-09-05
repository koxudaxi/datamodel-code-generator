from pathlib import Path
from typing import Any, ClassVar, DefaultDict, Dict, List, Optional, Set, Tuple, Union

from pydantic import Field

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import (
    ConstraintsBase,
    DataModel,
    DataModelFieldBase,
)
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.pydantic.imports import IMPORT_EXTRA, IMPORT_FIELD
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import chain_as_tuple


class Constraints(ConstraintsBase):
    gt: Optional[Union[int, float]] = Field(None, alias='exclusiveMinimum')
    ge: Optional[Union[int, float]] = Field(None, alias='minimum')
    lt: Optional[Union[int, float]] = Field(None, alias='exclusiveMaximum')
    le: Optional[Union[int, float]] = Field(None, alias='maximum')
    multiple_of: Optional[float] = Field(None, alias='multipleOf')
    min_items: Optional[int] = Field(None, alias='minItems')
    max_items: Optional[int] = Field(None, alias='maxItems')
    min_length: Optional[int] = Field(None, alias='minLength')
    max_length: Optional[int] = Field(None, alias='maxLength')
    regex: Optional[str] = Field(None, alias='pattern')
    unique_items: Optional[bool] = Field(None, alias='uniqueItems')


class DataModelField(DataModelFieldBase):
    _EXCLUDE_FIELD_KEYS: ClassVar[Set[str]] = {
        'alias',
        'default',
        'default_factory',
        'const',
        'gt',
        'ge',
        'lt',
        'le',
        'multiple_of',
        'min_items',
        'max_items',
        'min_length',
        'max_length',
        'regex',
    }
    _COMPARE_EXPRESSIONS: ClassVar[Set[str]] = {'gt', 'ge', 'lt', 'le'}
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

    def self_reference(self) -> bool:
        return isinstance(self.parent, BaseModel) and self.parent.reference.path in {
            d.reference.path for d in self.data_type.all_data_types if d.reference
        }

    def _get_strict_field_constraint_value(self, constraint: str, value: Any) -> Any:
        if value is None or constraint not in self._COMPARE_EXPRESSIONS:
            return value

        for data_type in self.data_type.all_data_types:
            if data_type.type == 'int':
                value = int(value)
            else:
                value = float(value)
                break
        return value

    def __str__(self) -> str:
        data: Dict[str, Any] = {
            k: v for k, v in self.extras.items() if k not in self._EXCLUDE_FIELD_KEYS
        }
        if self.alias:
            data['alias'] = self.alias
        if (
            self.constraints is not None
            and not self.self_reference()
            and not self.data_type.strict
        ):
            data = {
                **data,
                **{
                    k: self._get_strict_field_constraint_value(k, v)
                    for k, v in self.constraints.dict().items()
                },
            }

        field_arguments = sorted(
            f"{k}={repr(v)}" for k, v in data.items() if v is not None
        )
        if not field_arguments:
            if self.nullable and self.required:
                return 'Field(...)'  # Field() is for mypy
            return ""

        kwargs = ",".join(field_arguments)
        if self.use_annotated:
            return f'Field({kwargs})'
        value_arg = "..." if self.required else repr(self.default)

        return f'Field({value_arg}, {kwargs})'

    @property
    def annotated(self) -> Optional[str]:
        if not self.use_annotated or not str(self):
            return None
        return f'Annotated[{self.type_hint}, {str(self)}]'


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'pydantic/BaseModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'pydantic.BaseModel'

    def __init__(
        self,
        *,
        reference: Reference,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[Reference]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Any]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
        default: Any = UNDEFINED,
    ):

        methods: List[str] = [field.method for field in fields if field.method]

        super().__init__(
            fields=fields,  # type: ignore
            reference=reference,
            decorators=decorators,
            base_classes=base_classes,
            custom_base_class=custom_base_class,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            methods=methods,
            path=path,
            description=description,
            default=default,
        )

        config_parameters: Dict[str, Any] = {}

        additionalProperties = self.extra_template_data.get('additionalProperties')
        if additionalProperties is not None:
            config_parameters['extra'] = (
                'Extra.allow' if additionalProperties else 'Extra.forbid'
            )
            self._additional_imports.append(IMPORT_EXTRA)

        for config_attribute in 'allow_population_by_field_name', 'allow_mutation':
            if config_attribute in self.extra_template_data:
                config_parameters[config_attribute] = self.extra_template_data[
                    config_attribute
                ]
        for data_type in self.all_data_types:
            if data_type.is_custom_type:
                config_parameters['arbitrary_types_allowed'] = True
                break

        if config_parameters:
            from datamodel_code_generator.model.pydantic import Config

            self.extra_template_data['config'] = Config.parse_obj(config_parameters)

    @property
    def imports(self) -> Tuple[Import, ...]:
        if any(f for f in self.fields if f.field):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        return super().imports
