# generated by datamodel-codegen:
#   filename:  scientific_notation.json
#   timestamp: 2025-03-28T00:00:00+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Model(BaseModel):
    test: Optional[float] = Field(1e-05, description='Testcase', title='Test')
