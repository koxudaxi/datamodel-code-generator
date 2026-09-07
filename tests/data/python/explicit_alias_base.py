from pydantic import BaseModel, ConfigDict


class NamespaceBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
