from datamodel_code_generator import DataTypeManager
from datamodel_code_generator.model import DataModelFieldBase
from datamodel_code_generator.model.pydantic.custom_root_type import CustomRootType
from datamodel_code_generator.types import DataType, Types


def test_custom_root_type():
    custom_root_type = CustomRootType(
        name='test_model',
        fields=[
            DataModelFieldBase(
                name='a', data_type=DataType(type='str'), default='abc', required=False,
            )
        ],
    )

    assert custom_root_type.name == 'test_model'
    assert custom_root_type.fields == [
        DataModelFieldBase(
            name='a', data_type=DataType(type='str'), default='abc', required=False
        )
    ]

    assert custom_root_type.render() == (
        'class test_model(BaseModel):\n' '    __root__: Optional[str] = \'abc\''
    )


def test_custom_root_type_required():
    custom_root_type = CustomRootType(
        name='test_model',
        fields=[DataModelFieldBase(data_type=DataType(type='str'), required=True)],
    )

    assert custom_root_type.name == 'test_model'
    assert custom_root_type.fields == [
        DataModelFieldBase(data_type=DataType(type='str'), required=True)
    ]

    assert custom_root_type.render() == (
        'class test_model(BaseModel):\n' '    __root__: str'
    )


def test_custom_root_type_decorator():
    custom_root_type = CustomRootType(
        name='test_model',
        fields=[DataModelFieldBase(data_type=DataType(type='str'), required=True)],
        decorators=['@validate'],
        base_classes=['Base'],
    )

    assert custom_root_type.name == 'test_model'
    assert custom_root_type.fields == [
        DataModelFieldBase(data_type=DataType(type='str'), required=True)
    ]
    assert custom_root_type.base_class == 'Base'
    assert (
        custom_root_type.render() == '@validate\n'
        'class test_model(Base):\n'
        '    __root__: str'
    )


def test_custom_root_type_get_data_type():
    assert DataTypeManager().get_data_type(Types.integer) == DataType(type='int')
