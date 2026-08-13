"""Feature inventory and compatibility guard for built-in Jinja templates."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from jinja2 import Environment, nodes

if TYPE_CHECKING:
    from pathlib import Path

SUPPORTED_NODE_TYPES = frozenset({
    "And",
    "Assign",
    "Call",
    "Compare",
    "Concat",
    "Const",
    "Dict",
    "Filter",
    "FilterBlock",
    "For",
    "Getattr",
    "Getitem",
    "If",
    "Include",
    "Keyword",
    "List",
    "Macro",
    "NSRef",
    "Name",
    "Not",
    "Operand",
    "Or",
    "Output",
    "Pair",
    "Template",
    "TemplateData",
    "Test",
    "Tuple",
})
SUPPORTED_FILTERS = frozenset({
    "default",
    "indent",
    "join",
    "length",
    "list",
    "pprint",
    "replace",
    "repr",
    "selectattr",
})
SUPPORTED_TESTS = frozenset({"defined", "equalto", "false", "none"})
SUPPORTED_GLOBALS = frozenset({"namespace"})
SUPPORTED_LOOP_ATTRIBUTES = frozenset({"last"})
SUPPORTED_ASSIGNMENTS = frozenset({"Name", "NSRef"})
SUPPORTED_CALLS = frozenset({"append", "get", "items", "get_type_annotation", "get_type_hint", "namespace"})
_SELECTATTR_TEST_ARGUMENT_INDEX = 1
_SELECTATTR_TEST_MINIMUM_ARGUMENTS = 2
# ``prepared_validators`` is built as dictionaries in pydantic_v2/base_model.py.
# The template intentionally uses Jinja's mapping-dot fallback for these keys.
KNOWN_MAPPING_DOT_ACCESSES = frozenset({
    ("pydantic_v2/BaseModel.jinja2", "v", "fields_str"),
    ("pydantic_v2/BaseModel.jinja2", "v", "mode"),
    ("pydantic_v2/BaseModel.jinja2", "v", "mode_str"),
    ("pydantic_v2/BaseModel.jinja2", "v", "method_name"),
    ("pydantic_v2/BaseModel.jinja2", "v", "function_name"),
})


@dataclass(frozen=True)
class TemplateInventory:
    """The parsed feature set, kept useful for both checks and tests."""

    nodes: dict[str, tuple[str, ...]]
    filters: dict[str, tuple[str, ...]]
    tests: dict[str, tuple[str, ...]]
    globals: dict[str, tuple[str, ...]]
    loop_attributes: dict[str, tuple[str, ...]]
    assignments: dict[str, tuple[str, ...]]
    for_targets: dict[str, tuple[str, ...]]
    macros: dict[str, tuple[str, ...]]
    includes: dict[str, tuple[str, ...]]
    imports_and_inheritance: dict[str, tuple[str, ...]]
    undefined_usage: dict[str, tuple[str, ...]]
    namespaces: dict[str, tuple[str, ...]]
    mapping_dot_accesses: dict[str, tuple[str, ...]]


def iter_template_paths(template_dir: Path) -> tuple[Path, ...]:
    return tuple(sorted(template_dir.rglob("*.jinja2")))


def build_environment() -> Environment:
    """Match production's Jinja configuration for the parser frontend."""
    from jinja2 import select_autoescape  # noqa: PLC0415

    from datamodel_code_generator.model.base import escape_docstring, format_docstring  # noqa: PLC0415

    environment = Environment(autoescape=select_autoescape(["html", "xml"]))
    environment.filters["escape_docstring"] = escape_docstring
    environment.filters["format_docstring"] = format_docstring
    environment.filters["repr"] = repr
    return environment


def _location(path: Path, node: nodes.Node) -> str:
    line = getattr(node, "lineno", None)
    return f"{path}:{line}" if line is not None else str(path)


def _record(values: dict[str, list[str]], name: str, path: Path, node: nodes.Node) -> None:
    values[name].append(_location(path, node))


def _unsupported(path: Path, node: nodes.Node, kind: str, name: str) -> ValueError:
    return ValueError(
        f"{_location(path, node)}: unsupported Jinja {kind} {name!r}; "
        "update the standalone template compiler before using this feature"
    )


def _call_name(node: nodes.Call) -> str | None:
    if isinstance(node.node, nodes.Name):
        return node.node.name
    if isinstance(node.node, nodes.Getattr):
        return node.node.attr
    return None


