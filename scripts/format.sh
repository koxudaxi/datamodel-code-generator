#!/usr/bin/env bash
set -e

black datamodel_code_generator tests
isort $ISORT_OPT datamodel_code_generator tests
