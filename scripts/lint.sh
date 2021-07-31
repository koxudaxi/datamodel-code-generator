#!/usr/bin/env bash
set -e

black --check datamodel_code_generator tests
isort --check-only datamodel_code_generator tests

mypy datamodel_code_generator
