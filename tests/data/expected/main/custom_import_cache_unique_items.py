from __future__ import annotations

from enum import StrEnum
from typing import Optional, Set

from pydantic import BaseModel


class Status(StrEnum):
    active = 'active'
    inactive = 'inactive'
    pending = 'pending'


class Item(BaseModel):
    cache_clear_history = ['empty', 'cached', 'cached']
    __hash__ = object.__hash__
    name: Optional[str] = None


class Container(BaseModel):
    cache_clear_history = ['empty', 'cached', 'empty', 'empty', 'cached']
    statuses: Optional[Set[Status]] = None
    items: Optional[Set[Item]] = None
