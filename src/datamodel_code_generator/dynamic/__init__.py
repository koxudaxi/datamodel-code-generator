"""Dynamic model generation module.

This module provides functionality to generate actual Python model classes
at runtime using Pydantic's create_model(), instead of generating text code.
"""

from __future__ import annotations

from datamodel_code_generator.dynamic.creator import DynamicModelCreator
from datamodel_code_generator.dynamic.exceptions import (
    DynamicModelError,
    TypeResolutionError,
)

__all__ = [
    "DynamicModelCreator",
    "DynamicModelError",
    "TypeResolutionError",
]
