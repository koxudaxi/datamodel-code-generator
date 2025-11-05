from __future__ import annotations

from datamodel_code_generator.imports import Import

IMPORT_STRAWBERRY = Import(import_="strawberry", alias="strawberry")
IMPORT_STRAWBERRY_TYPE = Import(import_="strawberry", alias="strawberry", from_=None)
IMPORT_STRAWBERRY_ENUM = Import(import_="strawberry", alias="strawberry", from_=None)
IMPORT_STRAWBERRY_INPUT = Import(import_="strawberry", alias="strawberry", from_=None)
IMPORT_STRAWBERRY_DIRECTIVE = Import(import_="strawberry", alias="strawberry", from_=None)
IMPORT_STRAWBERRY_LOCATION = Import(import_="Location", alias="Location", from_="strawberry.schema_directives")
IMPORT_STRAWBERRY_SCALARS = Import(import_="*", from_="strawberry.scalars")
IMPORT_STRAWBERRY_FIELD = Import(import_="strawberry", alias="strawberry", from_="strawberry")
IMPORT_STRAWBERRY_ID = Import(import_="ID", alias="ID", from_="strawberry")
IMPORT_STRAWBERRY_SCALAR = Import(import_="strawberry", alias="strawberry", from_="strawberry")
IMPORT_STRAWBERRY_UNION = Import(import_="strawberry", alias="strawberry", from_="strawberry")
IMPORT_STRAWBERRY_INTERFACE = Import(import_="strawberry", alias="strawberry", from_="strawberry")
IMPORT_STRAWBERRY_FEDERATION_KEY = Import(import_="strawberry", alias="strawberry", from_="strawberry")
IMPORT_STRAWBERRY_FEDERATION_EXTERNAL = Import(import_="strawberry", alias="strawberry", from_="strawberry")
IMPORT_STRAWBERRY_FEDERATION_REQUIRES = Import(import_="strawberry", alias="strawberry", from_="strawberry")
IMPORT_STRAWBERRY_FEDERATION_PROVIDES = Import(import_="strawberry", alias="strawberry", from_="strawberry")
