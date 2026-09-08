"""Check generated value models used by requested unique-item set conversions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from datamodel_code_generator import Error
from datamodel_code_generator.model.base import TEMPLATE_DIR, DataModel, get_effective_fields
from datamodel_code_generator.model.enum import Enum

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from datamodel_code_generator._python_type_binding import BoundPythonType
    from datamodel_code_generator.types import DataType


class SetItemValidator:
    """Inspect reachable generated fields without importing external Python types."""

    def __init__(self, custom_template_dir: Path | None = None) -> None:
        self._uses_builtin_template_dir = (
            custom_template_dir is not None and custom_template_dir.resolve() == TEMPLATE_DIR.resolve()
        )
        self.safe_models: set[str] = set()
        self.frozen_models: dict[str, bool] = {}
        self.safe_fields: set[str] = set()
        self.native_hash_models: set[str] = set()

    def validate(self, data_type: DataType, owner: str) -> None:
        """Reject a known generated object whose value hash cannot be guaranteed."""
        if not data_type.reference and not data_type.data_types and not self._is_unhashable_container(data_type):
            return
        pending = [(data_type, False)]
        visited: set[str] = set()
        while pending:
            current, in_model = pending.pop()
            if self._is_unhashable_container(current, in_model=in_model):
                self._reject(owner, current.type_hint)
            if current.reference and isinstance(model := current.reference.source, DataModel):
                if isinstance(model, Enum) or (
                    model.reference.path in self.safe_models or model.reference.path in visited
                ):
                    continue
                if model.is_alias:
                    visited.add(model.reference.path)
                    pending.extend((field.data_type, in_model) for field in model.fields)
                    continue
                if (
                    model.custom_base_class
                    or (model._uses_custom_root_template and not self._uses_builtin_template_dir)  # noqa: SLF001
                    or not type(model).__module__.startswith("datamodel_code_generator.model.")
                ):
                    continue
                visited.add(model.reference.path)
                if not self._is_frozen(model):
                    self._reject(owner, model.name)
                pending.extend((field_type, True) for field_type in self._field_types(model))
            elif in_model and current.type == "Any" and not current.data_types:
                self._reject(owner, "Any")
            else:
                pending.extend((child, in_model) for child in current.data_types)
        self.safe_models.update(visited)

    def has_native_pydantic_hash(self, model: DataModel) -> bool:
        """Preserve proven native frozen hashes for explicitly declared model sets."""
        from datamodel_code_generator.model.pydantic_v2 import (  # ruff: ignore[import-outside-top-level]
            BaseModel,
            RootModel,
        )

        field_inspector = SetItemValidator()
        pending = [model]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            path = current.reference.path
            if path in self.native_hash_models or path in visited:
                continue
            if (
                type(current) not in {BaseModel, RootModel}
                or current.methods
                or current.decorators
                or current.extra_template_data.get("validators")
            ):
                return False
            if (
                current.custom_base_class
                or (current._custom_template_dir and not self._uses_builtin_template_dir)  # ruff: ignore[private-member-access]
                or not self._is_frozen(current)
            ):
                return False
            visited.add(path)
            pending.extend(
                source
                for parent in current.base_classes
                if parent.reference and isinstance(source := parent.reference.source, DataModel)
            )
            for field_type in field_inspector._field_types(current):
                for data_type in field_type.all_data_types:
                    if self._is_unhashable_container(data_type, in_model=True):
                        return False
                    if data_type.reference:
                        source = data_type.reference.source
                        if isinstance(source, Enum):
                            continue
                        if not isinstance(source, DataModel):
                            return False
                        pending.append(source)
                    elif (
                        not data_type.data_types
                        and not data_type.literals
                        and (
                            data_type.python_type
                            or data_type.import_
                            or data_type.type not in {"str", "int", "float", "bool", "bytes", "None"}
                        )
                    ):
                        return False
        self.native_hash_models.update(visited)
        return True

    def _field_types(self, model: DataModel) -> Iterator[DataType]:
        if model.reference.path in self.safe_fields:
            return
        if model.TEMPLATE_FILE_PATH == "msgspec.jinja2":
            yield from self._struct_field_types(model)
            return
        seen_fields: set[str | None] = set()
        seen_bases: set[str] = set()
        bases = [model]
        complete_ancestry = True
        while bases:
            base = bases.pop()
            if base.reference.path in seen_bases or (
                not bases and base is not model and base.reference.path in self.safe_fields
            ):
                continue
            seen_bases.add(base.reference.path)
            for field in base.fields:
                if field.name in seen_fields:
                    data_type = field.data_type
                    if not self._is_plain_hashable(data_type):
                        complete_ancestry = False
                else:
                    seen_fields.add(field.name)
                    if field.is_class_var or (
                        model.TEMPLATE_FILE_PATH == "dataclass.jinja2"
                        and (
                            field.extras.get("hash") is False
                            or (field.extras.get("hash") is None and field.extras.get("compare") is False)
                        )
                    ):
                        continue
                    yield field.data_type
            bases.extend(
                source
                for parent in reversed(base.base_classes)
                if parent.reference and isinstance(source := parent.reference.source, DataModel)
            )
        self.safe_fields.add(model.reference.path)
        if complete_ancestry:
            self.safe_fields.update(seen_bases)

    def _struct_field_types(self, model: DataModel) -> Iterator[DataType]:
        fields_by_name = {}
        visited: set[str] = set()
        pending = [model]
        ambiguous = False
        if all(not base.reference or base.reference.path in self.safe_fields for base in model.base_classes):
            fields_by_name.update((field.name, field) for field in model.fields)
            visited.add(model.reference.path)
            pending.clear()
        while pending:
            current = pending.pop()
            if current.reference.path in visited:
                continue
            visited.add(current.reference.path)
            for field in current.fields:
                if (previous := fields_by_name.get(field.name)) is not None:
                    ambiguous = ambiguous or not (
                        self._is_plain_hashable(previous.data_type) and self._is_plain_hashable(field.data_type)
                    )
                else:
                    fields_by_name[field.name] = field
            pending.extend(
                source
                for parent in current.base_classes
                if parent.reference and isinstance(source := parent.reference.source, DataModel)
            )
        fields = get_effective_fields(model) if ambiguous else fields_by_name.values()
        for field in fields:
            if not field.is_class_var:
                yield field.data_type
        self.safe_fields.add(model.reference.path)
        if not ambiguous:
            self.safe_fields.update(visited)

    def _is_plain_hashable(self, data_type: DataType) -> bool:
        return (
            not data_type.reference
            and not data_type.data_types
            and not self._is_unhashable_container(data_type, in_model=True)
            and data_type.type != "Any"
        )

    def _is_frozen(self, model: DataModel) -> bool:
        if model.USES_DATACLASS_ARGUMENTS:
            return model.dataclass_arguments.get("frozen") is True
        if model.TEMPLATE_FILE_PATH != "msgspec.jinja2" and not model.TEMPLATE_FILE_PATH.startswith("pydantic_v2/"):
            return False
        pending = [model]
        visited: set[str] = set()
        single_lineage = True
        while pending:
            current = pending.pop()
            path = current.reference.path
            if path in visited:
                continue
            visited.add(path)
            if path in self.frozen_models:
                frozen = self.frozen_models[path]
                break
            config = (
                current.extra_template_data.get("base_class_kwargs", {})
                if current.TEMPLATE_FILE_PATH == "msgspec.jinja2"
                else current.extra_template_data.get("config")
            )
            value = config.get("frozen") if isinstance(config, dict) else getattr(config, "frozen", None)
            if value is not None:
                frozen = value is True or value == "True"
                break
            parents = (
                current.base_classes[:1] if current.TEMPLATE_FILE_PATH == "msgspec.jinja2" else current.base_classes
            )
            single_lineage = single_lineage and len(parents) <= 1
            pending.extend(
                source
                for parent in parents
                if parent.reference and isinstance(source := parent.reference.source, DataModel)
            )
        else:
            frozen = False
        for path in visited if single_lineage else (model.reference.path,):
            self.frozen_models[path] = frozen
        return frozen

    @staticmethod
    def _is_unhashable_container(data_type: DataType, *, in_model: bool = False) -> bool:
        mutable_sequence = data_type.is_list or data_type.is_sequence
        if (
            data_type.is_dict
            or data_type.is_mapping
            or mutable_sequence
            or (data_type.is_set and not data_type.use_generic_container)
        ):
            return True
        return bool(
            data_type.python_type
            and SetItemValidator._has_unhashable_python_type(data_type.python_type, in_model=in_model)
        )

    @staticmethod
    def _has_unhashable_python_type(bound_type: BoundPythonType, *, in_model: bool) -> bool:
        from datamodel_code_generator._python_type_annotation import (  # noqa: PLC0415
            PythonTypeBoundName,
            PythonTypeName,
            PythonTypeSubscript,
            PythonTypeUnion,
        )

        pending = [bound_type.expression]
        while pending:
            expression = pending.pop()
            if isinstance(expression, PythonTypeUnion):
                pending.extend(expression.items)
                continue
            arguments = ()
            if isinstance(expression, PythonTypeSubscript):
                arguments = expression.arguments
                expression = expression.base
            match expression:
                case PythonTypeBoundName(import_from=module, import_name=name):
                    pass
                case PythonTypeName(value=name):
                    module = "builtins"
                case _:
                    continue
            match module, name:
                case "typing", "Any" if in_model:
                    return True
                case (
                    ("builtins", "list" | "dict" | "set" | "bytearray")
                    | ("collections", "deque" | "defaultdict" | "OrderedDict" | "Counter" | "ChainMap")
                    | (
                        "typing" | "collections.abc",
                        "List"
                        | "Dict"
                        | "Set"
                        | "Deque"
                        | "Mapping"
                        | "MutableMapping"
                        | "Sequence"
                        | "MutableSequence"
                        | "MutableSet",
                    )
                ):
                    return True
                case ("typing", "Optional" | "Union" | "Tuple" | "FrozenSet") | ("builtins", "tuple" | "frozenset"):
                    pending.extend(arguments)
                case "typing", "Annotated":
                    pending.extend(arguments[:1])
        return False

    @staticmethod
    def _reject(owner: str, item: str) -> None:
        msg = (
            f"Cannot convert uniqueItems field {owner!r} to a set: {item!r} does not have a statically safe "
            "value hash. Disable --use-unique-items-as-set or use an explicitly frozen model with hashable fields."
        )
        raise Error(msg)
