"""Input model loading and schema transformation for --input-model option."""

from __future__ import annotations

import importlib.util
import sys
import types
from collections import ChainMap, Counter, OrderedDict, defaultdict, deque
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
from dataclasses import is_dataclass
from enum import Enum as PyEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Union, cast, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from datamodel_code_generator._input_model_transport import PythonTypeExpressionCollector
from datamodel_code_generator._process_state import PROCESS_STATE_LOCK
from datamodel_code_generator._python_type_annotation import (
    PythonTypeExpr,
    PythonTypeName,
    PythonTypeQualifiedName,
    PythonTypeRuntimeSymbol,
    PythonTypeSubscript,
    PythonTypeUnion,
    render_python_type_expr,
    rewrite_python_type_expr,
)
from datamodel_code_generator.enums import InputModelRefStrategy, _get_output_model_family

if TYPE_CHECKING:
    from datamodel_code_generator import DataModelType, InputFileType
    from datamodel_code_generator.enums import _OutputModelFamily
    from datamodel_code_generator.input_model_result import LoadedInputModelSchema


class Error(Exception):
    """Error raised during input model loading."""


_MISSING_MODULE = object()
_ModuleRestoreState = tuple[str, object]


def _path_is_within(path: str | Path, directory: Path) -> bool:
    try:
        return Path(path).resolve().is_relative_to(directory)
    except OSError:
        return False


def _module_is_from_directory(
    module: object,
    directory: Path,
    excluded_directory: Path | None = None,
) -> bool:
    if not isinstance(module, types.ModuleType):
        return False

    def is_owned_path(path: str | Path) -> bool:
        return _path_is_within(path, directory) and (
            excluded_directory is None or not _path_is_within(path, excluded_directory)
        )

    if isinstance(module_file := getattr(module, "__file__", None), str):
        return is_owned_path(module_file)
    return any(is_owned_path(path) for path in getattr(module, "__path__", ()))


def _remove_local_module(module_name: str, module: types.ModuleType) -> None:
    if sys.modules.get(module_name) is not module:
        return
    sys.modules.pop(module_name, None)
    parent_name, separator, child_name = module_name.rpartition(".")
    if (
        separator
        and isinstance(parent := sys.modules.get(parent_name), types.ModuleType)
        and vars(parent).get(child_name) is module
    ):
        vars(parent).pop(child_name, None)


def _remove_input_model_path(cwd_entry: str) -> None:
    if (index := next((index for index, entry in enumerate(sys.path) if entry is cwd_entry), None)) is not None:
        sys.path.pop(index)


def _module_depth(module_name: str) -> int:
    return module_name.count(".")


