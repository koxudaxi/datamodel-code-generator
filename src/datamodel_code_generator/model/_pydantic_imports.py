"""Shared Pydantic import constants for model modules."""

from __future__ import annotations

from datamodel_code_generator.imports import Import

IMPORT_ANYURL = Import.from_full_path("pydantic.AnyUrl")
IMPORT_FIELD = Import.from_full_path("pydantic.Field")
