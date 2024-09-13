#!/usr/bin/env bash
set -e

ruff check datamodel_code_generator tests
ruff format --check datamodel_code_generator tests
python scripts/update_command_help_on_markdown.py --validate

mypy datamodel_code_generator