def inventory_templates(template_dir: Path, environment: Environment | None = None) -> TemplateInventory:
    """Parse and validate every built-in template, returning its derived inventory."""
    env = environment or build_environment()
    values: dict[str, dict[str, list[str]]] = {
        name: defaultdict(list)
        for name in (
            "nodes",
            "filters",
            "tests",
            "globals",
            "loop_attributes",
            "assignments",
            "for_targets",
            "macros",
            "includes",
            "imports_and_inheritance",
            "undefined_usage",
            "namespaces",
            "mapping_dot_accesses",
        )
    }
    include_graph: dict[Path, set[Path]] = defaultdict(set)
    for path in iter_template_paths(template_dir):
        relative_path = path.relative_to(template_dir)
        ast = env.parse(path.read_text(encoding="utf-8"))
        _record(values["nodes"], type(ast).__name__, relative_path, ast)
        static_mapping_names = {
            node.target.name
            for node in ast.find_all(nodes.Assign)
            if isinstance(node.target, nodes.Name) and isinstance(node.node, nodes.Dict)
        }
        for node in ast.find_all(nodes.Node):
            node_name = type(node).__name__
            _record(values["nodes"], node_name, relative_path, node)
            if node_name not in SUPPORTED_NODE_TYPES and not isinstance(
                node, (nodes.Import, nodes.FromImport, nodes.Extends)
            ):
                raise _unsupported(relative_path, node, "AST node", node_name)
            if isinstance(node, nodes.Filter):
                _record(values["filters"], node.name, relative_path, node)
                if node.name not in SUPPORTED_FILTERS:
                    raise _unsupported(relative_path, node, "filter", node.name)
                if node.name == "selectattr":
                    _inventory_selectattr_test(values["tests"], relative_path, node)
                if node.name == "default":
                    _record(values["undefined_usage"], "default filter", relative_path, node)
            elif isinstance(node, nodes.Test):
                _record(values["tests"], node.name, relative_path, node)
                if node.name not in SUPPORTED_TESTS:
                    raise _unsupported(relative_path, node, "test", node.name)
                if node.name == "defined":
                    _record(values["undefined_usage"], "defined test", relative_path, node)
            elif isinstance(node, nodes.Name) and node.ctx == "load" and node.name == "namespace":
                _record(values["globals"], node.name, relative_path, node)
            elif isinstance(node, nodes.Getattr) and isinstance(node.node, nodes.Name) and node.node.name == "loop":
                _record(values["loop_attributes"], node.attr, relative_path, node)
                if node.attr not in SUPPORTED_LOOP_ATTRIBUTES:
                    raise _unsupported(relative_path, node, "loop attribute", node.attr)
            elif isinstance(node, nodes.Assign):
                assignment = type(node.target).__name__
                _record(values["assignments"], assignment, relative_path, node)
                if assignment not in SUPPORTED_ASSIGNMENTS:
                    raise _unsupported(relative_path, node, "assignment target", assignment)
                if isinstance(node.target, nodes.NSRef):
                    _record(values["namespaces"], "attribute mutation", relative_path, node)
            elif isinstance(node, nodes.For):
                _record(values["for_targets"], _target_form(node.target), relative_path, node)
            elif isinstance(node, nodes.Macro):
                _inventory_macro(values["macros"], relative_path, node)
            elif isinstance(node, nodes.Include):
                if not isinstance(node.template, nodes.Const) or not isinstance(node.template.value, str):
                    raise _unsupported(relative_path, node, "include", "dynamic include")
                _record(values["includes"], node.template.value, relative_path, node)
                include_path = (template_dir / relative_path.parent / node.template.value).resolve()
                if not include_path.is_file() or template_dir.resolve() not in include_path.parents:
                    raise _unsupported(relative_path, node, "include", node.template.value)
                include_graph[relative_path].add(include_path.relative_to(template_dir.resolve()))
            elif isinstance(node, (nodes.Import, nodes.FromImport, nodes.Extends)):
                construct = type(node).__name__
                _record(values["imports_and_inheritance"], construct, relative_path, node)
                raise _unsupported(relative_path, node, "template import/inheritance", construct)
            elif isinstance(node, nodes.Call):
                if (call_name := _call_name(node)) not in SUPPORTED_CALLS:
                    raise _unsupported(relative_path, node, "call", call_name or type(node.node).__name__)
                if call_name == "namespace":
                    _record(values["namespaces"], "creation", relative_path, node)
        # A mapping value's ``.foo`` would need Jinja's getattr/item fallback.
        # Built-ins may call mapping methods (``.items``/``.get``), but must use
        # bracket syntax for mapping values.
        for node in ast.find_all(nodes.Getattr):
            if isinstance(node.node, nodes.Dict) or (
                isinstance(node.node, nodes.Name)
                and node.node.name in static_mapping_names
                and node.attr not in {"get", "items"}
            ):
                raise _unsupported(relative_path, node, "mapping dot access", node.attr)
            if (
                relative_path.as_posix() == "pydantic_v2/BaseModel.jinja2"
                and isinstance(node.node, nodes.Name)
                and node.node.name == "v"
            ):
                mapping_access = (relative_path.as_posix(), node.node.name, node.attr)
                if mapping_access in KNOWN_MAPPING_DOT_ACCESSES:
                    _record(values["mapping_dot_accesses"], node.attr, relative_path, node)
                else:
                    raise _unsupported(relative_path, node, "mapping dot access", node.attr)
    _check_include_cycles(include_graph)
    return TemplateInventory(**{
        name: {key: tuple(locations) for key, locations in mapping.items()} for name, mapping in values.items()
    })


