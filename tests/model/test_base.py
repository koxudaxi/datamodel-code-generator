from tempfile import NamedTemporaryFile

import pytest
from datamodel_code_generator.model.base import DataModel, DataModelField, TemplateBase


class A(TemplateBase):
    def render(self) -> str:
        return ''


class B(DataModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    TEMPLATE_FILE_PATH = ''


class C(DataModel):
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
    with NamedTemporaryFile('w') as dummy_template:
        dummy_template.write('abc')
        dummy_template.seek(0)
        a: TemplateBase = A(dummy_template.name)
    assert a.template_file_path == dummy_template.name
    assert a._render() == 'abc'
    assert str(a) == ''


def test_data_model():
    field = DataModelField(
        name='a', type_hint='str', default="" 'abc' "", required=True
    )

    with NamedTemporaryFile('w') as dummy_template:
        dummy_template.write(template)
        dummy_template.seek(0)
        B.TEMPLATE_FILE_PATH = dummy_template.name
        data_model = B(
            name='test_model',
            fields=[field],
            decorators=['@validate'],
            base_class='Base',
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
    field = DataModelField(
        name='a', type_hint='str', default="" 'abc' "", required=True
    )
    with pytest.raises(Exception, match='TEMPLATE_FILE_NAME is undefined'):
        C(name='abc', fields=[field])
