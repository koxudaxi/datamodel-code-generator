"""Helpers for imports required by generated non-finite float literals."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

_INF = 1
_NAN = 2
_NON_FINITE_NAMES = {"inf": _INF, "nan": _NAN}


@dataclass(slots=True)
class _Scope:
    kind: str
    bound: int = 0
    global_names: int = 0
    nonlocal_names: int = 0
    static_bound: int = 0


def _body_scope_bindings(body: list[ast.stmt]) -> tuple[int, int, int]:
    """Collect non-finite bindings declared directly in a lexical scope body."""
    bound = global_names = nonlocal_names = 0

    def collect(node: ast.AST) -> None:  # noqa: PLR0911, PLR0912
        nonlocal bound, global_names, nonlocal_names
        match node:
            case ast.Global():
                for name in node.names:
                    global_names |= _NON_FINITE_NAMES.get(name, 0)
                return
            case ast.Nonlocal():
                for name in node.names:
                    nonlocal_names |= _NON_FINITE_NAMES.get(name, 0)
                return
            case ast.Name(ctx=(ast.Store() | ast.Del())):
                bound |= _NON_FINITE_NAMES.get(node.id, 0)
                return
            case ast.Import():
                for alias in node.names:
                    bound |= _NON_FINITE_NAMES.get(alias.asname or alias.name.partition(".")[0], 0)
                return
            case ast.ImportFrom():
                for alias in node.names:
                    if alias.name != "*":
                        bound |= _NON_FINITE_NAMES.get(alias.asname or alias.name, 0)
                return
            case ast.ExceptHandler():
                if node.name is not None:
                    bound |= _NON_FINITE_NAMES.get(node.name, 0)
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
                bound |= _NON_FINITE_NAMES.get(node.name, 0)
                return
            case ast.Lambda() | ast.ListComp() | ast.SetComp() | ast.DictComp() | ast.GeneratorExp():
                return
            case _:
                pass
        for child in ast.iter_child_nodes(node):
            collect(child)

    for statement in body:
        collect(statement)
    return bound & ~(global_names | nonlocal_names), global_names, nonlocal_names


def _function_scope(arguments: ast.arguments, body: list[ast.stmt], kind: str = "function") -> _Scope:
    """Collect only non-finite bindings local to a function-like scope."""
    bound, global_names, nonlocal_names = _body_scope_bindings(body)
    for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
        bound |= _NON_FINITE_NAMES.get(argument.arg, 0)
    if arguments.vararg is not None:
        bound |= _NON_FINITE_NAMES.get(arguments.vararg.arg, 0)
    if arguments.kwarg is not None:
        bound |= _NON_FINITE_NAMES.get(arguments.kwarg.arg, 0)
    return _Scope(kind, bound, global_names, nonlocal_names)


def _get_required_non_finite_imports_from_tree(tree: ast.Module) -> int:  # noqa: PLR0915
    """Find loads whose lookup reaches an unbound module-level name."""
    missing = 0
    scopes = [_Scope("module")]

    def resolve(names: int) -> None:
        nonlocal missing
        class_visible = scopes[-1].kind == "class"
        for scope in reversed(scopes):  # pragma: no branch - the module scope always terminates lookup
            match scope.kind:
                case "function" | "lambda" | "comprehension":
                    if names & scope.global_names:
                        missing |= names & ~scopes[0].bound
                        return
                    if names & (scope.bound | scope.nonlocal_names):
                        return
                    class_visible = False
                case "class":
                    if class_visible and names & scope.global_names:
                        missing |= names & ~scopes[0].bound
                        return
                    if class_visible and names & scope.bound:
                        return
                    if class_visible and names & scope.static_bound:
                        missing |= names & ~scopes[0].bound
                        return
                    # A nested class cannot resolve names through an outer class body.
                    class_visible = False
                case "module":  # pragma: no branch - module lookup always returns
                    missing |= names & ~scope.bound
                    return

    def bind(name: str) -> None:
        scopes[-1].bound |= _NON_FINITE_NAMES.get(name, 0)

    def visit_arguments(arguments: ast.arguments) -> None:
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
            if argument.annotation is not None:
                visit(argument.annotation)
        for argument in (arguments.vararg, arguments.kwarg):
            if argument is not None and argument.annotation is not None:
                visit(argument.annotation)
        for default in (*arguments.defaults, *arguments.kw_defaults):
            if default is not None:
                visit(default)

    def visit_comprehension(generators: list[ast.comprehension], values: tuple[ast.expr, ...]) -> None:
        if not generators:  # pragma: no cover - Python comprehensions always have a generator
            return
        visit(generators[0].iter)
        scopes.append(_Scope("comprehension"))
        for index, generator in enumerate(generators):
            if index:
                visit(generator.iter)
            visit(generator.target)
            for condition in generator.ifs:
                visit(condition)
        for value in values:
            visit(value)
        scopes.pop()

    def visit(node: ast.AST) -> None:  # noqa: PLR0912, PLR0915
        match node:
            case ast.Name(ctx=ast.Load()):
                resolve(_NON_FINITE_NAMES.get(node.id, 0))
            case ast.Name(ctx=(ast.Store() | ast.Del())):
                bind(node.id)
            case ast.Assign():
                visit(node.value)
                for target in node.targets:
                    visit(target)
            case ast.AnnAssign():
                visit(node.annotation)
                if node.value is not None:
                    visit(node.value)
                visit(node.target)
            case ast.AugAssign(target=ast.Name()):
                resolve(_NON_FINITE_NAMES.get(node.target.id, 0))
                visit(node.value)
                bind(node.target.id)
            case ast.Import():
                for alias in node.names:
                    bind(alias.asname or alias.name.partition(".")[0])
            case ast.ImportFrom():
                for alias in node.names:
                    if alias.name == "*" and node.module == "math":
                        scopes[-1].bound |= _INF | _NAN
                    elif alias.name != "*":
                        bind(alias.asname or alias.name)
            case ast.If():
                visit(node.test)
                bound = scopes[-1].bound
                for statement in node.body:
                    visit(statement)
                scopes[-1].bound = bound
                for statement in node.orelse:
                    visit(statement)
                scopes[-1].bound = bound
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                for decorator in node.decorator_list:
                    visit(decorator)
                visit_arguments(node.args)
                if node.returns is not None:
                    visit(node.returns)
                bind(node.name)
                scopes.append(_function_scope(node.args, node.body))
                for statement in node.body:
                    visit(statement)
                scopes.pop()
            case ast.Lambda():
                visit_arguments(node.args)
                scopes.append(_function_scope(node.args, [], "lambda"))
                visit(node.body)
                scopes.pop()
            case ast.ClassDef():
                for decorator in node.decorator_list:
                    visit(decorator)
                for base in node.bases:
                    visit(base)
                for keyword in node.keywords:
                    visit(keyword.value)
                bind(node.name)
                static_bound = static_global_names = 0
                if any(scope.kind in {"function", "lambda"} for scope in scopes):
                    static_bound, static_global_names, _ = _body_scope_bindings(node.body)
                scopes.append(_Scope("class", global_names=static_global_names, static_bound=static_bound))
                for statement in node.body:
                    visit(statement)
                scopes.pop()
            case ast.ListComp() | ast.SetComp() | ast.GeneratorExp():
                visit_comprehension(node.generators, (node.elt,))
            case ast.DictComp():
                visit_comprehension(node.generators, (node.key, node.value))
            case _:
                for child in ast.iter_child_nodes(node):
                    visit(child)

    visit(tree)
    return missing


def _pep695_type_alias_loads(body: str, placeholder_body: str) -> dict[int, int]:
    """Read only PEP 695 type-alias RHS tokens replaced before AST parsing."""
    import tokenize  # noqa: PLC0415
    from io import StringIO  # noqa: PLC0415

    lines = body.splitlines()
    placeholder_lines = placeholder_body.splitlines()
    names_by_line: dict[int, int] = {}
    line_index = 0
    while line_index < len(lines):
        if line_index < len(placeholder_lines) and lines[line_index] == placeholder_lines[line_index]:
            line_index += 1
            continue
        start_line = line_index
        source_lines: list[str] = []
        while line_index < len(lines) and (
            line_index >= len(placeholder_lines) or lines[line_index] != placeholder_lines[line_index]
        ):
            source_lines.append(lines[line_index])
            line_index += 1
        right_hand_side = False
        previous = ""
        try:
            for token in tokenize.generate_tokens(StringIO("\n".join(source_lines)).readline):
                match token.type:
                    case tokenize.OP if token.string == "=":
                        right_hand_side = True
                    case tokenize.NAME if right_hand_side and previous != ".":
                        names_by_line[start_line + 1] = names_by_line.get(start_line + 1, 0) | _NON_FINITE_NAMES.get(
                            token.string, 0
                        )
                previous = token.string
        except tokenize.TokenError:  # pragma: no cover - malformed source is left untouched
            continue
    return names_by_line


def _restore_pep695_type_alias_loads(tree: ast.Module, names_by_line: dict[int, int]) -> None:
    """Give placeholder assignments the original RHS loads for scope analysis."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not (names := names_by_line.get(node.lineno, 0)):
            continue
        node.value = ast.Tuple(
            elts=[ast.Name(name, ast.Load()) for name, bit in _NON_FINITE_NAMES.items() if names & bit],
            ctx=ast.Load(),
        )


