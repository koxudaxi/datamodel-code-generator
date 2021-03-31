import pytest

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.pydantic.imports import (
    IMPORT_CONDECIMAL,
    IMPORT_CONFLOAT,
    IMPORT_CONINT,
    IMPORT_CONSTR,
    IMPORT_NEGATIVE_FLOAT,
    IMPORT_NEGATIVE_INT,
    IMPORT_POSITIVE_FLOAT,
    IMPORT_POSITIVE_INT,
)
from datamodel_code_generator.model.pydantic.types import DataTypeManager
from datamodel_code_generator.types import DataType, Types


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.integer, {}, DataType(type='int')),
        (
            Types.integer,
            {'maximum': 10},
            DataType(
                type='conint', is_func=True, kwargs={'le': 10}, import_=IMPORT_CONINT
            ),
        ),
        (
            Types.integer,
            {'exclusiveMaximum': 10},
            DataType(
                type='conint', is_func=True, kwargs={'lt': 10}, import_=IMPORT_CONINT
            ),
        ),
        (
            Types.integer,
            {'minimum': 10},
            DataType(
                type='conint', is_func=True, kwargs={'ge': 10}, import_=IMPORT_CONINT
            ),
        ),
        (
            Types.integer,
            {'exclusiveMinimum': 10},
            DataType(
                type='conint', is_func=True, kwargs={'gt': 10}, import_=IMPORT_CONINT
            ),
        ),
        (
            Types.integer,
            {'multipleOf': 10},
            DataType(
                type='conint',
                is_func=True,
                kwargs={'multiple_of': 10},
                import_=IMPORT_CONINT,
            ),
        ),
        (
            Types.integer,
            {'exclusiveMinimum': 0},
            DataType(type='PositiveInt', import_=IMPORT_POSITIVE_INT),
        ),
        (
            Types.integer,
            {'exclusiveMaximum': 0},
            DataType(type='NegativeInt', import_=IMPORT_NEGATIVE_INT),
        ),
    ],
)
def test_get_data_int_type(types, params, data_type):
    assert (
        DataTypeManager().get_data_int_type(types, **params).dict() == data_type.dict()
    )


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.float, {}, DataType(type='float')),
        (
            Types.float,
            {'maximum': 10},
            DataType(
                type='confloat',
                is_func=True,
                kwargs={'le': 10},
                import_=IMPORT_CONFLOAT,
            ),
        ),
        (
            Types.float,
            {'exclusiveMaximum': 10},
            DataType(
                type='confloat',
                is_func=True,
                kwargs={'lt': 10.0},
                import_=IMPORT_CONFLOAT,
            ),
        ),
        (
            Types.float,
            {'minimum': 10},
            DataType(
                type='confloat',
                is_func=True,
                kwargs={'ge': 10.0},
                import_=IMPORT_CONFLOAT,
            ),
        ),
        (
            Types.float,
            {'exclusiveMinimum': 10},
            DataType(
                type='confloat',
                is_func=True,
                kwargs={'gt': 10.0},
                import_=IMPORT_CONFLOAT,
            ),
        ),
        (
            Types.float,
            {'multipleOf': 10},
            DataType(
                type='confloat',
                is_func=True,
                kwargs={'multiple_of': 10.0},
                import_=IMPORT_CONFLOAT,
            ),
        ),
        (
            Types.float,
            {'exclusiveMinimum': 0},
            DataType(type='PositiveFloat', import_=IMPORT_POSITIVE_FLOAT),
        ),
        (
            Types.float,
            {'exclusiveMaximum': 0},
            DataType(type='NegativeFloat', import_=IMPORT_NEGATIVE_FLOAT),
        ),
    ],
)
def test_get_data_float_type(types, params, data_type):
    assert DataTypeManager().get_data_float_type(types, **params) == data_type


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (
            Types.decimal,
            {},
            DataType(
                type='Decimal', import_=Import(from_='decimal', import_='Decimal')
            ),
        ),
        (
            Types.decimal,
            {'maximum': 10},
            DataType(
                type='condecimal',
                is_func=True,
                kwargs={'le': 10},
                import_=IMPORT_CONDECIMAL,
            ),
        ),
        (
            Types.decimal,
            {'exclusiveMaximum': 10},
            DataType(
                type='condecimal',
                is_func=True,
                kwargs={'lt': 10},
                import_=IMPORT_CONDECIMAL,
            ),
        ),
        (
            Types.decimal,
            {'minimum': 10},
            DataType(
                type='condecimal',
                is_func=True,
                kwargs={'ge': 10},
                import_=IMPORT_CONDECIMAL,
            ),
        ),
        (
            Types.decimal,
            {'exclusiveMinimum': 10},
            DataType(
                type='condecimal',
                is_func=True,
                kwargs={'gt': 10},
                import_=IMPORT_CONDECIMAL,
            ),
        ),
        (
            Types.decimal,
            {'multipleOf': 10},
            DataType(
                type='condecimal',
                is_func=True,
                kwargs={'multiple_of': 10},
                import_=IMPORT_CONDECIMAL,
            ),
        ),
    ],
)
def test_get_data_decimal_type(types, params, data_type):
    assert DataTypeManager().get_data_decimal_type(types, **params) == data_type


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.string, {}, DataType(type='str')),
        (
            Types.string,
            {'pattern': '^abc'},
            DataType(
                type='constr',
                is_func=True,
                kwargs={'regex': "r'^abc'"},
                import_=IMPORT_CONSTR,
            ),
        ),
        (
            Types.string,
            {'minLength': 10},
            DataType(
                type='constr',
                is_func=True,
                kwargs={'min_length': 10},
                import_=IMPORT_CONSTR,
            ),
        ),
        (
            Types.string,
            {'maxLength': 10},
            DataType(
                type='constr',
                is_func=True,
                kwargs={'max_length': 10},
                import_=IMPORT_CONSTR,
            ),
        ),
    ],
)
def test_get_data_str_type(types, params, data_type):
    assert DataTypeManager().get_data_str_type(types, **params) == data_type


@pytest.mark.parametrize(
    'types,params,data_type',
    [
        (Types.string, {}, DataType(type='str')),
        (Types.integer, {}, DataType(type='int')),
        (Types.float, {}, DataType(type='float')),
        (Types.boolean, {}, DataType(type='bool')),
        (
            Types.decimal,
            {},
            DataType(
                type='Decimal', import_=Import(from_='decimal', import_='Decimal')
            ),
        ),
    ],
)
def test_get_data_type(types, params, data_type):
    assert DataTypeManager().get_data_type(types, **params) == data_type


def test_data_type_type_hint():
    assert DataType(type='str').type_hint == 'str'
    assert DataType(type='constr', is_func=True).type_hint == 'constr()'
    assert (
        DataType(type='constr', is_func=True, kwargs={'min_length': 10}).type_hint
        == 'constr(min_length=10)'
    )
