#!/usr/bin/env bash
set -e

ruff check datamodel_code_generator tests
ruff format --check datamodel_code_generator tests

mypy datamodel_code_generator
