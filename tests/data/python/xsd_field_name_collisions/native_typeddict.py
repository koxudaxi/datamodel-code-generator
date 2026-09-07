"""Independent native TypedDict matching the ordinary XSD field contract."""

from typing import TypedDict


class NativeRoot(TypedDict):
    item: int
    code: str
