import importlib as import_loader
import sys as runtime
from builtins import __import__ as builtin_import
from datamodel_code_generator.model import pydantic_v2
from datamodel_code_generator.model.pydantic_v2 import base_model
from importlib import import_module as load_module
from sys import modules as loaded_modules

from . import pydantic_v2 as relative_package
from .pydantic_v2 import base_model as relative_base_model

CONCRETE_BACKEND = "datamodel_code_generator.model.pydantic_v2.base_model"
CONCRETE_BACKEND_ALIAS = CONCRETE_BACKEND
TYPED_CONCRETE_BACKEND: str = CONCRETE_BACKEND_ALIAS
module_registry = loaded_modules
runtime_modules = runtime.modules
typed_registry: object = loaded_modules


def inspect_backend() -> None:
    import_loader.import_module(CONCRETE_BACKEND)
    load_module(CONCRETE_BACKEND_ALIAS)
    builtin_import(CONCRETE_BACKEND)
    runtime.modules.get(CONCRETE_BACKEND)
    loaded_modules.get(CONCRETE_BACKEND_ALIAS)
    module_registry[CONCRETE_BACKEND]
    runtime_modules[CONCRETE_BACKEND_ALIAS]
    typed_registry[TYPED_CONCRETE_BACKEND]
