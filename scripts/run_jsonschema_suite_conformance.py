"""Run JSON-Schema-Test-Suite conformance tests."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pytest


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "suite_root",
        type=Path,
        help="Path to a checkout of https://github.com/json-schema-org/JSON-Schema-Test-Suite",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Additional pytest arguments after '--'",
    )
    return parser.parse_args()


def main() -> int:
    """Run the JSON-Schema-Test-Suite conformance pytest module."""
    args = parse_args()
    suite_root = args.suite_root.resolve()
    if not suite_root.is_dir():
        print(f"JSON-Schema-Test-Suite checkout does not exist: {suite_root}")
        return 2
    os.environ["JSON_SCHEMA_TEST_SUITE_PATH"] = str(suite_root)
    pytest_args = args.pytest_args
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]
    return pytest.main(["tests/main/test_jsonschema_suite_conformance.py", *pytest_args])


if __name__ == "__main__":
    raise SystemExit(main())
