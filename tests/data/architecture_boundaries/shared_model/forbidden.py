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


def inspect_local_registry() -> None:
    local_registry = runtime.modules
    local_registry[CONCRETE_BACKEND]
    annotated_registry: object = loaded_modules
    annotated_registry[CONCRETE_BACKEND_ALIAS]


def inspect_local_import_aliases() -> None:
    import sys as local_runtime

    local_sys = local_runtime
    local_registry = local_sys.modules
    local_registry[CONCRETE_BACKEND]
    from sys import modules as local_modules

    local_modules.get(CONCRETE_BACKEND_ALIAS)


def inspect_local_strings() -> None:
    local_registry = runtime.modules
    local_backend = "datamodel_code_generator.model.pydantic_v2.base_model"
    local_registry[local_backend]
    typed_backend: str = local_backend
    local_registry.get(typed_backend)


def inspect_registry_rebinding() -> None:
    local_registry = runtime.modules
    local_registry = local_registry.get(CONCRETE_BACKEND)


def inspect_local_dynamic_alias() -> None:
    local_loader = load_module
    local_loader(CONCRETE_BACKEND)


def inspect_default(module_registry=module_registry.get(CONCRETE_BACKEND)) -> None:
    pass


@module_registry.get(CONCRETE_BACKEND)
def inspect_decorator() -> None:
    module_registry = {}


@module_registry.get(CONCRETE_BACKEND)
class DecoratedClass:
    module_registry = {}


class BaseEvaluatedClass(module_registry.get(CONCRETE_BACKEND)):
    module_registry = {}


class ClassBackend:
    local_registry = runtime.modules
    model = local_registry[CONCRETE_BACKEND]
