from datamodel_code_generator.reference import FieldNameResolver

import pytest

@pytest.mark.parametrize(
    'name,expected_resolved',
    [
        ('3a', 'field_3a'),
        ('$in', 'field_in'),
        ('field', 'field'),
    ],
)
def test_get_valid_field_name(name: str, expected_resolved: str) -> None:
    resolver = FieldNameResolver()
    assert expected_resolved == resolver.get_valid_name(name)
