"""Tests for import management functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator.imports import Import, Imports

if TYPE_CHECKING:
    from collections.abc import Sequence


@pytest.mark.parametrize(
    ("inputs", "value"),
    [
        ([(None, "foo")], "import foo"),
        ([(".", "foo")], "from . import foo"),
        ([("bar", "foo")], "from bar import foo"),
        ([("bar", "foo"), ("bar", "baz")], "from bar import baz, foo"),
        ([("bar", "foo"), ("rab", "oof")], "from bar import foo\nfrom rab import oof"),
        ([("bar", "foo"), ("bar", "foo")], "from bar import foo"),
        ([(None, "foo.baz")], "import foo.baz"),
    ],
)
def test_dump(inputs: Sequence[tuple[str | None, str]], value: str) -> None:
    """Test creating import lines."""
    imports = Imports()
    imports.append(Import(from_=from_, import_=import_) for from_, import_ in inputs)

    assert str(imports) == value


def test_is_future_true() -> None:
    """Test that __future__ imports are identified as future imports."""
    import_ = Import(from_="__future__", import_="annotations")
    assert import_.is_future is True


def test_is_future_false_regular_import() -> None:
    """Test that regular imports are not identified as future imports."""
    import_ = Import(from_="typing", import_="Optional")
    assert import_.is_future is False


def test_is_future_false_no_from() -> None:
    """Test that imports without from_ are not identified as future imports."""
    import_ = Import(from_=None, import_="os")
    assert import_.is_future is False


def test_extract_future_with_future_imports() -> None:
    """Test extracting future imports from mixed imports."""
    imports = Imports()
    imports.append(Import(from_="__future__", import_="annotations"))
    imports.append(Import(from_="typing", import_="Optional"))

    future = imports.extract_future()

    assert str(future) == "from __future__ import annotations"
    assert str(imports) == "from typing import Optional"
    assert "__future__" not in imports


def test_extract_future_no_future_imports() -> None:
    """Test extracting from imports without future imports."""
    imports = Imports()
    imports.append(Import(from_="typing", import_="Optional"))

    future = imports.extract_future()

    assert not str(future)
    assert str(imports) == "from typing import Optional"


def test_extract_future_only_future_imports() -> None:
    """Test extracting when only future imports exist."""
    imports = Imports()
    imports.append(Import(from_="__future__", import_="annotations"))

    future = imports.extract_future()

    assert str(future) == "from __future__ import annotations"
    assert not str(imports)


def test_extract_future_with_alias() -> None:
    """Test extracting future imports with alias (edge case)."""
    imports = Imports()
    imports.append(Import(from_="__future__", import_="annotations", alias="ann"))
    imports.append(Import(from_="typing", import_="Optional"))

    future = imports.extract_future()

    assert "annotations as ann" in str(future)
    assert "__future__" not in imports
    assert "__future__" not in imports.alias


def test_remove_nonexistent_import() -> None:
    """Test that removing non-existent import doesn't crash."""
    imports = Imports()
    imports.append(Import(from_="typing", import_="Optional"))

    imports.remove(Import(from_="typing", import_="List"))

    assert str(imports) == "from typing import Optional"


def test_remove_double_removal() -> None:
    """Test that double removal of same import doesn't crash."""
    imports = Imports()
    imports.append(Import(from_="typing", import_="Optional"))

    imports.remove(Import(from_="typing", import_="Optional"))
    imports.remove(Import(from_="typing", import_="Optional"))

    assert not str(imports)


def test_remove_cleans_up_counter() -> None:
    """Test that remove() properly cleans up counter entries."""
    imports = Imports()
    imports.append(Import(from_="typing", import_="Optional"))

    assert imports.counter.get(("typing", "Optional")) == 1

    imports.remove(Import(from_="typing", import_="Optional"))

    assert ("typing", "Optional") not in imports.counter


def test_remove_cleans_up_reference_paths() -> None:
    """Test that remove() properly cleans up reference_paths."""
    imports = Imports()
    imports.append(Import(from_="typing", import_="Optional", reference_path="/test/path"))

    assert "/test/path" in imports.reference_paths

    imports.remove(Import(from_="typing", import_="Optional", reference_path="/test/path"))

    assert "/test/path" not in imports.reference_paths


def test_extract_future_moves_reference_paths() -> None:
    """Test that extract_future() moves reference_paths for __future__ imports."""
    imports = Imports()
    imports.append(Import(from_="__future__", import_="annotations", reference_path="/future/ref"))
    imports.append(Import(from_="typing", import_="Optional", reference_path="/typing/ref"))

    future = imports.extract_future()

    assert "/future/ref" in future.reference_paths
    assert "/future/ref" not in imports.reference_paths
    assert "/typing/ref" in imports.reference_paths
    assert "/typing/ref" not in future.reference_paths
