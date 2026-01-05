"""Input model loading and schema transformation for --input-model option."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

if TYPE_CHECKING:
    from datamodel_code_generator import DataModelType, InputFileType
    from datamodel_code_generator.arguments import InputModelRefStrategy


class Error(Exception):
    """Error raised during input model loading."""


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
    import types  # noqa: PLC0415
    from typing import Union, get_args, get_origin  # noqa: PLC0415

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

    from typing import Annotated  # noqa: PLC0415

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
    from collections.abc import Callable as ABCCallable  # noqa: PLC0415

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
    """Get the InputModelJsonSchema class (lazy import to avoid Pydantic v1 issues)."""
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
    from typing import get_origin  # noqa: PLC0415

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
    from typing import Union, get_args, get_origin  # noqa: PLC0415

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
    from collections import ChainMap, Counter, OrderedDict, defaultdict, deque  # noqa: PLC0415
    from collections.abc import Mapping as ABCMapping  # noqa: PLC0415
    from collections.abc import MutableMapping as ABCMutableMapping  # noqa: PLC0415
    from collections.abc import MutableSequence as ABCMutableSequence  # noqa: PLC0415
    from collections.abc import MutableSet as ABCMutableSet  # noqa: PLC0415
    from collections.abc import Sequence as ABCSequence  # noqa: PLC0415
    from collections.abc import Set as AbstractSet  # noqa: PLC0415

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
    import types  # noqa: PLC0415
    from typing import get_args, get_origin  # noqa: PLC0415

    origin: type | None = get_origin(tp)
    args = get_args(tp)
    preserved_origins = _get_preserved_type_origins()

    from typing import Union  # noqa: PLC0415

    is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
    if is_union:
        if args:
            nested = [_serialize_python_type(a) for a in args]
            if any(n is not None for n in nested):
                return " | ".join(n or _full_type_name(a) for n, a in zip(nested, args, strict=False))
        return None  # pragma: no cover

    from typing import Annotated  # noqa: PLC0415

    if origin is Annotated:
        if args:
            return _serialize_python_type(args[0]) or _full_type_name(args[0])
        return None  # pragma: no cover

    type_name: str | None = None
    if origin is not None:
        type_name = preserved_origins.get(origin)  # ty: ignore
        if type_name is None and getattr(origin, "__module__", None) == "collections":  # pragma: no cover
            type_name = _simple_type_name(origin)  # ty: ignore
    if type_name is not None:
        if args:
            args_str = ", ".join(_serialize_python_type(a) or _full_type_name(a) for a in args)
            return f"{type_name}[{args_str}]"
        return type_name  # pragma: no cover

    if args:
        nested = [_serialize_python_type(a) for a in args]
        if any(n is not None for n in nested):
            origin_name = _simple_type_name(origin or tp)  # ty: ignore
            args_str = ", ".join(n or _full_type_name(a) for n, a in zip(nested, args, strict=False))
            return f"{origin_name}[{args_str}]"

    return None


def _simple_type_name(tp: type) -> str:
    """Get a simple string representation of a type."""
    from typing import get_origin  # noqa: PLC0415

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
    import types  # noqa: PLC0415
    from typing import ForwardRef, Union, get_args, get_origin  # noqa: PLC0415

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

        origin_name = _simple_type_name(origin)  # ty: ignore
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
    from dataclasses import is_dataclass  # noqa: PLC0415
    from enum import Enum as PyEnum  # noqa: PLC0415
    from typing import get_args  # noqa: PLC0415

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
    from typing import get_type_hints  # noqa: PLC0415

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
    from dataclasses import is_dataclass  # noqa: PLC0415
    from enum import Enum as PyEnum  # noqa: PLC0415

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
        DataModelType.PydanticBaseModel,
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
    from datamodel_code_generator.arguments import InputModelRefStrategy  # noqa: PLC0415

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
        from datamodel_code_generator.model.base import DataModel, DataModelFieldBase  # noqa: PLC0415
        from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: PLC0415
        from datamodel_code_generator.types import DataTypeManager, StrictTypes  # noqa: PLC0415

        types_namespace = {
            "DataModel": DataModel,
            "DataModelFieldBase": DataModelFieldBase,
            "DataTypeManager": DataTypeManager,
            "StrictTypes": StrictTypes,
            "UnionMode": UnionMode,
        }
        obj.model_rebuild(_types_namespace=types_namespace)  # ty: ignore
    elif module == "datamodel_code_generator.__main__" and class_name in main_config_classes:  # pragma: no cover
        from datamodel_code_generator.model.pydantic_v2 import UnionMode  # noqa: PLC0415
        from datamodel_code_generator.types import StrictTypes  # noqa: PLC0415

        types_namespace = {
            "UnionMode": UnionMode,
            "StrictTypes": StrictTypes,
        }
        obj.model_rebuild(_types_namespace=types_namespace)  # ty: ignore
    else:
        obj.model_rebuild()  # ty: ignore


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


def load_model_schema(  # noqa: PLR0912, PLR0914, PLR0915
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
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415

    from datamodel_code_generator import (  # noqa: PLC0415
        DataModelType,
        InputFileType,
    )
    from datamodel_code_generator.arguments import InputModelRefStrategy  # noqa: PLC0415

    if output_model_type is None:
        output_model_type = DataModelType.PydanticBaseModel

    if len(input_models) == 1:
        return _load_single_model_schema(input_models[0], input_file_type, ref_strategy, output_model_type)

    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    model_classes: list[type] = []
    loaded_modules: dict[str, object] = {}

    for input_model in input_models:
        modname, sep, qualname = input_model.rpartition(":")
        if not sep or not modname:
            msg = (
                f"Invalid --input-model format: {input_model!r}. Expected 'module:Object' or 'path/to/file.py:Object'."
            )
            raise Error(msg)

        if modname not in loaded_modules:
            is_path = "/" in modname or "\\" in modname
            if not is_path and modname.endswith(".py"):
                is_path = Path(modname).exists()

            if is_path:
                file_path = Path(modname).resolve()
                if not file_path.exists():
                    msg = f"File not found: {modname!r}"
                    raise Error(msg)
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    msg = f"Cannot load module from {modname!r}"
                    raise Error(msg)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            else:
                try:
                    found_spec = importlib.util.find_spec(modname)
                    if found_spec is None:
                        msg = f"Cannot find module {modname!r}"
                        raise Error(msg)
                    module = importlib.import_module(modname)
                except ImportError as e:
                    msg = f"Cannot import module {modname!r}: {e}"
                    raise Error(msg) from e
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

        if not hasattr(obj, "model_json_schema"):
            msg = (
                "Multiple --input-model with Pydantic model requires Pydantic v2 runtime. "
                "Please upgrade Pydantic to v2."
            )
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

        schema = model_class.model_json_schema(schema_generator=schema_generator)  # ty: ignore
        schema = _add_python_type_for_unserializable(schema, model_class)
        schema = _add_python_type_info(schema, model_class)

        schema = _transform_single_model_to_inheritance(schema, model_class, schema_generator, processed_parents)

        if "$defs" in schema:
            schema_defs = cast("dict[str, object]", schema["$defs"])
            for k, v in schema_defs.items():
                new_is_base = isinstance(v, dict) and v.get("x-is-base-class")  # ty: ignore
                existing = merged_defs.get(k)
                existing_is_base = isinstance(existing, dict) and existing.get("x-is-base-class") if existing else False  # ty: ignore
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


def _load_single_model_schema(  # noqa: PLR0912, PLR0914, PLR0915
    input_model: str,
    input_file_type: InputFileType,
    ref_strategy: InputModelRefStrategy | None,
    output_model_type: DataModelType,
) -> dict[str, object]:
    """Load schema from a Python import path.

    Args:
        input_model: Import path in 'module.path:ObjectName' format
        input_file_type: Current input file type setting for validation
        ref_strategy: Strategy for handling referenced types
        output_model_type: Target output model type for reuse-foreign strategy

    Returns:
        Schema dict

    Raises:
        Error: If format invalid, object cannot be loaded, or input_file_type invalid
    """
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415

    from datamodel_code_generator import InputFileType  # noqa: PLC0415
    from datamodel_code_generator.arguments import InputModelRefStrategy  # noqa: PLC0415

    modname, sep, qualname = input_model.rpartition(":")
    if not sep or not modname:
        msg = f"Invalid --input-model format: {input_model!r}. Expected 'module:Object' or 'path/to/file.py:Object'."
        raise Error(msg)

    is_path = "/" in modname or "\\" in modname
    if not is_path and modname.endswith(".py"):
        is_path = Path(modname).exists()

    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    if is_path:
        file_path = Path(modname).resolve()
        if not file_path.exists():
            msg = f"File not found: {modname!r}"
            raise Error(msg)
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            msg = f"Cannot load module from {modname!r}"
            raise Error(msg)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    else:
        try:
            spec = importlib.util.find_spec(modname)
            if spec is None:
                msg = f"Cannot find module {modname!r}"
                raise Error(msg)
            module = importlib.import_module(modname)
        except ImportError as e:
            msg = f"Cannot import module {modname!r}: {e}"
            raise Error(msg) from e

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
        if not hasattr(obj, "model_json_schema"):
            msg = "--input-model with Pydantic model requires Pydantic v2 runtime. Please upgrade Pydantic to v2."
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
            if model_name and "$defs" in schema and model_name in schema["$defs"]:  # pragma: no cover  # ty: ignore
                nested_models[model_name] = obj
            schema = _filter_defs_by_strategy(schema, nested_models, output_model_type, ref_strategy)

        return schema

    from dataclasses import is_dataclass  # noqa: PLC0415

    is_typed_dict = isinstance(obj, type) and hasattr(obj, "__required_keys__")
    if is_dataclass(obj) or is_typed_dict:
        if input_file_type not in {InputFileType.Auto, InputFileType.JsonSchema}:
            msg = (
                f"--input-file-type must be 'jsonschema' (or omitted) "
                f"when --input-model points to a dataclass or TypedDict, "
                f"got '{input_file_type.value}'"
            )
            raise Error(msg)
        try:
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
        except ImportError as e:
            msg = "--input-model with dataclass/TypedDict requires Pydantic v2 runtime."
            raise Error(msg) from e

        return schema

    msg = f"{qualname!r} is not a supported type. Supported: dict, Pydantic v2 BaseModel, dataclass, TypedDict"
    raise Error(msg)
