"""Bind colliding class-scope annotation and field-helper names."""

from __future__ import annotations

import ast
from itertools import accumulate
from typing import TYPE_CHECKING, Any, cast

from datamodel_code_generator.imports import Import
from datamodel_code_generator.reference import ModelType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from datamodel_code_generator.imports import Imports
    from datamodel_code_generator.model.base import DataModel


_EXPRESSION_ATTRIBUTES = ("type_hint", "base_type_hint", "annotated", "field", "represented_default")
_SHADOWABLE_IMPORTS = (
    Import(from_="builtins", import_="list"),
    Import(from_="typing", import_="Optional"),
    Import(from_="pydantic", import_="Field"),
)


def _expression_names(expression: ast.AST) -> set[str]:
    """Find unqualified loads without treating literal or keyword text as bindings."""
    return {node.id for node in ast.walk(expression) if isinstance(node, ast.Name)}


def _bind_expression(expression: str, bindings: dict[str, str]) -> str:
    """Replace bound name spans while preserving every other source byte."""
    source = expression.encode()
    offsets = [0, *accumulate(map(len, source.splitlines(keepends=True)))]
    replacements = [
        (
            offsets[node.lineno - 1] + node.col_offset,
            offsets[cast("int", node.end_lineno) - 1] + cast("int", node.end_col_offset),
            bindings[node.id],
        )
        for node in ast.walk(ast.parse(expression, mode="eval"))
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in bindings
    ]
    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement.encode() + source[end:]
    return source.decode()


class _BoundFieldExpressions:
    """Expose bound syntax while delegating all field metadata unchanged."""

    def __init__(self, field: Any, bindings: dict[str, str]) -> None:
        self._field = field
        self._bindings = bindings

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._field, name)
        if name in _EXPRESSION_ATTRIBUTES and isinstance(value, str) and value:
            value = _bind_expression(value, self._bindings)
        self.__dict__[name] = value
        return value


def bind_field_views(fields: Sequence[Any], bindings: dict[str, str]) -> list[_BoundFieldExpressions]:
    """Wrap generated syntax only for a module with a proven name collision."""
    return [_BoundFieldExpressions(field, bindings) for field in fields]


def bind_module_field_names(models: list[DataModel], imports: Imports) -> None:
    """Allocate aliases only where a property hides an emitted expression name."""
    shadowable_imports = tuple(
        import_
        for import_ in _SHADOWABLE_IMPORTS
        if import_.from_ == "builtins" or import_.import_ in imports.get(import_.from_, ())
    )
    collisions: set[str] = set()
    reserved_names = {model.class_name for model in models}
    for model in models:
        field_names = {field.name for field in model.fields if field.name is not None}
        reserved_names.update(field_names)
        candidates = field_names.intersection(import_.import_ for import_ in shadowable_imports)
        if not candidates:
            continue
        class_body = next(
            (
                node.body
                for node in ast.parse(model.render()).body
                if isinstance(node, ast.ClassDef) and node.name == model.class_name
            ),
            None,
        )
        if class_body is None:
            continue
        fields = [
            (node.target.id, node)
            for node in class_body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        ]
        # Struct creates slot descriptors even for fields without a default assignment.
        assigned_names = (
            field_names
            if model.FIELD_NAME_MODEL_TYPE is ModelType.MSGSPEC
            else {name for name, node in fields if node.value is not None}
        )
        candidates.intersection_update(assigned_names)
        previous_names: set[str] = set()
        for name, node in fields:
            collisions.update(candidates.intersection(_expression_names(node.annotation)))
            if node.value is not None:
                collisions.update(candidates.intersection(previous_names, _expression_names(node.value)))
                previous_names.add(name)
    if not collisions:
        return
    reserved_names.update(imports.get_effective_name(from_, name) for from_, names in imports.items() for name in names)
    bindings: dict[str, str] = {}
    for import_ in shadowable_imports:
        if import_.import_ not in collisions:
            continue
        alias = f"{import_.import_}_aliased"
        suffix = 1
        while alias in reserved_names:
            alias = f"{import_.import_}_aliased_{suffix}"
            suffix += 1
        reserved_names.add(alias)
        aliased_import = Import(from_=import_.from_, import_=import_.import_, alias=alias)
        bindings[import_.import_] = alias
        if import_.from_ == "builtins":
            imports.append(aliased_import)
        else:
            imports.apply_alias(aliased_import)
    for model in models:
        model.__dict__["_field_name_bindings"] = bindings
        model.invalidate_render_caches()
