# generated by datamodel-codegen:
#   filename:  titles.json
#   timestamp: 2019-07-26T00:00:00+00:00

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ProcessingStatusTitle(Enum):
    COMPLETED = 'COMPLETED'
    PENDING = 'PENDING'
    FAILED = 'FAILED'


class Kind(BaseModel):
    __root__: str


class NestedCommentTitle(BaseModel):
    comment: Optional[str] = None


class ProcessingTasksTitle(BaseModel):
    __root__: List[ProcessingTaskTitle] = Field(..., title='Processing Tasks Title')


class ExtendedProcessingTaskTitle(BaseModel):
    __root__: Union[ProcessingTasksTitle, NestedCommentTitle] = Field(
        ..., title='Extended Processing Task Title'
    )


class ExtendedProcessingTasksTitle(BaseModel):
    __root__: List[ExtendedProcessingTaskTitle] = Field(
        ..., title='Extended Processing Tasks Title'
    )


class ProcessingTaskTitle(BaseModel):
    processing_status_union: Optional[ProcessingStatusUnion] = 'COMPLETED'
    processing_status: Optional[ProcessingStatusTitle] = 'COMPLETED'
    name: Optional[str] = None
    kind: Optional[Kind] = None


class ProcessingStatusUnion(BaseModel):
    id: Optional[int] = None
    description: Optional[str] = None


ProcessingTasksTitle.update_forward_refs()
ProcessingTaskTitle.update_forward_refs()
