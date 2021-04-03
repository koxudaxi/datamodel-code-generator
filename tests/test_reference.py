from pathlib import Path

import pytest

from datamodel_code_generator.reference import get_relative_path


@pytest.mark.parametrize(
    'base_path,target_path,expected',
    [
        ('/a/b', '/a/b', '.'),
        ('/a/b', '/a/b/c', 'c'),
        ('/a/b', '/a/b/c/d', 'c/d'),
        ('/a/b/c', '/a/b', '..'),
        ('/a/b/c/d', '/a/b', '../..'),
        ('/a/b/c/d', '/a', '../../..'),
        ('/a/b/c/d', '/a/x/y/z', '../../../x/y/z'),
        ('/a/b/c/d', 'a/x/y/z', 'a/x/y/z'),
    ],
)
def test_get_relative_path(base_path: str, target_path: str, expected: str) -> None:
    assert get_relative_path(Path(base_path), Path(target_path)) == Path(expected)
