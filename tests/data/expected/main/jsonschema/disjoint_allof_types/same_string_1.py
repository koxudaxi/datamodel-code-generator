# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import RootModel


class Root(RootModel[str]):
    # Field types: str;
    root: str


class Base(RootModel[str]):
    # Field types: str;
    root: str
