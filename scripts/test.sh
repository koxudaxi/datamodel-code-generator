#!/usr/bin/env bash
set -e

pytest --cov=datamodel_code_generator --cov-report term-missing tests

