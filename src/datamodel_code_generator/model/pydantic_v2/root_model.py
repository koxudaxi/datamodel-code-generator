"""Pydantic v2 RootModel implementation.

Generates models inheriting from pydantic.RootModel for wrapping single types.
"""

from __future__ import annotations

from typing import Any, ClassVar

from datamodel_code_generator import Error
from datamodel_code_generator.imports import IMPORT_ANY, Import
from datamodel_code_generator.model.pydantic_v2.base_model import (
    _CONFIG_ITEMS_TEMPLATE_DATA_KEY,
    BaseModel,
    _config_dict_items,
    _safe_config_dict_items,
)
from datamodel_code_generator.model.pydantic_v2.imports import IMPORT_CONFIG_DICT

IMPORT_ABC_ITERATOR = Import.from_full_path("collections.abc.Iterator")
IMPORT_ABC_SEQUENCE = Import.from_full_path("collections.abc.Sequence")
IMPORT_OVERLOAD = Import.from_full_path("typing.overload")
IMPORT_SUPPORTS_INDEX = Import.from_full_path("typing.SupportsIndex")
_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY = "sequence_base_class"
_SEQUENCE_ITEM_TYPE_TEMPLATE_DATA_KEY = "sequence_item_type"
_SEQUENCE_SLICE_TYPE_TEMPLATE_DATA_KEY = "sequence_slice_type"
_ROOT_MODEL_CONFIG_KEYS: frozenset[str] = frozenset({"regex_engine", "frozen"})


def _root_model_config_items(config: Any) -> list[tuple[str, Any]]:
    return [
        (field_name, value)
        for field_name, value in _config_dict_items(config)
        if field_name in _ROOT_MODEL_CONFIG_KEYS and value is not None
    ]


class RootModel(BaseModel):
    """DataModel for Pydantic v2 RootModel."""

    TEMPLATE_FILE_PATH: ClassVar[str] = "pydantic_v2/RootModel.jinja2"
    BASE_CLASS: ClassVar[str] = "pydantic.RootModel"
    IS_ROOT_MODEL: ClassVar[bool] = True
    REQUIRES_FIELD_DEPENDENCY_ORDERING: ClassVar[bool] = True
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

        if not self._has_meaningful_config(self.extra_template_data.get("config")):
            self.extra_template_data.pop("config", None)
            self._pop_internal_template_data(_CONFIG_ITEMS_TEMPLATE_DATA_KEY)
            self._additional_imports = [imp for imp in self._additional_imports if imp != IMPORT_CONFIG_DICT]

    @staticmethod
    def _has_meaningful_config(config: Any) -> bool:
        has_config = False
        match config:
            case None:
                pass
            case _:
                has_config = bool(_root_model_config_items(config))
        return has_config

    def _sync_config_items(self) -> None:
        config = self.extra_template_data.get("config")
        if config_items := _root_model_config_items(config):
            self._set_internal_template_data(
                _CONFIG_ITEMS_TEMPLATE_DATA_KEY,
                _safe_config_dict_items(dict(config_items)),
            )
            if IMPORT_CONFIG_DICT not in self._additional_imports:
                self._additional_imports.append(IMPORT_CONFIG_DICT)
            self.clear_imports_cache()
            return
        self.extra_template_data.pop("config", None)
        self._pop_internal_template_data(_CONFIG_ITEMS_TEMPLATE_DATA_KEY)
        self._additional_imports = [imp for imp in self._additional_imports if imp != IMPORT_CONFIG_DICT]
        self.clear_imports_cache()

    def add_sequence_interface(self, item_type: str, slice_type: str) -> None:
        """Add sequence interface helpers that delegate to the wrapped root value."""
        self._additional_imports.append(IMPORT_ABC_ITERATOR)
        self._additional_imports.append(IMPORT_ABC_SEQUENCE)
        self._additional_imports.append(IMPORT_OVERLOAD)
        self._additional_imports.append(IMPORT_SUPPORTS_INDEX)
        if item_type == "Any":
            self._additional_imports.append(IMPORT_ANY)
        sequence_template_data = {
            _SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY: f"Sequence[{item_type}]",
            _SEQUENCE_ITEM_TYPE_TEMPLATE_DATA_KEY: item_type,
            _SEQUENCE_SLICE_TYPE_TEMPLATE_DATA_KEY: slice_type,
        }
        for key, value in sequence_template_data.items():
            self._set_internal_template_data(key, value)
        self.clear_imports_cache()

    def render(self, *, class_name: str | None = None) -> str:
        """Render the RootModel and validate custom sequence templates when needed."""
        use_custom_template = self._uses_custom_root_template
        fields = self._template_fields(use_custom_template=use_custom_template)
        if fields:
            _ = fields[0].type_hint
        self._sync_config_items()
        extra_template_data = self._custom_template_data() if use_custom_template else self._builtin_template_data()
        rendered = self._render(
            class_name=class_name or self.class_name,
            fields=fields,
            decorators=self.decorators,
            base_class=self.base_class,
            methods=self.methods,
            description=self._template_description(use_custom_template=use_custom_template),
            dataclass_arguments=self.dataclass_arguments,
            path=self.path,
            **extra_template_data,
        )
        self._validate_custom_template_sequence_interface(rendered)
        return rendered

    def _validate_custom_template_sequence_interface(self, rendered: str) -> None:
        sequence_base_class = self._internal_template_data.get(_SEQUENCE_BASE_CLASS_TEMPLATE_DATA_KEY)
        if not self._uses_custom_root_template or not sequence_base_class:
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
