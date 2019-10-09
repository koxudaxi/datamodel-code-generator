#!/usr/bin/env bash
set -e

black datamodel_code_generator tests --check --skip-string-normalization
isort --recursive --check-only -w 88  --combine-as --thirdparty datamodel_code_generator datamodel_code_generator tests -m 3 -tc
mypy pydataapi --disallow-untyped-defs --ignore-missing-imports