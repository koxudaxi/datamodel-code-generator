"""Helpers for imports required by generated non-finite float literals."""

from __future__ import annotations

import re
from typing import Any

NON_FINITE_LITERAL_PATTERN = re.compile(r"(?<![\w.'\"])[+-]?(?P<name>inf|nan)(?![\w'\"])")


def add_math_imports_for_non_finite_literals(body: str) -> str:
    if "inf" not in body and "nan" not in body:
        return body

    names = {match.group("name") for match in NON_FINITE_LITERAL_PATTERN.finditer(body)}
    if not names:
        return body

    import_line = f"from math import {', '.join(name for name in ('inf', 'nan') if name in names)}"
    if import_line in body:
        return body

    lines = body.splitlines()
    insert_at = 0
    while insert_at < len(lines) and (
        lines[insert_at].startswith("#")
        or lines[insert_at].startswith("from __future__ import ")
        or not lines[insert_at]
    ):
        insert_at += 1
    lines.insert(insert_at, import_line)
    return "\n".join(lines)


def apply_math_imports_to_parse_result(result: str | dict[tuple[str, ...], Any]) -> str | dict[tuple[str, ...], Any]:
    if isinstance(result, str):
        return add_math_imports_for_non_finite_literals(result)
    for item in result.values():
        item.body = add_math_imports_for_non_finite_literals(item.body)
    return result
