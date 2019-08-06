import pytest
from datamodel_code_generator.model.pydantic.types import (
    get_data_float_type,
    get_data_int_type,
    get_data_str_type,
    get_data_type,
)
from datamodel_code_generator.types import DataType, Types


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.integer, {}, DataType(type='int')),
        (
            Types.integer,
            {'maximum': 10},
            DataType(type='conint', is_func=True, kwargs={'gt': 10}),
        ),
        (
            Types.integer,
            {'exclusiveMaximum': 10},
            DataType(type='conint', is_func=True, kwargs={'ge': 10}),
        ),
        (
            Types.integer,
            {'minimum': 10},
            DataType(type='conint', is_func=True, kwargs={'lt': 10}),
        ),
        (
            Types.integer,
            {'exclusiveMinimum': 10},
            DataType(type='conint', is_func=True, kwargs={'le': 10}),
        ),
        (
            Types.integer,
            {'multipleOf': 10},
            DataType(type='conint', is_func=True, kwargs={'multiple_of': 10}),
        ),
        (Types.integer, {'exclusiveMinimum': 0}, DataType(type='PositiveInt')),
        (Types.integer, {'exclusiveMaximum': 0}, DataType(type='NegativeInt')),
    ],
)
def test_get_data_int_type(types, params, data_type):
    assert get_data_int_type(types, **params) == data_type


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.float, {}, DataType(type='float')),
        (
            Types.float,
            {'maximum': 10},
            DataType(type='confloat', is_func=True, kwargs={'gt': 10}),
        ),
        (
            Types.float,
            {'exclusiveMaximum': 10},
            DataType(type='confloat', is_func=True, kwargs={'ge': 10}),
        ),
        (
            Types.float,
            {'minimum': 10},
            DataType(type='confloat', is_func=True, kwargs={'lt': 10}),
        ),
        (
            Types.float,
            {'exclusiveMinimum': 10},
            DataType(type='confloat', is_func=True, kwargs={'le': 10}),
        ),
        (
            Types.float,
            {'multipleOf': 10},
            DataType(type='confloat', is_func=True, kwargs={'multiple_of': 10}),
        ),
        (Types.float, {'exclusiveMinimum': 0}, DataType(type='PositiveFloat')),
        (Types.float, {'exclusiveMaximum': 0}, DataType(type='NegativeFloat')),
    ],
)
def test_get_data_float_type(types, params, data_type):
    assert get_data_float_type(types, **params) == data_type


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.string, {}, DataType(type='str')),
        (
            Types.string,
            {'pattern': '^abc'},
            DataType(type='constr', is_func=True, kwargs={'regex': '^abc'}),
        ),
        (
            Types.string,
            {'minLength': 10},
            DataType(type='constr', is_func=True, kwargs={'min_length': 10}),
        ),
        (
            Types.string,
            {'maxLength': 10},
            DataType(type='constr', is_func=True, kwargs={'max_length': 10}),
        ),
    ],
)
def test_get_data_str_type(types, params, data_type):
    assert get_data_str_type(types, **params) == data_type


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.string, {}, DataType(type='str')),
        (Types.integer, {}, DataType(type='int')),
        (Types.float, {}, DataType(type='float')),
        (Types.boolean, {}, DataType(type='bool')),
    ],
)
def test_get_data_type(types, params, data_type):
    assert get_data_type(types, **params) == data_type


def test_data_type_type_hint():
    assert DataType(type='str').type_hint == 'str'
    assert DataType(type='constr', is_func=True).type_hint == 'constr()'
    assert (
        DataType(type='constr', is_func=True, kwargs={'min_length': 10}).type_hint
        == 'constr(min_length=10)'
    )
