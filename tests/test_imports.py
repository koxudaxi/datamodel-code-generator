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


def test_pydantic_import_constants_share_leaf_module() -> None:
    """Test Pydantic import constants share identity without changing dataclass Field."""
    from datamodel_code_generator.model import imports as model_imports
    from datamodel_code_generator.model import pydantic_base
    from datamodel_code_generator.model.pydantic_v2 import imports as pydantic_v2_imports

    assert pydantic_base.IMPORT_FIELD is pydantic_v2_imports.IMPORT_FIELD
    assert pydantic_base.IMPORT_ANYURL is pydantic_v2_imports.IMPORT_ANYURL
    assert Import(import_="Field", from_="pydantic") == pydantic_base.IMPORT_FIELD
    assert Import(import_="AnyUrl", from_="pydantic") == pydantic_base.IMPORT_ANYURL
    assert model_imports.IMPORT_FIELD is not pydantic_base.IMPORT_FIELD
    assert Import(import_="field", from_="dataclasses") == model_imports.IMPORT_FIELD


def test_import_from_full_path_cache_clear_preserves_value() -> None:
    """Clearing the bounded cache must not change Import.from_full_path results."""
    import_ = Import.from_full_path("typing.Optional")

    Import.from_full_path.cache_clear()

    assert Import.from_full_path("typing.Optional") == import_


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


def test_remove_dotted_import_decrements_counter_and_cleans_reference_paths() -> None:
    """Dotted imports keep their public counters and reference paths consistent."""
    imports = Imports()
    first_import = Import(from_=None, import_="collections.abc", reference_path="/first/path")
    second_import = Import(from_=None, import_="collections.abc", reference_path="/second/path")
    imports.append([first_import, second_import])

    assert str(imports) == "import collections.abc"
    assert imports.counter[None, "collections.abc"] == 2
    assert imports.reference_paths == {
        "/first/path": first_import,
        "/second/path": second_import,
    }

    imports.remove(first_import)

    assert str(imports) == "import collections.abc"
    assert imports.counter[None, "collections.abc"] == 1
    assert "/first/path" not in imports.reference_paths
    assert imports.reference_paths["/second/path"] is second_import

    imports.remove(second_import)

    assert not str(imports)
    assert (None, "collections.abc") not in imports.counter
    assert None not in imports
    assert "/second/path" not in imports.reference_paths


def test_remove_missing_dotted_import_is_noop() -> None:
    """Removing a dotted import that was never added leaves imports unchanged."""
    imports = Imports()
    imports.append(Import(from_=None, import_="collections.abc"))

    imports.remove(Import(from_=None, import_="pathlib.Path"))

    assert str(imports) == "import collections.abc"
    assert imports.counter[None, "collections.abc"] == 1


def test_remove_dotted_import_keeps_bucket_when_other_dotted_imports_remain() -> None:
    """Removing one dotted import keeps the import bucket when another remains."""
    imports = Imports()
    first_import = Import(from_=None, import_="collections.abc")
    second_import = Import(from_=None, import_="pathlib.Path")
    imports.append([first_import, second_import])

    imports.remove(first_import)

    assert str(imports) == "import pathlib.Path"
    assert imports[None] == {"pathlib.Path"}
    assert (None, "collections.abc") not in imports.counter
    assert imports.counter[None, "pathlib.Path"] == 1


def test_remove_dotted_import_without_bucket_cleans_reference_path() -> None:
    """Defensive dotted import removal still clears counters and reference paths."""
    imports = Imports()
    import_ = Import(from_=None, import_="collections.abc", reference_path="/stale/path")
    imports.counter[None, "collections.abc"] = 1
    imports.reference_paths["/stale/path"] = import_

    imports.remove(import_)

    assert not str(imports)
    assert (None, "collections.abc") not in imports.counter
    assert "/stale/path" not in imports.reference_paths


def test_plain_from_none_alias_cleanup_after_remove_and_remove_unused() -> None:
    """Plain imports without from_ still record and clean aliases."""
    imports = Imports()
    aliased_import = Import(from_=None, import_="datetime", alias="datetime_module", reference_path="/datetime")
    imports.append(aliased_import)

    assert str(imports) == "import datetime as datetime_module"
    assert imports[None] == {"datetime"}
    assert imports.alias[None] == {"datetime": "datetime_module"}
    assert imports.counter[None, "datetime"] == 1
    assert imports.reference_paths["/datetime"] is aliased_import

    imports.remove(aliased_import)

    assert not str(imports)
    assert None not in imports
    assert None not in imports.alias
    assert (None, "datetime") not in imports.counter
    assert "/datetime" not in imports.reference_paths

    imports.append(aliased_import)
    imports.remove_unused(set())

    assert not str(imports)
    assert None not in imports
    assert None not in imports.alias
    assert (None, "datetime") not in imports.counter
    assert "/datetime" not in imports.reference_paths

    imports.append(Import(from_=None, import_="datetime"))

    assert str(imports) == "import datetime"


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
