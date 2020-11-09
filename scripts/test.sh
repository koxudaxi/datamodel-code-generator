#!/usr/bin/env bash
set -e

python -m venv venv

source venv/bin/activate
pip install -e .[all] isort==4.3.21 "black>=19.10b0,<20"

pytest --cov=datamodel_code_generator --cov-report term-missing tests

deactivate
rm -r venv