def _parse_prefix(body: str) -> tuple[ast.Module | None, int]:
    """Parse a source prefix and return its error line when it is incomplete."""
    try:
        return ast.parse(body), 0
    except SyntaxError as syntax_error:
        return None, syntax_error.lineno or 1


def _parse_valid_prefix(body: str, syntax_error: SyntaxError) -> ast.Module | None:
    """Return the largest prefix before a syntax error that still parses."""
    lines = body.splitlines(keepends=True)
    end_line = min((syntax_error.lineno or 1) - 1, len(lines))
    while end_line:
        tree, error_line = _parse_prefix("".join(lines[:end_line]))
        if tree is not None:
            return tree
        end_line = min(end_line - 1, error_line - 1)
    return None


def _get_required_non_finite_imports(body: str) -> tuple[int, ast.Module | None]:
    if "inf" not in body and "nan" not in body:
        return 0, None
    try:
        tree = ast.parse(body)
    except SyntaxError as syntax_error:
        prefix_tree = _parse_valid_prefix(body, syntax_error)
        source_lines = body.splitlines()
        syntax_line_index = (syntax_error.lineno or 1) - 1
        syntax_line = "".join(source_lines[syntax_line_index : syntax_line_index + 1])
        if (
            prefix_tree is not None
            and (missing_names := _get_required_non_finite_imports_from_tree(prefix_tree))
            and not syntax_line.lstrip().startswith("type ")
        ):
            return missing_names, prefix_tree

        from datamodel_code_generator._builtin_formatter import (  # noqa: PLC0415
            _replace_pep695_type_aliases_with_placeholders,
        )

        placeholder_body = _replace_pep695_type_aliases_with_placeholders(body)
        if placeholder_body.splitlines() != body.splitlines():
            try:
                tree = ast.parse(placeholder_body)
            except SyntaxError as placeholder_syntax_error:
                tree = _parse_valid_prefix(placeholder_body, placeholder_syntax_error)
                if tree is not None:
                    _restore_pep695_type_alias_loads(tree, _pep695_type_alias_loads(body, placeholder_body))
                    return _get_required_non_finite_imports_from_tree(tree), tree
            else:
                _restore_pep695_type_alias_loads(tree, _pep695_type_alias_loads(body, placeholder_body))
                return _get_required_non_finite_imports_from_tree(tree), tree
        return 0, None
    return _get_required_non_finite_imports_from_tree(tree), tree


