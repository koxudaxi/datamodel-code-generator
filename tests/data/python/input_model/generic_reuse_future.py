"""Future annotations with stable exported metadata and an inline-only diagnostic."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Annotated, ForwardRef
from pydantic import BaseModel, Field
from tests.data.python.input_model.generic_reuse import Box, Positive
HiddenBox = RaisingBox = SafeExportedBox = Box[Annotated[int, Field(gt=3)]]
SafeExportedBox.__module__ = "unloaded_generic_module"
@dataclass
class FutureAliasRoot:
    box: Box[Positive]
@dataclass
class FutureExportRoot:
    box: SafeExportedBox
@dataclass
class FutureListRoot:
    box: Box[list[Positive]]
@dataclass
class FutureUnionRoot:
    box: Box[Positive | None]
@dataclass
class FutureInlineRoot:
    box: Box[Annotated[int, Field(gt=3)]]

import sys
import types
class NestedOwner:
    class NestedRoot(BaseModel):
        box: Box[Positive]

class _ExportModule(types.ModuleType):
    def __getattribute__(self, name):
        if name == "NestedRoot":
            return NestedOwner.NestedRoot
        if name == "HiddenBox":
            return Box[int]
        if name == "RaisingBox":
            raise AttributeError(name)
        return super().__getattribute__(name)
sys.modules[__name__].__class__ = _ExportModule

# Bind explicit forward-reference modules for the declared Pydantic 2.0 minimum.
for _model in (FutureAliasRoot, FutureExportRoot, FutureListRoot, FutureUnionRoot, FutureInlineRoot):
    for _name, _annotation in _model.__annotations__.items():
        _reference = ForwardRef(_annotation, module=__name__)
        _model.__annotations__[_name] = _reference
        _model.__dataclass_fields__[_name].type = _reference