def _load_model_schema_isolated(
    input_models: list[str],
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None,
    output_model_type: DataModelType | None,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> dict[str, object]:
    """Load a schema while restoring cwd-local import state afterwards."""
    with PROCESS_STATE_LOCK:
        cwd_entry = str(Path.cwd())
        added_path = cwd_entry not in sys.path
        if not added_path:
            return _load_model_schema(
                input_models,
                input_file_type,
                ref_strategy,
                output_model_type,
                expression_collector,
            )

        directory = Path(cwd_entry).resolve()
        environment_directory = Path(sys.prefix).resolve()
        importer_cache_entry = sys.path_importer_cache.get(cwd_entry, _MISSING_MODULE)
        baseline_modules = sys.modules.copy()
        sys.path.insert(0, cwd_entry)
        try:
            return _load_model_schema(
                input_models,
                input_file_type,
                ref_strategy,
                output_model_type,
                expression_collector,
            )
        finally:
            current_modules = sys.modules.copy()
            local_module_names = sorted(
                (
                    module_name
                    for module_name, module in current_modules.items()
                    if module_name not in baseline_modules
                    and _module_is_from_directory(module, directory, environment_directory)
                ),
                key=_module_depth,
                reverse=True,
            )
            for module_name in local_module_names:
                _remove_local_module(module_name, current_modules[module_name])
            _remove_input_model_path(cwd_entry)
            if importer_cache_entry is _MISSING_MODULE:
                sys.path_importer_cache.pop(cwd_entry, None)
            else:
                sys.path_importer_cache[cwd_entry] = cast("Any", importer_cache_entry)


def _restore_path_module(state: _ModuleRestoreState) -> None:
    module_name, previous_module = state
    if previous_module is _MISSING_MODULE:
        sys.modules.pop(module_name, None)
        return
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


def _load_module_from_path(file_path: Path, modname: str) -> tuple[types.ModuleType, _ModuleRestoreState]:
    module_name = _get_path_module_name(file_path)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load module from {modname!r}"
        raise Error(msg)

    previous_module = sys.modules.get(module_name, _MISSING_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        _restore_path_module((module_name, previous_module))
        raise
    return module, (module_name, previous_module)


def _split_input_model(input_model: str) -> tuple[str, str]:
    modname, separator, qualname = input_model.rpartition(":")
    if separator and modname:
        return modname, qualname

    msg = f"Invalid --input-model format: {input_model!r}. Expected 'module:Object' or 'path/to/file.py:Object'."
    raise Error(msg)


def _is_path_input_model_module(modname: str) -> bool:
    return "/" in modname or "\\" in modname or (modname.endswith(".py") and Path(modname).exists())


def _load_input_model_module(modname: str) -> tuple[types.ModuleType, _ModuleRestoreState | None]:
    if _is_path_input_model_module(modname):
        file_path = Path(modname).resolve()
        if not file_path.exists():
            msg = f"File not found: {modname!r}"
            raise Error(msg)
        return _load_module_from_path(file_path, modname)

    try:
        if importlib.util.find_spec(modname) is None:
            msg = f"Cannot find module {modname!r}"
            raise Error(msg)
        return importlib.import_module(modname), None
    except ImportError as e:
        msg = f"Cannot import module {modname!r}: {e}"
        raise Error(msg) from e


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


def _runtime_python_type_expr(tp: object, *, full_name: bool = False) -> PythonTypeExpr:
    """Bind a live type lazily so normal code-generation imports stay lightweight."""
    from datamodel_code_generator._python_type_runtime import (  # noqa: PLC0415
        python_type_expr_from_runtime,
        python_type_expr_from_runtime_full_name,
    )

    return python_type_expr_from_runtime_full_name(tp) if full_name else python_type_expr_from_runtime(tp)


def _transport_python_type_expr(
    expression: PythonTypeExpr,
    expression_collector: PythonTypeExpressionCollector | None,
) -> str:
    """Keep the public text contract while tokenizing the private parser path."""
    if expression_collector is not None:

        def bind_runtime_symbol_to_syntax(item: PythonTypeExpr) -> PythonTypeExpr:
            match item:
                case PythonTypeRuntimeSymbol() as runtime_symbol:
                    module = runtime_symbol.module
                    parts = runtime_symbol.qualname_parts
                    if len(parts) != 1:
                        return item if module else PythonTypeQualifiedName(parts)
                    if module:
                        # A top-level runtime symbol has the same import semantics as
                        # its historical dotted text. Nested qualnames must retain
                        # runtime provenance: their outer classes are not modules.
                        return PythonTypeQualifiedName((*module.split("."), parts[0]))
                    return PythonTypeName(parts[0])
            return item

        return expression_collector.add(rewrite_python_type_expr(expression, bind_runtime_symbol_to_syntax))
    return render_python_type_expr(expression)


def _serialize_python_type_full(
    tp: object,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> str:
    """Serialize ANY Python type to its string representation."""
    try:
        return _transport_python_type_expr(_runtime_python_type_expr(tp), expression_collector)
    except ValueError as exc:
        raise Error(str(exc)) from None


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


def _process_unserializable_property(
    prop: dict[str, Any],
    annotation: type,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> None:
    """Process a single property, handling anyOf/oneOf/items structures."""
    if "anyOf" in prop:
        for item in prop["anyOf"]:
            if item.get(_UNSERIALIZABLE_MARKER):
                _set_python_type_for_unserializable(item, annotation, expression_collector)
    elif "oneOf" in prop:  # pragma: no cover
        for item in prop["oneOf"]:
            if item.get(_UNSERIALIZABLE_MARKER):
                _set_python_type_for_unserializable(item, annotation, expression_collector)
    elif prop.get(_UNSERIALIZABLE_MARKER):
        _set_python_type_for_unserializable(prop, annotation, expression_collector)
    elif "items" in prop and prop["items"].get(_UNSERIALIZABLE_MARKER):
        prop["x-python-type"] = _serialize_python_type_full(annotation, expression_collector)
        prop["items"].pop(_UNSERIALIZABLE_MARKER, None)
    elif _is_type_origin(annotation):
        prop["x-python-type"] = _serialize_python_type_full(annotation, expression_collector)


def _set_python_type_for_unserializable(
    item: dict[str, Any],
    annotation: type,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> None:
    """Set x-python-type and clean up markers."""
    origin = get_origin(annotation)
    actual_type = annotation

    if origin is Union:
        for arg in get_args(annotation):  # pragma: no branch
            if arg is not type(None):  # pragma: no branch
                actual_type = arg
                break

    item["x-python-type"] = _serialize_python_type_full(actual_type, expression_collector)
    item.pop(_UNSERIALIZABLE_MARKER, None)


def _add_python_type_for_unserializable(
    schema: dict[str, Any],
    model: type,
    visited_defs: set[str] | None = None,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> dict[str, Any]:
    """Add x-python-type to ALL fields marked as unserializable."""
    if visited_defs is None:
        visited_defs = set()

    if "properties" in schema:
        model_fields = getattr(model, "model_fields", {})
        for field_name, prop in schema["properties"].items():
            if field_name in model_fields:  # pragma: no branch
                annotation = model_fields[field_name].annotation
                _process_unserializable_property(prop, annotation, expression_collector)

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
                _add_python_type_for_unserializable(
                    def_schema,
                    nested_models[def_name],
                    visited_defs,
                    expression_collector,
                )

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


def _serialize_python_type(
    tp: type,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> str | None:
    """Serialize Python type to a string for x-python-type field."""
    expression = _preserved_python_type_expr(tp)
    return _transport_python_type_expr(expression, expression_collector) if expression is not None else None


def _preserved_python_type_expr(tp: type) -> PythonTypeExpr | None:  # noqa: PLR0911
    """Build IR only when JSON Schema loses relevant runtime type structure."""
    origin: type | None = get_origin(tp)
    args = get_args(tp)
    preserved_origins = _get_preserved_type_origins()

    is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
    if is_union:
        if args:
            nested = tuple(_preserved_python_type_expr(argument) for argument in args)
            if any(expression is not None for expression in nested):
                return PythonTypeUnion(
                    tuple(
                        expression or _runtime_python_type_expr(argument, full_name=True)
                        for expression, argument in zip(nested, args, strict=True)
                    )
                )
        return None  # pragma: no cover

    if origin is Annotated:
        if args:
            return _preserved_python_type_expr(args[0]) or _runtime_python_type_expr(args[0], full_name=True)
        return None  # pragma: no cover

    type_name: str | None = None
    if origin is not None:
        type_name = preserved_origins.get(origin)
        if type_name is None and getattr(origin, "__module__", None) == "collections":  # pragma: no cover
            type_name = _simple_type_name(origin)
    if type_name is not None:
        if args:
            return PythonTypeSubscript(
                PythonTypeName(type_name),
                tuple(
                    _preserved_python_type_expr(argument) or _runtime_python_type_expr(argument, full_name=True)
                    for argument in args
                ),
            )
        return PythonTypeName(type_name)  # pragma: no cover

    if args:
        nested = tuple(_preserved_python_type_expr(argument) for argument in args)
        if any(expression is not None for expression in nested):
            return PythonTypeSubscript(
                PythonTypeName(_simple_type_name(origin or tp)),
                tuple(
                    expression or _runtime_python_type_expr(argument, full_name=True)
                    for expression, argument in zip(nested, args, strict=True)
                ),
            )

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


def _full_type_name(tp: type) -> str:
    """Get a full qualified name representation of a type for type arguments.

    For generic types, keeps outer type as short name but FQN-izes the type arguments.
    For non-generic types, returns FQN for non-builtin types.
    """
    return render_python_type_expr(_runtime_python_type_expr(tp, full_name=True))


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
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> None:
    """Add x-python-type to properties dict for given model fields."""
    for field_name, field_info in model_fields.items():
        if field_name not in properties:  # pragma: no cover
            continue
        serialized = _serialize_python_type(field_info.annotation, expression_collector)
        if serialized:
            properties[field_name]["x-python-type"] = serialized


def _add_python_type_info(
    schema: dict[str, Any],
    model: type,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> dict[str, Any]:
    """Add x-python-type information to JSON Schema for types lost during conversion."""
    model_fields = getattr(model, "model_fields", None)
    if model_fields and "properties" in schema:
        _add_python_type_to_properties(schema["properties"], model_fields, expression_collector)

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
                _add_python_type_to_properties(def_schema["properties"], nested_fields, expression_collector)

    return schema


def _add_python_type_info_generic(
    schema: dict[str, Any],
    obj: type,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> dict[str, Any]:
    """Add x-python-type information using get_type_hints (for dataclass/TypedDict)."""
    type_hints = _get_type_hints_safe(obj)
    if type_hints and "properties" in schema:  # pragma: no branch
        for field_name, field_type in type_hints.items():
            if field_name in schema["properties"]:  # pragma: no branch
                serialized = _serialize_python_type(field_type, expression_collector)
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


def _should_reuse_type(source_family: str, output_family: _OutputModelFamily) -> bool:
    """Determine if a source type can be reused without conversion."""
    if source_family == _TYPE_FAMILY_ENUM:
        return True
    return source_family == output_family


def _filter_defs_by_strategy(
    schema: dict[str, Any],
    nested_models: dict[str, type],
    output_family: _OutputModelFamily | None,
    strategy: InputModelRefStrategy,
) -> dict[str, Any]:
    """Filter $defs based on ref strategy, marking reused types with x-python-import."""
    if strategy == InputModelRefStrategy.RegenerateAll:  # pragma: no cover
        return schema

    if "$defs" not in schema:  # pragma: no cover
        return schema

    new_defs: dict[str, Any] = {}

    for def_name, def_schema in schema["$defs"].items():
        if def_name not in nested_models:  # pragma: no cover
            new_defs[def_name] = def_schema
            continue

        nested_type = nested_models[def_name]
        type_family = _get_type_family(nested_type)

        match strategy:
            case InputModelRefStrategy.ReuseAll:
                should_reuse = True
            case InputModelRefStrategy.ReuseForeign if output_family is not None:
                should_reuse = _should_reuse_type(type_family, output_family)
            case _:  # pragma: no cover
                should_reuse = False  # pragma: no cover

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
        from datamodel_code_generator.config import _rebuild_config_model  # noqa: PLC0415
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
        _rebuild_config_model(obj, types_namespace)  # ty: ignore[invalid-argument-type]
    elif module == "datamodel_code_generator.__main__" and class_name in main_config_classes:  # pragma: no cover
        from datamodel_code_generator.config import _rebuild_config_model  # noqa: PLC0415
        from datamodel_code_generator.enums import UnionMode  # noqa: PLC0415
        from datamodel_code_generator.types import StrictTypes  # noqa: PLC0415

        types_namespace = {
            "UnionMode": UnionMode,
            "StrictTypes": StrictTypes,
        }
        _rebuild_config_model(obj, types_namespace)  # ty: ignore[invalid-argument-type]
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
    expression_collector: PythonTypeExpressionCollector | None = None,
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
        parent_schema = _add_python_type_for_unserializable(
            parent_schema,
            parent,
            expression_collector=expression_collector,
        )
        parent_schema = _add_python_type_info(parent_schema, parent, expression_collector)
        parent_schema = _transform_single_model_to_inheritance(
            parent_schema,
            parent,
            schema_generator,
            processed_parents,
            expression_collector,
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
    return _load_model_schema_isolated(input_models, input_file_type, ref_strategy, output_model_type)


def _load_model_schema_with_python_type_expressions(
    input_models: list[str],
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None = None,
    output_model_type: DataModelType | None = None,
) -> LoadedInputModelSchema:
    """Load the CLI-only schema transport without rendering runtime expressions."""
    expression_collector = PythonTypeExpressionCollector()
    schema = _load_model_schema_isolated(
        input_models,
        input_file_type,
        ref_strategy,
        output_model_type,
        expression_collector,
    )
    return expression_collector.loaded_schema(schema)


def _load_model_schema(  # noqa: PLR0912, PLR0914, PLR0915
    input_models: list[str],
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None,
    output_model_type: DataModelType | None,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> dict[str, object]:
    from datamodel_code_generator import InputFileType  # noqa: PLC0415

    output_family: _OutputModelFamily | None = None
    if ref_strategy is InputModelRefStrategy.ReuseForeign:
        output_family = _get_output_model_family(output_model_type)

    if len(input_models) == 1:
        return _load_single_model_schema(
            input_models[0],
            input_file_type,
            ref_strategy,
            output_family,
            expression_collector,
        )

    model_classes: list[type] = []
    loaded_modules: dict[str, types.ModuleType] = {}
    path_module_states: list[_ModuleRestoreState] = []

    try:
        for input_model in input_models:
            modname, qualname = _split_input_model(input_model)

            if modname not in loaded_modules:
                module, module_state = _load_input_model_module(modname)
                if module_state is not None:
                    path_module_states.append(module_state)
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
            schema = _add_python_type_for_unserializable(
                schema,
                model_class,
                expression_collector=expression_collector,
            )
            schema = _add_python_type_info(schema, model_class, expression_collector)

            schema = _transform_single_model_to_inheritance(
                schema,
                model_class,
                schema_generator,
                processed_parents,
                expression_collector,
            )

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
            final_schema = _filter_defs_by_strategy(final_schema, all_nested_models, output_family, ref_strategy)

        return final_schema
    finally:
        for state in reversed(path_module_states):
            _restore_path_module(state)


def _load_single_model_schema(  # noqa: PLR0912, PLR0915
    input_model: str,
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None,
    output_family: _OutputModelFamily | None,
    expression_collector: PythonTypeExpressionCollector | None = None,
) -> dict[str, object]:
    """Load schema from a Python import path.

    Args:
        input_model: Import path in 'module.path:ObjectName' format
        input_file_type: Current input file type setting for validation
        ref_strategy: Strategy for handling referenced types
        output_family: Target output compatibility family for reuse-foreign strategy

    Returns:
        Schema dict

    Raises:
        Error: If format invalid, object cannot be loaded, or input_file_type invalid
    """
    from datamodel_code_generator import InputFileType  # noqa: PLC0415

    modname, qualname = _split_input_model(input_model)

    module, path_module_state = _load_input_model_module(modname)

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
            if expression_collector is None:
                return obj
            # Dict schemas contain no runtime IR. Preserve the former CLI JSON
            # round trip exactly: it both isolates module state and performs
            # JSON key coercion/validation before parser construction.
            import json  # noqa: PLC0415

            return cast("dict[str, object]", json.loads(json.dumps(obj)))

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
            schema = _add_python_type_for_unserializable(
                schema,
                obj,
                expression_collector=expression_collector,
            )
            schema = _add_python_type_info(schema, obj, expression_collector)

            schema = _transform_single_model_to_inheritance(
                schema,
                obj,
                schema_generator,
                expression_collector=expression_collector,
            )

            if ref_strategy and ref_strategy != InputModelRefStrategy.RegenerateAll:
                nested_models = _collect_nested_models(obj)
                model_name = getattr(obj, "__name__", None)
                schema_defs = cast("dict[str, object]", schema.get("$defs", {}))
                if model_name and model_name in schema_defs:  # pragma: no cover
                    nested_models[model_name] = obj
                schema = _filter_defs_by_strategy(schema, nested_models, output_family, ref_strategy)

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
            schema = _add_python_type_info_generic(schema, cast("type", obj), expression_collector)

            if ref_strategy and ref_strategy != InputModelRefStrategy.RegenerateAll:
                obj_type = cast("type", obj)
                nested_models = _collect_nested_models(obj_type)
                obj_name = getattr(obj, "__name__", None)
                if obj_name and "$defs" in schema and obj_name in schema["$defs"]:  # pragma: no cover
                    nested_models[obj_name] = obj_type
                schema = _filter_defs_by_strategy(schema, nested_models, output_family, ref_strategy)

            return schema

        msg = f"{qualname!r} is not a supported type. Supported: dict, Pydantic v2 BaseModel, dataclass, TypedDict"
        raise Error(msg)
    finally:
        if path_module_state is not None:
            _restore_path_module(path_module_state)
