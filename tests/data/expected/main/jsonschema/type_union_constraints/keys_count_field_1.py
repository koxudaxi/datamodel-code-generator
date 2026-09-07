# Type-specific union constraints

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, constr
from typing_extensions import TypeAliasType

ValueObject = TypeAliasType(
    "ValueObject", Annotated[dict[constr(pattern=r'^a'), Any], Field(min_length=1)]
)


class Root(BaseModel):
    before: bool | None = True
    value: ValueObject | list[Any] | None
    after: int | None = 7
