#!/usr/bin/env bash
set -e

black datamodel_code_generator tests --exclude tests/data
isort --recursive datamodel_code_generator tests
