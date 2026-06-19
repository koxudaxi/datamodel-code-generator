"""Pydantic v2 RootModel implementation.

Generates models inheriting from pydantic.RootModel for wrapping single types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from datamodel_code_generator.model.pydantic_v2.base_model import (
    _CONFIG_ITEMS_TEMPLATE_DATA_KEY,
    BaseModel,
    _config_dict_items,
)
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_CONFIG_DICT

if TYPE_CHECKING:
    from datamodel_code_generator.imports import Import


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

        self._sync_config_template_data()

    def _remove_config_template_data(self) -> None:
        self.extra_template_data.pop("config", None)
        self.extra_template_data.pop(_CONFIG_ITEMS_TEMPLATE_DATA_KEY, None)
        self._additional_imports = [imp for imp in self._additional_imports if imp != IMPORT_CONFIG_DICT]

    def _sync_config_template_data(self) -> None:
        config = self.extra_template_data.get("config")
        if config is None:
            self._remove_config_template_data()
            return

        config_items = _config_dict_items(config)
        has_meaningful_config = any(
            field_name in {"regex_engine", "frozen"} and value is not None for field_name, value in config_items
        )
        if not has_meaningful_config:
            self._remove_config_template_data()
            return

        self.extra_template_data[_CONFIG_ITEMS_TEMPLATE_DATA_KEY] = config_items
        if IMPORT_CONFIG_DICT not in self._additional_imports:
            self._additional_imports.append(IMPORT_CONFIG_DICT)

    @property
    def imports(self) -> tuple[Import, ...]:
        """Get imports after syncing RootModel config template data."""
        self._sync_config_template_data()
        return super().imports

    def render(self, *, class_name: str | None = None) -> str:
        """Render the RootModel after syncing config template data."""
        self._sync_config_template_data()
        return super().render(class_name=class_name)
