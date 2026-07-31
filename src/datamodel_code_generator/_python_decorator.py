"""Target-independent structure for rendered Python decorators."""

from __future__ import annotations

import keyword
import token
import tokenize
from dataclasses import dataclass
from functools import lru_cache
from io import StringIO


@dataclass(frozen=True, slots=True)
class PythonDecoratorExpression:
    """A rendered decorator paired with its direct callable target, if any."""

    rendered: str
    unqualified_target: str | None


_IGNORED_TOKEN_TYPES = frozenset({token.ENDMARKER, token.INDENT, token.DEDENT, token.NEWLINE, tokenize.NL})
_OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
_CLOSE_TOKENS = frozenset(_OPEN_TO_CLOSE.values())
_COMPLEX_CALL_ARGUMENT_CHARACTERS = frozenset("()[]{}\r\n#;")


def _significant_tokens(source: str) -> tuple[tokenize.TokenInfo, ...] | None:
    try:
        return tuple(
            item
            for item in tokenize.generate_tokens(StringIO(source).readline)
            if item.type not in _IGNORED_TOKEN_TYPES and item.type != token.COMMENT
        )
    except (IndentationError, tokenize.TokenError):
        return None


def _simple_call_target(body: str) -> str | None:
    """Return the direct target for the common flat-call fast path."""
    if (opening := body.find("(")) <= 0 or body[-1:] != ")":
        return None
    name = body[:opening].rstrip()
    if (
        not name.isidentifier()
        or keyword.iskeyword(name)
        or not _COMPLEX_CALL_ARGUMENT_CHARACTERS.isdisjoint(body[opening + 1 : -1])
    ):
        return None
    return name


def _consume_group(tokens: tuple[tokenize.TokenInfo, ...], index: int) -> int | None:
    """Return the index after one balanced group without parsing its target-version syntax."""
    stack = [_OPEN_TO_CLOSE[tokens[index].string]]
    for token_index in range(index + 1, len(tokens)):
        current = tokens[token_index]
        if current.type != token.OP:
            continue
        value = current.string
        if closing := _OPEN_TO_CLOSE.get(value):
            stack.append(closing)
        elif value in _CLOSE_TOKENS:
            if value != stack.pop():
                return None
            if not stack:
                return token_index + 1
    return None


def _parse_direct_expression(
    tokens: tuple[tokenize.TokenInfo, ...],
    index: int,
) -> tuple[str, int, bool] | None:
    """Parse a possibly parenthesized name with at most one direct call."""
    if index >= len(tokens):
        return None

    current = tokens[index]
    if current.type == token.NAME and not keyword.iskeyword(current.string):
        name, index, has_call = current.string, index + 1, False
    elif current.string == "(":
        if (
            (parsed := _parse_direct_expression(tokens, index + 1)) is None
            or parsed[1] >= len(tokens)
            or tokens[parsed[1]].string != ")"
        ):
            return None
        name, index, has_call = parsed[0], parsed[1] + 1, parsed[2]
    else:
        return None

    if index >= len(tokens) or tokens[index].string != "(":
        return name, index, has_call
    if has_call or (group_end := _consume_group(tokens, index)) is None:
        return None
    return name, group_end, True


@lru_cache(maxsize=128)
def parse_python_decorator(decorator: str) -> PythonDecoratorExpression:
    """Project rendered decorator text into the structure needed by model policies."""
    if decorator[:1] != "@":
        return PythonDecoratorExpression(decorator, None)

    body = decorator[1:].strip()
    if body.isidentifier() and not keyword.iskeyword(body):
        return PythonDecoratorExpression(decorator, body)
    if name := _simple_call_target(body):
        return PythonDecoratorExpression(decorator, name)
    if not body or (tokens := _significant_tokens(body)) is None:
        return PythonDecoratorExpression(decorator, None)
    if (parsed := _parse_direct_expression(tokens, 0)) is None or parsed[1] != len(tokens):
        return PythonDecoratorExpression(decorator, None)
    return PythonDecoratorExpression(decorator, parsed[0])
