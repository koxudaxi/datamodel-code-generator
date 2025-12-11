"""Tests for reference resolution functionality."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

import pytest

from datamodel_code_generator.http import join_url
from datamodel_code_generator.reference import ModelResolver, get_relative_path, is_url


@pytest.mark.parametrize(
    ("base_path", "target_path", "expected"),
    [
        ("/a/b", "/a/b", "."),
        ("/a/b", "/a/b/c", "c"),
        ("/a/b", "/a/b/c/d", "c/d"),
        ("/a/b/c", "/a/b", ".."),
        ("/a/b/c/d", "/a/b", "../.."),
        ("/a/b/c/d", "/a", "../../.."),
        ("/a/b/c/d", "/a/x/y/z", "../../../x/y/z"),
        ("/a/b/c/d", "a/x/y/z", "a/x/y/z"),
        ("/a/b/c/d", "/a/b/e/d", "../../e/d"),
    ],
)
def test_get_relative_path_posix(base_path: str, target_path: str, expected: str) -> None:
    """Test get_relative_path function on POSIX paths."""
    assert PurePosixPath(get_relative_path(PurePosixPath(base_path), PurePosixPath(target_path))) == PurePosixPath(
        expected
    )


@pytest.mark.parametrize(
    ("base_path", "target_path", "expected"),
    [
        ("c:/a/b", "c:/a/b", "."),
        ("c:/a/b", "c:/a/b/c", "c"),
        ("c:/a/b", "c:/a/b/c/d", "c/d"),
        ("c:/a/b/c", "c:/a/b", ".."),
        ("c:/a/b/c/d", "c:/a/b", "../.."),
        ("c:/a/b/c/d", "c:/a", "../../.."),
        ("c:/a/b/c/d", "c:/a/x/y/z", "../../../x/y/z"),
        ("c:/a/b/c/d", "a/x/y/z", "a/x/y/z"),
        ("c:/a/b/c/d", "c:/a/b/e/d", "../../e/d"),
    ],
)
def test_get_relative_path_windows(base_path: str, target_path: str, expected: str) -> None:
    """Test get_relative_path function on Windows paths."""
    assert PureWindowsPath(
        get_relative_path(PureWindowsPath(base_path), PureWindowsPath(target_path))
    ) == PureWindowsPath(expected)


def test_model_resolver_add_ref_with_hash() -> None:
    """Test adding reference with URL fragment."""
    model_resolver = ModelResolver()
    reference = model_resolver.add_ref("https://json-schema.org/draft/2020-12/meta/core#")
    assert reference.original_name == "core"


def test_model_resolver_add_ref_without_hash() -> None:
    """Test adding reference without URL fragment."""
    model_resolver = ModelResolver()
    reference = model_resolver.add_ref("meta/core")
    assert reference.original_name == "core"


def test_model_resolver_add_ref_unevaluated() -> None:
    """Test adding reference for unevaluated schema."""
    model_resolver = ModelResolver()
    reference = model_resolver.add_ref("meta/unevaluated")
    assert reference.original_name == "unevaluated"


def test_base_url_context_sets_url_when_base_url_already_set() -> None:
    """When _base_url is already set, base_url_context should switch to new URL."""
    resolver = ModelResolver(base_url="https://example.com/original.json")
    assert resolver.base_url == "https://example.com/original.json"

    with resolver.base_url_context("https://example.com/new.json"):
        assert resolver.base_url == "https://example.com/new.json"

    # Should restore original
    assert resolver.base_url == "https://example.com/original.json"


def test_base_url_context_sets_url_when_new_value_is_url() -> None:
    """When _base_url is None but new value is a URL, should set base_url."""
    resolver = ModelResolver()
    assert resolver.base_url is None

    with resolver.base_url_context("https://example.com/schema.json"):
        assert resolver.base_url == "https://example.com/schema.json"

    # Should restore to None
    assert resolver.base_url is None


def test_base_url_context_noop_when_new_value_is_not_url() -> None:
    """When _base_url is None and new value is not a URL, should do nothing."""
    resolver = ModelResolver()
    assert resolver.base_url is None

    with resolver.base_url_context("../relative/path.json"):
        # Should remain None because the value is not a URL
        assert resolver.base_url is None

    assert resolver.base_url is None


def test_base_url_context_nested() -> None:
    """Nested base_url_context should properly restore values."""
    resolver = ModelResolver(base_url="https://example.com/level0.json")

    with resolver.base_url_context("https://example.com/level1.json"):
        assert resolver.base_url == "https://example.com/level1.json"

        with resolver.base_url_context("https://example.com/level2.json"):
            assert resolver.base_url == "https://example.com/level2.json"

        assert resolver.base_url == "https://example.com/level1.json"

    assert resolver.base_url == "https://example.com/level0.json"


def test_resolve_ref_with_base_url_does_not_prepend_root_id_base_path() -> None:
    """When base_url is set, root_id_base_path should not be prepended to refs."""
    resolver = ModelResolver(base_url="https://example.com/schemas/main.json")
    resolver.set_root_id("https://example.com/schemas/main.json")

    # Resolve a relative ref
    result = resolver.resolve_ref("../other/schema.json")

    # Should resolve via join_url, not prepend root_id_base_path
    assert result == "https://example.com/other/schema.json#"
    # Should NOT be like "https://example.com/schemas/../other/schema.json#"


def test_resolve_ref_with_base_url_nested_relative_refs() -> None:
    """Nested relative refs should resolve correctly when base_url is set."""
    resolver = ModelResolver(base_url="https://example.com/a/b/c/main.json")

    # Resolve a deeply nested relative ref
    result = resolver.resolve_ref("../../other/schema.json")

    assert result == "https://example.com/a/other/schema.json#"


def test_resolve_ref_with_base_url_context_switch() -> None:
    """Relative refs should resolve correctly after base_url context switch."""
    resolver = ModelResolver(base_url="https://example.com/schemas/person.json")

    # Switch context to a different file
    with resolver.base_url_context("https://example.com/schemas/definitions/pet.json"):
        # Resolve a relative ref from the new context
        result = resolver.resolve_ref("../common/types.json")

        assert result == "https://example.com/schemas/common/types.json#"


def test_resolve_ref_local_fragment_with_base_url() -> None:
    """Local fragment refs should resolve to full URL when base_url is set."""
    resolver = ModelResolver(base_url="https://example.com/schemas/main.json")

    result = resolver.resolve_ref("#/definitions/Foo")

    # When base_url is set, local fragments are resolved to full URL
    assert result == "https://example.com/schemas/main.json#/definitions/Foo"


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        # HTTP/HTTPS URLs
        ("https://example.com/schema.json", True),
        ("http://example.com/schema.json", True),
        ("https://example.com/path/to/schema.json", True),
        # file:// URLs - recognized and handled via filesystem
        ("file:///home/user/schema.json", True),
        ("file:///C:/path/to/schema.json", True),
        ("file://server/share/schema.json", True),
        # file:/ (single slash) - NOT recognized as valid file URL
        ("file:/home/user/schema.json", False),
        # Other URL schemes - NOT recognized
        ("ftp://example.com/schema.json", False),
        # Relative paths (not URLs)
        ("../relative/path.json", False),
        ("relative/path.json", False),
        # Local fragments (not URLs)
        ("#/definitions/Foo", False),
        ("#", False),
        # Absolute paths (not URLs)
        ("/absolute/path.json", False),
        # Windows paths (not URLs)
        ("c:/windows/path.json", False),
        ("d:/path/to/file.json", False),
    ],
)
def test_is_url(ref: str, expected: bool) -> None:
    """Test is_url correctly identifies HTTP(S) and file:// URLs."""
    assert is_url(ref) == expected


