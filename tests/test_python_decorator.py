"""Tests for target-independent rendered decorator structure."""

from __future__ import annotations

import token
from tokenize import TokenInfo

import pytest

from datamodel_code_generator._python_decorator import (
    _consume_group,
    _parse_direct_expression,
    parse_python_decorator,
)


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("decorator", "expected"),
    [
        pytest.param("@deprecated", "deprecated", id="name-fastpath"),
        pytest.param("@deprecated('message')", "deprecated", id="call"),
        pytest.param("@deprecated(t'{reason}')", "deprecated", id="future-template-string"),
        pytest.param("@deprecated(lambda value: (value,))", "deprecated", id="nested-group"),
        pytest.param("@((deprecated))('message')", "deprecated", id="parenthesized-target"),
        pytest.param("@((deprecated('message')))", "deprecated", id="parenthesized-call"),
        pytest.param("@deprecated # comment", "deprecated", id="trailing-comment"),
        pytest.param("deprecated", None, id="missing-marker"),
        pytest.param("@deprecated.factory()", None, id="attribute"),
        pytest.param("@deprecated[str]", None, id="subscript"),
        pytest.param("@deprecated()()", None, id="nested-call"),
        pytest.param("@deprecated(", None, id="unclosed-call"),
        pytest.param("@deprecated(]", None, id="mismatched-call"),
        pytest.param("@(1)", None, id="parenthesized-non-name"),
        pytest.param("@1", None, id="non-name"),
        pytest.param("@class", None, id="keyword"),
        pytest.param("@", None, id="empty"),
    ],
)
def test_parse_python_decorator(decorator: str, expected: str | None) -> None:
    """Retain rendered text while projecting only the direct target structure."""
    expression = parse_python_decorator(decorator)

    assert expression.rendered == decorator
    assert expression.unqualified_target == expected


@pytest.mark.allow_direct_assert
def test_parse_python_decorator_reuses_immutable_structure() -> None:
    """Cache the immutable boundary projection instead of retaining an AST."""
    first = parse_python_decorator("@deprecated(t'{reason}')")

    assert parse_python_decorator("@deprecated(t'{reason}')") is first


@pytest.mark.allow_direct_assert
def test_direct_decorator_parser_rejects_empty_token_stream() -> None:
    """Reject a structurally empty expression at the private parser boundary."""
    assert _parse_direct_expression((), 0) is None


@pytest.mark.allow_direct_assert
def test_decorator_group_parser_rejects_unbalanced_pre_tokenized_input() -> None:
    """Defend against an incomplete token stream supplied below the tokenizer boundary."""
    tokens = (
        TokenInfo(token.OP, "(", (1, 0), (1, 1), "(value"),
        TokenInfo(token.NAME, "value", (1, 1), (1, 6), "(value"),
    )

    assert _consume_group(tokens, 0) is None
