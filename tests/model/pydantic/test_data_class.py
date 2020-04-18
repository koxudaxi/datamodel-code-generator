from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.pydantic.dataclass import DataClass
from datamodel_code_generator.types import DataType, Types


def test_data_class():
    field = DataModelFieldBase(
        name='a', data_types=[DataType(type='str')], required=True
    )

    data_class = DataClass(name='test_model', fields=[field])

    assert data_class.name == 'test_model'
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert data_class.render() == '@dataclass\n' 'class test_model:\n' '    a: str'


def test_data_class_base_class():
    field = DataModelFieldBase(
        name='a', data_types=[DataType(type='str')], required=True
    )

    data_class = DataClass(name='test_model', fields=[field], base_classes=['Base'])

    assert data_class.name == 'test_model'
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert (
        data_class.render() == '@dataclass\n' 'class test_model(Base):\n' '    a: str'
    )


def test_data_class_optional():
    field = DataModelFieldBase(
        name='a', data_types=[DataType(type='str')], default="'abc'", required=True
    )

    data_class = DataClass(name='test_model', fields=[field])

    assert data_class.name == 'test_model'
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert (
        data_class.render() == '@dataclass\n'
        'class test_model:\n'
        '    a: str = \'abc\''
    )


def test_data_class_get_data_type():
    assert DataClass.get_data_type(Types.integer) == DataType(type='int')
