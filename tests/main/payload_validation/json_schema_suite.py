"""JSON-Schema-Test-Suite helpers for payload validation conformance tests."""

from __future__ import annotations

import json
import os
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from .models import SchemaCase

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping
    from pathlib import Path

    from pydantic import TypeAdapter


JSON_SCHEMA_TEST_SUITE_COMMIT = "fe8c2f0de2041943975932b6bf4bd882625b6cfb"
DEFAULT_JSON_SCHEMA_TEST_SUITE_TARGET_DRAFTS = ("draft7", "draft2020-12")
ALL_JSON_SCHEMA_TEST_SUITE_TARGET_DRAFTS = ("draft3", "draft4", "draft6", "draft7", "draft2019-09", "draft2020-12")
JSON_SCHEMA_TEST_SUITE_DIALECTS = {
    "draft3": "http://json-schema.org/draft-03/schema#",
    "draft4": "http://json-schema.org/draft-04/schema#",
    "draft6": "http://json-schema.org/draft-06/schema#",
    "draft7": "http://json-schema.org/draft-07/schema#",
    "draft2019-09": "https://json-schema.org/draft/2019-09/schema",
    "draft2020-12": "https://json-schema.org/draft/2020-12/schema",
}
EXPECTED_JSON_SCHEMA_SUITE_GROUP_COUNTS_BY_DRAFT = {
    "draft3": 104,
    "draft4": 160,
    "draft6": 232,
    "draft7": 257,
    "draft2019-09": 372,
    "draft2020-12": 383,
}
EXPECTED_JSON_SCHEMA_SUITE_TEST_COUNTS_BY_DRAFT = {
    "draft3": 435,
    "draft4": 618,
    "draft6": 839,
    "draft7": 927,
    "draft2019-09": 1259,
    "draft2020-12": 1299,
}
JSON_SCHEMA_SUITE_EXCLUDED_CASES: dict[str, str] = {}
OBJECT_SCHEMA_KEYWORDS = {
    "additionalProperties",
    "maxProperties",
    "minProperties",
    "properties",
    "propertyNames",
    "required",
    "unevaluatedProperties",
}
ARRAY_SCHEMA_KEYWORDS = {
    "additionalItems",
    "contains",
    "items",
    "maxContains",
    "maxItems",
    "minContains",
    "minItems",
    "prefixItems",
    "unevaluatedItems",
    "uniqueItems",
}
UNSUPPORTED_SCHEMA_KEYWORD_REASONS = {
    "additionalItems": "tuple additionalItems semantics are not represented by generated pydantic v2 models",
    "contains": (
        "contains/minContains/maxContains array membership semantics are not represented by "
        "generated pydantic v2 models"
    ),
    "dependentRequired": (
        "dependentRequired object dependency semantics are not represented by generated pydantic v2 models"
    ),
    "dependentSchemas": "dependentSchemas applicator semantics are not represented by generated pydantic v2 models",
    "dependencies": (
        "draft7 dependencies object dependency semantics are not represented by generated pydantic v2 models"
    ),
    "disallow": "draft3 disallow semantics are not represented by generated pydantic v2 models",
    "divisibleBy": "draft3 divisibleBy numeric semantics are not enforced by generated pydantic v2 models by default",
    "extends": "draft3 extends inheritance semantics are not represented by generated pydantic v2 models",
    "exclusiveMaximum": "exclusive numeric bounds are not enforced by generated pydantic v2 models by default",
    "exclusiveMinimum": "exclusive numeric bounds are not enforced by generated pydantic v2 models by default",
    "if": "if/then/else conditional semantics are not represented by generated pydantic v2 models",
    "maximum": "numeric upper bounds are not enforced by generated pydantic v2 models by default",
    "maxItems": "array length bounds are not enforced by generated pydantic v2 models by default",
    "maxLength": "string length bounds are not enforced by generated pydantic v2 models by default",
    "maxProperties": "object property-count bounds are not enforced by generated pydantic v2 models by default",
    "minimum": "numeric lower bounds are not enforced by generated pydantic v2 models by default",
    "minItems": "array length bounds are not enforced by generated pydantic v2 models by default",
    "minLength": "string length bounds are not enforced by generated pydantic v2 models by default",
    "minProperties": "object property-count bounds are not enforced by generated pydantic v2 models by default",
    "multipleOf": "numeric multipleOf constraints are not enforced by generated pydantic v2 models by default",
    "not": "not applicator semantics are not represented by generated pydantic v2 models",
    "pattern": "string pattern constraints are not enforced by generated pydantic v2 models by default",
    "patternProperties": "patternProperties dynamic-key semantics are not represented by generated pydantic v2 models",
    "prefixItems": "prefixItems tuple semantics are not represented by generated pydantic v2 models",
    "propertyNames": "propertyNames key-validation semantics are not represented by generated pydantic v2 models",
    "then": "if/then/else conditional semantics are not represented by generated pydantic v2 models",
    "unevaluatedItems": (
        "unevaluatedItems annotation-dependent semantics are not represented by generated pydantic v2 models"
    ),
    "unevaluatedProperties": (
        "unevaluatedProperties annotation-dependent semantics are not represented by generated pydantic v2 models"
    ),
    "uniqueItems": "uniqueItems array uniqueness semantics are not represented by generated pydantic v2 models",
}
COMBINED_SCHEMA_KEYWORDS = ("allOf", "anyOf", "oneOf")


