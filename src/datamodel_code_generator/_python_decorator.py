"""Target-independent matching for rendered Python decorators."""

from __future__ import annotations

import keyword
import token
import tokenize
from functools import lru_cache
from io import StringIO

_OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
_CLOSE_TOKENS = frozenset(_OPEN_TO_CLOSE.values())
_INVALID_TOKEN_TYPES = frozenset({token.INDENT, token.DEDENT, token.ERRORTOKEN})


def _is_parenthesized_name(body: str, name: str) -> bool:
    """Match a name wrapped only in parentheses without invoking the tokenizer."""
    index = 0
    depth = 0
    body_length = len(body)

    while index < body_length:
        while index < body_length and body[index].isspace():
            index += 1
        if index >= body_length or body[index] != "(":
            break
        depth += 1
        index += 1

    if not depth or not body.startswith(name, index):
        return False
    index += len(name)

    while depth:
        while index < body_length and body[index].isspace():
            index += 1
        if index >= body_length or body[index] != ")":
            return False
        depth -= 1
        index += 1

    return not body[index:].strip()


def _significant_tokens(source: str) -> tuple[tokenize.TokenInfo, ...] | None:
    """Tokenize one logical expression while retaining bracket correctness."""
    result: list[tokenize.TokenInfo] = []
    brackets: list[str] = []
    logical_line_ended = False

    try:
        token_iterator = tokenize.generate_tokens(StringIO(source).readline)
        while (item := next(token_iterator)).type != token.ENDMARKER:
            if logical_line_ended or item.type in _INVALID_TOKEN_TYPES:
                return None
            if item.type == token.NEWLINE:
                logical_line_ended = True
                continue
            if item.type == tokenize.NL:
                continue
            if item.type == token.COMMENT:
                if not brackets and not result:
                    return None
                continue

            result.append(item)
            if item.type != token.OP:
                continue
            if closing := _OPEN_TO_CLOSE.get(item.string):
                brackets.append(closing)
            elif item.string in _CLOSE_TOKENS and (not brackets or item.string != brackets.pop()):
                return None
    except (IndentationError, tokenize.TokenError, UnicodeError):
        return None
    return tuple(result)


def _consume_group(tokens: tuple[tokenize.TokenInfo, ...], index: int) -> int | None:
    """Return the index after one balanced group with valid separators."""
    # Each frame stores the state of the current comma-delimited component:
    # 0 is empty, 1 has content, 2 follows a comma, and 3 follows '='. Bracket
    # pairing was already validated while tokenizing.
    stack = [0]
    token_index = index + 1
    while stack:
        current = tokens[token_index]
        if current.type != token.OP:
            stack[-1] = 1
        else:
            value = current.string
            if value in _OPEN_TO_CLOSE:
                stack[-1] = 1
                stack.append(0)
            elif value in _CLOSE_TOKENS:
                if stack.pop() == 3:
                    return None
            elif value == ",":
                if stack[-1] != 1:
                    return None
                stack[-1] = 2
            elif value == "=":
                if stack[-1] != 1:
                    return None
                stack[-1] = 3
            elif value == ";":
                return None
            else:
                stack[-1] = 1
        token_index += 1
    return token_index


def _parse_direct_target(
    tokens: tuple[tokenize.TokenInfo, ...],
    index: int,
) -> tuple[str, int, bool] | None:
    """Parse a possibly parenthesized name with at most one direct call."""
    wrapper_depth = 0
    while index < len(tokens) and tokens[index].string == "(":
        wrapper_depth += 1
        index += 1
    if index >= len(tokens) or tokens[index].type != token.NAME or keyword.iskeyword(name := tokens[index].string):
        return None
    index += 1
    has_call = False

    while index < len(tokens):
        if wrapper_depth and tokens[index].string == ")":
            wrapper_depth -= 1
            index += 1
        elif not has_call and tokens[index].string == "(":
            if (group_end := _consume_group(tokens, index)) is None:
                return None
            index = group_end
            has_call = True
        else:
            break
    return None if wrapper_depth else (name, index, has_call)


@lru_cache(maxsize=128)
def is_named_python_decorator(decorator: str, name: str) -> bool:
    """Return whether a decorator directly targets an exact unqualified name."""
    if decorator[:1] != "@" or not name.isidentifier() or keyword.iskeyword(name):
        return False

    body = decorator[1:].strip()
    if body.isidentifier():
        return not keyword.iskeyword(body) and body == name
    if _is_parenthesized_name(body, name):
        return True
    if not body or (tokens := _significant_tokens(body)) is None:
        return False
    return (parsed := _parse_direct_target(tokens, 0)) is not None and parsed[1] == len(tokens) and parsed[0] == name
