# Type-specific union constraints

from __future__ import annotations

from typing import Any

from pydantic import Field, RootModel, constr
from typing_extensions import TypeAliasType

RootObject = TypeAliasType("RootObject", dict[constr(pattern=r'^a'), Any])


class Root(RootModel[list[Any] | RootObject]):
    root: list[Any] | RootObject = Field(..., title='Root')
