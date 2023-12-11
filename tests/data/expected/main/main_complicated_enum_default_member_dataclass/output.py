# @generated by datamodel-codegen:
#   filename:  complicated_enum.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProcessingStatus(Enum):
    COMPLETED = 'COMPLETED'
    PENDING = 'PENDING'
    FAILED = 'FAILED'


Kind = str


@dataclass
class ProcessingTask:
    processing_status_union: Optional[ProcessingStatus] = ProcessingStatus.COMPLETED
    processing_status: Optional[ProcessingStatus] = ProcessingStatus.COMPLETED
    name: Optional[str] = None
    kind: Optional[Kind] = None
