from pathlib import PurePosixPath, PureWindowsPath

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
def test_get_relative_path_posix(
    base_path: str, target_path: str, expected: str
) -> None:
    assert PurePosixPath(
        get_relative_path(PurePosixPath(base_path), PurePosixPath(target_path))
    ) == PurePosixPath(expected)


@pytest.mark.parametrize(
    'base_path,target_path,expected',
    [
        ('c:/a/b', 'c:/a/b', '.'),
        ('c:/a/b', 'c:/a/b/c', 'c'),
        ('c:/a/b', 'c:/a/b/c/d', 'c/d'),
        ('c:/a/b/c', 'c:/a/b', '..'),
        ('c:/a/b/c/d', 'c:/a/b', '../..'),
        ('c:/a/b/c/d', 'c:/a', '../../..'),
        ('c:/a/b/c/d', 'c:/a/x/y/z', '../../../x/y/z'),
        ('c:/a/b/c/d', 'a/x/y/z', 'a/x/y/z'),
    ],
)
def test_get_relative_path_windows(
    base_path: str, target_path: str, expected: str
) -> None:
    assert PureWindowsPath(
        get_relative_path(PureWindowsPath(base_path), PureWindowsPath(target_path))
    ) == PureWindowsPath(expected)
