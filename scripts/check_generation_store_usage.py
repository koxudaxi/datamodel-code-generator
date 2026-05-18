"""Reject parser mutations that bypass GenerationStore."""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from datamodel_code_generator.parser.generation import GENERATION_STORE_MUTATION_METHODS  # noqa: E402

DEFAULT_TARGET = Path("src/datamodel_code_generator/parser")
GENERATION_STORE_MODULE = Path("src/datamodel_code_generator/parser/generation.py")

MUTATION_ATTRIBUTES = frozenset({"base_classes", "data_type", "fields", "reference"})
MODEL_COLLECTION_ATTRIBUTES = frozenset({"models", "results"})
MODEL_COLLECTION_HELPERS = {"append": "register_model"}
REFERENCE_METHODS = frozenset(
    {
        "_invalidate_after_mutation",
        "_refresh_after_mutation",
        "remove_reference",
        "replace_children_in_models",
        "replace_children_references",
        "replace_data_type",
        "replace_reference",
        "refresh_after_mutation",
        "set_reference_path",
    },
)
SEQUENCE_MUTATORS = frozenset({"append", "clear", "extend", "insert", "pop", "remove"})
SequenceOwner: TypeAlias = str


@dataclass(frozen=True)
class Violation:
    """A direct parser mutation that should go through GenerationStore."""

    path: Path
    line: int
    column: int
    message: str

    def format(self) -> str:
        """Format violation for CLI output."""
        return f"{self.path}:{self.line}:{self.column}: {self.message}"


def _attribute_chain(node: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        names.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        names.append(current.id)
    names.reverse()
    return tuple(names)


def _sequence_owner(node: ast.AST) -> SequenceOwner | None:
    if isinstance(node, ast.Attribute) and node.attr in {"base_classes", "fields", *MODEL_COLLECTION_ATTRIBUTES}:
        return node.attr
    if isinstance(node, ast.Subscript):
        return _sequence_owner(node.value)
    return None


class GenerationStoreUsageVisitor(ast.NodeVisitor):
    """AST visitor for parser code that must use GenerationStore mutation APIs."""

    def __init__(self, path: Path) -> None:
        """Create a visitor for ``path``."""
        self.path = path
        self.violations: list[Violation] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check assignment targets."""
        for target in node.targets:
            self._check_assignment_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check annotated assignment targets."""
        self._check_assignment_target(node.target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Check augmented assignment targets."""
        self._check_assignment_target(node.target)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check direct mutating method calls."""
        if isinstance(node.func, ast.Attribute):
            method = node.func.attr
            owner = _sequence_owner(node.func.value)
            if owner and method in SEQUENCE_MUTATORS:
                self._add(
                    node,
                    f"use GenerationStore.{self._sequence_helper(owner, method)}() instead of mutating {owner}",
                )
            elif method in REFERENCE_METHODS:
                self._add(node, f"use GenerationStore API instead of {method}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check direct ``Reference.children`` reads."""
        if node.attr == "children" and isinstance(node.ctx, ast.Load):
            self._add(node, "use GenerationIndex reverse-edge queries instead of Reference.children")
        self.generic_visit(node)

    def _check_assignment_target(self, target: ast.AST) -> None:
        owner = _sequence_owner(target)
        if owner:
            helper = self._sequence_helper(owner, "assign")
            self._add(target, f"use GenerationStore.{helper}() instead of assigning {owner}")
            return

        if not isinstance(target, ast.Attribute):
            return

        chain = _attribute_chain(target)
        if not chain:
            return

        if target.attr in MUTATION_ATTRIBUTES or (
            isinstance(target.value, ast.Attribute) and target.value.attr == "reference"
        ):
            self._add(target, f"use GenerationStore API instead of assigning {'.'.join(chain[-2:])}")

    def _add(self, node: ast.AST, message: str) -> None:
        self.violations.append(
            Violation(
                path=self.path,
                line=getattr(node, "lineno", 0),
                column=getattr(node, "col_offset", 0) + 1,
                message=message,
            )
        )

    @staticmethod
    def _sequence_helper(owner: SequenceOwner, method: str) -> str:
        if owner in MODEL_COLLECTION_ATTRIBUTES:
            helper = MODEL_COLLECTION_HELPERS.get(method, "register_model")
            return _ensure_generation_store_api(helper)
        if owner == "fields":
            helper = {
                "assign": "set_fields",
                "append": "append_field",
                "insert": "insert_field",
                "remove": "remove_field",
            }.get(method, "set_fields")
            return _ensure_generation_store_api(helper)
        return _ensure_generation_store_api("set_base_classes")


def _ensure_generation_store_api(method_name: str) -> str:
    if method_name not in GENERATION_STORE_MUTATION_METHODS:
        msg = f"{method_name!r} is not a registered GenerationStore mutation API"
        raise RuntimeError(msg)
    return method_name


def iter_python_files(paths: list[Path]) -> list[Path]:
    """Return checked Python files below ``paths``."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.suffix == ".py":
            files.append(path)
    generation_store_module = GENERATION_STORE_MODULE.resolve()
    return [path for path in files if path.resolve() != generation_store_module]


def check_paths(paths: list[Path]) -> list[Violation]:
    """Check paths and return all GenerationStore usage violations."""
    violations: list[Violation] = []
    for path in iter_python_files(paths):
        tree = ast.parse(path.read_text(), filename=str(path))
        visitor = GenerationStoreUsageVisitor(path)
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return violations


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_TARGET])
    args = parser.parse_args(argv)

    violations = check_paths(args.paths)
    if violations:
        print("GenerationStore usage violations found:", file=sys.stderr)
        for violation in violations:
            print(violation.format(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
