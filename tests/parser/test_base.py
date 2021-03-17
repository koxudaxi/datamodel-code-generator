from collections import OrderedDict
from typing import Dict, List, Tuple

import pytest

from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model.pydantic import BaseModel, DataModelField
from datamodel_code_generator.parser.base import Parser, relative, sort_data_models
from datamodel_code_generator.reference import Reference, snake_to_upper_camel
from datamodel_code_generator.types import DataType


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
    reference_a = Reference(path='A', original_name='A', name='A')
    reference_b = Reference(path='B', original_name='B', name='B')
    reference_c = Reference(path='C', original_name='C', name='C')
    data_type_a = DataType(reference=reference_a)
    data_type_b = DataType(reference=reference_b)
    data_type_c = DataType(reference=reference_c)
    reference = [
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelFieldBase(data_type=data_type_c),
            ],
            reference=reference_a,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)], reference=reference_b,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)], reference=reference_c,
        ),
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
    reference_a = Reference(path='A', original_name='A', name='A')
    reference_b = Reference(path='B', original_name='B', name='B')
    reference_c = Reference(path='C', original_name='C', name='C')
    reference_d = Reference(path='D', original_name='D', name='D')
    reference_v = Reference(path='V', original_name='V', name='V')
    reference_z = Reference(path='Z', original_name='Z', name='Z')
    data_type_a = DataType(reference=reference_a)
    data_type_b = DataType(reference=reference_b)
    data_type_c = DataType(reference=reference_c)
    data_type_v = DataType(reference=reference_v)
    data_type_z = DataType(reference=reference_z)
    reference = [
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelFieldBase(data_type=data_type_c),
            ],
            reference=reference_a,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)], reference=reference_b,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)], reference=reference_c,
        ),
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelField(data_type=data_type_c),
                DataModelField(data_type=data_type_z),
            ],
            reference=reference_d,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_v)], reference=reference_z,
        ),
    ]

    with pytest.raises(Exception):
        sort_data_models(reference)


def test_sort_data_models_unresolved_raise_recursion_error():
    reference_a = Reference(path='A', original_name='A', name='A')
    reference_b = Reference(path='B', original_name='B', name='B')
    reference_c = Reference(path='C', original_name='C', name='C')
    reference_d = Reference(path='D', original_name='D', name='D')
    reference_v = Reference(path='V', original_name='V', name='V')
    reference_z = Reference(path='Z', original_name='Z', name='Z')
    data_type_a = DataType(reference=reference_a)
    data_type_b = DataType(reference=reference_b)
    data_type_c = DataType(reference=reference_c)
    data_type_v = DataType(reference=reference_v)
    data_type_z = DataType(reference=reference_z)
    reference = [
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelFieldBase(data_type=data_type_c),
            ],
            reference=reference_a,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)], reference=reference_b,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_b)], reference=reference_c,
        ),
        BaseModel(
            fields=[
                DataModelField(data_type=data_type_a),
                DataModelField(data_type=data_type_c),
                DataModelField(data_type=data_type_z),
            ],
            reference=reference_d,
        ),
        BaseModel(
            fields=[DataModelField(data_type=data_type_v)], reference=reference_z,
        ),
    ]

    with pytest.raises(Exception):
        sort_data_models(reference, recursion_count=100000)


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
    def __init__(self, filename: str, data: str, fields: List[DataModelFieldBase]):
        super().__init__(fields=fields, reference=Reference(''))
        self._data = data

    def render(self) -> str:
        return self._data
