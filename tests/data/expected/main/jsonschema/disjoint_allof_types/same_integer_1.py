# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import RootModel


class Root(RootModel[int]):
    # Field types: int;
    root: int


class Base(RootModel[int]):
    # Field types: int;
    root: int
