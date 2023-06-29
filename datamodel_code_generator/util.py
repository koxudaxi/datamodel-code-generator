from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, Callable, Any

if TYPE_CHECKING:
    cached_property = property
    from yaml import SafeLoader

    Protocol = object
    runtime_checkable: Callable[..., Any]
else:
    try:
        from typing import Protocol, TYPE_CHECKING, Callable, Any
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
