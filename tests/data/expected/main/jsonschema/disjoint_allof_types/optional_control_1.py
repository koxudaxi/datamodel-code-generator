# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import BaseModel, RootModel


class Value(RootModel[str]):
    # Field types: str;
    root: str


class Root(BaseModel):
    # Field types: Value | None;
    value: Value | None = None
