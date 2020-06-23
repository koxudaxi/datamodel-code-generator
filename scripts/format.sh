#!/usr/bin/env bash
set -e

black datamodel_code_generator tests
isort --recursive datamodel_code_generator tests
