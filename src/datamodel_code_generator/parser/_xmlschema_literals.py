"""Literal and temporal helpers for XML Schema parsing."""

from __future__ import annotations

import contextlib
import datetime as datetime_module
import re
from decimal import Decimal
from math import inf, isfinite, nan
from typing import Any

from datamodel_code_generator.imports import Import

XML_DATE_PATTERN = re.compile(r"^(?P<date>-?\d{4,}-\d{2}-\d{2})(?:Z|[+-]\d{2}:\d{2})?$")
DAY_TIME_DURATION_PATTERN = re.compile(
    r"^(?P<sign>-)?P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)
XSD_WHITESPACE_CHARS = " \t\n\r"
IMPORT_DATETIME_MODULE = Import(import_="datetime", alias="datetime_module")


class _PythonExpression:
    """Raw Python expression rendered through repr() with required imports."""

    __slots__ = ("code", "imports")

    def __init__(self, code: str, *imports: Import) -> None:
        self.code = code
        self.imports = imports

    def __repr__(self) -> str:
        return self.code


def _collect_python_expression_imports(value: Any) -> tuple[Import, ...]:
    if isinstance(value, _PythonExpression):
        return value.imports
    if isinstance(value, dict):
        return tuple(import_ for item in value.values() for import_ in _collect_python_expression_imports(item))
    if isinstance(value, (list, tuple, set)):
        return tuple(import_ for item in value for import_ in _collect_python_expression_imports(item))
    return ()


def _safe_float(value: str) -> float | None:
    value = value.strip(XSD_WHITESPACE_CHARS)
    try:
        number = float(value)
    except ValueError:
        return None
    if isfinite(number):
        return number
    match value:
        case "INF" | "+INF":
            return inf
        case "-INF":
            return -inf
        case "NaN":
            return nan
    return None


def _safe_bool(value: str) -> bool | None:
    match value.strip(XSD_WHITESPACE_CHARS):
        case "true" | "1":
            return True
        case "false" | "0":
            return False
    return None


def _datetime_expression(code: str) -> _PythonExpression:
    return _PythonExpression(code, IMPORT_DATETIME_MODULE)


def _normalize_timezone(value: str) -> str:
    return f"{value[:-1]}+00:00" if value.endswith("Z") else value


def _safe_date_expression(value: str) -> _PythonExpression | None:
    value = value.strip(XSD_WHITESPACE_CHARS)
    date_match = XML_DATE_PATTERN.match(value)
    if date_match is None:
        return None
    date_value = date_match["date"]
    if value != date_value:
        return None
    with contextlib.suppress(ValueError):
        datetime_module.date.fromisoformat(date_value)
        return _datetime_expression(f"datetime_module.date.fromisoformat({date_value!r})")
    return None


def _safe_time_expression(value: str) -> _PythonExpression | None:
    value = value.strip(XSD_WHITESPACE_CHARS)
    normalized = _normalize_timezone(value)
    with contextlib.suppress(ValueError):
        datetime_module.time.fromisoformat(normalized)
        return _datetime_expression(f"datetime_module.time.fromisoformat({normalized!r})")
    return None


def _safe_datetime_expression(value: str) -> _PythonExpression | None:
    value = value.strip(XSD_WHITESPACE_CHARS)
    normalized = _normalize_timezone(value)
    with contextlib.suppress(ValueError):
        datetime_module.datetime.fromisoformat(normalized)
        return _datetime_expression(f"datetime_module.datetime.fromisoformat({normalized!r})")
    return None


def _safe_day_time_duration_expression(value: str) -> _PythonExpression | None:
    value = value.strip(XSD_WHITESPACE_CHARS)
    duration_match = DAY_TIME_DURATION_PATTERN.match(value)
    if duration_match is None:
        return None

    days = duration_match["days"]
    hours = duration_match["hours"]
    minutes = duration_match["minutes"]
    seconds = duration_match["seconds"]
    if not any((days, hours, minutes, seconds)):
        return None

    arguments: list[str] = []
    if days:
        arguments.append(f"days={int(days)}")
    if hours:
        arguments.append(f"hours={int(hours)}")
    if minutes:
        arguments.append(f"minutes={int(minutes)}")
    if seconds:
        seconds_in_microseconds = Decimal(seconds) * 1_000_000
        integral_microseconds = seconds_in_microseconds.to_integral_value()
        if seconds_in_microseconds != integral_microseconds:
            return None
        whole_seconds, microseconds = divmod(int(integral_microseconds), 1_000_000)
        if whole_seconds:
            arguments.append(f"seconds={whole_seconds}")
        if microseconds:
            arguments.append(f"microseconds={microseconds}")

    expression = f"datetime_module.timedelta({', '.join(arguments)})" if arguments else "datetime_module.timedelta(0)"
    if duration_match["sign"]:
        expression = f"-{expression}"
    return _datetime_expression(expression)
