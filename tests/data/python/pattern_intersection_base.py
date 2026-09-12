"""Custom base whose attribute validation already accepts sequential model values."""

from pydantic import BaseModel, ConfigDict


class AttributeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
