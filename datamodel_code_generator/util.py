from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pydantic
from packaging import version
from pydantic import BaseModel

PYDANTIC_VERSION = version.parse(
    pydantic.VERSION if isinstance(pydantic.VERSION, str) else str(pydantic.VERSION)
)

PYDANTIC_V2: bool = PYDANTIC_VERSION >= version.parse('2.0b3')

if TYPE_CHECKING:
    from typing import Any, Callable

    cached_property = property

    Protocol = object
    runtime_checkable: Callable[..., Any]
    from yaml import SafeLoader
else:
    try:
        from typing import TYPE_CHECKING, Any, Callable, Protocol
    except ImportError:
        from typing_extensions import Protocol, Literal  # noqa
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


SafeLoader.yaml_constructors[
    'tag:yaml.org,2002:timestamp'
] = SafeLoader.yaml_constructors['tag:yaml.org,2002:str']


Model = TypeVar('Model', bound=BaseModel)


def model_validator(
    mode: Literal['before', 'after'],
) -> Callable[[Callable[[Model, Any], Any]], Callable[[Model, Any], Any]]:
    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if PYDANTIC_V2:
            from pydantic import model_validator as model_validator_v2

            return model_validator_v2(mode=mode)(method)  # type: ignore
        else:
            from pydantic import root_validator

            return root_validator(method)  # type: ignore

    return inner


def field_validator(
    field_name: str,
    mode: Literal['before', 'after'] = 'after',
) -> Callable[[Callable[[Model, Any], Any]], Callable[[Model, Any], Any]]:
    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if PYDANTIC_V2:
            from pydantic import field_validator as field_validator_v2

            return field_validator_v2(field_name, mode=mode)(method)  # type: ignore
        else:
            from pydantic import validator

            return validator(field_name, pre=mode == 'before')(method)  # type: ignore

    return inner
