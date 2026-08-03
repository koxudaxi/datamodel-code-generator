"""Runtime symbols used by x-python-type end-to-end fixtures."""

from __future__ import annotations


class StrEnum(str):  # noqa: FURB189  # The mapped target intentionally has string semantics.
    """A target-independent stand-in for an explicitly mapped schema type."""

    __slots__ = ()
