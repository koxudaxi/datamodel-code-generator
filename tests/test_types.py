import pytest

from datamodel_code_generator.types import get_optional_type


@pytest.mark.parametrize(
    'input_,use_union_operator,expected',
    [
        ('List[str]', False, 'Optional[List[str]]'),
        ('List[str, int, float]', False, 'Optional[List[str, int, float]]'),
        ('List[str, int, None]', False, 'Optional[List[str, int, None]]'),
        ('Union[str]', False, 'Optional[str]'),
        ('Union[str, int, float]', False, 'Optional[Union[str, int, float]]'),
        ('Union[str, int, None]', False, 'Optional[Union[str, int]]'),
        ('Union[str, int, None, None]', False, 'Optional[Union[str, int]]'),
        (
            'Union[str, int, List[str, int, None], None]',
            False,
            'Optional[Union[str, int, List[str, int, None]]]',
        ),
        (
            'Union[str, int, List[str, Dict[int, str | None]], None]',
            False,
            'Optional[Union[str, int, List[str, Dict[int, str | None]]]]',
        ),
        ('List[str]', True, 'List[str] | None'),
        ('List[str | int | float]', True, 'List[str | int | float] | None'),
        ('List[str | int | None]', True, 'List[str | int | None] | None'),
        ('str', True, 'str | None'),
        ('str | int | float', True, 'str | int | float | None'),
        ('str | int | None', True, 'str | int | None'),
        ('str | int | None | None', True, 'str | int | None'),
        (
            'str | int | List[str | Dict[int | Union[str | None]]] | None',
            True,
            'str | int | List[str | Dict[int | Union[str | None]]] | None',
        ),
    ],
)
def test_get_optional_type(input_: str, use_union_operator: bool, expected: str):
    assert get_optional_type(input_, use_union_operator) == expected
