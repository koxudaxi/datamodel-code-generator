"""Public API signature baselines from origin/main."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from datamodel_code_generator import generate
from datamodel_code_generator.parser.base import Parser, YamlValue

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path
    from urllib.parse import ParseResult

    from typing_extensions import Unpack

    from datamodel_code_generator.config import GenerateConfig, GenerateConfigDict, ParserConfig, ParserConfigDict


def _baseline_generate(
    input_: Path | str | ParseResult | Mapping[str, Any],
    *,
    config: GenerateConfig | None = None,
    **options: Unpack[GenerateConfigDict],
) -> str | object | None:
    raise NotImplementedError


class _BaselineParser:
    def __init__(
        self,
        source: str | Path | list[Path] | ParseResult | dict[str, YamlValue],
        *,
        config: ParserConfig | None = None,
        **options: Unpack[ParserConfigDict],
    ) -> None:
        raise NotImplementedError


def _kwonly_params(signature: inspect.Signature) -> list[inspect.Parameter]:
    return [param for param in signature.parameters.values() if param.kind is inspect.Parameter.KEYWORD_ONLY]


def _kwonly_by_name(signature: inspect.Signature) -> dict[str, inspect.Parameter]:
    return {param.name: param for param in _kwonly_params(signature)}


def test_generate_signature_matches_baseline() -> None:
    """Ensure generate keeps the origin/main kw-only args and annotations."""
    expected = inspect.signature(_baseline_generate)
    actual = inspect.signature(generate)
    assert _kwonly_by_name(actual).keys() == _kwonly_by_name(expected).keys()
    for name, param in _kwonly_by_name(expected).items():
        assert _kwonly_by_name(actual)[name].annotation == param.annotation


def test_parser_signature_matches_baseline() -> None:
    """Ensure Parser.__init__ keeps the origin/main kw-only args and annotations."""
    expected = inspect.signature(_BaselineParser.__init__)
    actual = inspect.signature(Parser.__init__)
    assert _kwonly_by_name(actual).keys() == _kwonly_by_name(expected).keys()
    for name, param in _kwonly_by_name(expected).items():
        assert _kwonly_by_name(actual)[name].annotation == param.annotation
