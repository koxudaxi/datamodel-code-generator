"""Input model loading and schema transformation for --input-model option."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from collections import ChainMap, Counter, OrderedDict, defaultdict, deque
from collections.abc import (
    Callable as ABCCallable,
)
from collections.abc import (
    Iterator,
)
from collections.abc import (
    Mapping as ABCMapping,
)
from collections.abc import (
    MutableMapping as ABCMutableMapping,
)
from collections.abc import (
    MutableSequence as ABCMutableSequence,
)
from collections.abc import (
    MutableSet as ABCMutableSet,
)
from collections.abc import (
    Sequence as ABCSequence,
)
from collections.abc import (
    Set as AbstractSet,
)
from contextlib import contextmanager
from dataclasses import dataclass, is_dataclass
from enum import Enum as PyEnum
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Annotated, Any, ForwardRef, Union, cast, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from datamodel_code_generator._process_context import process_context, process_cwd
from datamodel_code_generator.enums import InputModelRefStrategy

if TYPE_CHECKING:
    from datamodel_code_generator import DataModelType, InputFileType


class Error(Exception):
    """Error raised during input model loading."""


_MISSING_MODULE = object()
_INPUT_MODEL_PATH_LOCK = Lock()
_INPUT_MODEL_ACTIVE_CWD: str | None = None
_INPUT_MODEL_ACTIVE_CALLS = 0
_INPUT_MODEL_CWD_ENTRY: str | None = None
_INPUT_MODULE_BASELINE: tuple[int, str | None, frozenset[str]] | None = None
_LOCAL_DOTTED_MODULE_CACHE: OrderedDict[tuple[str, str], dict[str, types.ModuleType]] = OrderedDict()
_LOCAL_DOTTED_MODULE_FINGERPRINTS: dict[
    tuple[str, str],
    dict[str, tuple[tuple[str, int, int], ...]],
] = {}
_LOCAL_DOTTED_MODULE_CACHE_SIZE = 16


@dataclass(slots=True)
class _InputModuleRestoreState:
    entries: dict[str, tuple[object, object]]
    baseline_names: frozenset[str]
    local_directory: Path | None = None
    module_root: str | None = None
    cache_key: tuple[str, str] | None = None
    requested_module: str | None = None
    baseline_count: int = 0


@dataclass(frozen=True, slots=True)
class _CachedLocalDottedModule:
    module: types.ModuleType
    module_root: str
    cache_key: tuple[str, str]


_LocalDottedModuleContext = tuple[str, Path] | _CachedLocalDottedModule
_CWD_INDEPENDENT_FIELD_TYPES = {bool, bytes, float, int, str}
_INERT_PACKAGE_ATTRIBUTES = frozenset({
    "__builtins__",
    "__cached__",
    "__doc__",
    "__file__",
    "__loader__",
    "__name__",
    "__package__",
    "__path__",
    "__spec__",
})


@dataclass(frozen=True, slots=True)
class _CwdIndependentModel:
    module: types.ModuleType
    root_module: types.ModuleType | None
    model: type[BaseModel]
    caller_cwd: str
    local_cache_key: tuple[str, str] | None
    model_json_schema: object
    pydantic_json_schema: object
    pydantic_core_schema: object
    core_schema: object


_CWD_INDEPENDENT_MODEL_CACHE: OrderedDict[tuple[str, str], _CwdIndependentModel] = OrderedDict()
_CWD_INDEPENDENT_MODEL_CACHE_SIZE = 16


def _path_is_within(path: str | Path, directory: Path) -> bool:
    try:
        return Path(path).resolve().is_relative_to(directory)
    except (OSError, TypeError):
        return False


def _module_is_from_directory(module: object, directory: Path) -> bool:
    if (module_file := getattr(module, "__file__", None)) and _path_is_within(module_file, directory):
        return True
    return any(_path_is_within(module_path, directory) for module_path in getattr(module, "__path__", ()))


@lru_cache(maxsize=128)
def _module_origins_are_from_cwd(origins: tuple[str, ...], cwd: str) -> bool:
    directory = Path(cwd).resolve()
    return any(_path_is_within(origin, directory) for origin in origins)


def _module_is_from_cwd(module: object, cwd: str) -> bool:
    """Check the common absolute-path case before resolving possible symlinks."""
    cwd_prefix = f"{cwd.rstrip(os.sep)}{os.sep}"
    origins = tuple(
        origin
        for origin in (
            getattr(module, "__file__", None),
            *getattr(module, "__path__", ()),
        )
        if isinstance(origin, str)
    )
    if any(origin.startswith(cwd_prefix) for origin in origins):
        return True
    return _module_origins_are_from_cwd(origins, cwd)


def _module_is_from_local_import(module_name: str, module: object, directory: Path) -> bool:
    """Return whether a module resolves from a direct entry under the import root."""
    module_root = module_name.partition(".")[0]
    for origin in (
        getattr(module, "__file__", None),
        *getattr(module, "__path__", ()),
    ):
        if not isinstance(origin, str | os.PathLike):
            continue
        try:
            relative_origin = Path(origin).resolve().relative_to(directory)
        except (OSError, ValueError):
            continue
        origin_root = relative_origin.parts[0]
        if origin_root == module_root or Path(origin_root).stem == module_root:
            return True
    return False


def _package_has_runtime_state(module_name: str, module: types.ModuleType) -> bool:
    """Ignore import machinery and child-module bindings in inert package initializers."""
    for attribute, value in vars(module).items():
        if attribute in _INERT_PACKAGE_ATTRIBUTES:
            continue
        if isinstance(value, types.ModuleType) and value.__name__ == f"{module_name}.{attribute}":
            continue
        return True
    return False


def _referenced_module_ids(modules: dict[str, types.ModuleType]) -> set[int]:
    """Collect explicit module globals while ignoring import-created child bindings."""
    referenced: set[int] = set()
    for owner_name, owner in modules.items():
        for attribute, value in vars(owner).items():
            if not isinstance(value, types.ModuleType) or value.__name__ == f"{owner_name}.{attribute}":
                continue
            referenced.add(id(value))
    return referenced


def _local_module_fingerprint(
    modname: str,
    modules: dict[str, types.ModuleType],
    directory: Path,
) -> tuple[tuple[str, int, int], ...] | None:
    """Snapshot the model source and cwd-local dependencies loaded with it."""
    fingerprints: list[tuple[str, int, int]] = []
    referenced_modules = _referenced_module_ids(modules)
    for module_name, module in modules.items():
        if module_name != modname:
            if not _module_is_from_directory(module, directory):
                continue
            if (
                modname.startswith(f"{module_name}.")
                and id(module) not in referenced_modules
                and not _package_has_runtime_state(module_name, module)
            ):
                continue
        if not isinstance(module_file := getattr(module, "__file__", None), str):
            if module_name == modname:
                return None
            continue
        try:
            source_stat = os.stat(module_file)  # noqa: PTH116 - avoid Path allocation while building cache metadata
        except OSError:
            return None
        fingerprints.append((module_file, source_stat.st_mtime_ns, source_stat.st_size))
    return tuple(sorted(fingerprints)) or None


def _local_module_fingerprint_is_current(fingerprint: tuple[tuple[str, int, int], ...] | None) -> bool:
    """Return whether every cached local source still has the recorded identity."""
    if fingerprint is None:
        return False
    for module_file, mtime_ns, size in fingerprint:
        try:
            source_stat = os.stat(module_file)  # noqa: PTH116 - this is the cached-model hot path
        except OSError:
            return False
        if source_stat.st_mtime_ns != mtime_ns or source_stat.st_size != size:
            return False
    return True


def _local_dotted_module_is_current(cache_key: tuple[str, str], modname: str) -> bool:
    return _local_module_fingerprint_is_current(_LOCAL_DOTTED_MODULE_FINGERPRINTS.get(cache_key, {}).get(modname))


def _track_input_modules(state: _InputModuleRestoreState) -> None:
    if len(sys.modules) == state.baseline_count:
        return
    module_prefix = f"{state.module_root}." if state.module_root is not None else None
    for module_name in sys.modules.keys() - state.baseline_names - state.entries.keys():
        module = sys.modules.get(module_name, _MISSING_MODULE)
        matches_module_root = module_prefix is not None and (
            module_name == state.module_root or module_name.startswith(module_prefix)
        )
        if not matches_module_root and (
            state.local_directory is None
            or not _module_is_from_local_import(module_name, module, state.local_directory)
        ):
            continue
        state.entries[module_name] = (_MISSING_MODULE, module)


def _input_module_baseline() -> tuple[int, frozenset[str]]:
    """Reuse the immutable sys.modules baseline while its key fingerprint is unchanged."""
    global _INPUT_MODULE_BASELINE  # noqa: PLW0603

    module_count = len(sys.modules)
    last_module_name = next(reversed(sys.modules), None)
    if (
        _INPUT_MODULE_BASELINE is None
        or _INPUT_MODULE_BASELINE[0] != module_count
        or _INPUT_MODULE_BASELINE[1] != last_module_name
        or _INPUT_MODULE_BASELINE[2] != sys.modules.keys()
    ):
        _INPUT_MODULE_BASELINE = module_count, last_module_name, frozenset(sys.modules)
    return module_count, _INPUT_MODULE_BASELINE[2]


def _restore_input_module(state: _InputModuleRestoreState) -> None:
    _track_input_modules(state)
    if state.cache_key is not None:
        cached_modules = {
            module_name: cast("types.ModuleType", loaded_module)
            for module_name, (_, loaded_module) in state.entries.items()
            if loaded_module is not _MISSING_MODULE and sys.modules.get(module_name, _MISSING_MODULE) is loaded_module
        }
        if cached_modules:
            cached_modules = {
                **_LOCAL_DOTTED_MODULE_CACHE.get(state.cache_key, {}),
                **cached_modules,
            }
            _LOCAL_DOTTED_MODULE_CACHE[state.cache_key] = cached_modules
            _LOCAL_DOTTED_MODULE_CACHE.move_to_end(state.cache_key)
            if state.requested_module is not None:
                fingerprints = _LOCAL_DOTTED_MODULE_FINGERPRINTS.setdefault(state.cache_key, {})
                if (
                    fingerprint := _local_module_fingerprint(
                        state.requested_module,
                        cached_modules,
                        state.local_directory or Path(state.cache_key[0]),
                    )
                ) is None:  # pragma: no cover - local model modules always have a source file
                    fingerprints.pop(state.requested_module, None)
                else:
                    fingerprints[state.requested_module] = fingerprint
            if len(_LOCAL_DOTTED_MODULE_CACHE) > _LOCAL_DOTTED_MODULE_CACHE_SIZE:
                evicted_key, _ = _LOCAL_DOTTED_MODULE_CACHE.popitem(last=False)
                _LOCAL_DOTTED_MODULE_FINGERPRINTS.pop(evicted_key, None)
    for module_name in sorted(state.entries, key=lambda name: name.count("."), reverse=True):
        previous_module, loaded_module = state.entries[module_name]
        if sys.modules.get(module_name, _MISSING_MODULE) is not loaded_module:
            continue
        if previous_module is _MISSING_MODULE:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = cast("types.ModuleType", previous_module)


def _get_path_module_name(file_path: Path) -> str:
    module_name = file_path.stem
    previous_module = sys.modules.get(module_name)
    if not isinstance(previous_module, types.ModuleType):
        return module_name
    if not (module_file := getattr(previous_module, "__file__", None)):
        return module_name
    try:
        previous_file = Path(module_file).resolve()
    except OSError:
        return module_name
    if previous_file == file_path:
        return module_name

    from hashlib import sha256  # noqa: PLC0415

    digest = sha256(str(file_path).encode()).hexdigest()[:16]
    return f"_datamodel_code_generator_input_model_{digest}"


def _load_module_from_path(file_path: Path, modname: str) -> tuple[types.ModuleType, _InputModuleRestoreState]:
    module_name = _get_path_module_name(file_path)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load module from {modname!r}"
        raise Error(msg)

    previous_module = sys.modules.get(module_name, _MISSING_MODULE)
    module = importlib.util.module_from_spec(spec)
    state = _InputModuleRestoreState(
        entries={module_name: (previous_module, module)},
        baseline_names=frozenset(sys.modules),
        local_directory=file_path.parent.resolve(),
        baseline_count=len(sys.modules) + (previous_module is _MISSING_MODULE),
    )
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        _restore_input_module(state)
        raise
    return module, state


def _split_input_model(input_model: str) -> tuple[str, str]:
    modname, separator, qualname = input_model.rpartition(":")
    if separator and modname:
        return modname, qualname

    msg = f"Invalid --input-model format: {input_model!r}. Expected 'module:Object' or 'path/to/file.py:Object'."
    raise Error(msg)


def _resolve_input_model_path(modname: str, cwd: str) -> Path | None:
    if "/" not in modname and "\\" not in modname and not modname.endswith(".py"):
        return None
    path = Path(modname).expanduser()
    if not path.is_absolute():
        path = Path(cwd) / path
    if "/" in modname or "\\" in modname or (modname.endswith(".py") and path.exists()):
        return path.resolve()
    return None


def _local_dotted_module_context(modname: str, cwd: str) -> _LocalDottedModuleContext | None:
    module_root = modname.partition(".")[0]
    cached_root = sys.modules.get(module_root)
    cache_key = cwd, module_root
    if (
        cached_root is None
        and (request_modules := _LOCAL_DOTTED_MODULE_CACHE.get(cache_key)) is not None
        and (request_module := request_modules.get(modname)) is not None
    ):
        if _local_dotted_module_is_current(cache_key, modname):
            return _CachedLocalDottedModule(request_module, module_root, cache_key)
        _LOCAL_DOTTED_MODULE_CACHE.pop(cache_key, None)
        _LOCAL_DOTTED_MODULE_FINGERPRINTS.pop(cache_key, None)
    if cached_root is not None and _module_is_from_cwd(cached_root, cwd):
        return None
    cwd_path = Path(cwd)
    module_path = cwd_path / module_root
    if not module_path.with_suffix(".py").is_file() and not module_path.is_dir():
        return None
    return module_root, cwd_path.resolve()


def _get_cwd_independent_cached_module(  # noqa: PLR0911, PLR0912
    model_spec: tuple[str, str],
) -> tuple[types.ModuleType, str] | None:
    """Return a loaded simple model that cannot consult request-local import state."""
    modname, qualname = model_spec
    caller_cwd = process_cwd()
    if (cached_model := _CWD_INDEPENDENT_MODEL_CACHE.get(model_spec)) is not None:
        if cached_model.local_cache_key is not None and not _local_dotted_module_is_current(
            cached_model.local_cache_key,
            modname,
        ):
            return None
        cached_modules = (
            sys.modules
            if cached_model.local_cache_key is None
            else _LOCAL_DOTTED_MODULE_CACHE.get(cached_model.local_cache_key, {})
        )
        if all((
            cached_model.caller_cwd == caller_cwd,
            caller_cwd in sys.path,
            cached_modules.get(modname) is cached_model.module,
            getattr(cached_model.module, qualname, None) is cached_model.model,
            cached_modules.get(modname.partition(".")[0]) is cached_model.root_module,
            not cached_model.model.model_config,
            getattr(cached_model.model.model_json_schema, "__func__", None) is cached_model.model_json_schema,
            getattr(cached_model.model.__get_pydantic_json_schema__, "__func__", None)
            is cached_model.pydantic_json_schema,
            getattr(cached_model.model.__get_pydantic_core_schema__, "__func__", None)
            is cached_model.pydantic_core_schema,
            cached_model.model.__pydantic_core_schema__ is cached_model.core_schema,
        )):
            _CWD_INDEPENDENT_MODEL_CACHE.move_to_end(model_spec)
            return cached_model.module, caller_cwd
    if caller_cwd not in sys.path:
        return None
    module_root = modname.partition(".")[0]
    local_cache_key: tuple[str, str] | None = None
    if not isinstance(module := sys.modules.get(modname), types.ModuleType):
        local_cache_key = caller_cwd, module_root
        if not isinstance(
            module := _LOCAL_DOTTED_MODULE_CACHE.get(local_cache_key, {}).get(modname),
            types.ModuleType,
        ):
            return None
        if not _local_dotted_module_is_current(local_cache_key, modname):
            return None
    modules = sys.modules if local_cache_key is None else _LOCAL_DOTTED_MODULE_CACHE[local_cache_key]
    if not isinstance(root_module := sys.modules.get(module_root), types.ModuleType) or _module_is_from_cwd(
        root_module, caller_cwd
    ):
        if local_cache_key is None:
            return None
        root_module = modules.get(module_root)
    elif local_cache_key is None:
        local_root = Path(caller_cwd) / module_root
        if local_root.with_suffix(".py").is_file() or local_root.is_dir():
            return None
    if (
        not isinstance(model := getattr(module, qualname, None), type)
        or not issubclass(model, BaseModel)
        or model.model_config
    ):
        return None
    for method_name in (
        "model_json_schema",
        "__get_pydantic_json_schema__",
        "__get_pydantic_core_schema__",
    ):
        model_method = getattr(getattr(model, method_name), "__func__", None)
        base_method = getattr(getattr(BaseModel, method_name), "__func__", None)
        if model_method is not base_method:
            return None
    if any(
        field.annotation not in _CWD_INDEPENDENT_FIELD_TYPES
        or field.json_schema_extra is not None
        or field.metadata
        or field.discriminator is not None
        for field in model.model_fields.values()
    ):
        return None
    _CWD_INDEPENDENT_MODEL_CACHE[model_spec] = _CwdIndependentModel(
        module=module,
        root_module=root_module,
        model=model,
        caller_cwd=caller_cwd,
        local_cache_key=local_cache_key,
        model_json_schema=getattr(model.model_json_schema, "__func__", None),
        pydantic_json_schema=getattr(model.__get_pydantic_json_schema__, "__func__", None),
        pydantic_core_schema=getattr(model.__get_pydantic_core_schema__, "__func__", None),
        core_schema=model.__pydantic_core_schema__,
    )
    _CWD_INDEPENDENT_MODEL_CACHE.move_to_end(model_spec)
    if len(_CWD_INDEPENDENT_MODEL_CACHE) > _CWD_INDEPENDENT_MODEL_CACHE_SIZE:
        _CWD_INDEPENDENT_MODEL_CACHE.popitem(last=False)
    return module, caller_cwd


def _load_local_dotted_module(
    modname: str,
    module_root: str,
    local_directory: Path,
) -> tuple[types.ModuleType, _InputModuleRestoreState | None]:
    module_prefix = f"{module_root}."
    cache_key = str(local_directory), module_root
    request_modules = _LOCAL_DOTTED_MODULE_CACHE.get(cache_key, {})
    cached_root = sys.modules.get(module_root)
    previous_modules = (
        {}
        if cached_root is not None and _module_is_from_directory(cached_root, local_directory)
        else {
            module_name: module
            for module_name, module in sys.modules.items()
            if module_name == module_root or module_name.startswith(module_prefix)
        }
    )
    for module_name, module in previous_modules.items():
        if sys.modules.get(module_name) is module:
            sys.modules.pop(module_name)
    for module_name, module in request_modules.items():
        sys.modules.setdefault(module_name, module)
    state = _InputModuleRestoreState(
        entries={
            **{
                module_name: (module, sys.modules.get(module_name, _MISSING_MODULE))
                for module_name, module in previous_modules.items()
            },
            **{
                module_name: (_MISSING_MODULE, module)
                for module_name, module in request_modules.items()
                if module_name not in previous_modules and sys.modules.get(module_name) is module
            },
        },
        baseline_names=frozenset(sys.modules),
        local_directory=local_directory,
        module_root=module_root,
        cache_key=cache_key,
        requested_module=modname,
        baseline_count=len(sys.modules),
    )
    try:
        module = importlib.import_module(modname)
    except BaseException:
        _restore_input_module(state)
        raise
    for module_name, (previous_module, loaded_module) in tuple(state.entries.items()):
        if loaded_module is _MISSING_MODULE and (loaded_entry := sys.modules.get(module_name)) is not None:
            state.entries[module_name] = (previous_module, loaded_entry)
    return module, state


def _load_input_model_module(
    modname: str,
    file_path: Path | None,
    local_context: _LocalDottedModuleContext | None,
) -> tuple[types.ModuleType, _InputModuleRestoreState | None]:
    if file_path is not None:
        if not file_path.exists():
            msg = f"File not found: {modname!r}"
            raise Error(msg)
        return _load_module_from_path(file_path, modname)
    if local_context is not None:
        match local_context:
            case _CachedLocalDottedModule(module, module_root, cache_key):
                baseline_count, baseline_names = _input_module_baseline()
                return module, _InputModuleRestoreState(
                    entries={},
                    baseline_names=baseline_names,
                    local_directory=Path(cache_key[0]),
                    module_root=module_root,
                    cache_key=cache_key,
                    requested_module=modname,
                    baseline_count=baseline_count,
                )
            case _:
                return _load_local_dotted_module(modname, *local_context)

    try:
        if importlib.util.find_spec(modname) is None:
            msg = f"Cannot find module {modname!r}"
            raise Error(msg)
        return importlib.import_module(modname), None
    except ImportError as e:
        msg = f"Cannot import module {modname!r}: {e}"
        raise Error(msg) from e


def _enter_input_model_cwd(cwd: str) -> None:
    global _INPUT_MODEL_ACTIVE_CALLS, _INPUT_MODEL_ACTIVE_CWD, _INPUT_MODEL_CWD_ENTRY  # noqa: PLW0603

    with _INPUT_MODEL_PATH_LOCK:
        if _INPUT_MODEL_ACTIVE_CALLS == 0:
            _INPUT_MODEL_ACTIVE_CWD = cwd
            _INPUT_MODEL_ACTIVE_CALLS = 1
            if (active_cwd := _INPUT_MODEL_ACTIVE_CWD) not in sys.path:
                _INPUT_MODEL_CWD_ENTRY = active_cwd
                sys.path.insert(0, active_cwd)
            return
        if cwd != _INPUT_MODEL_ACTIVE_CWD:  # pragma: no cover - guarded by process_context
            msg = "Concurrent input model calls cannot use different working directories."
            raise Error(msg)  # pragma: no cover
        _INPUT_MODEL_ACTIVE_CALLS += 1


def _exit_input_model_cwd() -> None:
    global _INPUT_MODEL_ACTIVE_CALLS, _INPUT_MODEL_ACTIVE_CWD, _INPUT_MODEL_CWD_ENTRY  # noqa: PLW0603

    with _INPUT_MODEL_PATH_LOCK:
        _INPUT_MODEL_ACTIVE_CALLS -= 1
        if _INPUT_MODEL_ACTIVE_CALLS:
            return
        if (cwd_entry := _INPUT_MODEL_CWD_ENTRY) is not None:
            for index, entry in enumerate(sys.path):
                if entry is cwd_entry:
                    sys.path.pop(index)
                    break
        _INPUT_MODEL_ACTIVE_CWD = None
        _INPUT_MODEL_CWD_ENTRY = None
        _ = _INPUT_MODEL_CWD_ENTRY


@contextmanager
def _input_model_cwd(cwd: str) -> Iterator[None]:
    if _INPUT_MODEL_ACTIVE_CALLS == 0 and cwd in sys.path:
        yield
        return
    _enter_input_model_cwd(cwd)
    try:
        yield
    finally:
        _exit_input_model_cwd()


def _is_input_model_base_schema(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(cast("dict[str, object]", value).get("x-is-base-class"))


# Types that are lost during JSON Schema conversion and need to be preserved
_PRESERVED_TYPE_ORIGINS: dict[type, str] = {}

# Marker for types that Pydantic cannot serialize to JSON Schema
_UNSERIALIZABLE_MARKER = "x-python-unserializable"

# Type family constants
_TYPE_FAMILY_ENUM = "enum"
_TYPE_FAMILY_PYDANTIC = "pydantic"
_TYPE_FAMILY_DATACLASS = "dataclass"
_TYPE_FAMILY_TYPEDDICT = "typeddict"
_TYPE_FAMILY_MSGSPEC = "msgspec"
_TYPE_FAMILY_OTHER = "other"


def _serialize_python_type_full(tp: type) -> str:  # noqa: PLR0911
    """Serialize ANY Python type to its string representation."""
    if tp is type(None):  # pragma: no cover
        return "None"

    if tp is ...:  # pragma: no cover
        return "..."

    origin = get_origin(tp)
    args = get_args(tp)

    if origin is None:
        module = getattr(tp, "__module__", "")
        name = getattr(tp, "__name__", None) or getattr(tp, "__qualname__", None)

        if name is None:
            return str(tp).replace("typing.", "")

        if module and module not in {"builtins", "typing", "collections.abc"}:
            return f"{module}.{name}"
        return name

    if _is_callable_origin(origin):
        return _serialize_callable(args)

    if origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType):  # pragma: no cover
        parts = [_serialize_python_type_full(arg) for arg in args]
        return " | ".join(parts)

    if origin is Annotated:
        if args:
            return _serialize_python_type_full(args[0])
        return str(tp).replace("typing.", "")  # pragma: no cover

    if origin is type:
        if args:
            return f"Type[{_serialize_python_type_full(args[0])}]"
        return "Type"  # pragma: no cover

    origin_name = _get_origin_name(origin)
    if args:
        args_str = ", ".join(_serialize_python_type_full(arg) for arg in args)
        return f"{origin_name}[{args_str}]"

    return origin_name  # pragma: no cover


def _is_callable_origin(origin: type | None) -> bool:
    """Check if origin is Callable."""
    if origin is None:  # pragma: no cover
        return False
    if origin is ABCCallable:
        return True
    origin_str = str(origin)
    return "Callable" in origin_str or "callable" in origin_str


def _serialize_callable(args: tuple[type, ...]) -> str:
    """Serialize Callable type."""
    if not args:  # pragma: no cover
        return "Callable"

    params = args[:-1]
    ret = args[-1]

    if len(params) == 1 and params[0] is ...:
        return f"Callable[..., {_serialize_python_type_full(ret)}]"

    if len(params) == 1 and isinstance(params[0], (list, tuple)):  # pragma: no cover
        params = tuple(params[0])

    params_str = ", ".join(_serialize_python_type_full(p) for p in params)
    return f"Callable[[{params_str}], {_serialize_python_type_full(ret)}]"


def _get_origin_name(origin: type) -> str:
    """Get the fully qualified name of a generic origin."""
    name = getattr(origin, "__qualname__", None) or getattr(origin, "__name__", None)
    if name:
        module = getattr(origin, "__module__", "")
        if module and module not in {"builtins", "typing", "collections.abc"}:
            return f"{module}.{name}"
        return name

    origin_str = str(origin)  # pragma: no cover
    if "typing." in origin_str:  # pragma: no cover
        return origin_str.replace("typing.", "")

    return origin_str  # pragma: no cover


def _get_input_model_json_schema_class() -> type:
    """Get the InputModelJsonSchema class lazily."""
    from pydantic.json_schema import GenerateJsonSchema  # noqa: PLC0415

    class InputModelJsonSchema(GenerateJsonSchema):
        """Custom schema generator that handles ALL unserializable types."""

        def handle_invalid_for_json_schema(  # noqa: PLR6301
            self,
            schema: Any,  # noqa: ARG002
            error_info: Any,  # noqa: ARG002
        ) -> dict[str, Any]:
            """Catch ALL types that Pydantic can't serialize to JSON Schema."""
            return {
                "type": "object",
                _UNSERIALIZABLE_MARKER: True,
            }

        def callable_schema(  # noqa: PLR6301
            self,
            schema: Any,  # noqa: ARG002
        ) -> dict[str, Any]:
            """Handle Callable types - these raise before handle_invalid_for_json_schema."""
            return {
                "type": "string",
                _UNSERIALIZABLE_MARKER: True,
            }

    return InputModelJsonSchema


