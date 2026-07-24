"""Run one nested generation from a custom formatter thread."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator.format import CustomCodeFormatter

_CHILD_SCHEMA = '{"title":"Child","type":"object","properties":{"value":{"type":"string"}}}'
_child_cwd: Path | None = None
_child_output: str | None = None


def reset() -> None:
    """Reset observations before the formatter runs."""
    global _child_cwd, _child_output  # noqa: PLW0603

    _child_cwd = None
    _child_output = None


def child_cwd() -> Path | None:
    """Return the cwd inherited by the nested request."""
    return _child_cwd


def child_output() -> str | None:
    """Return the nested generated source."""
    return _child_output


def _generate_child() -> str:
    global _child_cwd  # noqa: PLW0603

    _child_cwd = Path.cwd()
    output = generate(
        _CHILD_SCHEMA,
        input_file_type=InputFileType.JsonSchema,
        disable_timestamp=True,
        formatters=[],
    )
    assert isinstance(output, str)
    return output


class CodeFormatter(CustomCodeFormatter):
    """No-op formatter that waits for a nested request."""

    def apply(self, code: str) -> str:
        """Generate child source before returning the outer source unchanged."""
        global _child_output  # noqa: PLW0603

        with ThreadPoolExecutor(max_workers=1) as executor:
            _child_output = executor.submit(_generate_child).result(timeout=10)
        return code
