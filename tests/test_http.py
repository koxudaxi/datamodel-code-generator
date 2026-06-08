"""Tests for HTTP utilities."""

from __future__ import annotations

import socket
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


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/schema.json",
        "http://127.1/schema.json",
        "http://2130706433/schema.json",
        "http://0x7f000001/schema.json",
        "http://0177.0.0.1/schema.json",
        "http://[::1]/schema.json",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/schema.json",
        "http://schema.localhost/schema.json",
    ],
)
def test_get_body_blocks_unsafe_url_hosts(mocker: MockerFixture, url: str) -> None:
    """Block local and private network targets before fetching."""
    mock_get = mocker.patch("httpx.get")

    with pytest.raises(SchemaFetchError, match="--allow-private-network"):
        get_body(url)
    assert mock_get.call_count == 0


def test_get_body_allows_unsafe_url_host_with_explicit_opt_in(mocker: MockerFixture) -> None:
    """Allow trusted private network targets only when explicitly requested."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"type": "object"}'
    mock_get = mocker.patch("httpx.get", return_value=mock_response)

    result = get_body("http://127.0.0.1/schema.json", allow_private_network=True)

    assert result == '{"type": "object"}'
    assert mock_get.call_count == 1


def test_get_body_blocks_hostname_resolving_to_unsafe_ip(mocker: MockerFixture) -> None:
    """Block hostnames that resolve to local or private network targets."""
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0))],
    )
    mock_get = mocker.patch("httpx.get")

    with pytest.raises(SchemaFetchError, match="--allow-private-network"):
        get_body("https://metadata.example.com/schema.json")
    assert mock_get.call_count == 0


def test_get_body_blocks_redirect_to_unsafe_url(mocker: MockerFixture) -> None:
    """Validate redirect targets before the next request."""
    mock_response = Mock()
    mock_response.status_code = 302
    mock_response.headers = {"location": "http://127.0.0.1/schema.json"}
    mock_get = mocker.patch("httpx.get", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="--allow-private-network"):
        get_body("https://example.com/schema.json")
    assert mock_get.call_count == 1


def test_get_body_allows_redirect_to_unsafe_url_with_explicit_opt_in(mocker: MockerFixture) -> None:
    """Allow trusted redirects to private network targets only when explicitly requested."""
    redirect_response = Mock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "http://127.0.0.1/schema.json"}
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {"content-type": "application/json"}
    success_response.text = '{"type": "object"}'
    mock_get = mocker.patch("httpx.get", side_effect=[redirect_response, success_response])

    result = get_body("https://example.com/schema.json", allow_private_network=True)

    assert result == '{"type": "object"}'
    assert [call.args[0] for call in mock_get.call_args_list] == [
        "https://example.com/schema.json",
        "http://127.0.0.1/schema.json",
    ]


def test_get_body_follows_relative_redirect(mocker: MockerFixture) -> None:
    """Follow safe relative redirects."""
    redirect_response = Mock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "schema.json"}
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {"content-type": "application/json"}
    success_response.text = '{"type": "object"}'
    mock_get = mocker.patch("httpx.get", side_effect=[redirect_response, success_response])

    result = get_body(
        "https://example.com/schemas/root.json",
        query_parameters=[("version", "v2")],
    )

    assert result == '{"type": "object"}'
    assert [call.args[0] for call in mock_get.call_args_list] == [
        "https://example.com/schemas/root.json",
        "https://example.com/schemas/schema.json",
    ]
    assert mock_get.call_args_list[0].kwargs["params"] == [("version", "v2")]
    assert mock_get.call_args_list[1].kwargs["params"] is None


def test_get_body_wraps_transport_error(mocker: MockerFixture) -> None:
    """Test that transport failures (DNS, timeout, etc.) are wrapped in SchemaFetchError."""
    import httpx

    mocker.patch("httpx.get", side_effect=httpx.ConnectError("DNS resolution failed"))

    with pytest.raises(SchemaFetchError, match="Failed to fetch"):
        get_body("https://nonexistent.example.com/schema.json")
