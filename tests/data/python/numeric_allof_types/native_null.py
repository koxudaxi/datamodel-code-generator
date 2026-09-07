"""Independent native control for the established generated null root syntax."""
from pydantic import RootModel


class NativeNull(RootModel[None]):
    root: None
