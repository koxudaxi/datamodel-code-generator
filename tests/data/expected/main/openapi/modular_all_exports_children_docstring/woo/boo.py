"""
Custom module docstring header.

This is a multi-line docstring used for testing.
"""


from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .. import Source, bar, foo


class Chocolate(BaseModel):
    flavour: Optional[str] = None
    source: Optional[Source] = None
    cocoa: Optional[foo.Cocoa] = None
    field: Optional[bar.FieldModel] = None