def _is_type_origin(annotation: type) -> bool:
    """Check if annotation is Type[X]."""
    origin = get_origin(annotation)
    return origin is type


def _process_unserializable_property(prop: dict[str, Any], annotation: type) -> None:
    """Process a single property, handling anyOf/oneOf/items structures."""
    if "anyOf" in prop:
        for item in prop["anyOf"]:
            if item.get(_UNSERIALIZABLE_MARKER):
                _set_python_type_for_unserializable(item, annotation)
    elif "oneOf" in prop:  # pragma: no cover
        for item in prop["oneOf"]:
            if item.get(_UNSERIALIZABLE_MARKER):
                _set_python_type_for_unserializable(item, annotation)
    elif prop.get(_UNSERIALIZABLE_MARKER):
        _set_python_type_for_unserializable(prop, annotation)
    elif "items" in prop and prop["items"].get(_UNSERIALIZABLE_MARKER):
        prop["x-python-type"] = _serialize_python_type_full(annotation)
        prop["items"].pop(_UNSERIALIZABLE_MARKER, None)
    elif _is_type_origin(annotation):
        prop["x-python-type"] = _serialize_python_type_full(annotation)


def _set_python_type_for_unserializable(item: dict[str, Any], annotation: type) -> None:
    """Set x-python-type and clean up markers."""
    origin = get_origin(annotation)
    actual_type = annotation

    if origin is Union:
        for arg in get_args(annotation):  # pragma: no branch
            if arg is not type(None):  # pragma: no branch
                actual_type = arg
                break

    item["x-python-type"] = _serialize_python_type_full(actual_type)
    item.pop(_UNSERIALIZABLE_MARKER, None)


