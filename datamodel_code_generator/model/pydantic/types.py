from decimal import Decimal
from typing import Any, Dict, Set

from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_ANY,
    IMPORT_DATE,
    IMPORT_DATETIME,
    IMPORT_DECIMAL,
    IMPORT_DICT,
    IMPORT_LIST,
    IMPORT_UUID,
)
from datamodel_code_generator.model.pydantic.imports import (
    IMPORT_ANYURL,
    IMPORT_CONDECIMAL,
    IMPORT_CONFLOAT,
    IMPORT_CONINT,
    IMPORT_CONSTR,
    IMPORT_EMAIL_STR,
    IMPORT_IPV4ADDRESS,
    IMPORT_IPV6ADDRESS,
    IMPORT_NEGATIVE_FLOAT,
    IMPORT_NEGATIVE_INT,
    IMPORT_POSITIVE_FLOAT,
    IMPORT_POSITIVE_INT,
    IMPORT_SECRET_STR,
    IMPORT_UUID1,
    IMPORT_UUID2,
    IMPORT_UUID3,
    IMPORT_UUID4,
    IMPORT_UUID5,
)
from datamodel_code_generator.types import DataType
from datamodel_code_generator.types import DataTypeManager as _DataTypeManager
from datamodel_code_generator.types import Types

type_map: Dict[Types, DataType] = {
    Types.integer: DataType(type='int'),
    Types.int32: DataType(type='int'),
    Types.int64: DataType(type='int'),
    Types.number: DataType(type='float'),
    Types.float: DataType(type='float'),
    Types.double: DataType(type='float'),
    Types.decimal: DataType(type='Decimal', imports_=[IMPORT_DECIMAL]),
    Types.time: DataType(type='time'),
    Types.string: DataType(type='str'),
    Types.byte: DataType(type='str'),  # base64 encoded string
    Types.binary: DataType(type='bytes'),
    Types.date: DataType(type='date', imports_=[IMPORT_DATE]),
    Types.date_time: DataType(type='datetime', imports_=[IMPORT_DATETIME]),
    Types.password: DataType(type='SecretStr', imports_=[IMPORT_SECRET_STR]),
    Types.email: DataType(type='EmailStr', imports_=[IMPORT_EMAIL_STR]),
    Types.uuid: DataType(type='UUID', imports_=[IMPORT_UUID]),
    Types.uuid1: DataType(type='UUID1', imports_=[IMPORT_UUID1]),
    Types.uuid2: DataType(type='UUID2', imports_=[IMPORT_UUID2]),
    Types.uuid3: DataType(type='UUID3', imports_=[IMPORT_UUID3]),
    Types.uuid4: DataType(type='UUID4', imports_=[IMPORT_UUID4]),
    Types.uuid5: DataType(type='UUID5', imports_=[IMPORT_UUID5]),
    Types.uri: DataType(type='AnyUrl', imports_=[IMPORT_ANYURL]),
    Types.hostname: DataType(
        type='constr',
        imports_=[IMPORT_CONSTR],
        is_func=True,
        # https://github.com/horejsek/python-fastjsonschema/blob/61c6997a8348b8df9b22e029ca2ba35ef441fbb8/fastjsonschema/draft04.py#L31
        kwargs={
            'regex': "'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]{0,61}[A-Za-z0-9])\Z'"
        },
    ),
    Types.ipv4: DataType(type='IPv4Address', imports_=[IMPORT_IPV4ADDRESS]),
    Types.ipv6: DataType(type='IPv6Address', imports_=[IMPORT_IPV6ADDRESS]),
    Types.boolean: DataType(type='bool'),
    Types.object: DataType(type='Dict[str, Any]', imports_=[IMPORT_ANY, IMPORT_DICT,],),
    Types.null: DataType(type='Any', imports_=[IMPORT_ANY]),
    Types.array: DataType(type='List[Any]', imports_=[IMPORT_LIST, IMPORT_ANY]),
    Types.any: DataType(type='Any', imports_=[IMPORT_ANY]),
}

