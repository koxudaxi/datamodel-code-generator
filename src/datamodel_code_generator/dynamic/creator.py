"""Dynamic model creator for generating Python classes at runtime."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from pydantic import Field, create_model

from datamodel_code_generator.dynamic.constraints import constraints_to_field_kwargs
from datamodel_code_generator.dynamic.exceptions import (
    TypeResolutionError,
)
from datamodel_code_generator.dynamic.type_resolver import TypeResolver

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from datamodel_code_generator.model.base import DataModel, DataModelFieldBase
    from datamodel_code_generator.parser.base import Parser


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
        module_name = self._get_module_name(data_model)

        from pydantic import BaseModel as BaseModelCls  # noqa: PLC0415

        if len(base_classes) > 1:
            combined_base_name = f"_{data_model.class_name}Base"
            combined_base = type(combined_base_name, base_classes, {})
            effective_base: type[Any] = combined_base
        else:
            effective_base = base_classes[0] if base_classes else BaseModelCls

        model = cast(
            "type[Any]",
            create_model(
                data_model.class_name,
                __base__=effective_base,
                __module__=module_name,
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
        """Resolve base classes for the model."""
        from pydantic import BaseModel  # noqa: PLC0415

        if not data_model.base_classes:
            return (BaseModel,)

        bases = []
        for base_class in data_model.base_classes:
            if base_class.reference and base_class.reference.short_name in self._short_name_lookup:
                bases.append(self._short_name_lookup[base_class.reference.short_name])
            else:
                bases.append(BaseModel)

        return tuple(bases) if bases else (BaseModel,)

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

        for model in self._models.values():
            if isinstance(model, type) and issubclass(model, BaseModel):
                model.model_rebuild(_types_namespace=namespace)