def _add_python_type_for_unserializable(
    schema: dict[str, Any],
    model: type,
    visited_defs: set[str] | None = None,
) -> dict[str, Any]:
    """Add x-python-type to ALL fields marked as unserializable."""
    if visited_defs is None:
        visited_defs = set()

    if "properties" in schema:
        model_fields = getattr(model, "model_fields", {})
        for field_name, prop in schema["properties"].items():
            if field_name in model_fields:  # pragma: no branch
                annotation = model_fields[field_name].annotation
                _process_unserializable_property(prop, annotation)

    if "$defs" in schema:
        nested_models = _collect_nested_models(model)
        model_name = getattr(model, "__name__", None)
        if model_name:  # pragma: no branch
            nested_models[model_name] = model
        for def_name, def_schema in schema["$defs"].items():
            if def_name in visited_defs:  # pragma: no cover
                continue
            visited_defs.add(def_name)
            if def_name in nested_models:  # pragma: no branch
                _add_python_type_for_unserializable(def_schema, nested_models[def_name], visited_defs)

    return schema


def _init_preserved_type_origins() -> dict[type, str]:
    """Initialize preserved type origins mapping (lazy initialization)."""
    return {
        set: "set",
        frozenset: "frozenset",
        defaultdict: "defaultdict",
        OrderedDict: "OrderedDict",
        Counter: "Counter",
        deque: "deque",
        ChainMap: "ChainMap",
        AbstractSet: "AbstractSet",
        ABCMutableSet: "MutableSet",
        ABCMapping: "Mapping",
        ABCMutableMapping: "MutableMapping",
        ABCSequence: "Sequence",
        ABCMutableSequence: "MutableSequence",
    }