def _target_drafts_from_env(raw_drafts: str | None = None) -> tuple[str, ...]:
    if raw_drafts is None:
        raw_drafts = os.environ.get("DCG_JSON_SCHEMA_SUITE_DRAFTS")
    if not raw_drafts:
        return DEFAULT_JSON_SCHEMA_TEST_SUITE_TARGET_DRAFTS
    if raw_drafts == "all":
        return ALL_JSON_SCHEMA_TEST_SUITE_TARGET_DRAFTS
    drafts = tuple(draft.strip() for draft in raw_drafts.split(",") if draft.strip())
    if not drafts:
        msg = "DCG_JSON_SCHEMA_SUITE_DRAFTS must select at least one draft"
        raise ValueError(msg)
    if unknown_drafts := sorted(set(drafts) - set(JSON_SCHEMA_TEST_SUITE_DIALECTS)):
        msg = f"Unsupported JSON-Schema-Test-Suite drafts: {', '.join(unknown_drafts)}"
        raise ValueError(msg)
    return drafts


JSON_SCHEMA_TEST_SUITE_TARGET_DRAFTS = _target_drafts_from_env()


def _expected_counts_by_target_draft(counts_by_draft: Mapping[str, int]) -> Counter[str]:
    return Counter({draft: counts_by_draft[draft] for draft in JSON_SCHEMA_TEST_SUITE_TARGET_DRAFTS})


EXPECTED_JSON_SCHEMA_SUITE_GROUP_COUNTS = _expected_counts_by_target_draft(
    EXPECTED_JSON_SCHEMA_SUITE_GROUP_COUNTS_BY_DRAFT
)
EXPECTED_JSON_SCHEMA_SUITE_TEST_COUNTS = _expected_counts_by_target_draft(
    EXPECTED_JSON_SCHEMA_SUITE_TEST_COUNTS_BY_DRAFT
)


@dataclass(frozen=True)
class JsonSchemaSuiteTest:
    """A single JSON-Schema-Test-Suite instance expectation."""

    id: str
    description: str
    data: Any
    valid: bool


@dataclass(frozen=True)
class JsonSchemaSuiteCase:
    """A JSON-Schema-Test-Suite schema group and its instance expectations."""

    id: str
    draft: str
    file_path: Path
    description: str
    schema: Any
    tests: tuple[JsonSchemaSuiteTest, ...]

    @property
    def relative_path(self) -> str:
        """Return the suite path relative to the upstream tests directory."""
        return f"{self.draft}/{self.file_path.name}"


@dataclass(frozen=True)
class JsonSchemaSuiteFailure:
    """A generated-model conformance mismatch."""

    id: str
    reason: str


@dataclass(frozen=True)
class JsonSchemaSuiteReport:
    """Summary of a JSON-Schema-Test-Suite conformance run."""

    checked: int
    excluded: dict[str, str]
    failures: tuple[JsonSchemaSuiteFailure, ...]


def _has_schema_node(value: Any, keyword: str) -> bool:
    match value:
        case dict():
            return keyword in value or any(_has_schema_node(child, keyword) for child in value.values())
        case list():
            return any(_has_schema_node(child, keyword) for child in value)
    return False


def _has_boolean_schema_node(value: Any) -> bool:
    match value:
        case bool():
            return True
        case dict():
            return any(_has_boolean_schema_node(child) for child in value.values())
        case list():
            return any(_has_boolean_schema_node(child) for child in value)
    return False


def _has_external_ref(value: Any) -> bool:
    match value:
        case dict():
            if isinstance(ref := value.get("$ref"), str) and not ref.startswith("#"):
                return True
            return any(_has_external_ref(child) for child in value.values())
        case list():
            return any(_has_external_ref(child) for child in value)
    return False


def _has_object_keywords_without_object_type(value: Any) -> bool:
    match value:
        case dict():
            if "type" not in value and bool(OBJECT_SCHEMA_KEYWORDS & value.keys()):
                return True
            return any(_has_object_keywords_without_object_type(child) for child in value.values())
        case list():
            return any(_has_object_keywords_without_object_type(child) for child in value)
    return False


