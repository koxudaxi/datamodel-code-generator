from importlib import import_module
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

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


class CodeFormattersRunner:
    """Runner of code formatters."""

    disable_default_formatter: bool
    default_formatters: List[BaseCodeFormatter]
    custom_formatters: List[BaseCodeFormatter]
    custom_formatters_kwargs: Dict[str, Any]

    _mapping_from_formatter_name_to_formatter_module: Dict[str, str] = {
        'black': 'datamodel_code_generator.formatter.BlackCodeFormatter',
        'isort': 'datamodel_code_generator.formatter.IsortCodeFormatter',
        'ruff': 'datamodel_code_generator.formatter.RuffCodeFormatter',
    }
    _default_formatters: List[str] = [
        'datamodel_code_generator.formatter.RuffCodeFormatter'
    ]

    def __init__(
        self,
        disable_default_formatter: bool = False,
        default_formatter: Optional[List[str]] = None,
        custom_formatters: Optional[List[str]] = None,
        custom_formatters_kwargs: Optional[Dict[str, Any]] = None,
        settings_path: Optional[Path] = None,
        wrap_string_literal: Optional[bool] = None,
        skip_string_normalization: bool = True,
        known_third_party: Optional[List[str]] = None,
    ) -> None:
        self.disable_default_formatter = disable_default_formatter
        self.custom_formatters_kwargs = custom_formatters_kwargs or {}

        self.default_formatters = self._check_default_formatters(default_formatter)
        self.custom_formatters = self._check_custom_formatters(custom_formatters)

        self.custom_formatters_kwargs['black'] = {
            'settings_path': settings_path,
            'wrap_string_literal': wrap_string_literal,
            'skip_string_normalization': skip_string_normalization,
        }
        self.custom_formatters_kwargs['isort'] = {
            'settings_path': settings_path,
            'known_third_party': known_third_party,
        }

    def _load_formatters(self, formatters: List[str]) -> List[BaseCodeFormatter]:
        return [
            load_code_formatter(custom_formatter_import, self.custom_formatters_kwargs)
            for custom_formatter_import in formatters
        ]

    def _check_default_formatters(
        self,
        default_formatters: Optional[List[str]],
    ) -> List[BaseCodeFormatter]:
        if self.disable_default_formatter is True:
            return []

        if default_formatters is None:
            return self._load_formatters(self._default_formatters)

        formatters = []
        for formatter in default_formatters:
            if formatter not in self._mapping_from_formatter_name_to_formatter_module:
                raise ValueError(f'Unknown default formatter: {formatter}')

            formatters.append(
                self._mapping_from_formatter_name_to_formatter_module[formatter]
            )

        return self._load_formatters(formatters)

    def _check_custom_formatters(
        self, custom_formatters: Optional[List[str]]
    ) -> List[BaseCodeFormatter]:
        if custom_formatters is None:
            return []

        return self._load_formatters(custom_formatters)

    def format_code(
        self,
        code: str,
    ) -> str:
        for formatter in self.default_formatters:
            code = formatter.apply(code)

        for formatter in self.custom_formatters:
            code = formatter.apply(code)

        return code