def test_resolve_ref_with_root_id_differs_from_base_url() -> None:
    """When $id differs from fetch URL, refs should resolve against $id."""
    # Scenario: Schema fetched from CDN but has canonical $id
    resolver = ModelResolver(base_url="https://cdn.example.com/latest/schema.json")
    resolver.set_root_id("https://example.com/v1/schema.json")

    result = resolver.resolve_ref("../common/types.json")

    assert result == "https://example.com/common/types.json#"


@pytest.mark.parametrize(
    ("base_url", "ref", "expected"),
    [
        # file:// URL joining - relative refs
        ("file:///home/user/schemas/main.json", "../common/types.json", "file:///home/user/common/types.json"),
        ("file:///home/user/schemas/main.json", "other.json", "file:///home/user/schemas/other.json"),
        ("file:///home/user/schemas/main.json", "./sub/schema.json", "file:///home/user/schemas/sub/schema.json"),
        # file:// URL joining - absolute file:// refs
        ("file:///home/user/schemas/main.json", "file:///other/schema.json", "file:///other/schema.json"),
        # file:// URL joining - absolute path refs (starts with /)
        ("file:///home/user/schemas/main.json", "/absolute/path.json", "file:///absolute/path.json"),
        ("file://server/share/main.json", "/absolute/path.json", "file://server/absolute/path.json"),
        # Windows-style file:// URLs
        ("file:///C:/schemas/main.json", "../common/types.json", "file:///C:/common/types.json"),
        # UNC file:// URLs
        ("file://server/share/main.json", "../common/types.json", "file://server/share/common/types.json"),
        ("file://server/share/main.json", "child.json", "file://server/share/child.json"),
        # Fragment handling
        (
            "file:///home/user/schemas/main.json",
            "other.json#/definitions/Foo",
            "file:///home/user/schemas/other.json#/definitions/Foo",
        ),
        (
            "file:///home/user/schemas/main.json",
            "#/definitions/Bar",
            "file:///home/user/schemas/main.json#/definitions/Bar",
        ),
        # Multiple .. traversal - stops at root for non-UNC
        ("file:///a/b/main.json", "../../../other.json", "file:///other.json"),
        # Multiple .. traversal - stops at share level for UNC (min_depth=1)
        ("file://server/share/a/b/main.json", "../../../../other.json", "file://server/share/other.json"),
        # Empty and dot segments
        ("file:///home/user/schemas/main.json", "./", "file:///home/user/schemas/"),
        ("file:///home/user/schemas/main.json", "a//b/./c.json", "file:///home/user/schemas/a/b/c.json"),
        # Fragment-only ref without fragment content (just #)
        ("file:///home/user/schemas/main.json", "#", "file:///home/user/schemas/main.json#"),
        # Empty ref (keeps base URL unchanged)
        ("file:///home/user/schemas/main.json", "", "file:///home/user/schemas/main.json"),
        # Root directory base URL (triggers empty base_segments branch)
        ("file:///", "schema.json", "file:///schema.json"),
        ("file:///main.json", "../other.json", "file:///other.json"),
    ],
)
def test_join_url_file_scheme(base_url: str, ref: str, expected: str) -> None:
    """Test join_url correctly handles file:// URLs."""
    assert join_url(base_url, ref) == expected


