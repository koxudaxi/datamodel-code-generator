from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.parser.base import Parser


class A(DataModel):
    pass


class B(DataModel):
    pass


class C(Parser):
    def parse(self) -> str:
        return 'parsed'


def test_parser():
    c = C(A, B, DataModelField, 'abc.yaml')
    assert c.data_model_type == A
    assert c.data_model_root_type == B
    assert c.data_model_field_type == DataModelField
    assert c.filename == 'abc.yaml'
