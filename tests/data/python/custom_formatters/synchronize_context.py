"""Synchronize concurrent formatter calls for generation-context tests."""

from __future__ import annotations

from pathlib import Path
from threading import Event

from datamodel_code_generator.format import CustomCodeFormatter

_CONTEXT_NAMES = ("first", "second")
_entered = {name: Event() for name in _CONTEXT_NAMES}
_released = {name: Event() for name in _CONTEXT_NAMES}
_working_directories: dict[str, Path] = {}


def reset() -> None:
    """Reset synchronization state before a concurrent generation test."""
    _working_directories.clear()
    for event in (*_entered.values(), *_released.values()):
        event.clear()


def wait_until_entered(name: str, timeout: float = 10.0) -> bool:
    """Wait until one named formatter starts applying code."""
    return _entered[name].wait(timeout)


def release(name: str) -> None:
    """Allow one named formatter call to finish."""
    _released[name].set()


def working_directory(name: str) -> Path:
    """Return the process cwd observed by one formatter."""
    return _working_directories[name]


class CodeFormatter(CustomCodeFormatter):
    """No-op formatter whose completion order is controlled by the test."""

    def apply(self, code: str) -> str:
        """Wait for release, then return generated code unchanged."""
        name = self.formatter_kwargs["name"]
        _working_directories[name] = Path.cwd()
        _entered[name].set()
        if not _released[name].wait(10):
            msg = f"Timed out waiting to release {name} formatter"
            raise TimeoutError(msg)
        return code