def _get_preserved_type_origins() -> dict[type, str]:
    """Get the preserved type origins mapping, initializing if needed."""
    global _PRESERVED_TYPE_ORIGINS  # noqa: PLW0603
    if not _PRESERVED_TYPE_ORIGINS:
        _PRESERVED_TYPE_ORIGINS = _init_preserved_type_origins()
    return _PRESERVED_TYPE_ORIGINS


def _serialize_python_type(tp: type) -> str | None:  # noqa: PLR0911
    """Serialize Python type to a string for x-python-type field."""
    origin: type | None = get_origin(tp)
    args = get_args(tp)
    preserved_origins = _get_preserved_type_origins()

    is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
    if is_union:
        if args:
            nested = [_serialize_python_type(a) for a in args]
            if any(n is not None for n in nested):
                return " | ".join(n or _full_type_name(a) for n, a in zip(nested, args, strict=False))
        return None  # pragma: no cover

    if origin is Annotated:
        if args:
            return _serialize_python_type(args[0]) or _full_type_name(args[0])
        return None  # pragma: no cover

    type_name: str | None = None
    if origin is not None:
        type_name = preserved_origins.get(origin)
        if type_name is None and getattr(origin, "__module__", None) == "collections":  # pragma: no cover
            type_name = _simple_type_name(origin)
    if type_name is not None:
        if args:
            args_str = ", ".join(_serialize_python_type(a) or _full_type_name(a) for a in args)
            return f"{type_name}[{args_str}]"
        return type_name  # pragma: no cover

    if args:
        nested = [_serialize_python_type(a) for a in args]
        if any(n is not None for n in nested):
            origin_name = _simple_type_name(origin or tp)
            args_str = ", ".join(n or _full_type_name(a) for n, a in zip(nested, args, strict=False))
            return f"{origin_name}[{args_str}]"

    return None


