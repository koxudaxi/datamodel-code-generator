# Type-specific union constraints

from __future__ import annotations

from typing import Annotated

from pydantic import Field, conint, constr
from typing_extensions import TypeAliasType

Root = TypeAliasType(
    "Root", Annotated[conint(ge=2) | constr(max_length=2), Field(..., title='Root')]
)
