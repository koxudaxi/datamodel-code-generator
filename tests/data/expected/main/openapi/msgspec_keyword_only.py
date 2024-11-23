# generated by datamodel-codegen:
#   filename:  inheritance.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from typing import Optional

from msgspec import Struct


class Base(Struct, kw_only=True):
    id: str
    createdAt: Optional[str] = None
    version: Optional[float] = 1


class Child(Base, kw_only=True):
    title: str
    url: Optional[str] = 'https://example.com'
