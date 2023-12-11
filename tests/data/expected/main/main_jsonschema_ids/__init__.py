# @generated by datamodel-codegen:
#   filename:  Organization.schema.json
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from . import URI, ContactPoint, id, name, sameAs, type


class Organization(BaseModel):
    id: Optional[id.Schema] = None
    type: type.Schema
    name: name.Schema
    contactPoint: Optional[ContactPoint.Schema] = None
    sameAs: Optional[sameAs.Schema] = None
    url: Optional[URI.Schema] = None