def _inventory_selectattr_test(values: dict[str, list[str]], path: Path, node: nodes.Filter) -> None:
    if (
        len(node.args) < _SELECTATTR_TEST_MINIMUM_ARGUMENTS
        or not isinstance(node.args[_SELECTATTR_TEST_ARGUMENT_INDEX], nodes.Const)
        or not isinstance(node.args[_SELECTATTR_TEST_ARGUMENT_INDEX].value, str)
    ):
        raise _unsupported(path, node, "selectattr test", "dynamic or omitted test")
    test_name = node.args[_SELECTATTR_TEST_ARGUMENT_INDEX].value
    _record(values, test_name, path, node)
    if test_name not in SUPPORTED_TESTS:
        raise _unsupported(path, node, "test", test_name)


def _target_form(target: nodes.Expr) -> str:
    if isinstance(target, nodes.Name):
        return "Name"
    if isinstance(target, nodes.Tuple):
        return "Tuple[" + ", ".join(_target_form(item) for item in target.items) + "]"
    return type(target).__name__


def _inventory_macro(values: dict[str, list[str]], path: Path, node: nodes.Macro) -> None:
    signature = ", ".join(argument.name for argument in node.args)
    details = (
        f"{node.name}({signature}); defaults={len(node.defaults)}; "
        f"caller={getattr(node, 'caller', False)}; kwargs={getattr(node, 'catch_kwargs', False)}; "
        f"varargs={getattr(node, 'catch_varargs', False)}"
    )
    _record(values, details, path, node)
    if node.defaults:
        raise _unsupported(path, node, "macro defaults", node.name)
    if getattr(node, "caller", False) or getattr(node, "catch_kwargs", False) or getattr(node, "catch_varargs", False):
        raise _unsupported(path, node, "macro caller/kwargs/varargs", node.name)


def _check_include_cycles(graph: dict[Path, set[Path]]) -> None:
    visiting: list[Path] = []
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        if path in visited:
            return
        if path in visiting:
            cycle = " -> ".join(item.as_posix() for item in [*visiting[visiting.index(path) :], path])
            error_message = (
                f"{path}: include cycle detected ({cycle}); update the standalone template compiler before using it"
            )
            raise ValueError(error_message)
        visiting.append(path)
        for included in graph.get(path, ()):
            visit(included)
        visiting.pop()
        visited.add(path)

    for path in graph:
        visit(path)


def formatted_inventory(inventory: TemplateInventory) -> str:
    """Provide deterministic diagnostic output for the generation command."""
    lines: list[str] = []
    for name in (
        "nodes",
        "filters",
        "tests",
        "globals",
        "loop_attributes",
        "assignments",
        "for_targets",
        "macros",
        "includes",
        "imports_and_inheritance",
        "undefined_usage",
        "namespaces",
        "mapping_dot_accesses",
    ):
        entries: dict[str, tuple[str, ...]] = getattr(inventory, name)
        lines.append(f"{name}:")
        lines.extend(f"  {key}: {', '.join(value)}" for key, value in sorted(entries.items()))
    return "\n".join(lines)
