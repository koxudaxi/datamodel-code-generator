from typing import Any, Dict, ClassVar

from datamodel_code_generator.formatter.base import BaseCodeFormatter


class LicenseFormatter(BaseCodeFormatter):
    """Add a license to file from license file path."""
    formatter_name: ClassVar[str] = "license_formatter"

    def __init__(self, formatter_kwargs: Dict[str, Any]) -> None:
        super().__init__(formatter_kwargs)

        license_txt = formatter_kwargs.get('license_txt', "a license")
        self.license_header = '\n'.join([f'# {line}' for line in license_txt.split('\n')])

    def apply(self, code: str) -> str:
        return f'{self.license_header}\n{code}'
