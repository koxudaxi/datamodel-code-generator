#!/usr/bin/env bash
set -e

black --check datamodel_code_generator tests
ruff datamodel_code_generator tests

mypy datamodel_code_generator
