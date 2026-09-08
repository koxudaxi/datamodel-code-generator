# multiline custom ;
# header ;
# file ;

from __future__ import annotations

from pydantic import RootModel


class Root(RootModel[str | None]):
    root: str | None


class Base(RootModel[str | None]):
    root: str | None
