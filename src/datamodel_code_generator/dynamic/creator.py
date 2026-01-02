"""Dynamic model creator for generating Python classes at runtime."""

from __future__ import annotations

import importlib
import logging
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from pydantic import ConfigDict, Field, create_model

try:
    from pydantic.errors import PydanticUndefinedAnnotation
except ImportError:
    PydanticUndefinedAnnotation = NameError  # type: ignore[misc,assignment]

from datamodel_code_generator.dynamic.constraints import constraints_to_field_kwargs
from datamodel_code_generator.dynamic.exceptions import (
    TypeResolutionError,
)
from datamodel_code_generator.dynamic.type_resolver import TypeResolver

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from datamodel_code_generator.model.base import DataModel, DataModelFieldBase
    from datamodel_code_generator.parser.base import Parser

logger = logging.getLogger(__name__)


class DynamicModelCreator:
    """Creates actual Python classes from DataModel objects."""

    def __init__(self, parser: Parser) -> None:
        """Initialize with a parser instance."""
        self.parser = parser
        self._models: dict[str, type[Any]] = {}
        self._short_name_lookup: dict[str, type[Any]] = {}
        self._type_resolver = TypeResolver(self._short_name_lookup)

    def create_models(self) -> dict[str, type]:
        """Create all models from parser results.

        Returns:
            Dictionary mapping class names to actual Python classes.

        Raises:
            TypeResolutionError: If a type cannot be resolved.
            DynamicModelError: If model generation fails.
        """
        from datamodel_code_generator.model.enum import Enum as EnumModel  # noqa: PLC0415
        from datamodel_code_generator.parser.base import sort_data_models  # noqa: PLC0415

        if not self.parser.results:
            return {}

        _, sorted_models_dict, _ = sort_data_models(self.parser.results)

        for data_model in sorted_models_dict.values():
            if isinstance(data_model, EnumModel):
                self._create_enum_model(data_model)
            else:
                self._create_pydantic_model(data_model)

        self._rebuild_models()

        return self._models

    def _create_pydantic_model(self, data_model: DataModel) -> type[Any]:
        """Create a single Pydantic model from DataModel."""
        field_definitions: dict[str, tuple[Any, FieldInfo]] = {}

        for field in data_model.fields:
            if field.name is None:
                continue

            try:
                field_type, type_constraints = self._type_resolver.resolve_with_constraints(field.data_type)
            except Exception as e:
                raise TypeResolutionError(field.data_type, data_model.class_name, field.name or "") from e

            field_info = self._create_field_info(field, type_constraints)
            field_definitions[field.name] = (field_type, field_info)

        base_classes = self._resolve_base_classes(data_model)
        model_config = self._build_model_config(data_model)
        module_name = self._get_module_name(data_model)

        from pydantic import BaseModel as BaseModelCls  # noqa: PLC0415

        if len(base_classes) > 1:
            combined_base_name = f"_{data_model.class_name}Base"
            combined_base = type(combined_base_name, base_classes, {})
            effective_base: type[Any] = combined_base
        else:
            effective_base = base_classes[0] if base_classes else BaseModelCls

        create_kwargs: dict[str, Any] = {
            "__base__": effective_base,
            "__module__": module_name,
        }

        if model_config:
            create_kwargs["__config__"] = model_config

        model = cast(
            "type[Any]",
            create_model(
                data_model.class_name,
                **create_kwargs,
                **cast("dict[str, Any]", field_definitions),
            ),
        )

        model_key = self._get_model_key(data_model)
        self._models[model_key] = model
        self._short_name_lookup[data_model.class_name] = model

        if model_key != data_model.class_name:
            self._models[data_model.class_name] = model

        return model

    def _get_model_key(self, data_model: DataModel) -> str:
        """Get module-qualified key for model storage."""
        module_name = self._get_module_name(data_model)
        if module_name and module_name != "__dynamic__":
            return f"{module_name}.{data_model.class_name}"
        return data_model.class_name

    def _create_field_info(  # noqa: PLR6301
        self, field: DataModelFieldBase, type_constraints: dict[str, Any] | None = None
    ) -> FieldInfo:
        """Convert DataModelFieldBase to Pydantic FieldInfo."""
        kwargs = constraints_to_field_kwargs(field.constraints)

        if type_constraints:
            kwargs.update(type_constraints)

        if (hasattr(field, "has_default") and field.has_default) or field.default is not None:
            kwargs["default"] = field.default
        elif (default_factory := getattr(field, "default_factory", None)) is not None:
            kwargs["default_factory"] = default_factory
        elif field.required:
            kwargs["default"] = ...
        else:
            kwargs["default"] = None

        if field.alias:
            kwargs["alias"] = field.alias

        description = getattr(field, "description", None)
        if description:
            kwargs["description"] = description

        return Field(**kwargs)

    def _resolve_base_classes(self, data_model: DataModel) -> tuple[type, ...]:
        """Resolve base classes for the model, including custom base classes."""
        from pydantic import BaseModel  # noqa: PLC0415

        custom_base = getattr(data_model, "custom_base_class", None)
        if custom_base and isinstance(custom_base, str):
            if "." in custom_base:
                try:
                    module_path, class_name = custom_base.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    custom_base_cls = getattr(module, class_name)
                    return (custom_base_cls,)  # noqa: TRY300
                except (ValueError, ImportError, AttributeError) as e:
                    logger.warning("Failed to import custom_base_class %s: %s", custom_base, e)
            else:
                logger.warning("Invalid custom_base_class format: %s. Expected 'module.ClassName'", custom_base)

        if not data_model.base_classes:
            return (BaseModel,)

        bases = []
        for base_class in data_model.base_classes:
            if base_class.reference and base_class.reference.short_name in self._short_name_lookup:
                bases.append(self._short_name_lookup[base_class.reference.short_name])
            elif hasattr(base_class, "type") and base_class.type:
                type_name = base_class.type
                if type_name in self._short_name_lookup:
                    bases.append(self._short_name_lookup[type_name])
                else:
                    bases.append(BaseModel)
            else:
                bases.append(BaseModel)

        return tuple(bases) if bases else (BaseModel,)

    def _build_model_config(self, data_model: DataModel) -> ConfigDict | None:  # noqa: PLR6301
        """Build Pydantic ConfigDict from DataModel settings."""
        config_dict: dict[str, Any] = {}

        extra_data = getattr(data_model, "extra_template_data", {}) or {}

        if "config" in extra_data:
            existing_config = extra_data["config"]
            if isinstance(existing_config, dict):
                config_dict.update(existing_config)

        if "model_config" in extra_data:
            config_dict.update(extra_data["model_config"])

        if getattr(data_model, "allow_extra", False):
            config_dict["extra"] = "allow"

        if getattr(data_model, "use_enum_values", False):
            config_dict["use_enum_values"] = True

        if getattr(data_model, "populate_by_name", False):
            config_dict["populate_by_name"] = True

        return ConfigDict(**config_dict) if config_dict else None

    def _get_module_name(self, data_model: DataModel) -> str:  # noqa: PLR6301
        """Determine module name for the dynamic model."""
        if data_model.reference and data_model.reference.path:
            parts = data_model.reference.path.split("/")
            return ".".join(p for p in parts if p and p != "#")
        return "__dynamic__"

    def _create_enum_model(self, data_model: DataModel) -> type[Any]:
        """Create an Enum class from DataModel."""
        members = {}
        for field in data_model.fields:
            if field.name and field.default is not None:
                value = field.default
                if isinstance(value, str):
                    value = value.strip("'\"")
                members[field.name] = value

        enum_class: type[Any] = Enum(data_model.class_name, members)  # type: ignore[assignment]

        model_key = self._get_model_key(data_model)
        self._models[model_key] = enum_class
        self._short_name_lookup[data_model.class_name] = enum_class

        if model_key != data_model.class_name:
            self._models[data_model.class_name] = enum_class

        return enum_class

    def _rebuild_models(self) -> None:
        """Resolve forward references by calling model_rebuild() on all models."""
        from pydantic import BaseModel  # noqa: PLC0415

        namespace = {**self._short_name_lookup}

        for model_key, model in self._models.items():
            if isinstance(model, type) and issubclass(model, BaseModel):
                try:
                    model.model_rebuild(_types_namespace=namespace)
                except PydanticUndefinedAnnotation:
                    pass
                except (NameError, AttributeError) as e:
                    logger.debug("Model %s rebuild skipped: %s", model_key, e)
                except Exception as e:
                    logger.warning("Unexpected error rebuilding model %s: %s: %s", model_key, type(e).__name__, e)
                    raise
