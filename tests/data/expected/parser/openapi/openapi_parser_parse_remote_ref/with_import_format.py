from __future__ import annotations

from typing import Optional

from pydantic import AnyUrl, BaseModel, conint


class Problem(BaseModel):
    detail: Optional[str] = None
    instance: Optional[AnyUrl] = None
    status: Optional[conint(ge=100, le=600, lt=1)] = None
    title: Optional[str] = None
    type: Optional[AnyUrl] = 'about:blank'
