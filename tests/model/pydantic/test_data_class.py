from datamodel_code_generator.model import DataModelField
from datamodel_code_generator.model.pydantic.dataclass import DataClass


def test_data_class():
    field = DataModelField(name='a', type_hint='str', required=True)

    data_class = DataClass(name='test_model', fields=[field])

    assert data_class.name == 'test_model'
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert data_class.render() == '@dataclass\n' 'class test_model:\n' '    a: str'


def test_data_class_base_class():
    field = DataModelField(name='a', type_hint='str', required=True)

    data_class = DataClass(name='test_model', fields=[field])

    data_class.BASE_CLASS = 'Base'
    assert data_class.name == 'test_model'
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert (
        data_class.render() == '@dataclass\n' 'class test_model(Base):\n' '    a: str'
    )


def test_data_class_optional():
    field = DataModelField(name='a', type_hint='str', default="'abc'", required=False)

    data_class = DataClass(name='test_model', fields=[field])

    assert data_class.name == 'test_model'
    assert data_class.fields == [field]
    assert data_class.decorators == []
    assert (
        data_class.render() == '@dataclass\n'
        'class test_model:\n'
        '    a: str = \'abc\''
    )
