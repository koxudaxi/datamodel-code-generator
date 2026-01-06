"""OpenAPI-specific type definitions.

This module contains OpenAPI-specific types that are used by both
jsonschema.py and openapi.py. Separated to avoid circular imports.
"""

from __future__ import annotations

from typing import Optional

from datamodel_code_generator.util import BaseModel


class Discriminator(BaseModel):
    """Represent OpenAPI discriminator object.

    This is an OpenAPI-specific concept for supporting polymorphism.
    It identifies which schema applies based on a property value.

    Can be imported from:
    - datamodel_code_generator.parser.openapi (recommended)
    - datamodel_code_generator.parser.jsonschema (for backward compatibility)
    """

    propertyName: str  # noqa: N815
    mapping: Optional[dict[str, str]] = None  # noqa: UP045


__all__ = ["Discriminator"]
