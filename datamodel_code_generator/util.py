from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, TypeVar

import pydantic
from packaging import version
from pydantic import BaseModel as _BaseModel

PYDANTIC_VERSION = version.parse(
    pydantic.VERSION if isinstance(pydantic.VERSION, str) else str(pydantic.VERSION)
)

PYDANTIC_V2: bool = PYDANTIC_VERSION >= version.parse('2.0b3')

if TYPE_CHECKING:
    cached_property = property
    from yaml import SafeLoader

    Protocol = object
    runtime_checkable: Callable[..., Any]

    from typing_extensions import Literal

    def load_toml(path: Path) -> Dict[str, Any]:
        ...

else:
    try:
        from typing import Protocol
    except ImportError:
        from typing_extensions import Protocol  # noqa
    try:
        from typing import runtime_checkable
    except ImportError:
        from typing_extensions import runtime_checkable  # noqa
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:  # pragma: no cover
        from yaml import SafeLoader

    try:
        from functools import cached_property
    except ImportError:
        _NOT_FOUND = object()

        class cached_property:
            def __init__(self, func: Callable) -> None:
                self.func: Callable = func
                self.__doc__: Any = func.__doc__

            def __get__(self, instance: Any, owner: Any = None) -> Any:
                value = instance.__dict__.get(self.func.__name__, _NOT_FOUND)
                if value is _NOT_FOUND:  # pragma: no cover
                    value = instance.__dict__[self.func.__name__] = self.func(instance)
                return value

    try:
        import tomllib

        def load_toml(path: Path) -> Dict[str, Any]:
            with path.open('rb') as f:
                return tomllib.load(f)

    except ImportError:
        import toml

        def load_toml(path: Path) -> Dict[str, Any]:
            return toml.load(path)


SafeLoader.yaml_constructors[
    'tag:yaml.org,2002:timestamp'
] = SafeLoader.yaml_constructors['tag:yaml.org,2002:str']

Model = TypeVar('Model', bound=_BaseModel)


def model_validator(
    mode: Literal['before', 'after'] = 'after',
) -> Callable[[Callable[[Model, Any], Any]], Callable[[Model, Any], Any]]:
    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if PYDANTIC_V2:
            from pydantic import model_validator as model_validator_v2

            return model_validator_v2(mode=mode)(method)  # type: ignore
        else:
            from pydantic import root_validator

            return root_validator(method, pre=mode == 'before')  # type: ignore

    return inner


def field_validator(
    field_name: str,
    *fields: str,
    mode: Literal['before', 'after'] = 'after',
) -> Callable[[Any], Callable[[Model, Any], Any]]:
    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if PYDANTIC_V2:
            from pydantic import field_validator as field_validator_v2

            return field_validator_v2(field_name, *fields, mode=mode)(method)  # type: ignore
        else:
            from pydantic import validator

            return validator(field_name, *fields, pre=mode == 'before')(method)  # type: ignore

    return inner


if PYDANTIC_V2:
    from pydantic import ConfigDict as ConfigDict
else:
    ConfigDict = dict  # type: ignore


class BaseModel(_BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(strict=False)
