from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pytest

from datamodel_code_generator.model.base import (
    DataModel,
    DataModelFieldBase,
    TemplateBase,
)
from datamodel_code_generator.types import DataType, Types


class A(TemplateBase):
    def render(self) -> str:
        return ''


class B(DataModel):
    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    TEMPLATE_FILE_PATH = ''


class C(DataModel):
    @classmethod
    def get_data_type(cls, types: Types, **kwargs: Any) -> DataType:
        pass


template: str = '''{%- for decorator in decorators -%}
{{ decorator }}
{%- endfor %}
@dataclass
class {{ class_name }}:
{%- for field in fields -%}
    {%- if field.required %}
    {{ field.name }}: {{ field.type_hint }}
    {%- else %}
    {{ field.name }}: {{ field.type_hint }} = {{field.default}}
    {%- endif %}
{%- endfor -%}'''


def test_template_base():
    with NamedTemporaryFile('w', delete=False) as dummy_template:
        dummy_template.write('abc')
        dummy_template.seek(0)
        dummy_template.close()
        a: TemplateBase = A(Path(dummy_template.name))
    assert str(a.template_file_path) == dummy_template.name
    assert a._render() == 'abc'
    assert str(a) == ''


def test_data_model():
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str'), default="" 'abc' "", required=True
    )

    with NamedTemporaryFile('w', delete=False) as dummy_template:
        dummy_template.write(template)
        dummy_template.seek(0)
        dummy_template.close()
        B.TEMPLATE_FILE_PATH = dummy_template.name
        data_model = B(
            name='test_model',
            fields=[field],
            decorators=['@validate'],
            base_classes=['Base'],
        )

    assert data_model.name == 'test_model'
    assert data_model.fields == [field]
    assert data_model.decorators == ['@validate']
    assert data_model.base_class == 'Base'
    assert (
        data_model.render() == '@validate\n'
        '@dataclass\n'
        'class test_model:\n'
        '    a: str'
    )


def test_data_model_exception():
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str'), default="" 'abc' "", required=True
    )
    with pytest.raises(Exception, match='TEMPLATE_FILE_PATH is undefined'):
        C(name='abc', fields=[field])


def test_data_field():
    # field = DataModelField(name='a', data_types=[], required=True)
    # assert field.type_hint == ''
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(is_list=True),
        required=True,
        is_list=True,
        is_union=True,
    )
    assert field.type_hint == 'List'
    # field = DataModelField(
    #     name='a', data_types=[], required=True, is_list=False, is_union=True
    # )
    # assert field.type_hint == ''
    # field = DataModelField(
    #     name='a', data_types=[], required=True, is_list=False, is_union=False
    # )
    # assert field.type_hint == ''
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(is_list=True),
        required=True,
        is_list=True,
        is_union=False,
    )
    assert field.type_hint == 'List'
    field = DataModelFieldBase(name='a', data_type=DataType(), required=False)
    assert field.type_hint == 'Optional'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(is_list=True),
        required=False,
        is_list=True,
        is_union=True,
    )
    assert field.type_hint == 'Optional[List]'
    field = DataModelFieldBase(
        name='a', data_type=DataType(), required=False, is_list=False, is_union=True
    )
    assert field.type_hint == 'Optional'
    field = DataModelFieldBase(
        name='a', data_type=DataType(), required=False, is_list=False, is_union=False
    )
    assert field.type_hint == 'Optional'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(is_list=True),
        required=False,
        is_list=True,
        is_union=False,
    )
    assert field.type_hint == 'Optional[List]'
    field = DataModelFieldBase(name='a', data_type=DataType(type='str'), required=True)
    assert field.type_hint == 'str'
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str', is_list=True), required=True,
    )
    assert field.type_hint == 'List[str]'
    field = DataModelFieldBase(name='a', data_type=DataType(type='str'), required=True)
    assert field.type_hint == 'str'
    field = DataModelFieldBase(name='a', data_type=DataType(type='str'), required=True,)
    assert field.type_hint == 'str'
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str', is_list=True), required=True,
    )
    assert field.type_hint == 'List[str]'
    field = DataModelFieldBase(name='a', data_type=DataType(type='str'), required=False)
    assert field.type_hint == 'Optional[str]'
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str', is_list=True,), required=False,
    )
    assert field.type_hint == 'Optional[List[str]]'
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str'), required=False,
    )
    assert field.type_hint == 'Optional[str]'
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str'), required=False,
    )
    assert field.type_hint == 'Optional[str]'
    field = DataModelFieldBase(
        name='a', data_type=DataType(type='str', is_list=True,), required=False,
    )
    assert field.type_hint == 'Optional[List[str]]'

    field = DataModelFieldBase(
        name='a',
        data_type=DataType(data_types=[DataType(type='str'), DataType(type='int')]),
        required=True,
    )
    assert field.type_hint == 'Union[str, int]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(
            data_types=[DataType(type='str'), DataType(type='int')], is_list=True,
        ),
        required=True,
    )
    assert field.type_hint == 'List[Union[str, int]]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(data_types=[DataType(type='str'), DataType(type='int')]),
        required=True,
    )
    assert field.type_hint == 'Union[str, int]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(data_types=[DataType(type='str'), DataType(type='int')]),
        required=True,
    )
    assert field.type_hint == 'Union[str, int]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(
            data_types=[DataType(type='str'), DataType(type='int')], is_list=True
        ),
        required=True,
    )
    assert field.type_hint == 'List[Union[str, int]]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(data_types=[DataType(type='str'), DataType(type='int')]),
        required=False,
    )
    assert field.type_hint == 'Optional[Union[str, int]]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(
            data_types=[DataType(type='str'), DataType(type='int')], is_list=True,
        ),
        required=False,
    )
    assert field.type_hint == 'Optional[List[Union[str, int]]]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(data_types=[DataType(type='str'), DataType(type='int')]),
        required=False,
    )
    assert field.type_hint == 'Optional[Union[str, int]]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(data_types=[DataType(type='str'), DataType(type='int')]),
        required=False,
    )
    assert field.type_hint == 'Optional[Union[str, int]]'
    field = DataModelFieldBase(
        name='a',
        data_type=DataType(
            data_types=[DataType(type='str'), DataType(type='int')], is_list=True
        ),
        required=False,
    )
    assert field.type_hint == 'Optional[List[Union[str, int]]]'

    field = DataModelFieldBase(
        name='a', data_type=DataType(is_list=True), required=False
    )
    assert field.type_hint == 'Optional[List]'
