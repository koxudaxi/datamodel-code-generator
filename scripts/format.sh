#!/usr/bin/env bash
set -e

black datamodel_code_generator tests --skip-string-normalization
isort --recursive datamodel_code_generator tests
