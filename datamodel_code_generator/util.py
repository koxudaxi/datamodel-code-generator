from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic
from packaging import version

PYDANTIC_VERSION = version.parse(pydantic.VERSION)

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
        from typing_extensions import Protocol  # noqa
    try:
        from typing import runtime_checkable
    except ImportError:
        from typing_extensions import runtime_checkable  # noqa
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:  # pragma: no cover
        pass

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
