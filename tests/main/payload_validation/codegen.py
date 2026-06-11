"""Generate and import payload models for validation tests."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import TypeAdapter

from datamodel_code_generator.__main__ import Exit, main

from .constants import PAYLOAD_CLASS_NAME, PAYLOAD_TARGET_PYTHON_VERSION

if TYPE_CHECKING:
    from pathlib import Path

    from .models import SchemaCase


def _safe_filename(case_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", case_id)


def _write_input_schema(case: SchemaCase, directory: Path) -> Path:
    input_path = directory / f"input{case.temp_input_suffix}"
    if case.temp_input_suffix == ".json":
        input_path.write_text(json.dumps(case.codegen_schema), encoding="utf-8")
    else:
        import yaml

        input_path.write_text(yaml.safe_dump(case.codegen_schema, sort_keys=False), encoding="utf-8")
    return input_path


class PayloadAdapterError(Exception):
    """Raised when a generated payload adapter cannot be created."""


def _payload_codegen_args(case: SchemaCase, input_path: Path, output_path: Path) -> list[str]:
    args = [
        "--input",
        str(input_path),
        "--input-file-type",
        case.input_file_type,
        "--output",
        str(output_path),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        PAYLOAD_TARGET_PYTHON_VERSION,
        "--class-name",
        PAYLOAD_CLASS_NAME,
        "--disable-timestamp",
    ]
    if case.input_file_type == "openapi":
        args.extend(["--openapi-scopes", "schemas", "--strict-nullable"])
    return args


def _load_payload_type(module_name: str, output_path: Path) -> type[Any]:
    spec = importlib.util.spec_from_file_location(module_name, output_path)
    if spec is None or spec.loader is None:
        msg = f"Unable to import generated module from {output_path}"
        raise PayloadAdapterError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        msg = f"Generated module failed to import: {type(exc).__name__}: {exc}"
        raise PayloadAdapterError(msg) from exc
    payload_type = getattr(module, PAYLOAD_CLASS_NAME, None)
    if payload_type is None:
        generated_types = [
            value
            for value in module.__dict__.values()
            if isinstance(value, type) and getattr(value, "__module__", None) == module_name
        ]
        if len(generated_types) != 1:
            msg = f"Generated module did not contain {PAYLOAD_CLASS_NAME}"
            raise PayloadAdapterError(msg)
        payload_type = generated_types[0]
    return payload_type


def generate_payload_adapter(case: SchemaCase, generated_model_cache: dict[str, Any]) -> TypeAdapter[Any]:
    """Generate or load the Pydantic adapter for a payload validation case."""
    adapters: dict[str, TypeAdapter[Any]] = generated_model_cache["adapters"]
    if case.id in adapters:
        return adapters[case.id]

    case_dir = generated_model_cache["base"] / _safe_filename(case.id)
    case_dir.mkdir(exist_ok=True)
    input_path = _write_input_schema(case, case_dir)
    output_path = case_dir / "model.py"
    return_code = main(_payload_codegen_args(case, input_path, output_path))
    if return_code != Exit.OK:
        msg = f"Generation failed with exit code {return_code!r}"
        raise PayloadAdapterError(msg)
    module_name = f"payload_validation_{abs(hash(case.id))}"
    payload_type = _load_payload_type(module_name, output_path)
    try:
        adapter = TypeAdapter(payload_type)
    except Exception as exc:
        msg = f"Generated payload type could not be adapted: {type(exc).__name__}: {exc}"
        raise PayloadAdapterError(msg) from exc
    adapters[case.id] = adapter
    return adapter


def load_generated_payload_adapter(case: SchemaCase, generated_model_cache: dict[str, Any]) -> TypeAdapter[Any]:
    """Generate or load the Pydantic adapter for a payload validation case."""
    try:
        return generate_payload_adapter(case, generated_model_cache)
    except PayloadAdapterError as exc:  # pragma: no cover
        pytest.fail(f"{case.id}: {exc}")
        raise AssertionError from exc
