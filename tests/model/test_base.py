from tempfile import NamedTemporaryFile

from datamodel_code_generator.model.base import TemplateBase


class A(TemplateBase):
    def render(self) -> str:
        return ''


def test_template_base():
    with NamedTemporaryFile('w') as dummy_template:
        dummy_template.write('abc')
        dummy_template.seek(0)
        a: TemplateBase = A(dummy_template.name)
    assert a.template_file_path == dummy_template.name
    assert a._render() == 'abc'
    assert str(a) == ''
