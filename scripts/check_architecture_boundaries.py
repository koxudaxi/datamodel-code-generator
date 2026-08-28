"""Reject cross-layer dependencies that bypass declared architecture capabilities."""

from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src" / "datamodel_code_generator"

Layer: TypeAlias = Literal["parser", "config", "input-model", "shared"]

CONCRETE_BACKEND_ROOTS: Final = frozenset({
    "dataclass",
    "msgspec",
    "pydantic_base",
    "pydantic_v2",
    "typed_dict",
})
PARSER_BACKEND_ATTRIBUTES: Final = frozenset({
    "SCHEMA_RUNTIME_VALIDATION_HELPERS_TEMPLATE_FILE_PATH",
    "is_pydantic_extra_field",
})
_BACKEND_MODULE_PART_COUNT: Final = 3


@dataclass(frozen=True, order=True)
class BoundaryKey:
    """Stable allowlist identity independent from source line movement."""

    path: str
    qualname: str
    rule: str
    target: str


@dataclass(frozen=True)
class AllowlistEntry:
    """Document a bounded legacy dependency while preventing new copies."""

    reason: str
    count: int = 1

    def __post_init__(self) -> None:
        """Reject entries that cannot explain or bound legacy debt."""
        if not self.reason.strip():
            msg = "architecture boundary allowlist entries require a reason"
            raise ValueError(msg)
        if self.count < 1:
            msg = "architecture boundary allowlist counts must be positive"
            raise ValueError(msg)


@dataclass(frozen=True)
class Violation:
    """One actionable architecture boundary violation."""

    path: str
    line: int
    column: int
    qualname: str
    rule: str
    target: str
    message: str

    @property
    def key(self) -> BoundaryKey:
        """Stable allowlist identity for this violation."""
        return BoundaryKey(self.path, self.qualname, self.rule, self.target)

    def format(self) -> str:
        """Format a compiler-style error with a concrete remediation."""
        return (
            f"{self.path}:{self.line}:{self.column}: [{self.rule}] {self.target}: {self.message} (in {self.qualname})"
        )


DEFAULT_ALLOWLIST: Final[dict[BoundaryKey, AllowlistEntry]] = {
    BoundaryKey(
        "src/datamodel_code_generator/config.py",
        "<module>",
        "config-backend-import",
        "datamodel_code_generator.model.pydantic_v2",
    ): AllowlistEntry("ParserConfig keeps its historical concrete default types until a separate public-API migration"),
    BoundaryKey(
        "src/datamodel_code_generator/config.py",
        "ParserConfig",
        "config-backend-reference",
        "datamodel_code_generator.model.pydantic_v2.BaseModel",
    ): AllowlistEntry("Preserve the public ParserConfig default model class"),
    BoundaryKey(
        "src/datamodel_code_generator/config.py",
        "ParserConfig",
        "config-backend-reference",
        "datamodel_code_generator.model.pydantic_v2.RootModel",
    ): AllowlistEntry("Preserve the public ParserConfig default root model class"),
    BoundaryKey(
        "src/datamodel_code_generator/config.py",
        "ParserConfig",
        "config-backend-reference",
        "datamodel_code_generator.model.pydantic_v2.DataTypeManager",
    ): AllowlistEntry("Preserve the public ParserConfig default type manager"),
    BoundaryKey(
        "src/datamodel_code_generator/config.py",
        "ParserConfig",
        "config-backend-reference",
        "datamodel_code_generator.model.pydantic_v2.DataModelField",
    ): AllowlistEntry("Preserve the public ParserConfig default field model"),
    BoundaryKey(
        "src/datamodel_code_generator/parser/base.py",
        "_is_pydantic_v2_data_model_field",
        "backend-module-identity",
        "datamodel_code_generator.model.pydantic_v2.base_model#DataModelField",
    ): AllowlistEntry("Keep the production-unused private compatibility helper without eager backend imports"),
    BoundaryKey(
        "src/datamodel_code_generator/parser/base.py",
        "__getattr__",
        "backend-import",
        "datamodel_code_generator.model.dataclass",
    ): AllowlistEntry("Keep the lazy legacy parser.base.dataclass_model compatibility export"),
    BoundaryKey(
        "src/datamodel_code_generator/parser/base.py",
        "__getattr__",
        "backend-import",
        "datamodel_code_generator.model.msgspec",
    ): AllowlistEntry("Keep the lazy legacy parser.base.msgspec_model compatibility export"),
    BoundaryKey(
        "src/datamodel_code_generator/parser/jsonschema.py",
        "__getattr__",
        "backend-import",
        "datamodel_code_generator.model.typed_dict",
    ): AllowlistEntry("Keep the lazy legacy parser.jsonschema.TypedDictModel compatibility export"),
    BoundaryKey(
        "src/datamodel_code_generator/parser/jsonschema.py",
        "JsonSchemaParser._get_runtime_validation_root_model_type",
        "backend-import",
        "datamodel_code_generator.model.pydantic_v2.root_model",
    ): AllowlistEntry("Keep the lazy executable RootModel fallback for runtime validators on alias outputs"),
}


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _module_name(path: Path, layer: Layer) -> str:
    try:
        relative = path.resolve().relative_to(SOURCE_ROOT)
    except ValueError:
        return {
            "parser": "datamodel_code_generator.parser.fixture",
            "config": "datamodel_code_generator.config_fixture",
            "input-model": "datamodel_code_generator.input_model_fixture",
            "shared": "datamodel_code_generator.shared_fixture",
        }[layer]

    parts = ["datamodel_code_generator", *relative.with_suffix("").parts]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _normalize_import(module: str | None, level: int, current_module: str, path: Path) -> str:
    if level == 0:
        return module or ""

    module_parts = current_module.split(".")
    package_parts = module_parts if path.name == "__init__.py" else module_parts[:-1]
    keep = max(0, len(package_parts) - level + 1)
    return ".".join((*package_parts[:keep], *((module or "").split(".") if module else ())))