def _header_end_line(tree: ast.Module) -> int:
    statements = tree.body
    index = end_line = 0
    if (
        statements
        and isinstance(statements[0], ast.Expr)
        and isinstance(statements[0].value, ast.Constant)
        and isinstance(statements[0].value.value, str)
    ):
        end_line = statements[0].end_lineno or statements[0].lineno
        index = 1
    while index < len(statements):  # pragma: no branch - a missing name requires a statement after the header
        statement = statements[index]
        if not isinstance(statement, ast.ImportFrom) or statement.module != "__future__":
            break
        end_line = statement.end_lineno or statement.lineno
        index += 1
    return end_line


def add_math_imports_for_non_finite_literals(body: str) -> str:
    missing_names, tree = _get_required_non_finite_imports(body)
    if not missing_names:
        return body

    import_line = "from math import " + (
        "inf, nan" if missing_names == _INF | _NAN else "inf" if missing_names == _INF else "nan"
    )
    lines = body.splitlines(keepends=True)
    index = _header_end_line(tree) if tree is not None else 0
    offset = sum(len(lines[line_index]) for line_index in range(index))
    while index < len(lines) and (not (stripped := lines[index].strip()) or stripped.startswith("#")):
        offset += len(lines[index])
        index += 1
    line_ending = "\r\n" if "\r\n" in body else "\n"
    return f"{body[:offset]}{import_line}{line_ending}{body[offset:]}"


def apply_math_imports_to_parse_result(result: str | dict[tuple[str, ...], Any]) -> str | dict[tuple[str, ...], Any]:
    if isinstance(result, str):
        return add_math_imports_for_non_finite_literals(result)
    for item in result.values():
        item.body = add_math_imports_for_non_finite_literals(item.body)
    return result