def test_url_ref_matches_local_id_no_fragment() -> None:
    """URL $ref matching a local $id should resolve to the $id's path (Issue #1747)."""
    resolver = ModelResolver()
    resolver.set_current_root([])
    resolver.add_id("https://schemas.example.org/child", ["#", "$defs", "child"])

    result = resolver.resolve_ref("https://schemas.example.org/child#")

    assert result == "#/$defs/child"


def test_url_ref_matches_local_id_with_fragment() -> None:
    """URL $ref with fragment should combine $id path with fragment (Issue #1747)."""
    resolver = ModelResolver()
    resolver.set_current_root([])
    resolver.add_id("https://schemas.example.org/child", ["#", "$defs", "child"])

    result = resolver.resolve_ref("https://schemas.example.org/child#/properties/name")

    assert result == "#/$defs/child/properties/name"


def test_url_ref_no_matching_local_id() -> None:
    """URL $ref not matching any local $id should remain as URL (Issue #1747)."""
    resolver = ModelResolver()
    resolver.set_current_root([])

    result = resolver.resolve_ref("https://schemas.example.org/other#")

    assert result == "https://schemas.example.org/other#"


def test_url_ref_matches_local_id_nested_fragment() -> None:
    """URL $ref with deeply nested fragment should resolve correctly (Issue #1747)."""
    resolver = ModelResolver()
    resolver.set_current_root([])
    resolver.add_id("https://example.org/types", ["#", "$defs", "types"])

    result = resolver.resolve_ref("https://example.org/types#/definitions/Address/properties/city")

    assert result == "#/$defs/types/definitions/Address/properties/city"


def test_url_ref_matches_local_id_with_base_url() -> None:
    """URL $ref matching local $id should resolve via $id mapping even when base_url is set (Issue #1747)."""
    resolver = ModelResolver(base_url="https://cdn.example.com/schemas/main.json")
    resolver.set_current_root([])
    resolver.add_id("https://schemas.example.org/child", ["#", "$defs", "child"])

    result = resolver.resolve_ref("https://schemas.example.org/child#")

    assert result == "https://cdn.example.com/schemas/main.json#/$defs/child"


def test_url_ref_matches_local_id_preserves_empty_json_pointer_token() -> None:
    """URL $ref fragment with empty JSON Pointer token (//) should be preserved (Issue #1747)."""
    resolver = ModelResolver()
    resolver.set_current_root([])
    resolver.add_id("https://example.org/types", ["#", "$defs", "types"])

    result = resolver.resolve_ref("https://example.org/types#/items//child")

    assert result == "#/$defs/types/items//child"


def test_resolve_ref_local_fragment_with_base_url_and_current_root() -> None:
    """Local fragment refs should resolve to current_root when it's set, even with base_url (Issue #1798)."""
    resolver = ModelResolver(base_url="https://raw.githubusercontent.com/user/repo/schema.json")
    resolver.set_root_id("https://cveproject.github.io/schema/schema.json")
    resolver.set_current_root(["https://raw.githubusercontent.com/user/repo/schema.json"])

    result = resolver.resolve_ref("#/definitions/Foo")

    assert result == "https://raw.githubusercontent.com/user/repo/schema.json#/definitions/Foo"


def test_resolve_ref_local_fragment_with_different_host_base_url_and_root_id() -> None:
    """Local fragment refs should resolve correctly when base_url and root_id have different hosts (Issue #1798)."""
    resolver = ModelResolver(base_url="https://raw.githubusercontent.com/user/repo/schema.json")
    resolver.set_root_id("https://cveproject.github.io/schema/schema.json")
    resolver.set_current_root(["https://raw.githubusercontent.com/user/repo/schema.json"])

    result = resolver.resolve_ref("#/definitions/product/properties/url")

    assert result == "https://raw.githubusercontent.com/user/repo/schema.json#/definitions/product/properties/url"


def test_resolve_ref_local_fragment_without_current_root_falls_back_to_url() -> None:
    """Local fragment refs without current_root should fall back to URL resolution (Issue #1798)."""
    resolver = ModelResolver(base_url="https://example.com/schemas/main.json")

    result = resolver.resolve_ref("#/definitions/Foo")

    assert result == "https://example.com/schemas/main.json#/definitions/Foo"
