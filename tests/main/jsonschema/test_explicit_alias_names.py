"""Diagnose invalid explicit field aliases before writing generated code."""

from __future__ import annotations

import json
import operator
import re
import subprocess
import sys
from collections import defaultdict
from contextlib import nullcontext
from typing import TYPE_CHECKING

import msgspec
import pytest

from datamodel_code_generator import DataModelType, Error, InputFileType, generate
from datamodel_code_generator.__main__ import Exit
from tests.conftest import assert_output
from tests.main.conftest import (
    ALIASES_DATA_PATH,
    GRAPHQL_DATA_PATH,
    JSON_SCHEMA_DATA_PATH,
    _generated_model,
    assert_generated_model_json_validation,
    run_generate_file_and_assert,
    run_main_and_assert,
)
from tests.main.jsonschema.conftest import assert_file_content

if TYPE_CHECKING:
    from pathlib import Path

ALIASES = json.loads((ALIASES_DATA_PATH / "explicit_alias_names.json").read_text())


@pytest.mark.parametrize(
    ("case", "backend"),
    [
        (case, backend)
        for case in ["duplicate", "existing", "scoped_duplicate", "keyword", "invalid", "empty"]
        for backend in DataModelType
        if backend != DataModelType.PydanticV2BaseModel or case not in {"keyword", "invalid", "empty"}
    ]
    + [
        ("snake_existing", DataModelType.PydanticV2BaseModel),
        ("snake_duplicate", DataModelType.PydanticV2BaseModel),
        ("nfkc_duplicate", DataModelType.PydanticV2BaseModel),
        ("snake_config", DataModelType.PydanticV2BaseModel),
        ("reserved_config", DataModelType.PydanticV2BaseModel),
        ("reserved_validate", DataModelType.PydanticV2BaseModel),
        ("reserved_msgspec", DataModelType.MsgspecStruct),
    ],
)
def test_explicit_alias_names_invalid(
    case: str, backend: DataModelType, output_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Reject collisions and invalid Python identifiers for every output model."""
    aliases = ALIASES[case]
    field_name = (
        "b" if case in {"duplicate", "existing", "scoped_duplicate", "snake_duplicate", "nfkc_duplicate"} else "a"
    )
    alias = aliases.get(f"AliasNames.{field_name}", aliases.get(field_name))
    reason = (
        "conflicts with another field" if field_name == "b" or case == "snake_existing" else "is not a valid field name"
    )
    message = f"Alias {alias!r} for field {field_name!r} {reason}."
    with pytest.raises(Error, match=re.escape(message)):
        generate(
            JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
            input_file_type=InputFileType.JsonSchema,
            output=output_file,
            aliases=aliases,
            output_model_type=backend,
            snake_case_field=case != "nfkc_duplicate",
        )
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--aliases",
            json.dumps(aliases),
            "--output-model-type",
            backend.value,
            *([] if case == "nfkc_duplicate" else ["--snake-case-field"]),
        ],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=message,
        output_should_not_exist=True,
    )


@pytest.mark.parametrize("case", ["normal", "global", "scoped", "choices", "neutral_reserved", "scoped_empty_choices"])
def test_explicit_alias_names_valid(case: str, output_file: Path) -> None:
    """Preserve valid aliases, spelling, precedence, field order and required fields."""
    backend = DataModelType.DataclassesDataclass if case == "neutral_reserved" else DataModelType.PydanticV2BaseModel
    run_generate_file_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type=InputFileType.JsonSchema,
        aliases=ALIASES[case],
        output_model_type=backend,
        snake_case_field=True,
        disable_timestamp=True,
        assert_func=assert_file_content,
        expected_file=f"explicit_alias_names_{case}.py",
        unchanged_inputs={"aliases": ALIASES[case]},
    )
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--aliases",
            json.dumps(ALIASES[case]),
            "--snake-case-field",
            "--output-model-type",
            backend.value,
            "--disable-timestamp",
        ],
        assert_func=assert_file_content,
        expected_file=f"explicit_alias_names_{case}.py",
        force_exec_validation=True,
    )
    fields = {
        "normal": ("a", "b"),
        "scoped_empty_choices": ("value", "b"),
        "global": ("camel_name", "count"),
        "scoped": ("value", "count"),
        "choices": ("first", "count"),
        "neutral_reserved": ("model_config", "model_validate"),
    }[case]
    data = {fields[0]: "A", fields[1]: 1} if case == "neutral_reserved" else {"a": "A", "b": 1}
    assert_generated_model_json_validation(
        output_file,
        module_name=f"explicit_alias_names_{case}",
        model_name="AliasNames",
        valid_json=json.dumps(data),
        invalid_json=json.dumps({next(iter(data)): "A"}),
        expected_error_type="missing",
        expected_repr=f"AliasNames({fields[0]}='A', {fields[1]}=1)",
    )


@pytest.mark.parametrize(
    "case",
    [
        "keyword",
        "invalid",
        "empty",
        "msgspec_field",
        "shadow_dict",
        "shadow_json",
        "shadow_copy",
        "shadow_schema",
        "shadow_validate",
        "shadow_model_fields",
        "namespace_warning",
    ],
)
def test_explicit_alias_names_valid_shadows(case: str, output_file: Path) -> None:
    """Preserve baseline-valid identifiers, including warning-only Pydantic shadows."""
    backend = DataModelType.MsgspecStruct if case == "msgspec_field" else DataModelType.PydanticV2BaseModel
    run_generate_file_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type=InputFileType.JsonSchema,
        aliases=ALIASES[case],
        output_model_type=backend,
        disable_timestamp=True,
        assert_func=assert_file_content,
        expected_file=f"explicit_alias_names_{case}.py",
        unchanged_inputs={"aliases": ALIASES[case]},
    )
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--aliases",
            json.dumps(ALIASES[case]),
            "--output-model-type",
            backend.value,
            "--disable-timestamp",
        ],
        assert_func=assert_file_content,
        expected_file=f"explicit_alias_names_{case}.py",
        force_exec_validation=True,
    )
    name = {"keyword": "class_", "invalid": "not_valid", "empty": "field_", "msgspec_field": "field"}.get(
        case, ALIASES[case]["a"]
    )
    if case == "msgspec_field":
        with _generated_model(output_file, "explicit_alias_names_msgspec_field", "AliasNames") as model:
            parsed = msgspec.json.decode(b'{"a": "A", "b": 1}', type=model)
            assert_output(
                json.dumps(msgspec.to_builtins(parsed), sort_keys=True) + "\n" + repr(parsed) + "\n",
                JSON_SCHEMA_DATA_PATH.parent / "payloads" / "explicit_alias_msgspec_field.txt",
            )
            with pytest.raises(msgspec.ValidationError, match="missing required field `b`"):
                msgspec.json.decode(b'{"a": "A"}', type=model)
        return
    with (
        pytest.warns(UserWarning, match="shadows an attribute|conflicts with protected namespace")
        if case.startswith("shadow_") or case == "namespace_warning"
        else nullcontext()
    ):
        assert_generated_model_json_validation(
            output_file,
            module_name=f"explicit_alias_names_{case}",
            model_name="AliasNames",
            valid_json='{"a": "A", "b": 1}',
            invalid_json='{"a": "A"}',
            expected_error_type="missing",
            expected_repr=f"AliasNames({name}='A', b=1)",
        )


@pytest.mark.parametrize("inherited", [False, True])
def test_explicit_alias_names_configured_namespace(inherited: bool, output_file: Path) -> None:
    """Honor generated protected namespace configuration and inherited configuration."""
    input_path = JSON_SCHEMA_DATA_PATH / (
        "explicit_alias_names_inherited.json" if inherited else "explicit_alias_names.json"
    )
    config_path = ALIASES_DATA_PATH / (
        "explicit_alias_names_config_inherited.json" if inherited else "explicit_alias_names_config.json"
    )
    extra = json.loads(config_path.read_text())
    aliases = {"a": "model_validate"}
    expected_file = f"explicit_alias_names_configured_{inherited}.py"
    run_generate_file_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type=InputFileType.JsonSchema,
        aliases=aliases,
        extra_template_data=defaultdict(dict, extra),
        disable_timestamp=True,
        assert_func=assert_file_content,
        expected_file=expected_file,
    )
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--aliases", json.dumps(aliases), "--extra-template-data", str(config_path), "--disable-timestamp"],
        force_exec_validation=True,
    )
    with pytest.warns(UserWarning, match="shadows an attribute"):
        assert_generated_model_json_validation(
            output_file,
            module_name=f"explicit_alias_names_configured_{inherited}",
            model_name="AliasNames",
            valid_json='{"a": "A", "b": 1}',
            invalid_json='{"a": "A"}',
            expected_error_type="missing",
            expected_attribute_path=("model_validate",),
            expected_attribute_value="A",
        )


@pytest.mark.parametrize("backend", list(DataModelType))
def test_explicit_alias_names_unicode(backend: DataModelType, output_file: Path) -> None:
    """Preserve Unicode names alongside synthetic root and boolean-schema fields."""
    expected_file = f"explicit_alias_names_unicode_{backend.name}.py"
    run_generate_file_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names_unicode.json",
        output_path=output_file,
        input_file_type=InputFileType.JsonSchema,
        aliases=ALIASES["unicode"],
        output_model_type=backend,
        disable_timestamp=True,
        assert_func=assert_file_content,
        expected_file=expected_file,
    )
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "explicit_alias_names_unicode.json",
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=[
            "--aliases",
            json.dumps(ALIASES["unicode"]),
            "--output-model-type",
            backend.value,
            "--disable-timestamp",
        ],
        assert_func=assert_file_content,
        expected_file=expected_file,
        force_exec_validation=True,
    )


@pytest.mark.parametrize("case", ["global", "literal", "duplicate", "reserved_config"])
def test_explicit_alias_names_graphql(case: str, output_file: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Use original wire names for aliases in GraphQL and ignore enum members."""
    aliases = ALIASES["global" if case == "literal" else case]
    if case in {"global", "literal"}:
        expected_file = f"explicit_alias_names_graphql_{case}.py"
        run_generate_file_and_assert(
            input_path=GRAPHQL_DATA_PATH / "explicit_alias_names.graphql",
            output_path=output_file,
            input_file_type=InputFileType.GraphQL,
            aliases=aliases,
            enum_field_as_literal="all" if case == "literal" else None,
            disable_timestamp=True,
            assert_func=assert_file_content,
            expected_file=expected_file,
        )
        run_main_and_assert(
            input_path=GRAPHQL_DATA_PATH / "explicit_alias_names.graphql",
            output_path=output_file,
            input_file_type="graphql",
            extra_args=[
                "--aliases",
                json.dumps(aliases),
                "--disable-timestamp",
                *(["--enum-field-as-literal", "all"] if case == "literal" else []),
            ],
            assert_func=assert_file_content,
            expected_file=expected_file,
            force_exec_validation=True,
        )
        return
    message = (
        "Alias 'same' for field 'b' conflicts with another field."
        if case == "duplicate"
        else "Alias 'model_config' for field 'a' is not a valid field name."
    )
    with pytest.raises(Error, match=re.escape(message)):
        generate(
            GRAPHQL_DATA_PATH / "explicit_alias_names.graphql",
            input_file_type=InputFileType.GraphQL,
            output=output_file,
            aliases=aliases,
        )
    run_main_and_assert(
        input_path=GRAPHQL_DATA_PATH / "explicit_alias_names.graphql",
        output_path=output_file,
        input_file_type="graphql",
        extra_args=["--aliases", json.dumps(aliases)],
        expected_exit=Exit.ERROR,
        capsys=capsys,
        expected_stderr_contains=message,
        output_should_not_exist=True,
    )


@pytest.mark.parametrize("inherited", [False, True])
def test_explicit_alias_names_custom_namespace(
    inherited: bool, output_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not assume default protected namespaces for an external custom base."""
    input_path = JSON_SCHEMA_DATA_PATH / (
        "explicit_alias_names_inherited.json" if inherited else "explicit_alias_names.json"
    )
    monkeypatch.syspath_prepend(str(JSON_SCHEMA_DATA_PATH.parent / "python"))
    base_class = "explicit_alias_base.NamespaceBase"
    expected_file = f"explicit_alias_names_custom_{inherited}.py"
    run_generate_file_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type=InputFileType.JsonSchema,
        aliases={"a": "model_validate"},
        base_class=base_class,
        disable_timestamp=True,
        assert_func=assert_file_content,
        expected_file=expected_file,
    )
    run_main_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type="jsonschema",
        extra_args=["--aliases", '{"a": "model_validate"}', "--base-class", base_class, "--disable-timestamp"],
        assert_func=assert_file_content,
        expected_file=expected_file,
        force_exec_validation=True,
    )
    with pytest.warns(UserWarning, match="shadows an attribute"):
        assert_generated_model_json_validation(
            output_file,
            module_name=f"explicit_alias_names_custom_{inherited}",
            model_name="AliasNames",
            valid_json='{"a": "A", "b": 1}',
            invalid_json='{"a": "A"}',
            expected_error_type="missing",
            expected_attribute_path=("model_validate",),
            expected_attribute_value="A",
        )


@pytest.mark.parametrize(
    "case",
    json.loads(
        (JSON_SCHEMA_DATA_PATH.parent / "payloads" / "explicit_alias_namespace_inheritance_cases.json").read_text()
    ),
    ids=operator.itemgetter("name"),
)
def test_explicit_alias_names_external_namespace_precedence(
    case: dict, output_file: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use effective base precedence and preserve uncertainty from an external base."""
    directory = JSON_SCHEMA_DATA_PATH / "explicit_alias_namespace_inheritance"
    input_path = directory / f"{case['schema']}.json"
    extra = defaultdict(dict, case["config"])
    aliases = {"Child.a": "model_validate"}
    base_class = "explicit_alias_base.NamespaceBase"
    monkeypatch.syspath_prepend(str(JSON_SCHEMA_DATA_PATH.parent / "python"))
    args = [
        "--aliases",
        json.dumps(aliases),
        "--extra-template-data",
        str(directory / f"{case['name']}_config.json"),
        "--base-class",
        base_class,
        "--disable-timestamp",
    ]
    if not case["valid"]:
        message = "Alias 'model_validate' for field 'a' is not a valid field name."
        with pytest.raises(Error, match=re.escape(message)):
            generate(
                input_path,
                input_file_type=InputFileType.JsonSchema,
                output=output_file,
                aliases=aliases,
                extra_template_data=extra,
                base_class=base_class,
            )
        run_main_and_assert(
            input_path=input_path,
            output_path=output_file,
            input_file_type="jsonschema",
            extra_args=args,
            expected_exit=Exit.ERROR,
            capsys=capsys,
            expected_stderr_contains=message,
            output_should_not_exist=True,
        )
        return
    expected = f"explicit_alias_namespace_inheritance/{case['name']}.py"
    run_generate_file_and_assert(
        input_path=input_path,
        output_path=output_file,
        input_file_type=InputFileType.JsonSchema,
        aliases=aliases,
        extra_template_data=extra,
        base_class=base_class,
        disable_timestamp=True,
        assert_func=assert_file_content,
        expected_file=expected,
    )
    for entrypoint in ("api", "cli"):
        if entrypoint == "cli":
            run_main_and_assert(
                input_path=input_path,
                output_path=output_file,
                input_file_type="jsonschema",
                extra_args=args,
                assert_func=assert_file_content,
                expected_file=expected,
            )
        result = subprocess.run(
            [
                sys.executable,
                str(JSON_SCHEMA_DATA_PATH.parent / "python" / "explicit_alias_namespace_runtime.py"),
                str(output_file),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert_output(
            result.stdout,
            JSON_SCHEMA_DATA_PATH.parent
            / "expected"
            / "main"
            / "jsonschema"
            / "explicit_alias_namespace_inheritance"
            / f"{case['name']}_runtime.txt",
        )
