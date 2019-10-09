#!/usr/bin/env bash
set -e

black datamodel_code_generator tests --skip-string-normalization
isort --recursive -w 88  --combine-as --thirdparty datamodel_code_generator datamodel_code_generator tests -m 3 -tc
