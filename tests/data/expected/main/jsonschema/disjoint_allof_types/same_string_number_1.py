# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import RootModel


class Root(RootModel[str | float]):
    # Field types: str | float;
    root: str | float


class Base(RootModel[str | float]):
    # Field types: str | float;
    root: str | float
