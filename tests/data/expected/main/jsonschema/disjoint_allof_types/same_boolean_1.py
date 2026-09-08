# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import RootModel


class Root(RootModel[bool]):
    # Field types: bool;
    root: bool


class Base(RootModel[bool]):
    # Field types: bool;
    root: bool
