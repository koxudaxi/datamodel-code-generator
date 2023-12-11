# @generated by datamodel-codegen:
#   filename:  Organization.schema.json
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from pydantic import BaseModel, Field

from . import URI


class Schema(BaseModel):
    __root__: URI.Schema = Field(
        ...,
        description='Use the sameAs property to indicate the most canonical URLs for the original in cases of the entity. For example this may be a link to the original metadata of a dataset, definition of a property, Person, Organization or Place.',
        title='sameAs',
    )
