import inspect
import json
from enum import Enum
from json import JSONDecodeError
from typing import Callable, Dict, Optional, Type, TypeVar

import pysnooper
import yaml

from .version import version as __version__

T = TypeVar('T')

pysnooper.tracer.DISABLED = True


def enable_debug_message() -> None:  # pragma: no cover
    pysnooper.tracer.DISABLED = False


class PythonVersion(Enum):
    PY_36 = '3.6'
    PY_37 = '3.7'
    PY_38 = '3.8'


def snooper_to_methods(  # type: ignore
    output=None,
    watch=(),
    watch_explode=(),
    depth=1,
    prefix='',
    overwrite=False,
    thread_info=False,
    custom_repr=(),
    max_variable_length=100,
) -> Callable:
    def inner(cls: Type[T]) -> Type[T]:
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, method in methods:
            snooper_method = pysnooper.snoop(
                output,
                watch,
                watch_explode,
                depth,
                prefix,
                overwrite,
                thread_info,
                custom_repr,
                max_variable_length,
            )(method)
            setattr(cls, name, snooper_method)
        return cls

    return inner


def load_json_or_yaml(text: str) -> Dict:
    try:
        data = json.loads(text)
    except JSONDecodeError:
        data = yaml.safe_load(text)
    return data
