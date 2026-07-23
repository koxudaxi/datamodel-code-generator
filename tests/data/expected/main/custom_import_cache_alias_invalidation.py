from __future__ import annotations

from datetime import date as date_aliased
from typing import Optional

from pydantic import AwareDatetime, BaseModel


class TypeDate(BaseModel):
    cache_clear_history = ['empty', 'cached', 'cached']
    date: Optional[date_aliased]
    datetime: Optional[AwareDatetime] = None
