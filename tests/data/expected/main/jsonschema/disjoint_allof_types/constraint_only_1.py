# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import RootModel, constr


class Root(RootModel[constr(min_length=1)]):
    # Field types: constr(min_length=1);
    root: constr(min_length=1)


class Base(RootModel[str]):
    # Field types: str;
    root: str
