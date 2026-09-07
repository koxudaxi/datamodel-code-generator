"""Simulate an inflect update that needs another typeguard API."""
from typeguard import typechecked

from .compat.py38 import Annotated


@typechecked(collection_check_strategy="ALL")
def marker():
    return Annotated


from typeguard import future_api
