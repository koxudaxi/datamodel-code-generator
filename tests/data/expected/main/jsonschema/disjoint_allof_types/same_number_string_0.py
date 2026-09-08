# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import RootModel


class Root(RootModel[float | str]):
    root: float | str


class Base(RootModel[float | str]):
    root: float | str
