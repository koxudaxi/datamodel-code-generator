"""Helpers for imports required by generated non-finite float literals."""

from __future__ import annotations

import ast
import re
from typing import Any

NON_FINITE_LITERAL_PATTERN = re.compile(r"(?<![\w.'\"])[+-]?(?P<name>inf|nan)(?![\w'\"])")
TRIPLE_QUOTES = ('"""', "'''")


def _get_required_non_finite_imports(body: str) -> set[str]:
    if "inf" not in body and "nan" not in body:
        return set()
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return {match.group("name") for match in NON_FINITE_LITERAL_PATTERN.finditer(body)}

    used_names: set[str] = set()
    imported_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in {"inf", "nan"}:
            used_names.add(node.id)
        elif isinstance(node, (ast.ImportFrom, ast.Import)):
            for alias in node.names:
                if (alias.asname or alias.name) in {"inf", "nan"}:
                    imported_names.add(alias.asname or alias.name)

    return used_names - imported_names


def add_math_imports_for_non_finite_literals(body: str) -> str:
    missing_names = _get_required_non_finite_imports(body)
    if not missing_names:
        return body

    needed = sorted(missing_names)
    import_line = f"from math import {', '.join(name for name in ('inf', 'nan') if name in needed)}"

    lines = body.splitlines()
    insert_at = 0
    in_multiline = False
    quote_char = ""
    while insert_at < len(lines):
        line = lines[insert_at]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            insert_at += 1
            continue
        if stripped.startswith("from __future__ import "):
            insert_at += 1
            while insert_at < len(lines) and not lines[insert_at].strip():
                insert_at += 1
            continue
        if not in_multiline and stripped.startswith(TRIPLE_QUOTES):
            quote = stripped[:3]
            if stripped.endswith(quote) and len(stripped) > len(quote):
                insert_at += 1
                continue
            in_multiline = True
            quote_char = quote
            insert_at += 1
            continue
        if in_multiline:
            if quote_char in stripped:
                in_multiline = False
            insert_at += 1
            continue
        break

    lines.insert(insert_at, import_line)
    return "\n".join(lines)


def apply_math_imports_to_parse_result(result: str | dict[tuple[str, ...], Any]) -> str | dict[tuple[str, ...], Any]:
    if isinstance(result, str):
        return add_math_imports_for_non_finite_literals(result)
    for item in result.values():
        item.body = add_math_imports_for_non_finite_literals(item.body)
    return result
