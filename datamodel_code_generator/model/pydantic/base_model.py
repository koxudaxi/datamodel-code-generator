from __future__ import annotations

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
    gt: Optional[Union[float, int]] = Field(None, alias='exclusiveMinimum')
    ge: Optional[Union[float, int]] = Field(None, alias='minimum')
    lt: Optional[Union[float, int]] = Field(None, alias='exclusiveMaximum')
    le: Optional[Union[float, int]] = Field(None, alias='maximum')
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
        if self.use_default_kwarg and not result.startswith("Field(..."):
            # Use `default=` for fields that have a default value so that type
            # checkers using @dataclass_transform can infer the field as
            # optional in __init__.
            result = result.replace("Field(", "Field(default=")
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

    def _get_default_as_pydantic_model(self) -> Optional[str]:
        for data_type in self.data_type.data_types or (self.data_type,):
            # TODO: Check nested data_types
            if data_type.is_dict or self.data_type.is_union:
                # TODO: Parse Union and dict model for default
                continue
            elif data_type.is_list and len(data_type.data_types) == 1:
                data_type = data_type.data_types[0]
                data_type.alias
                if (
                    data_type.reference
                    and isinstance(data_type.reference.source, BaseModel)
                    and isinstance(self.default, list)
                ):  # pragma: no cover
                    return f'lambda :[{data_type.alias or data_type.reference.source.class_name}.parse_obj(v) for v in {repr(self.default)}]'
            elif data_type.reference and isinstance(
                data_type.reference.source, BaseModel
            ):  # pragma: no cover
                return f'lambda :{data_type.alias or data_type.reference.source.class_name}.parse_obj({repr(self.default)})'
        return None

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

        if self.use_field_description:
            data.pop('description', None)  # Description is part of field docstring

        if self.const:
            data['const'] = True

        discriminator = data.pop('discriminator', None)
        if discriminator:
            if isinstance(discriminator, str):
                data['discriminator'] = discriminator
            elif isinstance(discriminator, dict):  # pragma: no cover
                data['discriminator'] = discriminator['propertyName']

        if self.required:
            default_factory = None
        elif self.default and 'default_factory' not in data:
            default_factory = self._get_default_as_pydantic_model()
        else:
            default_factory = data.pop('default_factory', None)

        field_arguments = sorted(
            f"{k}={repr(v)}" for k, v in data.items() if v is not None
        )

        if not field_arguments and not default_factory:
            if self.nullable and self.required:
                return 'Field(...)'  # Field() is for mypy
            return ""

        if self.use_annotated:
            pass
        elif self.required:
            field_arguments = ['...', *field_arguments]
        elif default_factory:
            field_arguments = [f'default_factory={default_factory}', *field_arguments]
        else:
            field_arguments = [f'{repr(self.default)}', *field_arguments]

        return f'Field({", ".join(field_arguments)})'

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
        nullable: bool = False,
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
            nullable=nullable,
        )

        config_parameters: Dict[str, Any] = {}

        additionalProperties = self.extra_template_data.get('additionalProperties')
        allow_extra_fields = self.extra_template_data.get('allow_extra_fields')
        if additionalProperties is not None or allow_extra_fields:
            config_parameters['extra'] = (
                'Extra.allow'
                if additionalProperties or allow_extra_fields
                else 'Extra.forbid'
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

        if isinstance(self.extra_template_data.get('config'), dict):
            for key, value in self.extra_template_data['config'].items():
                config_parameters[key] = value

        if config_parameters:
            from datamodel_code_generator.model.pydantic import Config

            self.extra_template_data['config'] = Config.parse_obj(config_parameters)

    @property
    def imports(self) -> Tuple[Import, ...]:
        if any(f for f in self.fields if f.field):
            return chain_as_tuple(super().imports, (IMPORT_FIELD,))
        return super().imports
