"""Tests for HTTP utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from datamodel_code_generator import SchemaFetchError
from datamodel_code_generator.http import get_body

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_get_body_raises_on_http_error(mocker: MockerFixture) -> None:
    """Test that get_body raises on HTTP error status codes."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.headers = {"content-type": "text/html"}
    mocker.patch("httpx.get", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="HTTP 404 error fetching"):
        get_body("https://example.com/missing.json")


def test_get_body_raises_on_html_response(mocker: MockerFixture) -> None:
    """Test that get_body raises when response is HTML instead of JSON/YAML."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mocker.patch("httpx.get", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="Unexpected HTML response"):
        get_body("https://example.com/schema.json")


def test_get_body_succeeds_with_json_response(mocker: MockerFixture) -> None:
    """Test that get_body returns text for valid JSON responses."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"type": "object"}'
    mocker.patch("httpx.get", return_value=mock_response)

    result = get_body("https://example.com/schema.json")
    assert result == '{"type": "object"}'


def test_get_body_succeeds_without_content_type(mocker: MockerFixture) -> None:
    """Test that get_body returns text when no Content-Type header is present."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.text = '{"type": "object"}'
    mocker.patch("httpx.get", return_value=mock_response)

    result = get_body("https://example.com/schema.json")
    assert result == '{"type": "object"}'


def test_get_body_wraps_transport_error(mocker: MockerFixture) -> None:
    """Test that transport failures (DNS, timeout, etc.) are wrapped in SchemaFetchError."""
    import httpx

    mocker.patch("httpx.get", side_effect=httpx.ConnectError("DNS resolution failed"))

    with pytest.raises(SchemaFetchError, match="Failed to fetch"):
        get_body("https://nonexistent.example.com/schema.json")