standard_collections_type_map = {
    **type_map,
    Types.object: DataType(type='dict[str, Any]', imports_=[IMPORT_ANY,],),
    Types.array: DataType(type='list[Any]', imports_=[IMPORT_ANY]),
}
kwargs_schema_to_model = {
    'exclusiveMinimum': 'gt',
    'minimum': 'ge',
    'exclusiveMaximum': 'lt',
    'maximum': 'le',
    'multipleOf': 'multiple_of',
    'minItems': 'min_items',
    'maxItems': 'max_items',
    'minLength': 'min_length',
    'maxLength': 'max_length',
    'pattern': 'regex',
}

number_kwargs = {
    'exclusiveMinimum',
    'minimum',
    'exclusiveMaximum',
    'maximum',
    'multipleOf',
}

string_kwargs = {'minItems', 'maxItems', 'minLength', 'maxLength', 'pattern'}


def transform_kwargs(kwargs: Dict[str, Any], filter: Set[str]) -> Dict[str, str]:
    return {
        kwargs_schema_to_model.get(k, k): v
        for (k, v) in kwargs.items()
        if v is not None and k in filter
    }


class DataTypeManager(_DataTypeManager):
    def __init__(
        self,
        python_version: PythonVersion = PythonVersion.PY_37,
        use_standard_collections: bool = False,
    ):
        super().__init__(python_version, use_standard_collections)
        self.type_map: Dict[
            Types, DataType
        ] = standard_collections_type_map if use_standard_collections else type_map

    def get_data_int_type(self, types: Types, **kwargs: Any) -> DataType:
        data_type_kwargs = transform_kwargs(kwargs, number_kwargs)
        if data_type_kwargs:
            if data_type_kwargs == {'gt': 0}:
                return self.data_type(
                    type='PositiveInt', imports_=[IMPORT_POSITIVE_INT]
                )
            if data_type_kwargs == {'lt': 0}:
                return self.data_type(
                    type='NegativeInt', imports_=[IMPORT_NEGATIVE_INT]
                )
            return self.data_type(
                type='conint',
                is_func=True,
                kwargs={k: int(v) for k, v in data_type_kwargs.items()},
                imports_=[IMPORT_CONINT],
            )
        return self.type_map[types]

    def get_data_float_type(self, types: Types, **kwargs: Any) -> DataType:
        data_type_kwargs = transform_kwargs(kwargs, number_kwargs)
        if data_type_kwargs:
            if data_type_kwargs == {'gt': 0}:
                return self.data_type(
                    type='PositiveFloat', imports_=[IMPORT_POSITIVE_FLOAT]
                )
            if data_type_kwargs == {'lt': 0}:
                return self.data_type(
                    type='NegativeFloat', imports_=[IMPORT_NEGATIVE_FLOAT]
                )
            return DataType(
                type='confloat',
                is_func=True,
                kwargs={k: float(v) for k, v in data_type_kwargs.items()},
                imports_=[IMPORT_CONFLOAT],
            )
        return self.type_map[types]

    def get_data_decimal_type(self, types: Types, **kwargs: Any) -> DataType:
        data_type_kwargs = transform_kwargs(kwargs, number_kwargs)
        if data_type_kwargs:
            return self.data_type(
                type='condecimal',
                is_func=True,
                kwargs={k: Decimal(v) for k, v in data_type_kwargs.items()},
                imports_=[IMPORT_CONDECIMAL],
            )
        return self.type_map[types]

    def get_data_str_type(self, types: Types, **kwargs: Any) -> DataType:
        data_type_kwargs = transform_kwargs(kwargs, string_kwargs)
        if data_type_kwargs:
            if 'regex' in data_type_kwargs:
                data_type_kwargs['regex'] = f'\'{data_type_kwargs["regex"]}\''
            return self.data_type(
                type='constr',
                is_func=True,
                kwargs=data_type_kwargs,
                imports_=[IMPORT_CONSTR],
            )
        return self.type_map[types]

    def get_data_type(self, types: Types, **kwargs: Any) -> DataType:
        if types == Types.string:
            return self.get_data_str_type(types, **kwargs)
        elif types in (Types.int32, Types.int64, Types.integer):
            return self.get_data_int_type(types, **kwargs)
        elif types in (Types.float, Types.double, Types.number, Types.time):
            return self.get_data_float_type(types, **kwargs)
        elif types == Types.decimal:
            return self.get_data_decimal_type(types, **kwargs)
        return self.type_map[types]
