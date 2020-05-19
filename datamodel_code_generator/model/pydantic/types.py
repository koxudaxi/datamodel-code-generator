from typing import Any, Dict, Set

from datamodel_code_generator.imports import (
    IMPORT_CONFLOAT,
    IMPORT_CONINT,
    IMPORT_CONSTR,
    Import,
)
from datamodel_code_generator.types import DataType, Types

type_map: Dict[Types, DataType] = {
    Types.integer: DataType(type='int'),
    Types.int32: DataType(type='int'),
    Types.int64: DataType(type='int'),
    Types.number: DataType(type='float'),
    Types.float: DataType(type='float'),
    Types.double: DataType(type='float'),
    Types.time: DataType(type='time'),
    Types.string: DataType(type='str'),
    Types.byte: DataType(type='str'),  # base64 encoded string
    Types.binary: DataType(type='bytes'),
    Types.date: DataType(
        type='date', imports_=[Import(from_='datetime', import_='date')]
    ),
    Types.date_time: DataType(
        type='datetime', imports_=[Import(from_='datetime', import_='datetime')]
    ),
    Types.password: DataType(
        type='SecretStr', imports_=[Import(from_='pydantic', import_='SecretStr')]
    ),
    Types.email: DataType(
        type='EmailStr', imports_=[Import(from_='pydantic', import_='EmailStr')]
    ),
    Types.uuid: DataType(type='UUID', imports_=[Import(from_='uuid', import_='UUID')]),
    Types.uuid1: DataType(
        type='UUID1', imports_=[Import(from_='pydantic', import_='UUID1')]
    ),
    Types.uuid2: DataType(
        type='UUID2', imports_=[Import(from_='pydantic', import_='UUID2')]
    ),
    Types.uuid3: DataType(
        type='UUID3', imports_=[Import(from_='pydantic', import_='UUID3')]
    ),
    Types.uuid4: DataType(
        type='UUID4', imports_=[Import(from_='pydantic', import_='UUID4')]
    ),
    Types.uuid5: DataType(
        type='UUID5', imports_=[Import(from_='pydantic', import_='UUID5')]
    ),
    Types.uri: DataType(
        type='AnyUrl', imports_=[Import(from_='pydantic', import_='AnyUrl')]
    ),
    Types.ipv4: DataType(
        type='IPv4Address', imports_=[Import(from_='pydantic', import_='IPv4Address')]
    ),
    Types.ipv6: DataType(
        type='IPv6Address', imports_=[Import(from_='pydantic', import_='IPv6Address')]
    ),
    Types.boolean: DataType(type='bool'),
    Types.object: DataType(
        type='Dict[str, Any]',
        imports_=[
            Import(from_='typing', import_='Any'),
            Import(from_='typing', import_='Dict'),
        ],
    ),
    Types.null: DataType(type='Any', imports_=[Import(from_='typing', import_='Any')]),
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


def get_data_int_type(types: Types, **kwargs: Any) -> DataType:
    data_type_kwargs = transform_kwargs(kwargs, number_kwargs)
    if data_type_kwargs:
        if data_type_kwargs == {'gt': 0}:
            return DataType(type='PositiveInt')
        if data_type_kwargs == {'lt': 0}:
            return DataType(type='NegativeInt')
        return DataType(
            type='conint',
            is_func=True,
            kwargs={k: int(v) for k, v in data_type_kwargs.items()},
            imports_=[IMPORT_CONINT],
        )
    return type_map[types]


def get_data_float_type(types: Types, **kwargs: Any) -> DataType:
    data_type_kwargs = transform_kwargs(kwargs, number_kwargs)
    if data_type_kwargs:
        if data_type_kwargs == {'gt': 0}:
            return DataType(type='PositiveFloat')
        if data_type_kwargs == {'lt': 0}:
            return DataType(type='NegativeFloat')
        return DataType(
            type='confloat',
            is_func=True,
            kwargs={k: float(v) for k, v in data_type_kwargs.items()},
            imports_=[IMPORT_CONFLOAT],
        )
    return type_map[types]


def get_data_str_type(types: Types, **kwargs: Any) -> DataType:
    data_type_kwargs = transform_kwargs(kwargs, string_kwargs)
    if data_type_kwargs:
        if 'regex' in data_type_kwargs:
            data_type_kwargs['regex'] = f'\'{data_type_kwargs["regex"]}\''
        return DataType(
            type='constr',
            is_func=True,
            kwargs=data_type_kwargs,
            imports_=[IMPORT_CONSTR],
        )
    return type_map[types]


def get_data_type(types: Types, **kwargs: Any) -> DataType:
    if types == Types.string:
        return get_data_str_type(types, **kwargs)
    elif types in (Types.int32, Types.int64, Types.integer):
        return get_data_int_type(types, **kwargs)
    elif types in (Types.float, Types.double, Types.number, Types.time):
        return get_data_float_type(types, **kwargs)
    return type_map[types]
