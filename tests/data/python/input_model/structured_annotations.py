"""Runtime annotations that must retain structure through --input-model."""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003  # Pydantic resolves this annotation at runtime.
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Wrapper(Generic[T]):
    """Arbitrary generic used to force x-python-type transport."""


class StructuredAnnotations(BaseModel):
    """Model containing a nested Callable and runtime symbols."""

    model_config = {"arbitrary_types_allowed": True}

    handler: Wrapper[Callable[[int, str], bool]]
