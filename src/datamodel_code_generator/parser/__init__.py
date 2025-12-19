"""Parser utilities and base types for schema parsing.

Provides LiteralType enum for literal parsing options and DefaultPutDict
for caching remote schema content.
"""

from __future__ import annotations

from collections import UserDict
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

TK = TypeVar("TK")
TV = TypeVar("TV")


class LiteralType(Enum):
    """Options for handling enum fields as literals."""

    All = "all"
    One = "one"
    Off = "none"


class DefaultPutDict(UserDict[TK, TV]):
    """Dict that can lazily compute and cache missing values."""

    def get_or_put(
        self,
        key: TK,
        default: TV | None = None,
        default_factory: Callable[[TK], TV] | None = None,
    ) -> TV:
        """Get value for key, or compute and store it if missing."""
        if key in self:
            return self[key]
        if default:  # pragma: no cover
            value = self[key] = default
            return value
        if default_factory:
            value = self[key] = default_factory(key)
            return value
        msg = "Not found default and default_factory"  # pragma: no cover
        raise ValueError(msg)  # pragma: no cover


__all__ = [
    "DefaultPutDict",
    "LiteralType",
]