def _simple_type_name(tp: type) -> str:
    """Get a simple string representation of a type."""
    if tp is type(None):
        return "None"
    if get_origin(tp) is not None:
        return str(tp).replace("typing.", "")
    if hasattr(tp, "__name__"):
        return tp.__name__
    return str(tp).replace("typing.", "")  # pragma: no cover


def _full_type_name(tp: type) -> str:  # noqa: PLR0911
    """Get a full qualified name representation of a type for type arguments.

    For generic types, keeps outer type as short name but FQN-izes the type arguments.
    For non-generic types, returns FQN for non-builtin types.
    """
    if tp is type(None):
        return "None"

    if isinstance(tp, str):
        return tp
    if isinstance(tp, ForwardRef):
        return tp.__forward_arg__

    origin = get_origin(tp)
    if origin is not None:
        # Handle Union types (both typing.Union and types.UnionType) with | syntax
        is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
        if is_union:
            args = get_args(tp)
            if args:
                return " | ".join(_full_type_name(a) for a in args)
            return str(tp)  # pragma: no cover

        origin_name = _simple_type_name(origin)
        args = get_args(tp)
        if args:
            args_str = ", ".join(_full_type_name(a) for a in args)
            return f"{origin_name}[{args_str}]"
        return origin_name

    module = getattr(tp, "__module__", None)
    name = getattr(tp, "__name__", None)

    if module == "typing":
        if name:
            return name
        return str(tp).replace("typing.", "")  # pragma: no cover

    if module and name and module not in {"builtins", "collections.abc"}:
        return f"{module}.{name}"
    if name:
        return name
    return str(tp).replace("typing.", "")  # pragma: no cover


def _collect_nested_models(model: type, visited: set[type] | None = None) -> dict[str, type]:
    """Collect all nested types (BaseModel, Enum, dataclass) from a model's fields."""
    if visited is None:
        visited = set()

    if model in visited:  # pragma: no cover
        return {}
    visited.add(model)

    result: dict[str, type] = {}

    model_fields = getattr(model, "model_fields", None)
    if model_fields is not None:
        for field_info in model_fields.values():
            tp = field_info.annotation
            _find_models_in_type(tp, result, visited)
    else:
        type_hints = _get_type_hints_safe(model)
        for tp in type_hints.values():
            _find_models_in_type(tp, result, visited)

    return result


