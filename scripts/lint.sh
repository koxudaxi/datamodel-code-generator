#!/usr/bin/env bash

set -e

python -m venv lint
source lint/bin/activate

pip install black==19.10b0 "isort>=4.3.21,<5.0"

black --check datamodel_code_generator tests
isort --check-only datamodel_code_generator tests

deactivate
rm -r lint

mypy datamodel_code_generator
