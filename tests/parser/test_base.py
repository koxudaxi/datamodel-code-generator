from collections import OrderedDict
from typing import Dict, Tuple

import pytest

from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic import BaseModel
from datamodel_code_generator.parser.base import Parser, relative, sort_data_models


class A(DataModel):
    pass


class B(DataModel):
    pass


class C(Parser):
    def parse_raw(self, name: str, raw: Dict) -> None:
        pass

    def parse(self) -> str:
        return 'parsed'


def test_parser():
    c = C(A, B, DataModelFieldBase, 'Base')
    assert c.data_model_type == A
    assert c.data_model_root_type == B
    assert c.data_model_field_type == DataModelFieldBase
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


@pytest.mark.parametrize(
    'current_module,reference,val',
    [
        ('', 'Foo', ('', '')),
        ('a', 'a.Foo', ('', '')),
        ('a', 'a.b.Foo', ('.', 'b')),
        ('a.b', 'a.Foo', ('.', 'Foo')),
        ('a.b.c', 'a.Foo', ('..', 'Foo')),
        ('a.b.c', 'Foo', ('...', 'Foo')),
    ],
)
def test_relative(current_module: str, reference: str, val: Tuple[str, str]):

    assert relative(current_module, reference) == val
