from datamodel_code_generator.formatter.base import (
    BaseCodeFormatter,
    load_code_formatter,
)
from datamodel_code_generator.formatter.black import BlackCodeFormatter


def test_black_formatter_is_subclass_if_base():
    assert issubclass(BlackCodeFormatter, BaseCodeFormatter)
    assert BlackCodeFormatter.formatter_name == 'black'
    assert hasattr(BlackCodeFormatter, 'apply')


def test_load_black_formatter():
    _ = load_code_formatter('datamodel_code_generator.formatter.BlackCodeFormatter', {})
