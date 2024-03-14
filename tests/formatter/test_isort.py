from datamodel_code_generator.formatter.base import (
    BaseCodeFormatter,
    load_code_formatter,
)
from datamodel_code_generator.formatter.isort import IsortCodeFormatter


def test_isort_formatter_is_subclass_if_base():
    assert issubclass(IsortCodeFormatter, BaseCodeFormatter)
    assert IsortCodeFormatter.formatter_name == 'isort'
    assert hasattr(IsortCodeFormatter, 'apply')


def test_load_isort_formatter():
    _ = load_code_formatter('datamodel_code_generator.formatter.IsortCodeFormatter', {})
