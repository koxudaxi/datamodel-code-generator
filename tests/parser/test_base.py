from collections import OrderedDict
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Tuple

import pytest

from datamodel_code_generator import DataTypeManager
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic import BaseModel
from datamodel_code_generator.parser.base import Parser, relative, sort_data_models
from datamodel_code_generator.reference import snake_to_upper_camel


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
    c = C(
        data_model_type=D,
        data_model_root_type=B,
        data_model_field_type=DataModelFieldBase,
        base_class='Base',
        source='',
    )
    assert c.data_model_type == D
    assert c.data_model_root_type == B
    assert c.data_model_field_type == DataModelFieldBase
    assert c.base_class == 'Base'


def test_sort_data_models():
    reference = [
        BaseModel(name='A', reference_classes={'A', 'C'}, fields=[]),
        BaseModel(name='B', reference_classes={'B'}, fields=[]),
        BaseModel(name='C', reference_classes={'B'}, fields=[]),
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


@pytest.mark.parametrize(
    'word,expected',
    [
        (
            '_hello',
            '_Hello',
        ),  # In case a name starts with a underline, we should keep it.
        ('hello_again', 'HelloAgain'),  # regular snake case
        ('hello__again', 'HelloAgain'),  # handles double underscores
        (
            'hello___again_again',
            'HelloAgainAgain',
        ),  # handles double and single underscores
        ('hello_again_', 'HelloAgain'),  # handles trailing underscores
        ('hello', 'Hello'),  # no underscores
        ('____', '_'),  # degenerate case, but this is the current expected behavior
    ],
)
def test_snake_to_upper_camel(word, expected):
    """Tests the snake to upper camel function."""
    actual = snake_to_upper_camel(word)
    assert actual == expected


class D(DataModel):
    def __init__(
        self, filename: str, data: str, name: str, fields: List[DataModelFieldBase]
    ):
        super().__init__(name, fields)
        self._data = data

    def render(self) -> str:
        return self._data
