# Type-specific union constraints

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, RootModel, constr
from typing_extensions import TypeAliasType

RootObject = TypeAliasType(
    "RootObject", Annotated[dict[constr(pattern=r'^a'), Any], Field(min_length=1)]
)


class Root(RootModel[RootObject | list[Any] | None]):
    root: RootObject | list[Any] | None = Field(..., title='Root')
