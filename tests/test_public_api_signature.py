"""Public API shape checks to avoid breaking changes."""

from __future__ import annotations

import inspect

from datamodel_code_generator import GenerateConfigDict, ParseConfigDict, ParserConfigDict, generate
from datamodel_code_generator.parser.base import Parser


def test_generate_signature_has_config_and_options() -> None:
    """generate keeps keyword-only config and **options for compatibility."""
    signature = inspect.signature(generate)
    params = signature.parameters

    assert "input_" in params
    assert "config" in params
    assert params["config"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["config"].default is None
    assert any(param.kind is inspect.Parameter.VAR_KEYWORD for param in params.values())


def test_parser_init_signature_has_config_and_options() -> None:
    """Parser.__init__ keeps keyword-only config and **options for compatibility."""
    signature = inspect.signature(Parser.__init__)
    params = signature.parameters

    assert "source" in params
    assert "config" in params
    assert params["config"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["config"].default is None
    assert any(param.kind is inspect.Parameter.VAR_KEYWORD for param in params.values())


def test_config_dicts_are_exposed() -> None:
    """TypedDicts remain available as runtime symbols."""
    for config_dict in (GenerateConfigDict, ParseConfigDict, ParserConfigDict):
        assert hasattr(config_dict, "__annotations__")
        assert isinstance(config_dict.__annotations__, dict)
