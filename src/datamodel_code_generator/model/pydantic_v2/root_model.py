"""Pydantic v2 RootModel implementation.

Generates models inheriting from pydantic.RootModel for wrapping single types.
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_CONFIG_DICT


class RootModel(BaseModel):
    """DataModel for Pydantic v2 RootModel."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/RootModel.jinja2"
    BASE_CLASS: ClassVar[str] = "pydantic.RootModel"

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
            self._additional_imports = [imp for imp in self._additional_imports if imp != IMPORT_CONFIG_DICT]

    def _get_config_extra(self) -> Literal["'allow'", "'forbid'"] | None:  # noqa: PLR6301
        # PydanticV2 RootModels cannot have extra fields
        return None
