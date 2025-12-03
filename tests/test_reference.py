"""Tests for reference resolution functionality."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

import pytest

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
        # file:// URLs
        ("file:///home/user/schema.json", True),
        ("file:/home/user/schema.json", True),
        # Other URL schemes
        ("ftp://example.com/schema.json", True),
        # Relative paths (not URLs)
        ("../relative/path.json", False),
        ("relative/path.json", False),
        # Local fragments (not URLs)
        ("#/definitions/Foo", False),
        ("#", False),
        # Absolute paths (not URLs)
        ("/absolute/path.json", False),
        # Windows paths (not URLs - single letter scheme)
        ("c:/windows/path.json", False),
        ("d:/path/to/file.json", False),
    ],
)
def test_is_url(ref: str, expected: bool) -> None:
    """Test is_url correctly identifies URLs vs file paths."""
    assert is_url(ref) == expected


def test_base_url_context_with_file_url() -> None:
    """base_url_context should work with file:// URLs."""
    resolver = ModelResolver()
    assert resolver.base_url is None

    with resolver.base_url_context("file:///home/user/schema.json"):
        assert resolver.base_url == "file:///home/user/schema.json"

    assert resolver.base_url is None
