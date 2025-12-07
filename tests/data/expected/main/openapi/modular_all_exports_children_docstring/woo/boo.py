"""
Custom module docstring header.

This is a multi-line docstring used for testing.
"""


from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .. import _internal as field_internal
from .. import bar


class Chocolate(BaseModel):
    flavour: Optional[str] = None
    source: Optional[field_internal.Source] = None
    cocoa: Optional[field_internal.Cocoa] = None
    field: Optional[bar.FieldModel] = None