def _find_models_in_type(tp: type, result: dict[str, type], visited: set[type]) -> None:
    """Recursively find BaseModel, Enum, dataclass, TypedDict, and msgspec in a type annotation."""
    if isinstance(tp, type) and tp not in visited:
        if issubclass(tp, BaseModel):
            result[tp.__name__] = tp
            result.update(_collect_nested_models(tp, visited))
        elif (
            issubclass(tp, PyEnum)
            or is_dataclass(tp)
            or hasattr(tp, "__required_keys__")
            or hasattr(tp, "__struct_fields__")
        ):
            result[tp.__name__] = tp

    for arg in get_args(tp):
        _find_models_in_type(arg, result, visited)


def _get_type_hints_safe(obj: type) -> dict[str, Any]:
    """Safely get type hints from a class, handling forward references."""
    try:
        return get_type_hints(obj)
    except Exception:  # noqa: BLE001  # pragma: no cover
        return getattr(obj, "__annotations__", {})


def _add_python_type_to_properties(
    properties: dict[str, Any],
    model_fields: dict[str, Any],
) -> None:
    """Add x-python-type to properties dict for given model fields."""
    for field_name, field_info in model_fields.items():
        if field_name not in properties:  # pragma: no cover
            continue
        serialized = _serialize_python_type(field_info.annotation)
        if serialized:
            properties[field_name]["x-python-type"] = serialized


def _add_python_type_info(schema: dict[str, Any], model: type) -> dict[str, Any]:
    """Add x-python-type information to JSON Schema for types lost during conversion."""
    model_fields = getattr(model, "model_fields", None)
    if model_fields and "properties" in schema:
        _add_python_type_to_properties(schema["properties"], model_fields)

    if "$defs" in schema:
        nested_models = _collect_nested_models(model)
        model_name = getattr(model, "__name__", None)
        if model_name and model_name in schema["$defs"]:
            nested_models[model_name] = model
        for def_name, def_schema in schema["$defs"].items():
            if def_name not in nested_models or "properties" not in def_schema:  # pragma: no cover
                continue
            nested_model = nested_models[def_name]
            nested_fields = getattr(nested_model, "model_fields", None)
            if nested_fields:
                _add_python_type_to_properties(def_schema["properties"], nested_fields)

    return schema


def _add_python_type_info_generic(schema: dict[str, Any], obj: type) -> dict[str, Any]:
    """Add x-python-type information using get_type_hints (for dataclass/TypedDict)."""
    type_hints = _get_type_hints_safe(obj)
    if type_hints and "properties" in schema:  # pragma: no branch
        for field_name, field_type in type_hints.items():
            if field_name in schema["properties"]:  # pragma: no branch
                serialized = _serialize_python_type(field_type)
                if serialized:
                    schema["properties"][field_name]["x-python-type"] = serialized

    return schema


def _get_type_family(tp: type) -> str:  # noqa: PLR0911
    """Determine the type family of a Python type."""
    if isinstance(tp, type) and issubclass(tp, PyEnum):
        return _TYPE_FAMILY_ENUM

    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return _TYPE_FAMILY_PYDANTIC

    if hasattr(tp, "__pydantic_fields__") and is_dataclass(tp):  # pragma: no cover
        return _TYPE_FAMILY_PYDANTIC

    if is_dataclass(tp):
        return _TYPE_FAMILY_DATACLASS

    if isinstance(tp, type) and hasattr(tp, "__required_keys__"):
        return _TYPE_FAMILY_TYPEDDICT

    if isinstance(tp, type) and hasattr(tp, "__struct_fields__"):  # pragma: no cover
        return _TYPE_FAMILY_MSGSPEC

    return _TYPE_FAMILY_OTHER  # pragma: no cover


def _get_output_family(output_model_type: DataModelType) -> str:
    """Get the type family corresponding to a DataModelType."""
    from datamodel_code_generator import DataModelType  # noqa: PLC0415

    pydantic_types = {
        DataModelType.PydanticV2BaseModel,
        DataModelType.PydanticV2Dataclass,
    }
    if output_model_type in pydantic_types:
        return _TYPE_FAMILY_PYDANTIC
    if output_model_type == DataModelType.DataclassesDataclass:
        return _TYPE_FAMILY_DATACLASS
    if output_model_type == DataModelType.TypingTypedDict:
        return _TYPE_FAMILY_TYPEDDICT
    if output_model_type == DataModelType.MsgspecStruct:
        return _TYPE_FAMILY_MSGSPEC
    return _TYPE_FAMILY_OTHER  # pragma: no cover


def _should_reuse_type(source_family: str, output_family: str) -> bool:
    """Determine if a source type can be reused without conversion."""
    if source_family == _TYPE_FAMILY_ENUM:
        return True
    return source_family == output_family


def _filter_defs_by_strategy(
    schema: dict[str, Any],
    nested_models: dict[str, type],
    output_model_type: DataModelType,
    strategy: InputModelRefStrategy,
) -> dict[str, Any]:
    """Filter $defs based on ref strategy, marking reused types with x-python-import."""
    if strategy == InputModelRefStrategy.RegenerateAll:  # pragma: no cover
        return schema

    if "$defs" not in schema:  # pragma: no cover
        return schema

    output_family = _get_output_family(output_model_type)
    new_defs: dict[str, Any] = {}

    for def_name, def_schema in schema["$defs"].items():
        if def_name not in nested_models:  # pragma: no cover
            new_defs[def_name] = def_schema
            continue

        nested_type = nested_models[def_name]
        type_family = _get_type_family(nested_type)

        should_reuse = strategy == InputModelRefStrategy.ReuseAll or (
            strategy == InputModelRefStrategy.ReuseForeign and _should_reuse_type(type_family, output_family)
        )

        if should_reuse:
            new_defs[def_name] = {
                "x-python-import": {
                    "module": nested_type.__module__,
                    "name": nested_type.__name__,
                },
            }
        else:
            new_defs[def_name] = def_schema

    return {**schema, "$defs": new_defs}


def _try_rebuild_model(obj: type) -> None:
    """Try to rebuild a Pydantic model, handling config models specially."""
    module = getattr(obj, "__module__", "")
    class_name = getattr(obj, "__name__", "")
    config_classes = {"GenerateConfig", "ParserConfig", "ParseConfig"}
    main_config_classes = {"Config"}
    if module in {"datamodel_code_generator.config", "config"} and class_name in config_classes:
        from datamodel_code_generator.enums import UnionMode  # noqa: PLC0415
        from datamodel_code_generator.model.base import DataModel, DataModelFieldBase  # noqa: PLC0415
        from datamodel_code_generator.types import DataTypeManager, StrictTypes  # noqa: PLC0415

        types_namespace = {
            "DataModel": DataModel,
            "DataModelFieldBase": DataModelFieldBase,
            "DataTypeManager": DataTypeManager,
            "StrictTypes": StrictTypes,
            "UnionMode": UnionMode,
        }
        obj.model_rebuild(_types_namespace=types_namespace)  # ty: ignore[unresolved-attribute]
    elif module == "datamodel_code_generator.__main__" and class_name in main_config_classes:  # pragma: no cover
        from datamodel_code_generator.enums import UnionMode  # noqa: PLC0415
        from datamodel_code_generator.types import StrictTypes  # noqa: PLC0415

        types_namespace = {
            "UnionMode": UnionMode,
            "StrictTypes": StrictTypes,
        }
        obj.model_rebuild(_types_namespace=types_namespace)  # ty: ignore[unresolved-attribute]
    else:
        obj.model_rebuild()  # ty: ignore[unresolved-attribute]


