"""Lightweight helpers for interpreting dotted model names."""

from __future__ import annotations

from keyword import iskeyword


def split_module_name(name: str, *, treat_dot_as_module: bool | None) -> list[str] | None:
    """Split a dotted model name when it can safely represent a Python path."""
    match treat_dot_as_module:
        case False:
            return None
        case _ if "." not in name:
            return None
        case True:
            return name.split(".")

    is_normalized = None
    if not name.isascii():
        from unicodedata import is_normalized  # noqa: PLC0415

    parts = name.split(".")
    for part in parts:
        if (
            not part.isidentifier()
            or iskeyword(part)
            or (is_normalized is not None and not is_normalized("NFKC", part))
        ):
            return None
    return parts
