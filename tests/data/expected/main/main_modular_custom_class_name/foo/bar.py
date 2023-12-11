# @generated by datamodel-codegen:
#   filename:  modular.yaml
#   timestamp: 1985-10-26T08:21:00+00:00

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CustomThing(BaseModel):
    attributes: Optional[Dict[str, Any]] = None


class CustomThang(BaseModel):
    attributes: Optional[List[Dict[str, Any]]] = None


class CustomOthers(BaseModel):
    name: Optional[str] = None


class CustomClone(CustomThing):
    others: Optional[CustomOthers] = None
