"""Tests for parser cache helper behavior."""

from __future__ import annotations

import pytest

from datamodel_code_generator.parser import DefaultPutDict


def test_get_or_put_returns_existing_value_without_using_default() -> None:
    """Return cached values without evaluating defaults."""
    cache = DefaultPutDict[str, str]({"schema": "cached"})

    def fail_factory(key: str) -> str:
        msg = f"default factory should not be called for {key}"
        raise AssertionError(msg)

    assert cache.get_or_put("schema", default="fresh", default_factory=fail_factory) == "cached"
    assert cache["schema"] == "cached"


def test_get_or_put_stores_truthy_default() -> None:
    """Store and return a truthy explicit default."""
    cache = DefaultPutDict[str, str]()

    assert cache.get_or_put("schema", default="fresh") == "fresh"
    assert cache["schema"] == "fresh"


def test_get_or_put_stores_default_factory_value_once() -> None:
    """Store factory output and avoid calling the factory on cache hits."""
    cache = DefaultPutDict[str, str]()
    calls: list[str] = []

    def default_factory(key: str) -> str:
        calls.append(key)
        return f"value for {key}"

    assert cache.get_or_put("schema", default_factory=default_factory) == "value for schema"
    assert cache.get_or_put("schema", default_factory=default_factory) == "value for schema"
    assert cache["schema"] == "value for schema"
    assert calls == ["schema"]


def test_get_or_put_raises_when_default_and_factory_are_missing() -> None:
    """Raise the current error when no default source is supplied."""
    cache = DefaultPutDict[str, str]()

    with pytest.raises(ValueError, match=r"^Not found default and default_factory$"):
        cache.get_or_put("schema")