def _has_array_keywords_without_array_type(value: Any) -> bool:
    match value:
        case dict():
            if "type" not in value and bool(ARRAY_SCHEMA_KEYWORDS & value.keys()):
                return True
            return any(_has_array_keywords_without_array_type(child) for child in value.values())
        case list():
            return any(_has_array_keywords_without_array_type(child) for child in value)
    return False


def _has_nested_items_schema(value: Any) -> bool:
    match value:
        case dict():
            if isinstance(items := value.get("items"), dict) and _has_schema_node(items, "items"):
                return True
            return any(_has_nested_items_schema(child) for child in value.values())
        case list():
            return any(_has_nested_items_schema(child) for child in value)
    return False


def _const_or_enum_value_needs_json_equality(value: Any) -> bool:
    return isinstance(value, bool | int | float | list | dict)


def _has_const_or_enum_needing_json_equality(value: Any) -> bool:
    match value:
        case dict():
            if "const" in value and _const_or_enum_value_needs_json_equality(value["const"]):
                return True
            if isinstance(enum := value.get("enum"), list) and (
                not enum or any(_const_or_enum_value_needs_json_equality(item) for item in enum)
            ):
                return True
            return any(_has_const_or_enum_needing_json_equality(child) for child in value.values())
        case list():
            return any(_has_const_or_enum_needing_json_equality(child) for child in value)
    return False


def _has_recursive_internal_ref(value: Any) -> bool:
    graph: dict[str, set[str]] = {}

    def collect(pointer: str, node: Any) -> None:
        match node:
            case dict():
                graph.setdefault(pointer, set())
                if isinstance(ref := node.get("$ref"), str) and ref.startswith("#/"):
                    graph[pointer].add(ref)
                for key, child in node.items():
                    collect(f"{pointer}/{key}", child)
            case list():
                for index, child in enumerate(node):
                    collect(f"{pointer}/{index}", child)

    collect("#", value)

    def visit(pointer: str, seen: set[str]) -> bool:
        if pointer in seen:
            return True
        return any(visit(ref, {*seen, pointer}) for ref in graph.get(pointer, set()) if ref in graph)

    return any(visit(pointer, set()) for pointer in graph)


def _suite_scope_exclusion_reason(case: JsonSchemaSuiteCase) -> str | None:  # noqa: PLR0911, PLR0912
    schema = case.schema
    if isinstance(schema, bool):
        return "boolean JSON Schemas are not accepted by the generator input path"
    if _has_boolean_schema_node(schema):
        return "boolean subschemas are not accepted by the generator input path"
    if _has_external_ref(schema):
        return "remote $ref cases require the suite remotes, which are outside the initial conformance scope"
    if _has_recursive_internal_ref(schema):
        return "recursive internal $ref cases can recurse during generated model construction"
    if _has_schema_node(schema, "$dynamicRef") or _has_schema_node(schema, "$dynamicAnchor"):
        return "$dynamicRef/$dynamicAnchor require dynamic-scope semantics that generated static models do not support"
    if case.relative_path.endswith("/type.json"):
        return "primitive type strictness differs because generated pydantic v2 models use non-strict types by default"
    if _has_object_keywords_without_object_type(schema):
        return "object keywords without type object allow non-object instances that generated BaseModel roots reject"
    if _has_array_keywords_without_array_type(schema):
        return "array keywords without type array allow non-array instances that generated collection roots reject"
    if _has_nested_items_schema(schema):
        return "nested items validation is not fully represented by generated pydantic v2 models"
    for keyword, reason in UNSUPPORTED_SCHEMA_KEYWORD_REASONS.items():
        if _has_schema_node(schema, keyword):
            return reason
    if any(_has_schema_node(schema, keyword) for keyword in COMBINED_SCHEMA_KEYWORDS):
        return "combined schema applicator semantics need a dedicated generated-model compatibility policy"
    if _has_const_or_enum_needing_json_equality(schema):
        return "const/enum JSON equality semantics are not represented by generated pydantic v2 models"
    return None


def _schema_with_dialect(case: JsonSchemaSuiteCase) -> dict[str, Any]:
    schema = deepcopy(case.schema)
    if not isinstance(schema, dict):
        msg = f"{case.id}: expected an object schema"
        raise TypeError(msg)
    schema.setdefault("$schema", JSON_SCHEMA_TEST_SUITE_DIALECTS[case.draft])
    return schema


def _suite_schema_case(case: JsonSchemaSuiteCase) -> SchemaCase:
    schema = _schema_with_dialect(case)
    return SchemaCase(
        id=case.id,
        input_file_type="jsonschema",
        source_path=case.file_path,
        source_schema=deepcopy(schema),
        codegen_schema=schema,
        temp_input_suffix=".json",
    )


