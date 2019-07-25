from datamodel_code_generator.model import DataModelField
from datamodel_code_generator.model.pydantic.base_model import BaseModel


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

    base_model = BaseModel(name='test_model', fields=[field], decorators=['@validate'])

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.decorators == ['@validate']
    assert (
        base_model.render() == '@validate\n'
        'class test_model(BaseModel):\n'
        '    a: Optional[str] = \'abc\''
    )
