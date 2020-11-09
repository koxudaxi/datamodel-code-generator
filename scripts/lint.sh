#!/usr/bin/env bash

set -e

ISORT_VERSION=$(python -c "import isort; print(isort.__version__.split('.')[0])")

if [ "$ISORT_VERSION" == 4 ] ; then
   ISORT_OPT="--recursive"
fi

black --check datamodel_code_generator tests
isort --check-only $ISORT_OPT datamodel_code_generator tests


mypy datamodel_code_generator
