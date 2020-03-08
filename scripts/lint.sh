#!/usr/bin/env bash

set -e

black --check datamodel_code_generator tests
isort --recursive --check-only datamodel_code_generator tests
mypy datamodel_code_generator
