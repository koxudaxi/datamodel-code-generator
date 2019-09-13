from collections import OrderedDict

import pytest
from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.model.pydantic import BaseModel
from datamodel_code_generator.parser.base import Parser, sort_data_models


class A(DataModel):
    pass


class B(DataModel):
    pass


class C(Parser):
    def parse(self) -> str:
        return 'parsed'


def test_parser():
    c = C(A, B, DataModelField, 'abc.yaml', 'Base')
    assert c.data_model_type == A
    assert c.data_model_root_type == B
    assert c.data_model_field_type == DataModelField
    assert c.filename == 'abc.yaml'
    assert c.base_class == 'Base'


def test_sort_data_models():
    reference = [
        BaseModel(name='A', reference_classes=['A', 'C'], fields=[]),
        BaseModel(name='B', reference_classes=['B'], fields=[]),
        BaseModel(name='C', reference_classes=['B'], fields=[]),
    ]

    unresolved, resolved, require_update_action_models = sort_data_models(reference)
    expected = OrderedDict()
    expected['B'] = reference[1]
    expected['C'] = reference[2]
    expected['A'] = reference[0]

    assert resolved == expected
    assert unresolved == []
    assert require_update_action_models == ['B', 'A']


def test_sort_data_models_unresolved():
    reference = [
        BaseModel(name='A', reference_classes=['A', 'C'], fields=[]),
        BaseModel(name='B', reference_classes=['B'], fields=[]),
        BaseModel(name='C', reference_classes=['B'], fields=[]),
        BaseModel(name='D', reference_classes=['A', 'C', 'v'], fields=[]),
        BaseModel(name='z', reference_classes=['v'], fields=[]),
    ]

    with pytest.raises(Exception):
        sort_data_models(reference)
