"""Tests for HTTP utilities."""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from typing import TYPE_CHECKING, ClassVar
from unittest.mock import Mock

import pytest

from datamodel_code_generator import SchemaFetchError
from datamodel_code_generator.http import (
    MAX_HTTP_REDIRECTS,
    _create_ssl_context,
    _get_addr_info_ip,
    _get_http_response,
    _get_httpx,
    _get_redirect_headers,
    _get_url_origin,
    _normalize_dns_host,
    _PinnedNetworkBackend,
    get_body,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def block_dns_by_default(mocker: MockerFixture) -> None:
    """Keep tests that mock httpx.get independent from external DNS."""
    mocker.patch("socket.getaddrinfo", side_effect=OSError)


class _SchemaHandler(BaseHTTPRequestHandler):
    routes: ClassVar[dict[str, tuple[int, dict[str, str], bytes]]] = {
        "/schema.json": (200, {"content-type": "application/json"}, b'{"type":"object"}'),
    }

    def do_GET(self) -> None:
        if self.path.startswith("/echo"):
            body = json.dumps({
                "path": self.path,
                "test_header": self.headers.get("X-Test-Header"),
            }).encode()
            status, headers = 200, {"content-type": "application/json"}
        else:
            status, headers, body = self.routes.get(
                self.path,
                (404, {"content-type": "application/json"}, b'{"error":"not found"}'),
            )

        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


@pytest.fixture
def local_http_server() -> Iterator[str]:
    """Run a local HTTP server for transport-level tests."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SchemaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def test_get_body_raises_on_http_error(mocker: MockerFixture) -> None:
    """Test that get_body raises on HTTP error status codes."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.headers = {"content-type": "text/html"}
    mocker.patch("httpx.get", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="HTTP 404 error fetching"):
        get_body("https://example.com/missing.json", allow_private_network=True)


def test_get_body_raises_on_html_response(mocker: MockerFixture) -> None:
    """Test that get_body raises when response is HTML instead of JSON/YAML."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mocker.patch("httpx.get", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="Unexpected HTML response"):
        get_body("https://example.com/schema.json", allow_private_network=True)


def test_get_body_succeeds_with_json_response(mocker: MockerFixture) -> None:
    """Test that get_body returns text for valid JSON responses."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"type": "object"}'
    mocker.patch("httpx.get", return_value=mock_response)

    result = get_body("https://example.com/schema.json", allow_private_network=True)
    assert result == '{"type": "object"}'


def test_get_body_succeeds_without_content_type(mocker: MockerFixture) -> None:
    """Test that get_body returns text when no Content-Type header is present."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.text = '{"type": "object"}'
    mocker.patch("httpx.get", return_value=mock_response)

    result = get_body("https://example.com/schema.json", allow_private_network=True)
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


@pytest.mark.parametrize(
    "url",
    [
        "http://127.1/schema.json",
        "http://2130706433/schema.json",
        "http://0x7f000001/schema.json",
        "http://0177.0.0.1/schema.json",
    ],
)
def test_get_body_blocks_unsafe_ipv4_literals_without_dns(mocker: MockerFixture, url: str) -> None:
    """Block legacy IPv4 literals without depending on platform DNS behavior."""
    mocker.patch("socket.getaddrinfo", side_effect=OSError)
    mock_get = mocker.patch("httpx.get")

    with pytest.raises(SchemaFetchError, match="--allow-private-network"):
        get_body(url)
    assert mock_get.call_count == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://1.2.3.4.5/schema.json",
        "http://256.0.0.1/schema.json",
    ],
)
def test_get_body_blocks_unresolvable_ipv4_like_hosts(mocker: MockerFixture, url: str) -> None:
    """Fail closed when an IPv4-like host is neither a valid IP literal nor resolvable."""
    mocker.patch("socket.getaddrinfo", side_effect=OSError)
    mock_get = mocker.patch("httpx.get")

    with pytest.raises(SchemaFetchError, match="could not be resolved to a public IP address"):
        get_body(url)
    assert mock_get.call_count == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.1/schema.json",
        "http://1.2.3.4.5/schema.json",
        "http://256.0.0.1/schema.json",
    ],
)
def test_get_body_handles_legacy_ipv4_literal_boundaries(mocker: MockerFixture, url: str) -> None:
    """Cover legacy IPv4 parser boundary cases without platform DNS behavior."""
    mocker.patch("socket.getaddrinfo", side_effect=OSError)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"type": "object"}'
    mock_get = mocker.patch("httpx.get", return_value=mock_response)

    if url == "http://127.0.1/schema.json":
        with pytest.raises(SchemaFetchError, match="--allow-private-network"):
            get_body(url)
        assert mock_get.call_count == 0
    else:
        result = get_body(url, allow_private_network=True)
        assert result == '{"type": "object"}'
        assert mock_get.call_count == 1


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


def test_get_body_blocks_unresolved_hostname(mocker: MockerFixture) -> None:
    """Block unresolved hostnames when the public address cannot be validated."""
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response")

    with pytest.raises(SchemaFetchError, match="could not be resolved to a public IP address"):
        get_body("https://missing.example.com/schema.json")
    assert mock_fetch.call_count == 0


def test_get_body_blocks_invalid_idn_hostname(mocker: MockerFixture) -> None:
    """Block hostnames that cannot be normalized to an ASCII DNS name."""
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response")

    with pytest.raises(SchemaFetchError, match="Invalid URL host"):
        get_body(f"https://{chr(0xD800)}.example/schema.json")
    assert mock_fetch.call_count == 0


def test_get_body_reports_resolved_ips_in_dns_order(mocker: MockerFixture) -> None:
    """Preserve DNS result order when reporting unsafe resolved addresses."""
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
        ],
    )
    mock_get = mocker.patch("httpx.get")

    with pytest.raises(SchemaFetchError, match=r"Resolved IPs: 93\.184\.216\.34, 127\.0\.0\.1"):
        get_body("https://metadata.example.com/schema.json")
    assert mock_get.call_count == 0


def test_get_body_ignores_malformed_addrinfo_records(mocker: MockerFixture) -> None:
    """Ignore malformed resolver records instead of failing before the fetch."""
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 0, ""),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0)),
        ],
    )
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"type": "object"}'
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response", return_value=mock_response)

    result = get_body("https://metadata.example.com/schema.json")

    assert result == '{"type": "object"}'
    assert mock_fetch.call_count == 1


def test_get_body_pins_validated_dns_resolution(mocker: MockerFixture) -> None:
    """Use the DNS result validated by the SSRF guard for the actual HTTP connection."""
    validated_ip = "93.184.216.34"
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", (validated_ip, 0))],
    )
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"type": "object"}'
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response", return_value=mock_response)

    result = get_body("https://metadata.example.com/schema.json")

    assert result == '{"type": "object"}'
    assert mock_fetch.call_args.kwargs["pinned_host"] == "metadata.example.com"
    assert mock_fetch.call_args.kwargs["pinned_ips"] == (ip_address(validated_ip),)


@pytest.mark.parametrize(
    ("url", "expected_host"),
    [
        ("https://bücher.example/schema.json", "xn--bcher-kva.example"),
        ("https://faß.example/schema.json", "xn--fa-hia.example"),
    ],
)
def test_get_body_pins_idn_hostname_as_canonical_dns_name(
    mocker: MockerFixture,
    url: str,
    expected_host: str,
) -> None:
    """Pin IDN hosts using the same ASCII DNS name that httpcore connects to."""
    validated_ip = "93.184.216.34"
    mock_getaddrinfo = mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", (validated_ip, 0))],
    )
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"type": "object"}'
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response", return_value=mock_response)

    result = get_body(url)

    assert result == '{"type": "object"}'
    assert mock_getaddrinfo.call_args.args == (expected_host, None)
    assert mock_fetch.call_args.kwargs["pinned_host"] == expected_host
    assert mock_fetch.call_args.kwargs["pinned_ips"] == (ip_address(validated_ip),)


@pytest.mark.parametrize("verify", [True, False])
def test_get_http_response_uses_pinned_backend_with_real_local_http(
    mocker: MockerFixture,
    local_http_server: str,
    *,
    verify: bool,
) -> None:
    """Exercise the pinned httpcore backend with a real local HTTP connection."""
    mocker.stopall()

    response = _get_http_response(
        _get_httpx(),
        f"{local_http_server}/echo",
        headers=[("X-Test-Header", "yes")],
        verify=verify,
        follow_redirects=False,
        query_parameters=[("q", "1")],
        timeout=5.0,
        pinned_host="localhost",
        pinned_ips=(ip_address("127.0.0.1"),),
    )

    assert response.status_code == 200
    assert json.loads(response.text) == {"path": "/echo?q=1", "test_header": "yes"}

    schema_response = _get_http_response(
        _get_httpx(),
        f"{local_http_server}/schema.json",
        headers=None,
        verify=verify,
        follow_redirects=False,
        query_parameters=None,
        timeout=5.0,
        pinned_host="localhost",
        pinned_ips=(ip_address("127.0.0.1"),),
    )

    assert schema_response.status_code == 200
    assert schema_response.text == '{"type":"object"}'


def test_create_ssl_context_verify_modes() -> None:
    """Build an SSL context only when certificate verification is disabled."""
    assert _create_ssl_context(verify=True) is None

    context = _create_ssl_context(verify=False)

    assert context is not None
    assert context.check_hostname is False
    assert context.verify_mode == 0


@pytest.mark.parametrize(
    ("addr_info", "expected"),
    [
        (("short",), None),
        ((socket.AF_INET, socket.SOCK_STREAM, 0, "", ()), None),
        ((socket.AF_INET, socket.SOCK_STREAM, 0, "", ("not-an-ip", 0)), None),
        ((socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("2001:db8::1%eth0", 0, 0, 0)), ip_address("2001:db8::1")),
    ],
)
def test_get_addr_info_ip_handles_invalid_records(addr_info: object, expected: object) -> None:
    """Ignore malformed resolver records and strip IPv6 zone identifiers."""
    assert _get_addr_info_ip(addr_info) == expected


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        (None, None),
        (b"Example.COM.", "example.com"),
        (b"xn--bcher-kva.example.", "xn--bcher-kva.example"),
        (b"\xff", None),
        ("Example.COM.", "example.com"),
        ("bücher.example.", "xn--bcher-kva.example"),
        ("faß.example.", "xn--fa-hia.example"),
        ("xn--bcher-kva.example.", "xn--bcher-kva.example"),
    ],
)
def test_normalize_dns_host(host: bytes | str | None, expected: str | None) -> None:
    """Normalize DNS names before comparing pinned hosts."""
    assert _normalize_dns_host(host) == expected


class _FakeNetworkBackend:
    def __init__(self, *, fail_hosts: set[str] | None = None) -> None:
        self.calls: list[tuple[str, int]] = []
        self.fail_hosts = fail_hosts or set()
        self.unix_socket_calls: list[str] = []
        self.sleep_calls: list[float] = []

    def connect_tcp(self, host: str, port: int, **_kwargs: object) -> str:
        self.calls.append((host, port))
        if host in self.fail_hosts:
            raise OSError(host)
        return f"stream:{host}:{port}"

    def connect_unix_socket(self, path: str, **_kwargs: object) -> str:
        self.unix_socket_calls.append(path)
        return f"unix:{path}"

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)


def test_pinned_network_backend_connects_to_validated_ip() -> None:
    """Connect through the IP address that was validated before the HTTP request."""
    backend = _FakeNetworkBackend()
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="metadata.example.com",
        pinned_ips=(ip_address("93.184.216.34"),),
        backend=backend,
    )

    result = pinned_backend.connect_tcp("metadata.example.com", 443)

    assert result == "stream:93.184.216.34:443"
    assert backend.calls == [("93.184.216.34", 443)]


def test_pinned_network_backend_rejects_mismatched_host() -> None:
    """Do not fall back to unvalidated DNS for a different connection host."""
    backend = _FakeNetworkBackend()
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="metadata.example.com",
        pinned_ips=(ip_address("93.184.216.34"),),
        backend=backend,
    )

    with pytest.raises(OSError, match="does not match the validated host"):
        pinned_backend.connect_tcp("example.com", 443)

    assert backend.calls == []


def test_pinned_network_backend_rejects_idna_mismatch_without_dns_fallback() -> None:
    """Reject IDNA2003/IDNA2008 mismatches instead of resolving another host."""
    backend = _FakeNetworkBackend()
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="faß.example",
        pinned_ips=(ip_address("93.184.216.34"),),
        backend=backend,
    )

    with pytest.raises(OSError, match="does not match the validated host"):
        pinned_backend.connect_tcp("fass.example", 443)

    assert backend.calls == []


def test_pinned_network_backend_matches_idn_punycode_host() -> None:
    """Pin IDN hosts even when httpcore connects with the punycode DNS name."""
    backend = _FakeNetworkBackend()
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="bücher.example",
        pinned_ips=(ip_address("93.184.216.34"),),
        backend=backend,
    )

    result = pinned_backend.connect_tcp("xn--bcher-kva.example", 443)

    assert result == "stream:93.184.216.34:443"
    assert backend.calls == [("93.184.216.34", 443)]


def test_pinned_network_backend_tries_next_validated_ip() -> None:
    """Try the next validated DNS result when the first pinned address fails."""
    backend = _FakeNetworkBackend(fail_hosts={"93.184.216.34"})
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="metadata.example.com",
        pinned_ips=(ip_address("93.184.216.34"), ip_address("93.184.216.35")),
        backend=backend,
    )

    result = pinned_backend.connect_tcp("metadata.example.com", 443)

    assert result == "stream:93.184.216.35:443"
    assert backend.calls == [("93.184.216.34", 443), ("93.184.216.35", 443)]


def test_pinned_network_backend_raises_last_connect_error() -> None:
    """Report the final connection error after trying all validated addresses."""
    backend = _FakeNetworkBackend(fail_hosts={"93.184.216.34", "93.184.216.35"})
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="metadata.example.com",
        pinned_ips=(ip_address("93.184.216.34"), ip_address("93.184.216.35")),
        backend=backend,
    )

    with pytest.raises(OSError, match=r"93\.184\.216\.35"):
        pinned_backend.connect_tcp("metadata.example.com", 443)
    assert backend.calls == [("93.184.216.34", 443), ("93.184.216.35", 443)]


def test_pinned_network_backend_rejects_empty_pinned_ips() -> None:
    """Reject pinned connections when validation produced no usable IP address."""
    backend = _FakeNetworkBackend()
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="metadata.example.com",
        pinned_ips=(),
        backend=backend,
    )

    with pytest.raises(OSError, match="No validated DNS addresses"):
        pinned_backend.connect_tcp("metadata.example.com", 443)
    assert backend.calls == []


def test_pinned_network_backend_delegates_unix_socket_and_sleep() -> None:
    """Forward backend methods that are unrelated to DNS pinning."""
    backend = _FakeNetworkBackend()
    pinned_backend = _PinnedNetworkBackend(
        pinned_host="metadata.example.com",
        pinned_ips=(ip_address("93.184.216.34"),),
        backend=backend,
    )

    assert pinned_backend.connect_unix_socket("/tmp/test.sock") == "unix:/tmp/test.sock"
    pinned_backend.sleep(0.1)
    assert backend.unix_socket_calls == ["/tmp/test.sock"]
    assert backend.sleep_calls == [0.1]


def test_get_body_blocks_redirect_to_unsafe_url(mocker: MockerFixture) -> None:
    """Validate redirect targets before the next request."""
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
    )
    mock_response = Mock()
    mock_response.status_code = 302
    mock_response.headers = {"location": "http://127.0.0.1/schema.json"}
    mock_fetch = mocker.patch("datamodel_code_generator.http._get_http_response", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="--allow-private-network"):
        get_body("https://example.com/schema.json")
    assert mock_fetch.call_count == 1


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
    mocker.patch(
        "socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))],
    )
    redirect_response = Mock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "schema.json"}
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {"content-type": "application/json"}
    success_response.text = '{"type": "object"}'
    mock_fetch = mocker.patch(
        "datamodel_code_generator.http._get_http_response",
        side_effect=[redirect_response, success_response],
    )

    result = get_body(
        "https://example.com/schemas/root.json",
        query_parameters=[("version", "v2")],
    )

    assert result == '{"type": "object"}'
    assert [call.args[1] for call in mock_fetch.call_args_list] == [
        "https://example.com/schemas/root.json",
        "https://example.com/schemas/schema.json",
    ]
    assert mock_fetch.call_args_list[0].kwargs["query_parameters"] == [("version", "v2")]
    assert mock_fetch.call_args_list[1].kwargs["query_parameters"] is None


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://schema.example/root.json", ("https", "schema.example", 443)),
        ("https://SCHEMA.EXAMPLE.:443/root.json", ("https", "schema.example", 443)),
        ("http://schema.example/root.json", ("http", "schema.example", 80)),
        ("https://bücher.example/root.json", ("https", "xn--bcher-kva.example", 443)),
        ("https:///root.json", None),
        ("https://schema.example:bad/root.json", None),
    ],
)
def test_get_url_origin_normalizes_redirect_scope(url: str, expected: tuple[str, str, int | None] | None) -> None:
    """Normalize scheme, host, and effective port for redirect credential scoping."""
    assert _get_url_origin(url) == expected


@pytest.mark.parametrize(
    ("current_url", "redirect_url", "expected_headers"),
    [
        (
            "https://schema.example/root.json",
            "https://schema.example/next.json",
            [
                ("authorization", "Bearer token"),
                ("COOKIE", "session=secret"),
                ("Proxy-Authorization", "Basic secret"),
                ("X-Trace", "1"),
            ],
        ),
        (
            "https://schema.example/root.json",
            "https://schema.example:443/next.json",
            [
                ("authorization", "Bearer token"),
                ("COOKIE", "session=secret"),
                ("Proxy-Authorization", "Basic secret"),
                ("X-Trace", "1"),
            ],
        ),
        (
            "https://schema.example./root.json",
            "https://SCHEMA.EXAMPLE/next.json",
            [
                ("authorization", "Bearer token"),
                ("COOKIE", "session=secret"),
                ("Proxy-Authorization", "Basic secret"),
                ("X-Trace", "1"),
            ],
        ),
        (
            "https://bücher.example/root.json",
            "https://xn--bcher-kva.example/next.json",
            [
                ("authorization", "Bearer token"),
                ("COOKIE", "session=secret"),
                ("Proxy-Authorization", "Basic secret"),
                ("X-Trace", "1"),
            ],
        ),
        ("https://schema.example/root.json", "http://schema.example/next.json", [("X-Trace", "1")]),
        ("https://schema.example/root.json", "https://other.example/next.json", [("X-Trace", "1")]),
        ("https://schema.example/root.json", "https://schema.example:444/next.json", [("X-Trace", "1")]),
        ("https://schema.example:bad/root.json", "https://other.example/next.json", [("X-Trace", "1")]),
        ("https://schema.example/root.json", "https://schema.example:bad/next.json", [("X-Trace", "1")]),
        ("https://schema.example:bad/root.json", "https://other.example:bad/next.json", [("X-Trace", "1")]),
    ],
)
def test_get_redirect_headers_scopes_sensitive_headers(
    current_url: str,
    redirect_url: str,
    expected_headers: list[tuple[str, str]],
) -> None:
    """Keep sensitive headers only when redirect origin is unchanged."""
    headers = [
        ("authorization", "Bearer token"),
        ("COOKIE", "session=secret"),
        ("Proxy-Authorization", "Basic secret"),
        ("X-Trace", "1"),
    ]

    assert _get_redirect_headers(headers, current_url, redirect_url) == expected_headers


def test_get_redirect_headers_handles_no_headers() -> None:
    """Preserve no-header inputs without creating a new header list."""
    assert _get_redirect_headers(None, "https://schema.example/root.json", "https://other.example/next.json") is None
    assert _get_redirect_headers([], "https://schema.example/root.json", "https://other.example/next.json") == []


def test_get_body_drops_sensitive_headers_on_cross_origin_redirect(mocker: MockerFixture) -> None:
    """Do not forward scoped credentials to a different redirect origin."""
    redirect_response = Mock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "https://other.example/schema.json"}
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {"content-type": "application/json"}
    success_response.text = '{"type": "object"}'
    mock_get = mocker.patch("httpx.get", side_effect=[redirect_response, success_response])

    result = get_body(
        "https://schema.example/root.json",
        headers=[
            ("Authorization", "Bearer token"),
            ("Cookie", "session=secret"),
            ("Proxy-Authorization", "Basic secret"),
            ("X-Trace", "1"),
        ],
        allow_private_network=True,
    )

    assert result == '{"type": "object"}'
    assert mock_get.call_args_list[0].kwargs["headers"] == [
        ("Authorization", "Bearer token"),
        ("Cookie", "session=secret"),
        ("Proxy-Authorization", "Basic secret"),
        ("X-Trace", "1"),
    ]
    assert mock_get.call_args_list[1].kwargs["headers"] == [("X-Trace", "1")]


def test_get_body_does_not_restore_sensitive_headers_after_cross_origin_redirect(mocker: MockerFixture) -> None:
    """Once sensitive headers are dropped on a redirect chain, later hops do not restore them."""
    same_origin_redirect = Mock()
    same_origin_redirect.status_code = 302
    same_origin_redirect.headers = {"location": "https://schema.example/step1.json"}
    cross_origin_redirect = Mock()
    cross_origin_redirect.status_code = 302
    cross_origin_redirect.headers = {"location": "https://other.example/step2.json"}
    return_redirect = Mock()
    return_redirect.status_code = 302
    return_redirect.headers = {"location": "https://schema.example/final.json"}
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {"content-type": "application/json"}
    success_response.text = '{"type": "object"}'
    mock_get = mocker.patch(
        "httpx.get",
        side_effect=[same_origin_redirect, cross_origin_redirect, return_redirect, success_response],
    )
    headers = [("Authorization", "Bearer token"), ("X-Trace", "1")]

    result = get_body("https://schema.example/root.json", headers=headers, allow_private_network=True)

    assert result == '{"type": "object"}'
    assert [call.kwargs["headers"] for call in mock_get.call_args_list] == [
        headers,
        headers,
        [("X-Trace", "1")],
        [("X-Trace", "1")],
    ]


def test_get_body_keeps_headers_on_same_origin_redirect(mocker: MockerFixture) -> None:
    """Keep headers when a redirect stays within the same origin."""
    redirect_response = Mock()
    redirect_response.status_code = 302
    redirect_response.headers = {"location": "https://schema.example/next.json"}
    success_response = Mock()
    success_response.status_code = 200
    success_response.headers = {"content-type": "application/json"}
    success_response.text = '{"type": "object"}'
    headers = [("Authorization", "Bearer token")]
    mock_get = mocker.patch("httpx.get", side_effect=[redirect_response, success_response])

    result = get_body("https://schema.example/root.json", headers=headers, allow_private_network=True)

    assert result == '{"type": "object"}'
    assert mock_get.call_args_list[1].kwargs["headers"] == headers


@pytest.mark.parametrize("url", ["ftp://example.com/schema.json", "https:///schema.json"])
def test_get_body_rejects_invalid_fetch_urls(mocker: MockerFixture, url: str) -> None:
    """Reject unsupported or incomplete URLs before fetching."""
    mock_get = mocker.patch("httpx.get")

    with pytest.raises(SchemaFetchError, match="HTTP fetch"):
        get_body(url)
    assert mock_get.call_count == 0


def test_get_body_rejects_redirect_without_location(mocker: MockerFixture) -> None:
    """Reject redirect responses that do not provide a target."""
    mock_response = Mock()
    mock_response.status_code = 302
    mock_response.headers = {}
    mock_get = mocker.patch("httpx.get", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="missing a Location header"):
        get_body("https://example.com/schema.json", allow_private_network=True)
    assert mock_get.call_count == 1


def test_get_body_rejects_too_many_redirects(mocker: MockerFixture) -> None:
    """Reject redirect chains that exceed the configured limit."""
    mock_response = Mock()
    mock_response.status_code = 302
    mock_response.headers = {"location": "https://example.com/schema.json"}
    mock_get = mocker.patch("httpx.get", return_value=mock_response)

    with pytest.raises(SchemaFetchError, match="Too many redirects"):
        get_body("https://example.com/schema.json", allow_private_network=True)
    assert mock_get.call_count == MAX_HTTP_REDIRECTS + 1


def test_get_body_wraps_transport_error(mocker: MockerFixture) -> None:
    """Test that transport failures (DNS, timeout, etc.) are wrapped in SchemaFetchError."""
    import httpx

    mocker.patch("httpx.get", side_effect=httpx.ConnectError("DNS resolution failed"))

    with pytest.raises(SchemaFetchError, match="Failed to fetch"):
        get_body("https://nonexistent.example.com/schema.json", allow_private_network=True)
