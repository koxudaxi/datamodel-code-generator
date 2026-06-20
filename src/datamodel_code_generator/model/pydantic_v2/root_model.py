"""Pydantic v2 RootModel implementation.

Generates models inheriting from pydantic.RootModel for wrapping single types.
"""

from __future__ import annotations

from typing import Any, ClassVar

from datamodel_code_generator.imports import IMPORT_ANY, Import
from datamodel_code_generator.model.pydantic_v2.base_model import _CONFIG_ITEMS_TEMPLATE_DATA_KEY, BaseModel
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_CONFIG_DICT

IMPORT_ABC_ITERATOR = Import.from_full_path("collections.abc.Iterator")
IMPORT_ABC_SEQUENCE = Import.from_full_path("collections.abc.Sequence")
IMPORT_OVERLOAD = Import.from_full_path("typing.overload")
IMPORT_SUPPORTS_INDEX = Import.from_full_path("typing.SupportsIndex")
_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY = "sequence_base_class"


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

    def add_sequence_methods(self, item_type: str, slice_type: str) -> None:
        """Add sequence helper methods that delegate to the wrapped root value."""
        self._additional_imports.append(IMPORT_ABC_ITERATOR)
        self._additional_imports.append(IMPORT_ABC_SEQUENCE)
        self._additional_imports.append(IMPORT_OVERLOAD)
        self._additional_imports.append(IMPORT_SUPPORTS_INDEX)
        if item_type == "Any":
            self._additional_imports.append(IMPORT_ANY)
        self.extra_template_data[_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY] = f"Sequence[{item_type}]"
        self.methods.extend([
            f"def __iter__(self) -> Iterator[{item_type}]:\n        return iter(self.root)",
            f"@overload\n    def __getitem__(self, index: SupportsIndex) -> {item_type}: ...",
            f"@overload\n    def __getitem__(self, index: slice) -> {slice_type}: ...",
            (
                f"def __getitem__(self, index: SupportsIndex | slice) -> {item_type} | {slice_type}:\n"
                "        return self.root[index]"
            ),
            "def __len__(self) -> int:\n        return len(self.root)",
        ])
