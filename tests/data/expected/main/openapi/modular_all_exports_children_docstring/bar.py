"""
Custom module docstring header.

This is a multi-line docstring used for testing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FieldModel(BaseModel):
    __root__: str = Field(..., example='green')
