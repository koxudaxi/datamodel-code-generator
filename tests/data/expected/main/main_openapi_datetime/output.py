# generated by datamodel-codegen:
#   filename:  datetime.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    releaseDate: datetime = Field(..., example='2016-08-29T09:12:33.001Z')
