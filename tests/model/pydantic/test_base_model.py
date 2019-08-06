from datamodel_code_generator.model import DataModelField
from datamodel_code_generator.model.pydantic.base_model import BaseModel
from datamodel_code_generator.types import DataType, Types


def test_base_model():
    field = DataModelField(name='a', type_hint='str', required=True)

    base_model = BaseModel(name='test_model', fields=[field])

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.decorators == []
    assert base_model.render() == 'class test_model(BaseModel):\n' '    a: str'


def test_base_model_optional():
    field = DataModelField(name='a', type_hint='str', default="'abc'", required=False)

    base_model = BaseModel(name='test_model', fields=[field])

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.decorators == []
    assert (
        base_model.render() == 'class test_model(BaseModel):\n'
        '    a: Optional[str] = \'abc\''
    )


def test_base_model_decorator():
    field = DataModelField(name='a', type_hint='str', default="'abc'", required=False)

    base_model = BaseModel(
        name='test_model', fields=[field], decorators=['@validate'], base_class='Base'
    )

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.base_class == 'Base'
    assert base_model.decorators == ['@validate']
    assert (
        base_model.render() == '@validate\n'
        'class test_model(Base):\n'
        '    a: Optional[str] = \'abc\''
    )


def test_base_model_get_data_type():
    assert BaseModel.get_data_type(Types.integer) == DataType(type='int')
