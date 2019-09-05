from collections import OrderedDict

import pytest
from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.parser.base import Parser, resolve_references


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


def test_resolve_references():
    reference = OrderedDict({'A': {'A', 'C'}, 'B': {'B'}, 'C': {'B'}})
    resolved, unresolved = resolve_references([], reference)
    assert resolved == ['B', 'C', 'A']
    assert unresolved == OrderedDict()


def test_resolve_references_unresolved():
    reference = OrderedDict(
        {'A': {'A', 'C'}, 'B': {'B'}, 'C': {'B'}, 'D': {'A', 'C', 'v'}, 'z': {'v'}}
    )
    with pytest.raises(Exception):
        resolve_references([], reference)
