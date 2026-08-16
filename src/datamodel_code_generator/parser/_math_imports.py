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


def _function_scope(arguments: ast.arguments, body: list[ast.stmt], kind: str = "function") -> _Scope:
    """Collect only non-finite bindings local to a function-like scope."""
    bound = global_names = nonlocal_names = 0

    def collect(node: ast.AST) -> None:  # noqa: PLR0911, PLR0912
        nonlocal bound, global_names, nonlocal_names
        match node:
            case ast.Global(names=global_declarations):
                for name in global_declarations:
                    global_names |= _NON_FINITE_NAMES.get(name, 0)
                return
            case ast.Nonlocal(names=nonlocal_declarations):
                for name in nonlocal_declarations:
                    nonlocal_names |= _NON_FINITE_NAMES.get(name, 0)
                return
            case ast.Name(id=name, ctx=(ast.Store() | ast.Del())):
                bound |= _NON_FINITE_NAMES.get(name, 0)
                return
            case ast.Import(names=import_aliases):
                for alias in import_aliases:
                    bound |= _NON_FINITE_NAMES.get(alias.asname or alias.name.partition(".")[0], 0)
                return
            case ast.ImportFrom(names=from_import_aliases):
                for alias in from_import_aliases:
                    if alias.name != "*":
                        bound |= _NON_FINITE_NAMES.get(alias.asname or alias.name, 0)
                return
            case ast.ExceptHandler(name=name):
                bound |= _NON_FINITE_NAMES.get(name, 0)
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name) | ast.ClassDef(name=name):
                bound |= _NON_FINITE_NAMES.get(name, 0)
                return
            case ast.Lambda() | ast.ListComp() | ast.SetComp() | ast.DictComp() | ast.GeneratorExp():
                return
            case _:
                pass
        for child in ast.iter_child_nodes(node):
            collect(child)

    for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
        bound |= _NON_FINITE_NAMES.get(argument.arg, 0)
    if arguments.vararg is not None:
        bound |= _NON_FINITE_NAMES.get(arguments.vararg.arg, 0)
    if arguments.kwarg is not None:
        bound |= _NON_FINITE_NAMES.get(arguments.kwarg.arg, 0)
    for statement in body:
        collect(statement)
    return _Scope(kind, bound & ~(global_names | nonlocal_names), global_names, nonlocal_names)


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
                    if class_visible and names & scope.bound:
                        return
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

    def visit(node: ast.AST) -> None:  # noqa: PLR0912, PLR0914, PLR0915
        match node:
            case ast.Name(id=name, ctx=ast.Load()):
                resolve(_NON_FINITE_NAMES.get(name, 0))
            case ast.Name(id=name, ctx=(ast.Store() | ast.Del())):
                bind(name)
            case ast.Assign(value=assigned_value, targets=assignment_targets):
                visit(assigned_value)
                for target in assignment_targets:
                    visit(target)
            case ast.AnnAssign(annotation=assigned_annotation, value=annotated_value, target=annotated_target):
                visit(assigned_annotation)
                if annotated_value is not None:
                    visit(annotated_value)
                visit(annotated_target)
            case ast.AugAssign(target=ast.Name(id=name), value=augmented_value):
                resolve(_NON_FINITE_NAMES.get(name, 0))
                visit(augmented_value)
                bind(name)
            case ast.Import(names=import_aliases):
                for alias in import_aliases:
                    bind(alias.asname or alias.name.partition(".")[0])
            case ast.ImportFrom(module=module, names=from_import_aliases):
                for alias in from_import_aliases:
                    if alias.name == "*" and module == "math":
                        scopes[-1].bound |= _INF | _NAN
                    elif alias.name != "*":
                        bind(alias.asname or alias.name)
            case ast.If(test=test, body=body, orelse=orelse):
                visit(test)
                bound = scopes[-1].bound
                for statement in body:
                    visit(statement)
                scopes[-1].bound = bound
                for statement in orelse:
                    visit(statement)
                scopes[-1].bound = bound
            case (
                ast.FunctionDef(name=name, args=arguments, body=body, decorator_list=decorators, returns=returns)
                | ast.AsyncFunctionDef(name=name, args=arguments, body=body, decorator_list=decorators, returns=returns)
            ):
                for decorator in decorators:
                    visit(decorator)
                visit_arguments(arguments)
                if returns is not None:
                    visit(returns)
                bind(name)
                scopes.append(_function_scope(arguments, body))
                for statement in body:
                    visit(statement)
                scopes.pop()
            case ast.Lambda(args=arguments, body=body):
                visit_arguments(arguments)
                scopes.append(_function_scope(arguments, [], "lambda"))
                visit(body)
                scopes.pop()
            case ast.ClassDef(name=name, bases=bases, keywords=keywords, body=body, decorator_list=decorators):
                for decorator in decorators:
                    visit(decorator)
                for base in bases:
                    visit(base)
                for keyword in keywords:
                    visit(keyword.value)
                bind(name)
                scopes.append(_Scope("class"))
                for statement in body:
                    visit(statement)
                scopes.pop()
            case (
                ast.ListComp(generators=generators, elt=element)
                | ast.SetComp(generators=generators, elt=element)
                | ast.GeneratorExp(generators=generators, elt=element)
            ):
                visit_comprehension(generators, (element,))
            case ast.DictComp(generators=generators, key=key, value=value):
                visit_comprehension(generators, (key, value))
            case _:
                for child in ast.iter_child_nodes(node):
                    visit(child)

    visit(tree)
    return missing


def _pep695_type_alias_loads(body: str, placeholder_body: str) -> dict[int, int]:
    """Read only PEP 695 type-alias RHS tokens replaced before AST parsing."""
    import tokenize  # noqa: PLC0415
    from io import StringIO  # noqa: PLC0415

    lines = body.splitlines(keepends=True)
    placeholder_lines = placeholder_body.splitlines(keepends=True)
    names_by_line: dict[int, int] = {}
    line_index = 0
    while line_index < len(lines):
        if lines[line_index] == placeholder_lines[line_index]:
            line_index += 1
            continue
        start_line = line_index
        source_lines: list[str] = []
        while line_index < len(lines) and lines[line_index] != placeholder_lines[line_index]:
            source_lines.append(lines[line_index])
            line_index += 1
        right_hand_side = False
        previous = ""
        try:
            for token in tokenize.generate_tokens(StringIO("".join(source_lines)).readline):
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


def _get_required_non_finite_imports(body: str) -> tuple[int, ast.Module | None]:
    if "inf" not in body and "nan" not in body:
        return 0, None
    try:
        tree = ast.parse(body)
    except SyntaxError:
        from datamodel_code_generator._builtin_formatter import (  # noqa: PLC0415
            _replace_pep695_type_aliases_with_placeholders,
        )

        if (placeholder_body := _replace_pep695_type_aliases_with_placeholders(body)).splitlines() == body.splitlines():
            return 0, None
        try:
            tree = ast.parse(placeholder_body)
        except SyntaxError:  # pragma: no cover - unsupported target syntax is left untouched
            return 0, None
        _restore_pep695_type_alias_loads(tree, _pep695_type_alias_loads(body, placeholder_body))
        return _get_required_non_finite_imports_from_tree(tree), tree
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
