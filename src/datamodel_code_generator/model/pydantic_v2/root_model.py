"""Pydantic v2 RootModel implementation.

Generates models inheriting from pydantic.RootModel for wrapping single types.
"""

from __future__ import annotations

from typing import Any, ClassVar

from datamodel_code_generator import Error
from datamodel_code_generator.imports import IMPORT_ANY, Import
from datamodel_code_generator.model.pydantic_v2.base_model import _CONFIG_ITEMS_TEMPLATE_DATA_KEY, BaseModel
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_CONFIG_DICT

IMPORT_ABC_ITERATOR = Import.from_full_path("collections.abc.Iterator")
IMPORT_ABC_SEQUENCE = Import.from_full_path("collections.abc.Sequence")
IMPORT_OVERLOAD = Import.from_full_path("typing.overload")
IMPORT_SUPPORTS_INDEX = Import.from_full_path("typing.SupportsIndex")
_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY = "sequence_base_class"
_SEQUENCE_ITEM_TYPE_TEMPLATE_DATA_KEY = "sequence_item_type"
_SEQUENCE_SLICE_TYPE_TEMPLATE_DATA_KEY = "sequence_slice_type"


class RootModel(BaseModel):
    """DataModel for Pydantic v2 RootModel."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/RootModel.jinja2"
    BASE_CLASS: ClassVar[str] = "pydantic.RootModel"
    SUPPORTS_CONFIG_EXTRA: ClassVar[bool] = False
    SUPPORTS_ARBITRARY_TYPES_ALLOWED: ClassVar[bool] = False

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        """Initialize RootModel without unnecessary model_config.

        RootModel subclasses should not have model_config except when regex_engine is required
        for lookaround patterns. Also removes custom_base_class as it cannot implement both
        BaseModel and RootModel.
        """
        if "custom_base_class" in kwargs:
            kwargs.pop("custom_base_class")

        super().__init__(**kwargs)

        config = self.extra_template_data.get("config")
        has_meaningful_config = config is not None and (
            getattr(config, "regex_engine", None) is not None or getattr(config, "frozen", None) is not None
        )
        if not has_meaningful_config:
            self.extra_template_data.pop("config", None)
            self.extra_template_data.pop(_CONFIG_ITEMS_TEMPLATE_DATA_KEY, None)
            self._additional_imports = [imp for imp in self._additional_imports if imp != IMPORT_CONFIG_DICT]

    def add_sequence_interface(self, item_type: str, slice_type: str) -> None:
        """Add sequence interface helpers that delegate to the wrapped root value."""
        self._additional_imports.append(IMPORT_ABC_ITERATOR)
        self._additional_imports.append(IMPORT_ABC_SEQUENCE)
        self._additional_imports.append(IMPORT_OVERLOAD)
        self._additional_imports.append(IMPORT_SUPPORTS_INDEX)
        if item_type == "Any":
            self._additional_imports.append(IMPORT_ANY)
        self.extra_template_data[_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY] = f"Sequence[{item_type}]"
        self.extra_template_data[_SEQUENCE_ITEM_TYPE_TEMPLATE_DATA_KEY] = item_type
        self.extra_template_data[_SEQUENCE_SLICE_TYPE_TEMPLATE_DATA_KEY] = slice_type

    def render(self, *, class_name: str | None = None) -> str:
        """Render the RootModel and validate custom sequence templates when needed."""
        rendered = super().render(class_name=class_name)
        self._validate_custom_template_sequence_interface(rendered)
        return rendered

    def _validate_custom_template_sequence_interface(self, rendered: str) -> None:
        sequence_base_class = self.extra_template_data.get(_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY)
        if not self.template_file_path.is_absolute() or not sequence_base_class:
            return

        missing: list[str] = []
        if sequence_base_class not in rendered:
            missing.append(_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY)

        missing.extend(
            method_name
            for method_name in ("__iter__", "__getitem__", "__len__")
            if f"def {method_name}(" not in rendered
        )

        if missing:
            missing_items = ", ".join(missing)
            msg = (
                "The custom RootModel template does not support --use-root-model-sequence-interface. "
                f"Update {self.template_file_path} to render sequence_base_class, "
                "sequence_item_type, and sequence_slice_type. "
                f"Missing: {missing_items}."
            )
            raise Error(msg)
