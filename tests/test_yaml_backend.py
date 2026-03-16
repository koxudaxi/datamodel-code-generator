"""Tests for YAML backend detection and ryaml/PyYAML switching."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import yaml

from datamodel_code_generator import InputFileType, infer_input_type, load_yaml
from datamodel_code_generator.util import get_yaml_backend, get_yaml_parse_errors

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _clear_caches() -> Iterator[None]:
    """Clear lru_cache before and after each test."""
    get_yaml_backend.cache_clear()
    get_yaml_parse_errors.cache_clear()
    yield
    get_yaml_backend.cache_clear()
    get_yaml_parse_errors.cache_clear()


class TestGetYamlBackend:
    """Tests for get_yaml_backend()."""

    def test_without_ryaml(self) -> None:
        """When ryaml is not importable, returns 'pyyaml'."""
        with patch.dict("sys.modules", {"ryaml": None}):
            assert get_yaml_backend() == "pyyaml"

    def test_with_ryaml(self) -> None:
        """When ryaml is importable, returns 'ryaml'."""
        mock_ryaml = MagicMock()
        with patch.dict("sys.modules", {"ryaml": mock_ryaml}):
            assert get_yaml_backend() == "ryaml"


class TestGetYamlParseErrors:
    """Tests for get_yaml_parse_errors()."""

    def test_pyyaml_only(self) -> None:
        """Without ryaml, only yaml.YAMLError is returned."""
        with patch.dict("sys.modules", {"ryaml": None}):
            errors = get_yaml_parse_errors()
            assert errors == (yaml.YAMLError,)

    def test_includes_ryaml(self) -> None:
        """With ryaml, InvalidYamlError is included."""
        mock_ryaml = MagicMock()
        mock_ryaml.InvalidYamlError = type("InvalidYamlError", (Exception,), {})
        with patch.dict("sys.modules", {"ryaml": mock_ryaml}):
            errors = get_yaml_parse_errors()
            assert yaml.YAMLError in errors
            assert mock_ryaml.InvalidYamlError in errors
            assert len(errors) == 2


class TestLoadYaml:
    """Tests for load_yaml() with backend switching."""

    def test_pyyaml_fallback_string(self) -> None:
        """When ryaml is unavailable, PyYAML is used for string input."""
        with patch.dict("sys.modules", {"ryaml": None}):
            result = load_yaml("key: value")
            assert result == {"key": "value"}

    def test_pyyaml_fallback_textio(self) -> None:
        """When ryaml is unavailable, PyYAML is used for TextIO input."""
        with patch.dict("sys.modules", {"ryaml": None}):
            result = load_yaml(io.StringIO("key: value"))
            assert result == {"key": "value"}

    def test_with_ryaml_string(self) -> None:
        """When ryaml is available, ryaml.loads() is used for string input."""
        mock_ryaml = MagicMock()
        mock_ryaml.loads.return_value = {"key": "value"}
        with patch.dict("sys.modules", {"ryaml": mock_ryaml}):
            result = load_yaml("key: value")
            mock_ryaml.loads.assert_called_once_with("key: value")
            assert result == {"key": "value"}

    def test_with_ryaml_textio(self) -> None:
        """When ryaml is available, TextIO.read() is called before ryaml.loads()."""
        mock_ryaml = MagicMock()
        mock_ryaml.loads.return_value = {"key": "value"}
        stream = io.StringIO("key: value")
        with patch.dict("sys.modules", {"ryaml": mock_ryaml}):
            result = load_yaml(stream)
            mock_ryaml.loads.assert_called_once_with("key: value")
            assert result == {"key": "value"}


class TestInferInputType:
    """Tests for infer_input_type() with backend error handling."""

    def test_csv_with_pyyaml_error(self) -> None:
        """YAML parse error from PyYAML returns CSV type."""
        with patch.dict("sys.modules", {"ryaml": None}):
            result = infer_input_type("a,b,c\n1,2,3\n::")
            assert result == InputFileType.CSV

    def test_csv_with_ryaml_error(self) -> None:
        """YAML parse error from ryaml returns CSV type."""
        mock_invalid_yaml_error = type("InvalidYamlError", (Exception,), {})
        mock_ryaml = MagicMock()
        mock_ryaml.InvalidYamlError = mock_invalid_yaml_error
        mock_ryaml.loads.side_effect = mock_invalid_yaml_error("parse error")
        with patch.dict("sys.modules", {"ryaml": mock_ryaml}):
            result = infer_input_type(":::invalid yaml:::")
            assert result == InputFileType.CSV

    def test_openapi_detection(self) -> None:
        """OpenAPI input is detected correctly regardless of backend."""
        with patch.dict("sys.modules", {"ryaml": None}):
            result = infer_input_type("openapi: '3.0.0'\ninfo:\n  title: Test\n  version: '1.0'")
            assert result == InputFileType.OpenAPI
