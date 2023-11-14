# generated by datamodel-codegen:
#   filename:  user_default.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

Model = Any


@dataclass
class User:
    name: Optional[str] = None
    pets: Optional[List[User]] = field(default_factory=lambda: ['dog', 'cat'])


@dataclass
class Pet:
    name: Optional[str] = 'dog'
