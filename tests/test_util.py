"""Direct tests for datamodel_code_generator.util helper behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from datamodel_code_generator.util import create_module_getattr, get_safe_loader


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear lru_cache state so loader construction is characterized directly."""
    get_safe_loader.cache_clear()


def test_safe_loader_warns_for_uppercase_yaml_bool() -> None:
    """PyYAML uppercase bool construction emits the deprecation warning."""
    yaml = pytest.importorskip("yaml")

    with pytest.warns(DeprecationWarning, match=r"YAML bool 'TRUE' is deprecated"):
        result = yaml.load("enabled: TRUE\n", Loader=get_safe_loader())

    assert result == {"enabled": True}


def test_create_module_getattr_imports_lazy_attribute() -> None:
    """create_module_getattr imports and returns configured lazy attributes."""
    module_getattr = create_module_getattr(
        "example.module",
        {"Path": ("pathlib", "Path")},
    )

    assert module_getattr("Path") is Path


def test_create_module_getattr_raises_attribute_error_for_unknown_attribute() -> None:
    """create_module_getattr raises the normal module AttributeError message."""
    module_getattr = create_module_getattr("example.module", {})

    with pytest.raises(AttributeError) as exc_info:
        module_getattr("Missing")

    assert str(exc_info.value) == "module 'example.module' has no attribute 'Missing'"
