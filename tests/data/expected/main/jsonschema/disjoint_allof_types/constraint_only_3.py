# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import Field, RootModel


class Root(RootModel[str]):
    # Field types: str;
    root: str = Field(..., min_length=1)


class Base(RootModel[str]):
    # Field types: str;
    root: str
