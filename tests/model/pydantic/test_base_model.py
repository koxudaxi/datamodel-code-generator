import pytest

from datamodel_code_generator import DataTypeManager
from datamodel_code_generator.model.pydantic.base_model import BaseModel, DataModelField
from datamodel_code_generator.types import DataType, Types


def test_base_model():
    field = DataModelField(name='a', data_type=DataType(type='str'), required=True)

    base_model = BaseModel(name='test_model', fields=[field])

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.decorators == []
    assert base_model.render() == 'class test_model(BaseModel):\n' '    a: str'


def test_base_model_optional():
    field = DataModelField(
        name='a', data_type=DataType(type='str'), default='abc', required=False
    )

    base_model = BaseModel(name='test_model', fields=[field])

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.decorators == []
    assert (
        base_model.render() == 'class test_model(BaseModel):\n'
        '    a: Optional[str] = \'abc\''
    )


def test_base_model_decorator():
    field = DataModelField(
        name='a', data_type=DataType(type='str'), default='abc', required=False
    )

    base_model = BaseModel(
        name='test_model',
        fields=[field],
        decorators=['@validate'],
        base_classes=['Base'],
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
    assert DataTypeManager().get_data_type(Types.integer) == DataType(type='int')


def test_base_model_reserved_name():
    field = DataModelField(name='except', data_type=DataType(type='str'), required=True)

    base_model = BaseModel(name='test_model', fields=[field])

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.decorators == []
    assert (
        base_model.render()
        == """class test_model(BaseModel):
    except_: str = Field(..., alias='except')"""
    )

    field = DataModelField(
        name='def', data_type=DataType(type='str'), required=True, alias='def-field'
    )

    base_model = BaseModel(name='test_model', fields=[field])

    assert base_model.name == 'test_model'
    assert base_model.fields == [field]
    assert base_model.decorators == []
    assert (
        base_model.render()
        == """class test_model(BaseModel):
    def_: str = Field(..., alias='def-field')"""
    )


@pytest.mark.parametrize(
    'kwargs,expected',
    [
        ({'required': True}, None),
        ({'required': True, 'example': 'example'}, "Field(..., example='example')"),
        ({'example': 'example'}, "Field(None, example='example')"),
        (
            {'required': True, 'default': 123, 'example': 'example'},
            "Field(..., example='example')",
        ),
        (
            {'required': False, 'default': 123, 'example': 'example'},
            "Field(123, example='example')",
        ),
        ({'description': 'description'}, "Field(None, description='description')"),
        ({'title': 'title'}, "Field(None, title='title')"),
        ({'alias': 'alias'}, "Field(None, alias='alias')"),
        ({'example': True}, "Field(None, example=True)"),
        ({'examples': True}, "Field(None, examples=True)"),
        (
            {
                'example': True,
                'description': 'description',
                'title': 'title',
                'alias': 'alias',
            },
            "Field(None, alias='alias',description='description',example=True,title='title')",
        ),
        ({'examples': [1, 2, 3]}, "Field(None, examples=[1, 2, 3])"),
        (
            {'examples': {'name': 'dog', 'age': 1}},
            'Field(None, examples={\'name\': \'dog\', \'age\': 1})',
        ),
        ({'default': 'abc', 'title': 'title'}, 'Field(\'abc\', title=\'title\')'),
        ({'default': 123, 'title': 'title'}, 'Field(123, title=\'title\')'),
    ],
)
def test_data_model_field(kwargs, expected):
    assert DataModelField(**kwargs, data_type=DataType()).field == expected
