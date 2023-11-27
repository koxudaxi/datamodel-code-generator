from importlib import import_module
from typing import Any, ClassVar, Dict

from datamodel_code_generator.imports import Import


class BaseCodeFormatter:
    """An abstract class for representing a code formatter.

    All formatters that format a generated code should subclass
    it. All subclass should override `apply` method which
    has a string with code in input and returns a formatted code in string.
    We also need to determine a `formatter_name` field
    which is unique name of formatter.

    Example:
        >>> class CustomHeaderCodeFormatter(BaseCodeFormatter):
        ...     formatter_name: ClassVar[str] = "custom"
        ...     def __init__(self, formatter_kwargs: Dict[str, Any]) -> None:
        ...         super().__init__(formatter_kwargs=formatter_kwargs)
        ...
        ...         default_header = "my header"
        ...         self.header: str = self.formatter_kwargs.get("header", default_header)
        ...     def apply(self, code: str) -> str:
        ...         return f'# {self.header}\\n{code}'
        ...
        ... formatter_kwargs = {"header": "formatted with CustomHeaderCodeFormatter"}
        ... formatter = CustomHeaderCodeFormatter(formatter_kwargs)
        ... code = '''x = 1\ny = 2'''
        ... print(formatter.apply(code))
        # formatted with CustomHeaderCodeFormatter
        x = 1
        y = 2

    """

    formatter_name: ClassVar[str] = ''

    def __init__(self, formatter_kwargs: Dict[str, Any]) -> None:
        if self.formatter_name == '':
            raise ValueError('`formatter_name` should be not empty string')

        self.formatter_kwargs = formatter_kwargs

    def apply(self, code: str) -> str:
        raise NotImplementedError


def load_code_formatter(
    custom_formatter_import: str, custom_formatters_kwargs: Dict[str, Any]
) -> BaseCodeFormatter:
    """Load a formatter by import path as string.

    Args:
        custom_formatter_import: custom formatter module.
        custom_formatters_kwargs: kwargs for custom formatters from config.

    Examples:
        for default formatters use
        >>> custom_formatter_import = "datamodel_code_generator.formatter.BlackCodeFormatter"
        this is equivalent to code
        >>> from datamodel_code_generator.formatter import BlackCodeFormatter

        custom formatter
        >>> custom_formatter_import = "my_package.my_sub_package.FormatterName"
        this is equivalent to code
        >>> from my_package.my_sub_package import FormatterName

    """

    import_ = Import.from_full_path(custom_formatter_import)
    imported_module_ = import_module(import_.from_)

    if not hasattr(imported_module_, import_.import_):
        raise NameError(
            f'Custom formatter module `{import_.from_}` not contains formatter with name `{import_.import_}`'
        )

    formatter_class = imported_module_.__getattribute__(import_.import_)

    if not issubclass(formatter_class, BaseCodeFormatter):
        raise TypeError(
            f'The custom module `{custom_formatter_import}` must inherit from '
            '`datamodel-code-generator.formatter.BaseCodeFormatter`'
        )

    custom_formatter_kwargs = custom_formatters_kwargs.get(
        formatter_class.formatter_name, {}
    )

    return formatter_class(formatter_kwargs=custom_formatter_kwargs)