def _concrete_backend_module(target: str) -> str | None:
    parts = target.split(".")
    prefix = ["datamodel_code_generator", "model"]
    if parts[:2] != prefix or len(parts) < _BACKEND_MODULE_PART_COUNT or parts[2] not in CONCRETE_BACKEND_ROOTS:
        return None
    return ".".join((*prefix, parts[2]))


def _attribute_chain(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    parts.reverse()
    return tuple(parts)


class ArchitectureBoundaryVisitor(ast.NodeVisitor):
    """Find forbidden imports and semantic backend inspection for one layer."""

    def __init__(self, path: Path, layer: Layer, tree: ast.Module) -> None:
        """Create a visitor and collect conservative module string constants."""
        self.path = path
        self.display_path = _display_path(path)
        self.layer = layer
        self.current_module = _module_name(path, layer)
        self.qualnames: list[str] = []
        self.violations: list[Violation] = []
        self.backend_aliases: dict[str, str] = {}
        self.data_model_type_aliases = {"DataModelType"}
        self.string_constants = self._collect_string_constants(tree)

    @staticmethod
    def _collect_string_constants(tree: ast.Module) -> dict[str, str]:
        constants: dict[str, str] = {}
        for node in tree.body:
            match node:
                case ast.Assign(targets=[ast.Name(id=name)], value=ast.Constant(value=str() as value)):
                    constants[name] = value
                case ast.AnnAssign(target=ast.Name(id=name), value=ast.Constant(value=str() as value)):
                    constants[name] = value
        return constants

    @property
    def qualname(self) -> str:
        """Current enclosing symbol."""
        return ".".join(self.qualnames) or "<module>"

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context for stable allowlist entries."""
        self.qualnames.append(node.name)
        self.generic_visit(node)
        self.qualnames.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function context for stable allowlist entries."""
        self.qualnames.append(node.name)
        self.generic_visit(node)
        self.qualnames.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function context for stable allowlist entries."""
        self.qualnames.append(node.name)
        self.generic_visit(node)
        self.qualnames.pop()

    def visit_Import(self, node: ast.Import) -> None:
        """Check direct absolute backend and private-parser imports."""
        for alias in node.names:
            self._record_import_alias(alias.asname or alias.name.partition(".")[0], alias.name)
            self._check_import(node, alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check absolute, relative, and package-root import forms."""
        module = _normalize_import(node.module, node.level, self.current_module, self.path)
        for alias in node.names:
            target = f"{module}.{alias.name}" if module else alias.name
            if (
                module in {"datamodel_code_generator", "datamodel_code_generator.enums"}
                and alias.name == "DataModelType"
            ):
                self.data_model_type_aliases.add(alias.asname or alias.name)
            if module == "datamodel_code_generator.model" and alias.name in CONCRETE_BACKEND_ROOTS:
                self._record_import_alias(alias.asname or alias.name, target)
                self._check_import(node, target)
                continue
            self._record_import_alias(alias.asname or alias.name, module)
            self._check_import(node, module)

    def visit_Call(self, node: ast.Call) -> None:
        """Check dynamic imports, semantic getattr, and backend module identity helpers."""
        chain = _attribute_chain(node.func)
        dynamic_target = None
        match self.layer, chain[-1:], node.args:
            case ("parser" | "config", ("__import__" | "import_module",), [first_argument, *_]):
                dynamic_target = self._resolved_string(first_argument)
            case _:
                pass
        if dynamic_target and _concrete_backend_module(dynamic_target):
            self._add(
                node,
                "backend-dynamic-import",
                dynamic_target,
                "parser/config layers must not dynamically import output backends; declare a neutral capability",
            )

        if (
            chain
            and chain[-1] in {"getattr", "hasattr"}
            and len(node.args) > 1
            and (
                self.layer == "parser"
                and (attribute := self._resolved_string(node.args[1])) in PARSER_BACKEND_ATTRIBUTES
            )
        ):
            self._add(
                node,
                "backend-semantic-inspection",
                attribute,
                "parser code must query a neutral DataModel or DataModelFieldBase capability",
            )

        module_keyword = next((keyword.value for keyword in node.keywords if keyword.arg == "module"), None)
        if (
            self.layer == "parser"
            and module_keyword is not None
            and (target := self._resolved_string(module_keyword))
            and _concrete_backend_module(target)
        ):
            name_keyword = next((keyword.value for keyword in node.keywords if keyword.arg == "name"), None)
            if name := self._resolved_string(name_keyword):
                target = f"{target}#{name}"
            self._add(
                node,
                "backend-module-identity",
                target,
                "parser code must not identify an output backend by module/name; declare a neutral capability",
            )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check direct ``__module__`` comparisons to concrete backends."""
        operands = (node.left, *node.comparators)
        if (
            self.layer == "parser"
            and any(isinstance(operand, ast.Attribute) and operand.attr == "__module__" for operand in operands)
            and (
                target := next(
                    (
                        value
                        for operand in operands
                        if (value := self._resolved_string(operand)) and _concrete_backend_module(value)
                    ),
                    None,
                )
            )
        ):
            self._add(
                node,
                "backend-module-identity",
                target,
                "parser code must not identify an output backend by module/name; declare a neutral capability",
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check backend-specific semantic attributes and output policy references."""
        if self.layer == "parser" and node.attr in PARSER_BACKEND_ATTRIBUTES:
            self._add(
                node,
                "backend-semantic-inspection",
                node.attr,
                "parser code must query a neutral DataModel or DataModelFieldBase capability",
            )
        elif self.layer == "config":
            chain = _attribute_chain(node)
            if chain and (backend := self.backend_aliases.get(chain[0])):
                target = ".".join((backend, *chain[1:]))
                self._add(
                    node,
                    "config-backend-reference",
                    target,
                    "configuration must receive output implementations through a neutral registry or injection",
                )
        elif self.layer == "input-model":
            chain = _attribute_chain(node)
            if len(chain) > 1 and chain[0] in self.data_model_type_aliases:
                self._add(
                    node,
                    "input-model-output-policy",
                    ".".join(chain),
                    "input-model conversion must obtain output-family policy from the output selection registry",
                )
        self.generic_visit(node)

    def _record_import_alias(self, alias: str, target: str) -> None:
        if backend := _concrete_backend_module(target):
            self.backend_aliases[alias] = backend

    def _check_import(self, node: ast.AST, target: str) -> None:
        if self.layer == "parser" and _concrete_backend_module(target):
            self._add(
                node,
                "backend-import",
                target,
                "parser code must depend on neutral model capabilities, not a concrete output backend",
            )
            return
        if self.layer == "config" and _concrete_backend_module(target):
            self._add(
                node,
                "config-backend-import",
                target,
                "configuration must receive output implementations through a neutral registry or injection",
            )
            return
        if target.startswith("datamodel_code_generator.parser._") and self.layer != "parser":
            self._add(
                node,
                "private-parser-import",
                target,
                "shared code outside parser must move reusable helpers to a neutral package module",
            )
        elif self.layer == "config" and (
            target == "datamodel_code_generator.parser" or target.startswith("datamodel_code_generator.parser.")
        ):
            self._add(
                node,
                "config-parser-import",
                target,
                "configuration must not depend on parser implementation modules",
            )

    def _resolved_string(self, node: ast.AST | None) -> str | None:
        match node:
            case ast.Constant(value=str() as value):
                return value
            case ast.Name(id=name):
                return self.string_constants.get(name)
        return None

    def _add(self, node: ast.AST, rule: str, target: str, message: str) -> None:
        self.violations.append(
            Violation(
                path=self.display_path,
                line=getattr(node, "lineno", 0),
                column=getattr(node, "col_offset", 0) + 1,
                qualname=self.qualname,
                rule=rule,
                target=target,
                message=message,
            )
        )


def _classify_source_path(path: Path) -> Layer:
    relative = path.resolve().relative_to(SOURCE_ROOT)
    if relative.parts[0] == "parser":
        return "parser"
    if relative == Path("config.py"):
        return "config"
    if relative == Path("input_model.py"):
        return "input-model"
    return "shared"


def iter_python_files(paths: list[Path]) -> list[Path]:
    """Return stable Python file paths below the requested targets."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(path.rglob("*.py"))
        elif path.suffix == ".py":
            files.append(path)
    return sorted({path.resolve() for path in files})


def check_files(
    files: list[tuple[Path, Layer]],
    *,
    allowlist: dict[BoundaryKey, AllowlistEntry] | None = None,
) -> list[Violation]:
    """Check explicitly classified files and apply a bounded, stale-aware allowlist."""
    active_allowlist = DEFAULT_ALLOWLIST if allowlist is None else allowlist
    raw_violations: list[Violation] = []
    scanned_paths: set[str] = set()
    for path, layer in files:
        display_path = _display_path(path)
        scanned_paths.add(display_path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = ArchitectureBoundaryVisitor(path, layer, tree)
        visitor.visit(tree)
        raw_violations.extend(visitor.violations)

    found_counts = Counter(violation.key for violation in raw_violations)
    allowed_counts = Counter({key: entry.count for key, entry in active_allowlist.items()})
    emitted_counts: Counter[BoundaryKey] = Counter()
    violations: list[Violation] = []
    for violation in sorted(
        raw_violations,
        key=lambda item: (item.path, item.line, item.column, item.rule, item.target),
    ):
        emitted_counts[violation.key] += 1
        if emitted_counts[violation.key] <= allowed_counts[violation.key]:
            continue
        violations.append(violation)

    for key, entry in sorted(active_allowlist.items()):
        if key.path not in scanned_paths or found_counts[key] >= entry.count:
            continue
        violations.append(
            Violation(
                path=key.path,
                line=0,
                column=0,
                qualname=key.qualname,
                rule="stale-allowlist",
                target=f"{key.rule}:{key.target}",
                message=(
                    f"remove or reduce this allowlist entry; expected {entry.count} legacy occurrence(s), "
                    f"found {found_counts[key]}. Reason: {entry.reason}"
                ),
            )
        )
    return sorted(violations, key=lambda item: (item.path, item.line, item.column, item.rule, item.target))


def check_paths(
    paths: list[Path],
    *,
    allowlist: dict[BoundaryKey, AllowlistEntry] | None = None,
) -> list[Violation]:
    """Check source-tree paths using their architecture layer classification."""
    files = iter_python_files(paths)
    return check_files([(path, _classify_source_path(path)) for path in files], allowlist=allowlist)


def format_report(violations: list[Violation]) -> str:
    """Return a stable human- and LLM-readable report."""
    if not violations:
        return "No architecture boundary violations.\n"
    return "Architecture boundary violations found:\n" + "".join(f"{violation.format()}\n" for violation in violations)


def main(argv: list[str] | None = None) -> int:
    """Run the architecture boundary guard."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[SOURCE_ROOT])
    args = parser.parse_args(argv)

    violations = check_paths(args.paths)
    if violations:
        print(format_report(violations), end="", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
