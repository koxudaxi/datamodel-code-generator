from datamodel_code_generator.formatter.base import (
    BaseCodeFormatter,
    load_code_formatter,
)
from datamodel_code_generator.formatter.ruff import RuffCodeFormatter


def test_ruff_formatter_is_subclass_if_base():
    assert issubclass(RuffCodeFormatter, BaseCodeFormatter)
    assert RuffCodeFormatter.formatter_name == 'ruff'
    assert hasattr(RuffCodeFormatter, 'apply')


def test_load_ruff_formatter():
    _ = load_code_formatter('datamodel_code_generator.formatter.RuffCodeFormatter', {})