def _get_base_model_parents(model_class: type) -> list[type]:
    """Get parent classes that are BaseModel subclasses (excluding BaseModel itself)."""
    return [p for p in model_class.__bases__ if isinstance(p, type) and issubclass(p, BaseModel) and p is not BaseModel]


def _transform_single_model_to_inheritance(
    schema: dict[str, object],
    model_class: type,
    schema_generator: type,
    processed_parents: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    """Transform a single model's schema to use allOf inheritance structure."""
    if processed_parents is None:
        processed_parents = {}

    direct_parents = _get_base_model_parents(model_class)

    if not direct_parents:
        return schema

    parent = direct_parents[0]
    parent_name = parent.__name__
    parent_fields = set(parent.model_fields.keys())

    defs = dict(cast("dict[str, object]", schema.get("$defs", {})))

    if parent_name not in processed_parents:
        _try_rebuild_model(parent)
        parent_schema = parent.model_json_schema(schema_generator=schema_generator)
        parent_schema = _add_python_type_for_unserializable(parent_schema, parent)
        parent_schema = _add_python_type_info(parent_schema, parent)
        parent_schema = _transform_single_model_to_inheritance(
            parent_schema, parent, schema_generator, processed_parents
        )
        processed_parents[parent_name] = parent_schema
    parent_schema = processed_parents[parent_name]

    if "$defs" in parent_schema:
        parent_defs = cast("dict[str, object]", parent_schema["$defs"])
        defs.update(parent_defs)

    parent_def = {k: v for k, v in parent_schema.items() if k != "$defs"}
    parent_def["x-is-base-class"] = True
    defs[parent_name] = parent_def

    original_props = cast("dict[str, object]", schema.get("properties", {}))
    child_props = {k: v for k, v in original_props.items() if k not in parent_fields}

    new_schema: dict[str, object] = {"$defs": defs, "allOf": [{"$ref": f"#/$defs/{parent_name}"}]}
    if child_props:
        new_schema["properties"] = child_props
    original_required = cast("list[str]", schema.get("required", []))
    child_required = [r for r in original_required if r not in parent_fields]
    if child_required:
        new_schema["required"] = child_required
    new_schema["title"] = schema.get("title")
    new_schema["type"] = "object"

    new_schema.update({
        key: value
        for key, value in schema.items()
        if key not in {"$defs", "properties", "required", "title", "type", "allOf"}
    })

    return new_schema


def _load_single_model_schema_in_cwd(  # noqa: PLR0913, PLR0917
    model_spec: tuple[str, str],
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None,
    output_model_type: DataModelType,
    caller_cwd: str,
    file_path: Path | None,
    local_context: _LocalDottedModuleContext | None,
    loaded_module: types.ModuleType | None = None,
) -> dict[str, object]:
    """Use the allocation-free cwd fast path when no sys.path update is needed."""
    if _INPUT_MODEL_ACTIVE_CALLS == 0 and caller_cwd in sys.path:
        return _load_single_model_schema(
            model_spec,
            input_file_type,
            ref_strategy,
            output_model_type,
            file_path,
            local_context,
            loaded_module,
        )
    with _input_model_cwd(caller_cwd):
        return _load_single_model_schema(
            model_spec,
            input_file_type,
            ref_strategy,
            output_model_type,
            file_path,
            local_context,
            loaded_module,
        )


def load_model_schema(
    input_models: list[str],
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None = None,
    output_model_type: DataModelType | None = None,
) -> dict[str, object]:
    """Load and merge schemas from Python import paths with inheritance support.

    Args:
        input_models: List of import paths in 'module.path:ObjectName' format
        input_file_type: Current input file type setting for validation
        ref_strategy: Strategy for handling referenced types
        output_model_type: Target output model type for reuse-foreign strategy

    Returns:
        Merged schema dict with anyOf referencing all root models
    """
    from datamodel_code_generator import DataModelType  # noqa: PLC0415

    if output_model_type is None:
        output_model_type = DataModelType.PydanticV2BaseModel

    if len(input_models) == 1:
        model_spec = _split_input_model(input_models[0])
        if (cached_context := _get_cwd_independent_cached_module(model_spec)) is not None:
            cached_module, caller_cwd = cached_context
            return _load_single_model_schema_in_cwd(
                model_spec,
                input_file_type,
                ref_strategy,
                output_model_type,
                caller_cwd,
                None,
                None,
                cached_module,
            )
        modname = model_spec[0]
        explicit_path = "/" in modname or "\\" in modname
        cached_local_hint = any(modname in request_modules for request_modules in _LOCAL_DOTTED_MODULE_CACHE.values())
        initial_exclusive = explicit_path or cached_local_hint
        with process_context(exclusive=initial_exclusive, borrow_writer=False) as caller_cwd:
            file_path = _resolve_input_model_path(modname, caller_cwd)
            local_context = None if file_path is not None else _local_dotted_module_context(modname, caller_cwd)
            if (file_path is not None or local_context is not None) and not initial_exclusive:
                with process_context(exclusive=True):
                    return _load_single_model_schema_in_cwd(
                        model_spec,
                        input_file_type,
                        ref_strategy,
                        output_model_type,
                        caller_cwd,
                        file_path,
                        local_context,
                    )
            return _load_single_model_schema_in_cwd(
                model_spec,
                input_file_type,
                ref_strategy,
                output_model_type,
                caller_cwd,
                file_path,
                local_context,
            )

    module_names = [_split_input_model(input_model)[0] for input_model in input_models]

    def load_multiple(
        caller_cwd: str,
        path_modules: dict[str, Path],
        local_module_contexts: dict[str, _LocalDottedModuleContext],
    ) -> dict[str, object]:
        with _input_model_cwd(caller_cwd):
            return _load_multiple_model_schemas(
                input_models,
                input_file_type,
                ref_strategy,
                output_model_type,
                path_modules,
                local_module_contexts,
            )

    explicit_path = any("/" in module_name or "\\" in module_name for module_name in module_names)
    cached_local_hint = any(
        module_name in request_modules
        for request_modules in _LOCAL_DOTTED_MODULE_CACHE.values()
        for module_name in module_names
    )
    initial_exclusive = explicit_path or cached_local_hint
    with process_context(exclusive=initial_exclusive, borrow_writer=False) as caller_cwd:
        path_modules = {
            module_name: path
            for module_name in module_names
            if (path := _resolve_input_model_path(module_name, caller_cwd)) is not None
        }
        local_module_contexts = {
            module_name: local_context
            for module_name in module_names
            if module_name not in path_modules
            and (local_context := _local_dotted_module_context(module_name, caller_cwd)) is not None
        }
        requires_local_import = bool(local_module_contexts)
        if (path_modules or requires_local_import) and not initial_exclusive:
            with process_context(exclusive=True):
                return load_multiple(caller_cwd, path_modules, local_module_contexts)
        return load_multiple(caller_cwd, path_modules, local_module_contexts)


def _load_multiple_model_schemas(  # noqa: PLR0912, PLR0913, PLR0914, PLR0915, PLR0917
    input_models: list[str],
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None,
    output_model_type: DataModelType,
    path_modules: dict[str, Path],
    local_module_contexts: dict[str, _LocalDottedModuleContext],
) -> dict[str, object]:
    from datamodel_code_generator import InputFileType  # noqa: PLC0415

    model_classes: list[type] = []
    loaded_modules: dict[str, types.ModuleType] = {}
    module_states: list[_InputModuleRestoreState] = []

    try:
        for input_model in input_models:
            modname, qualname = _split_input_model(input_model)

            if modname not in loaded_modules:
                module, module_state = _load_input_model_module(
                    modname,
                    path_modules.get(modname),
                    local_module_contexts.get(modname),
                )
                if module_state is not None:
                    module_states.append(module_state)
                loaded_modules[modname] = module
            else:
                module = loaded_modules[modname]

            try:
                obj = getattr(module, qualname)
            except AttributeError as e:
                msg = f"Module {modname!r} has no attribute {qualname!r}"
                raise Error(msg) from e

            if not (isinstance(obj, type) and issubclass(obj, BaseModel)):
                msg = f"Multiple --input-model only supports Pydantic v2 BaseModel classes, got {type(obj).__name__}"
                raise Error(msg)

            model_classes.append(obj)

        if input_file_type not in {InputFileType.Auto, InputFileType.JsonSchema}:
            msg = (
                f"--input-file-type must be 'jsonschema' (or omitted) "
                f"when --input-model points to Pydantic models, "
                f"got '{input_file_type.value}'"
            )
            raise Error(msg)

        schema_generator = _get_input_model_json_schema_class()
        merged_defs: dict[str, object] = {}
        root_refs: list[dict[str, str]] = []
        processed_parents: dict[str, dict[str, object]] = {}

        for model_class in model_classes:
            model_name = model_class.__name__
            _try_rebuild_model(model_class)

            schema = model_class.model_json_schema(schema_generator=schema_generator)  # ty: ignore[unresolved-attribute]
            schema = _add_python_type_for_unserializable(schema, model_class)
            schema = _add_python_type_info(schema, model_class)

            schema = _transform_single_model_to_inheritance(schema, model_class, schema_generator, processed_parents)

            if "$defs" in schema:
                schema_defs = cast("dict[str, object]", schema["$defs"])
                for k, v in schema_defs.items():
                    new_is_base = _is_input_model_base_schema(v)
                    existing = merged_defs.get(k)
                    existing_is_base = _is_input_model_base_schema(existing) if existing is not None else False
                    if k not in merged_defs or (new_is_base and not existing_is_base):
                        merged_defs[k] = v

            model_def = {k: v for k, v in schema.items() if k != "$defs"}
            merged_defs[model_name] = model_def

            root_refs.append({"$ref": f"#/$defs/{model_name}"})

        final_schema: dict[str, object] = {"$defs": merged_defs, "anyOf": root_refs}

        if ref_strategy and ref_strategy != InputModelRefStrategy.RegenerateAll:
            all_nested_models: dict[str, type] = {}
            for model_class in model_classes:
                all_nested_models.update(_collect_nested_models(model_class))
            final_schema = _filter_defs_by_strategy(final_schema, all_nested_models, output_model_type, ref_strategy)

        return final_schema
    finally:
        for state in reversed(module_states):
            _restore_input_module(state)


def _load_single_model_schema(  # noqa: PLR0912, PLR0913, PLR0915, PLR0917
    model_spec: tuple[str, str],
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None,
    output_model_type: DataModelType,
    file_path: Path | None,
    local_context: _LocalDottedModuleContext | None,
    loaded_module: types.ModuleType | None = None,
) -> dict[str, object]:
    """Load schema from a Python import path.

    Args:
        model_spec: Module path and qualified object name
        input_file_type: Current input file type setting for validation
        ref_strategy: Strategy for handling referenced types
        output_model_type: Target output model type for reuse-foreign strategy

    Returns:
        Schema dict

    Raises:
        Error: If format invalid, object cannot be loaded, or input_file_type invalid
    """
    from datamodel_code_generator import InputFileType  # noqa: PLC0415

    modname, qualname = model_spec

    if loaded_module is None:
        module, module_state = _load_input_model_module(modname, file_path, local_context)
    else:
        module = loaded_module
        module_state = None

    try:
        try:
            obj = getattr(module, qualname)
        except AttributeError as e:
            msg = f"Module {modname!r} has no attribute {qualname!r}"
            raise Error(msg) from e

        if isinstance(obj, dict):
            if input_file_type == InputFileType.Auto:
                msg = "--input-file-type is required when --input-model points to a dict"
                raise Error(msg)
            return obj

        if isinstance(obj, type) and issubclass(obj, BaseModel):
            if input_file_type not in {InputFileType.Auto, InputFileType.JsonSchema}:
                msg = (
                    f"--input-file-type must be 'jsonschema' (or omitted) "
                    f"when --input-model points to a Pydantic model, "
                    f"got '{input_file_type.value}'"
                )
                raise Error(msg)
            _try_rebuild_model(obj)
            schema_generator = _get_input_model_json_schema_class()
            schema = obj.model_json_schema(schema_generator=schema_generator)
            schema = _add_python_type_for_unserializable(schema, obj)
            schema = _add_python_type_info(schema, obj)

            schema = _transform_single_model_to_inheritance(schema, obj, schema_generator)

            if ref_strategy and ref_strategy != InputModelRefStrategy.RegenerateAll:
                nested_models = _collect_nested_models(obj)
                model_name = getattr(obj, "__name__", None)
                if (
                    model_name and "$defs" in schema and model_name in schema["$defs"]  # ty: ignore[unsupported-operator]
                ):  # pragma: no cover
                    nested_models[model_name] = obj
                schema = _filter_defs_by_strategy(schema, nested_models, output_model_type, ref_strategy)

            return schema

        is_typed_dict = isinstance(obj, type) and hasattr(obj, "__required_keys__")
        if is_dataclass(obj) or is_typed_dict:
            if input_file_type not in {InputFileType.Auto, InputFileType.JsonSchema}:
                msg = (
                    f"--input-file-type must be 'jsonschema' (or omitted) "
                    f"when --input-model points to a dataclass or TypedDict, "
                    f"got '{input_file_type.value}'"
                )
                raise Error(msg)
            from pydantic import TypeAdapter  # noqa: PLC0415

            schema = TypeAdapter(obj).json_schema()
            schema = _add_python_type_info_generic(schema, cast("type", obj))

            if ref_strategy and ref_strategy != InputModelRefStrategy.RegenerateAll:
                obj_type = cast("type", obj)
                nested_models = _collect_nested_models(obj_type)
                obj_name = getattr(obj, "__name__", None)
                if obj_name and "$defs" in schema and obj_name in schema["$defs"]:  # pragma: no cover
                    nested_models[obj_name] = obj_type
                schema = _filter_defs_by_strategy(schema, nested_models, output_model_type, ref_strategy)

            return schema

        msg = f"{qualname!r} is not a supported type. Supported: dict, Pydantic v2 BaseModel, dataclass, TypedDict"
        raise Error(msg)
    finally:
        if module_state is not None:
            _restore_input_module(module_state)