def _case_id(draft: str, path: Path, index: int, description: str) -> str:
    return f"{draft}/{path.name}::{index}::{description}"


def _test_id(case_id: str, index: int, description: str) -> str:
    return f"{case_id}::{index}::{description}"


def iter_json_schema_suite_cases(suite_root: Path) -> Iterator[JsonSchemaSuiteCase]:
    """Yield target draft cases from a JSON-Schema-Test-Suite checkout."""
    tests_root = suite_root / "tests"
    for draft in JSON_SCHEMA_TEST_SUITE_TARGET_DRAFTS:
        for path in sorted((tests_root / draft).glob("*.json")):
            groups = json.loads(path.read_text(encoding="utf-8"))
            for group_index, group in enumerate(groups):
                case_id = _case_id(draft, path, group_index, group["description"])
                yield JsonSchemaSuiteCase(
                    id=case_id,
                    draft=draft,
                    file_path=path,
                    description=group["description"],
                    schema=group["schema"],
                    tests=tuple(
                        JsonSchemaSuiteTest(
                            id=_test_id(case_id, test_index, test["description"]),
                            description=test["description"],
                            data=test["data"],
                            valid=test["valid"],
                        )
                        for test_index, test in enumerate(group["tests"])
                    ),
                )


def json_schema_suite_case_counts(
    cases: Iterable[JsonSchemaSuiteCase],
) -> tuple[Counter[str], Counter[str]]:
    """Return group and instance counts by draft."""
    group_counts: Counter[str] = Counter()
    test_counts: Counter[str] = Counter()
    for case in cases:
        group_counts[case.draft] += 1
        test_counts[case.draft] += len(case.tests)
    return group_counts, test_counts


def _exclusion_reason(case: JsonSchemaSuiteCase, suite_test: JsonSchemaSuiteTest | None = None) -> str | None:
    if suite_test is not None and (reason := JSON_SCHEMA_SUITE_EXCLUDED_CASES.get(suite_test.id)):
        return reason
    if reason := JSON_SCHEMA_SUITE_EXCLUDED_CASES.get(case.id):
        return reason
    return _suite_scope_exclusion_reason(case)


def _validate_instance(adapter: TypeAdapter[Any], suite_test: JsonSchemaSuiteTest) -> JsonSchemaSuiteFailure | None:
    try:
        adapter.validate_python(suite_test.data)
    except ValidationError as exc:
        if not suite_test.valid:
            return None
        return JsonSchemaSuiteFailure(
            suite_test.id,
            f"expected generated model to accept valid instance, got {type(exc).__name__}: {exc}",
        )
    if suite_test.valid:
        return None
    return JsonSchemaSuiteFailure(suite_test.id, "expected generated model to reject invalid instance")


def evaluate_json_schema_suite_cases(
    cases: Iterable[JsonSchemaSuiteCase],
    generated_model_cache: dict[str, Any],
) -> JsonSchemaSuiteReport:
    """Run generated pydantic v2 models against JSON-Schema-Test-Suite expectations."""
    from .codegen import PayloadAdapterError, generate_payload_adapter

    checked = 0
    excluded: dict[str, str] = {}
    failures: list[JsonSchemaSuiteFailure] = []
    for case in cases:
        if reason := _exclusion_reason(case):
            excluded[case.id] = reason
            continue
        try:
            adapter = generate_payload_adapter(_suite_schema_case(case), generated_model_cache)
        except PayloadAdapterError as exc:
            if reason := JSON_SCHEMA_SUITE_EXCLUDED_CASES.get(case.id):
                excluded[case.id] = reason
                continue
            failures.append(JsonSchemaSuiteFailure(case.id, f"generated model unavailable: {exc}"))
            continue
        for suite_test in case.tests:
            if reason := _exclusion_reason(case, suite_test):
                excluded[suite_test.id] = reason
                continue
            checked += 1
            if failure := _validate_instance(adapter, suite_test):
                failures.append(failure)
    return JsonSchemaSuiteReport(checked=checked, excluded=excluded, failures=tuple(failures))


def format_json_schema_suite_failures(failures: Iterable[JsonSchemaSuiteFailure], *, limit: int = 50) -> str:
    """Format a bounded conformance failure report."""
    lines = [f"{failure.id}: {failure.reason}" for failure in failures]
    if len(lines) <= limit:
        return "\n".join(lines)
    remaining = len(lines) - limit
    return "\n".join([*lines[:limit], f"... and {remaining} more"])


def explicit_json_schema_suite_exclusions() -> Mapping[str, str]:
    """Return explicit hand-classified conformance exclusions."""
    return JSON_SCHEMA_SUITE_EXCLUDED_CASES
