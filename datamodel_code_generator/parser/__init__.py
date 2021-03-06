from enum import Enum
from typing import Callable, Dict, Optional, TypeVar

TK = TypeVar('TK')
TV = TypeVar('TV')


class LiteralType(Enum):
    All = 'all'
    One = 'one'


class DefaultPutDict(Dict[TK, TV]):
    def get_or_put(
        self,
        key: TK,
        default: Optional[TV] = None,
        default_factory: Optional[Callable[[TK], TV]] = None,
    ) -> TV:
        if key in self:
            return self[key]
        elif default:  # pragma: no cover
            value = self[key] = default
            return value
        elif default_factory:
            value = self[key] = default_factory(key)
            return value
        raise ValueError('Not found default and default_factory')  # pragma: no cover
