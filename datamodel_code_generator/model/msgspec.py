from functools import wraps
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from pydantic import Field

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.base import UNDEFINED
from datamodel_code_generator.model.imports import (
    IMPORT_MSGSPEC_CONVERT,
    IMPORT_MSGSPEC_FIELD,
    IMPORT_MSGSPEC_META,
    IMPORT_MSGSPEC_STRUCT,
)
from datamodel_code_generator.model.pydantic.base_model import (
    Constraints as _Constraints,
)
from datamodel_code_generator.model.rootmodel import RootModel as _RootModel
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import chain_as_tuple, get_optional_type


def _has_field_assignment(field: DataModelFieldBase) -> bool:
    return bool(field.field) or not (
        field.required
        or (field.represented_default == 'None' and field.strip_default_none)
    )


DataModelFieldBaseT = TypeVar('DataModelFieldBaseT', bound=DataModelFieldBase)


def import_extender(cls: Type[DataModelFieldBaseT]) -> Type[DataModelFieldBaseT]:
    original_imports: property = getattr(cls, 'imports', None)  # type: ignore

    @wraps(original_imports.fget)  # type: ignore
    def new_imports(self: DataModelFieldBaseT) -> Tuple[Import, ...]:
        extra_imports = []
        if self.field:
            extra_imports.append(IMPORT_MSGSPEC_FIELD)
        if self.field and 'lambda: convert' in self.field:
            extra_imports.append(IMPORT_MSGSPEC_CONVERT)
        if self.annotated:
            extra_imports.append(IMPORT_MSGSPEC_META)
        return chain_as_tuple(original_imports.fget(self), extra_imports)  # type: ignore

    setattr(cls, 'imports', property(new_imports))
    return cls


class RootModel(_RootModel):
    pass


class Struct(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'msgspec.jinja2'
    BASE_CLASS: ClassVar[str] = 'msgspec.Struct'
    DEFAULT_IMPORTS: ClassVar[Tuple[Import, ...]] = (IMPORT_MSGSPEC_STRUCT,)

    def __init__(
        self,
        *,
        reference: Reference,
        fields: List[DataModelFieldBase],
        decorators: Optional[List[str]] = None,
        base_classes: Optional[List[Reference]] = None,
        custom_base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        methods: Optional[List[str]] = None,
        path: Optional[Path] = None,
        description: Optional[str] = None,
        default: Any = UNDEFINED,
        nullable: bool = False,
    ) -> None:
        super().__init__(
            reference=reference,
            fields=sorted(fields, key=_has_field_assignment, reverse=False),
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


class Constraints(_Constraints):
    # To override existing pattern alias
    regex: Optional[str] = Field(None, alias='regex')
    pattern: Optional[str] = Field(None, alias='pattern')


@import_extender
class DataModelField(DataModelFieldBase):
    _FIELD_KEYS: ClassVar[Set[str]] = {
        'default',
        'default_factory',
    }
    _META_FIELD_KEYS: ClassVar[Set[str]] = {
        'title',
        'description',
        'gt',
        'ge',
        'lt',
        'le',
        'multiple_of',
        # 'min_items', # not supported by msgspec
        # 'max_items', # not supported by msgspec
        'min_length',
        'max_length',
        'pattern',
        # 'unique_items', # not supported by msgspec
    }
    _PARSE_METHOD = 'convert'
    _COMPARE_EXPRESSIONS: ClassVar[Set[str]] = {'gt', 'ge', 'lt', 'le', 'multiple_of'}
    constraints: Optional[Constraints] = None

    def self_reference(self) -> bool:  # pragma: no cover
        return isinstance(self.parent, Struct) and self.parent.reference.path in {
            d.reference.path for d in self.data_type.all_data_types if d.reference
        }

    def process_const(self) -> None:
        if 'const' not in self.extras:
            return None
        self.const = True
        self.nullable = False
        const = self.extras['const']
        if self.data_type.type == 'str' and isinstance(
            const, str
        ):  # pragma: no cover # Literal supports only str
            self.data_type = self.data_type.__class__(literals=[const])

    def _get_strict_field_constraint_value(self, constraint: str, value: Any) -> Any:
        if value is None or constraint not in self._COMPARE_EXPRESSIONS:
            return value

        if any(
            data_type.type == 'float' for data_type in self.data_type.all_data_types
        ):
            return float(value)
        return int(value)

    @property
    def field(self) -> Optional[str]:
        """for backwards compatibility"""
        result = str(self)
        if result == '':
            return None

        return result

    def __str__(self) -> str:
        data: Dict[str, Any] = {
            k: v for k, v in self.extras.items() if k in self._FIELD_KEYS
        }
        if self.alias:
            data['name'] = self.alias

        if self.default != UNDEFINED and self.default is not None:
            data['default'] = self.default

        if self.required:
            data = {
                k: v
                for k, v in data.items()
                if k
                not in (
                    'default',
                    'default_factory',
                )
            }
        elif self.default and 'default_factory' not in data:
            default_factory = self._get_default_as_struct_model()
            if default_factory is not None:
                data.pop('default')
                data['default_factory'] = default_factory

        if not data:
            return ''

        if len(data) == 1 and 'default' in data:
            return repr(data['default'])

        kwargs = [
            f'{k}={v if k == "default_factory" else repr(v)}' for k, v in data.items()
        ]
        return f'field({", ".join(kwargs)})'

    @property
    def annotated(self) -> Optional[str]:
        if not self.use_annotated:  # pragma: no cover
            return None

        data: Dict[str, Any] = {
            k: v for k, v in self.extras.items() if k in self._META_FIELD_KEYS
        }
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
                    if k in self._META_FIELD_KEYS
                },
            }

        meta_arguments = sorted(
            f'{k}={repr(v)}' for k, v in data.items() if v is not None
        )
        if not meta_arguments:
            return None

        meta = f'Meta({", ".join(meta_arguments)})'

        if not self.required:
            type_hint = self.data_type.type_hint
            annotated_type = f'Annotated[{type_hint}, {meta}]'
            return get_optional_type(annotated_type, self.data_type.use_union_operator)
        return f'Annotated[{self.type_hint}, {meta}]'

    def _get_default_as_struct_model(self) -> Optional[str]:
        for data_type in self.data_type.data_types or (self.data_type,):
            # TODO: Check nested data_types
            if data_type.is_dict or self.data_type.is_union:
                # TODO: Parse Union and dict model for default
                continue  # pragma: no cover
            elif data_type.is_list and len(data_type.data_types) == 1:
                data_type = data_type.data_types[0]
                if (  # pragma: no cover
                    data_type.reference
                    and (
                        isinstance(data_type.reference.source, Struct)
                        or isinstance(data_type.reference.source, RootModel)
                    )
                    and isinstance(self.default, list)
                ):
                    return f'lambda: {self._PARSE_METHOD}({repr(self.default)},  type=list[{data_type.alias or data_type.reference.source.class_name}])'
            elif data_type.reference and isinstance(data_type.reference.source, Struct):
                return f'lambda: {self._PARSE_METHOD}({repr(self.default)},  type={data_type.alias or data_type.reference.source.class_name})'
        return None
