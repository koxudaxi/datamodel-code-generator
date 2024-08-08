#!/usr/bin/env bash
set -e

ruff check --fix  datamodel_code_generator tests
ruff format datamodel_code_generator tests
python scripts/update_command_help_on_markdown.py



