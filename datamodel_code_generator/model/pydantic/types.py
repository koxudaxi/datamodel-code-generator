from typing import Any, Dict

from datamodel_code_generator.types import DataType, Import, Types

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
    Types.date: DataType(type='date'),
    Types.date_time: DataType(type='datetime'),
    Types.password: DataType(
        type='SecretStr', import_=Import(from_='pydantic', import_='SecretStr')
    ),
    Types.email: DataType(
        type='EmailStr', import_=Import(from_='pydantic', import_='EmailStr')
    ),
    Types.uuid: DataType(type='UUID', import_=Import(from_='pydantic', import_='UUID')),
    Types.uuid1: DataType(
        type='UUID1', import_=Import(from_='pydantic', import_='UUID1')
    ),
    Types.uuid2: DataType(
        type='UUID2', import_=Import(from_='pydantic', import_='UUID2')
    ),
    Types.uuid3: DataType(
        type='UUID3', import_=Import(from_='pydantic', import_='UUID3')
    ),
    Types.uuid4: DataType(
        type='UUID4', import_=Import(from_='pydantic', import_='UUID4')
    ),
    Types.uuid5: DataType(
        type='UUID5', import_=Import(from_='pydantic', import_='UUID5')
    ),
    Types.uri: DataType(
        type='UrlStr', import_=Import(from_='pydantic', import_='UrlStr')
    ),
    Types.ipv4: DataType(
        type='IPv4Address', import_=Import(from_='pydantic', import_='IPv4Address')
    ),
    Types.ipv6: DataType(
        type='IPv6Address', import_=Import(from_='pydantic', import_='IPv6Address')
    ),
    Types.boolean: DataType(type='bool'),
}


def get_data_int_type(types: Types, **kwargs: Any) -> DataType:
    data_type_kwargs: Dict[str, str] = {}
    if kwargs.get('maximum') is not None:
        data_type_kwargs['gt'] = kwargs['maximum']
    if kwargs.get('exclusiveMaximum') is not None:
        data_type_kwargs['ge'] = kwargs['exclusiveMaximum']
    if kwargs.get('minimum') is not None:
        data_type_kwargs['lt'] = kwargs['minimum']
    if kwargs.get('exclusiveMinimum') is not None:
        data_type_kwargs['le'] = kwargs['exclusiveMinimum']
    if kwargs.get('multipleOf') is not None:
        data_type_kwargs['multiple_of'] = kwargs['multipleOf']

    if data_type_kwargs:
        if len(data_type_kwargs) == 1 and data_type_kwargs.get('le') == 0:
            return DataType(type='PositiveInt')
        if len(data_type_kwargs) == 1 and data_type_kwargs.get('ge') == 0:
            return DataType(type='NegativeInt')
        return DataType(type='conint', is_func=True, kwargs=data_type_kwargs)
    return type_map[types]


def get_data_float_type(types: Types, **kwargs: Any) -> DataType:
    data_type_kwargs: Dict[str, str] = {}
    if kwargs.get('maximum') is not None:
        data_type_kwargs['gt'] = kwargs['maximum']
    if kwargs.get('exclusiveMaximum') is not None:
        data_type_kwargs['ge'] = kwargs['exclusiveMaximum']
    if kwargs.get('minimum') is not None:
        data_type_kwargs['lt'] = kwargs['minimum']
    if kwargs.get('exclusiveMinimum') is not None:
        data_type_kwargs['le'] = kwargs['exclusiveMinimum']
    if kwargs.get('multipleOf') is not None:
        data_type_kwargs['multiple_of'] = kwargs['multipleOf']

    if data_type_kwargs:
        if len(data_type_kwargs) == 1 and data_type_kwargs.get('le') == 0:
            return DataType(type='PositiveFloat')
        if len(data_type_kwargs) == 1 and data_type_kwargs.get('ge') == 0:
            return DataType(type='NegativeFloat')
        return DataType(type='confloat', is_func=True, kwargs=data_type_kwargs)
    return type_map[types]


def get_data_str_type(types: Types, **kwargs: Any) -> DataType:
    data_type_kwargs: Dict[str, str] = {}
    if kwargs.get('pattern') is not None:
        data_type_kwargs['regex'] = kwargs['pattern']
    if kwargs.get('minLength') is not None:
        data_type_kwargs['min_length'] = kwargs['minLength']
    if kwargs.get('maxLength') is not None:
        data_type_kwargs['max_length'] = kwargs['maxLength']
    if data_type_kwargs:
        return DataType(type='constr', is_func=True, kwargs=data_type_kwargs)
    return type_map[types]


def get_data_type(types: Types, **kwargs: Any) -> DataType:
    if types == Types.string:
        return get_data_str_type(types, **kwargs)
    elif types in (Types.int32, Types.int64, Types.integer):
        return get_data_str_type(types, **kwargs)
    elif types in (Types.float, Types.double, Types.number, Types.time):
        return get_data_float_type(types, **kwargs)
    return type_map[types]
