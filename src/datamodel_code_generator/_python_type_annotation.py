"""Internal transport codec for structured Python type annotations."""

from __future__ import annotations

import ast
import keyword
import sys
from typing import TYPE_CHECKING, NamedTuple

from typing_extensions import Self

if TYPE_CHECKING:
    from enum import Enum

PYTHON_LITERAL_ENUM_MEMBER_MARKER = "__datamodel_code_generator_literal_enum_member__"
_MISSING_ATTRIBUTE = object()


def _is_python_identifier(value: str) -> bool:
    return value.isidentifier() and not keyword.iskeyword(value)


def _not_importable_error(module: str, qualname: str, member: str | None) -> ValueError:
    return ValueError(f"Literal enum member is not importable: {module}.{qualname}.{member}")


class LiteralEnumMemberRef(NamedTuple):
    """Importable identity of one enum member transported through JSON Schema."""

    module: str
    qualname_parts: tuple[str, ...]
    member: str

    @classmethod
    def from_enum(cls, value: Enum) -> Self:
        """Build a reference only when the runtime enum is importable by its identity."""
        enum_type = type(value)
        reference = cls._from_parts(enum_type.__module__, enum_type.__qualname__, value.name)
        target: object = sys.modules.get(reference.module, _MISSING_ATTRIBUTE)
        for part in reference.qualname_parts:
            if target is _MISSING_ATTRIBUTE:
                break
            target = getattr(target, "__dict__", {}).get(part, _MISSING_ATTRIBUTE)
        if target is not enum_type:
            raise _not_importable_error(
                reference.module,
                ".".join(reference.qualname_parts),
                reference.member,
            )
        return reference

    @classmethod
    def from_marker_ast(cls, node: ast.Subscript) -> Self | None:
        """Decode the reserved marker, returning None for an ordinary subscript."""
        if not isinstance(node.value, ast.Name) or node.value.id != PYTHON_LITERAL_ENUM_MEMBER_MARKER:
            return None
        match node.slice:
            case ast.Tuple(
                elts=[
                    ast.Constant(value=str() as module),
                    ast.Constant(value=str() as qualname),
                    ast.Constant(value=str() as member),
                ]
            ):
                return cls._from_parts(module, qualname, member)

        msg = "Invalid internal Literal enum member marker"
        raise ValueError(msg)

    @classmethod
    def _from_parts(cls, module: str, qualname: str, member: str | None) -> Self:
        if member is None:
            raise _not_importable_error(module, qualname, member)

        module_parts = module.split(".")
        qualname_parts = qualname.split(".")
        if (
            not module
            or not qualname
            or not all(map(_is_python_identifier, module_parts))
            or not all(map(_is_python_identifier, qualname_parts))
            or not _is_python_identifier(member)
        ):
            raise _not_importable_error(module, qualname, member)
        return cls(module, tuple(qualname_parts), member)

    @property
    def import_path(self) -> str:
        """Return the import path for the outermost enum container."""
        return f"{self.module}.{self.qualname_parts[0]}"

    def to_marker_text(self) -> str:
        """Encode this reference at the existing x-python-type string boundary."""
        qualname = ".".join(self.qualname_parts)
        return f"{PYTHON_LITERAL_ENUM_MEMBER_MARKER}[{self.module!r}, {qualname!r}, {self.member!r}]"

    def to_member_expression(self) -> ast.expr:
        """Build the exact nested enum member access expression."""
        module_root, *module_attrs = self.module.split(".")
        expression: ast.expr = ast.Name(id=module_root, ctx=ast.Load())
        for attr in (*module_attrs, *self.qualname_parts, self.member):
            expression = ast.Attribute(value=expression, attr=attr, ctx=ast.Load())
        return expression


def encode_literal_enum_member(value: Enum) -> str:
    """Encode a runtime enum member at the existing x-python-type boundary."""
    return LiteralEnumMemberRef.from_enum(value).to_marker_text()
