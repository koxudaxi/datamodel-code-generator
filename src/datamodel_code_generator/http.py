"""HTTP utilities for fetching remote schema files.

Provides functions to fetch schema content from URLs and join URL references.
HTTP(S) URLs require the 'http' extra: `pip install 'datamodel-code-generator[http]'`.
file:// URLs are handled without additional dependencies.
"""

from __future__ import annotations

import socket
import ssl
from collections.abc import Iterable, Sequence
from ipaddress import IPv4Address, IPv6Address, IPv6Network, ip_address
from types import MappingProxyType
from typing import TYPE_CHECKING, Protocol, cast, overload
from urllib.parse import urlparse

from typing_extensions import Self

from datamodel_code_generator import SchemaFetchError

if TYPE_CHECKING:
    from types import TracebackType

    import httpcore
    import httpx


class _ResponseHeaders(Protocol):
    @overload
    def get(self, key: str) -> str | None: ...

    @overload
    def get(self, key: str, default: str) -> str: ...


class _HTTPResponse(Protocol):
    status_code: int
    headers: _ResponseHeaders
    text: str


class _HTTPXClient(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def get(
        self,
        url: str,
        *,
        headers: Sequence[tuple[str, str]] | None,
        follow_redirects: bool,
        params: Sequence[tuple[str, str]] | None,
    ) -> _HTTPResponse: ...


class _HTTPXClientFactory(Protocol):
    def __call__(self, *, transport: httpx.BaseTransport, timeout: float) -> _HTTPXClient: ...


class _HTTPXURLJoiner(Protocol):
    def join(self, url: str) -> _HTTPXURLJoiner: ...

    def __str__(self) -> str: ...


class _HTTPXURLFactory(Protocol):
    def __call__(self, url: str) -> _HTTPXURLJoiner: ...


class _HTTPXModule(Protocol):
    Client: _HTTPXClientFactory
    URL: _HTTPXURLFactory

    def get(  # noqa: PLR0913
        self,
        url: str,
        *,
        headers: Sequence[tuple[str, str]] | None,
        verify: bool,
        follow_redirects: bool,
        params: Sequence[tuple[str, str]] | None,
        timeout: float,
    ) -> _HTTPResponse: ...


class _ClosableByteStream(Iterable[bytes], Protocol):
    def close(self) -> None: ...


class _NetworkBackend(Protocol):
    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> httpcore.NetworkStream: ...

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> httpcore.NetworkStream: ...

    def sleep(self, seconds: float) -> None: ...


def _get_httpx() -> _HTTPXModule:
    """Lazily import httpx, raising a helpful error if not installed."""
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        msg = "Please run `$pip install 'datamodel-code-generator[http]`' to resolve HTTP(S) URL references"
        raise Exception(msg) from exc  # noqa: TRY002
    return cast("_HTTPXModule", httpx)


DEFAULT_HTTP_TIMEOUT = 30.0
MAX_HTTP_REDIRECTS = 20
_HTTP_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_SENSITIVE_REDIRECT_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})
_UNSAFE_HOST_NAMES = frozenset({"localhost"})
_IPV4_PART_COUNT = 4
_IPV4_OCTET_MAX = 0xFF
_IPV4_THREE_PART_TAIL_MAX = 0xFFFF
_IPV4_TWO_PART_TAIL_MAX = 0xFFFFFF
_IPV4_ADDRESS_MAX = 0xFFFFFFFF
_DEFAULT_PORTS = MappingProxyType({"http": 80, "https": 443})
_ADDR_INFO_MIN_LENGTH = 5
_EMBEDDED_IPV4_PREFIXES = (
    IPv6Network("::/96"),
    IPv6Network("::ffff:0:0:0/96"),
    IPv6Network("64:ff9b::/96"),
)


def _embedded_ipv4(ip: IPv4Address | IPv6Address) -> IPv4Address | None:
    """Return the IPv4 address embedded in an IPv6 address, if any.

    IPv6 can encode an IPv4 target several ways, including IPv4-mapped, IPv4-compatible,
    IPv4-translated, and NAT64 well-known prefix addresses. Unwrapping them lets the SSRF guard
    apply the same private-address checks it already applies to plain and legacy IPv4 literals.
    """
    if not isinstance(ip, IPv6Address):
        return None
    if (mapped := ip.ipv4_mapped) is not None:
        return mapped
    for network in _EMBEDDED_IPV4_PREFIXES:
        if ip in network:
            return IPv4Address(int(ip) & _IPV4_ADDRESS_MAX)
    return None


def _is_safe_ip(ip: IPv4Address | IPv6Address) -> bool:
    """Return whether an address is allowed for default remote schema fetches.

    Only globally routable addresses are accepted so untrusted schema URLs cannot reach local, private,
    link-local, reserved, or otherwise non-public networks unless the caller explicitly opts in. IPv6
    addresses that embed an IPv4 target are unwrapped so the embedded address is validated too.
    """
    if (embedded := _embedded_ipv4(ip)) is not None:
        return ip.is_global and embedded.is_global
    return ip.is_global


def _parse_legacy_ipv4_int(value: str) -> int | None:
    """Parse one component of a legacy IPv4 literal.

    Some network stacks accept decimal, octal, or hexadecimal IPv4 spellings that `ip_address()` rejects.
    Parsing them here prevents those spellings from bypassing the private-address checks.
    """
    try:
        if value.lower().startswith("0x"):
            return int(value, 0)
        if len(value) > 1 and value.startswith("0"):
            return int(value[1:], 8)
        return int(value, 10)
    except ValueError:
        return None


def _parse_legacy_ipv4_address(host: str) -> IPv4Address | None:
    """Convert one- to four-part legacy IPv4 literals into a canonical IPv4 address.

    Legacy forms such as `127.1`, `2130706433`, or `0x7f000001` can still describe loopback or private
    targets, so the SSRF guard treats them as IP literals before considering DNS.
    """
    parts = host.split(".")
    if len(parts) > _IPV4_PART_COUNT:
        return None

    numbers: list[int] = []
    for part in parts:
        if (number := _parse_legacy_ipv4_int(part)) is None:
            return None
        numbers.append(number)

    ipv4_value: int | None
    match numbers:
        case [a] if 0 <= a <= _IPV4_ADDRESS_MAX:
            ipv4_value = a
        case [a, b] if 0 <= a <= _IPV4_OCTET_MAX and 0 <= b <= _IPV4_TWO_PART_TAIL_MAX:
            ipv4_value = (a << 24) | b
        case [a, b, c] if (
            0 <= a <= _IPV4_OCTET_MAX and 0 <= b <= _IPV4_OCTET_MAX and 0 <= c <= _IPV4_THREE_PART_TAIL_MAX
        ):
            ipv4_value = (a << 24) | (b << 16) | c
        case [a, b, c, d] if all(0 <= part <= _IPV4_OCTET_MAX for part in (a, b, c, d)):
            ipv4_value = (a << 24) | (b << 16) | (c << 8) | d
        case _:
            ipv4_value = None

    return IPv4Address(ipv4_value) if ipv4_value is not None else None


def _get_ips_from_host(host: str) -> tuple[IPv4Address | IPv6Address, ...]:
    """Resolve a host to the exact address set used by the fetch guard.

    The function handles IP literals, scoped IPv6 literals, legacy IPv4 spellings, and DNS names before any
    HTTP connection is opened. The returned addresses are later pinned to prevent DNS rebinding between
    validation and the actual TCP connect.
    """
    normalized_host = host.split("%", maxsplit=1)[0]
    try:
        return (ip_address(normalized_host),)
    except ValueError:
        pass

    if (legacy_ipv4 := _parse_legacy_ipv4_address(normalized_host)) is not None:
        return (legacy_ipv4,)

    try:
        addr_infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return ()

    return _deduplicate_ips(_get_addr_info_ip(addr_info) for addr_info in addr_infos)


def _get_addr_info_ip(addr_info: object) -> IPv4Address | IPv6Address | None:
    """Extract an IP address from a resolver record.

    Malformed records are ignored because the guard should rely only on valid resolver output and then fail
    closed if no usable public address remains.
    """
    if not isinstance(addr_info, tuple) or len(addr_info) < _ADDR_INFO_MIN_LENGTH:
        return None
    sockaddr = addr_info[4]
    if not isinstance(sockaddr, tuple) or not sockaddr:
        return None
    try:
        raw_ip = str(sockaddr[0]).split("%", maxsplit=1)[0]
        return ip_address(raw_ip)
    except ValueError:
        return None


def _deduplicate_ips(ips: Iterable[IPv4Address | IPv6Address | None]) -> tuple[IPv4Address | IPv6Address, ...]:
    """Return unique IP addresses while preserving resolver order.

    Keeping the original order makes connection attempts match the validated DNS result while avoiding repeated
    attempts for duplicate records.
    """
    deduplicated: list[IPv4Address | IPv6Address] = []
    seen: set[IPv4Address | IPv6Address] = set()
    for ip in ips:
        if ip is None or ip in seen:
            continue
        seen.add(ip)
        deduplicated.append(ip)
    return tuple(deduplicated)


def _normalize_dns_host(host: bytes | str | None) -> str | None:
    """Normalize a URL or transport host to the ASCII DNS name used for pinning.

    httpcore connects with an ASCII DNS name, including IDNA encoding for Unicode hostnames. Using the same
    comparison form prevents Unicode and punycode spelling differences from bypassing the pinned host check.
    """
    if host is None:
        return None
    try:
        if isinstance(host, bytes):
            host = host.decode("ascii")
        normalized_host = host.rstrip(".").lower()
        if normalized_host.isascii():
            return normalized_host
        import idna  # noqa: PLC0415

        return idna.encode(normalized_host).decode("ascii")
    except UnicodeError:
        return None


class _PinnedNetworkBackend:
    """httpcore network backend that connects only to previously validated addresses.

    URL validation happens before the HTTP request, but DNS could otherwise be resolved again during the TCP
    connect. This backend closes that gap by refusing host changes and trying only the validated IP set.
    """

    def __init__(
        self,
        *,
        pinned_host: str,
        pinned_ips: tuple[IPv4Address | IPv6Address, ...],
        backend: _NetworkBackend,
    ) -> None:
        """Store the validated host, validated IPs, and wrapped backend.

        The host is normalized once so URL validation and httpcore's connection host are compared in the same
        ASCII DNS form.
        """
        self._pinned_host = _normalize_dns_host(pinned_host)
        self._pinned_ips = pinned_ips
        self._backend = backend

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> httpcore.NetworkStream:
        """Open a TCP connection through the pinned addresses for the validated host.

        A host mismatch raises before any DNS fallback. That keeps redirects, IDNA edge cases, or transport
        behavior from triggering a fresh lookup after validation.
        """
        if _normalize_dns_host(host) != self._pinned_host:
            msg = f"Requested DNS host {host} does not match the validated host"
            raise OSError(msg)

        last_error: Exception | None = None
        for ip in self._pinned_ips:
            try:
                return self._backend.connect_tcp(
                    str(ip),
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except Exception as exc:  # noqa: BLE001, PERF203
                last_error = exc
        if last_error is not None:
            raise last_error
        msg = f"No validated DNS addresses are available for {host}"
        raise OSError(msg)

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[tuple[int, int, int | bytes]] | None = None,
    ) -> httpcore.NetworkStream:
        """Delegate Unix socket connections to the wrapped backend.

        DNS pinning only applies to TCP hostnames, but httpcore expects a complete network backend interface.
        """
        return self._backend.connect_unix_socket(path, timeout=timeout, socket_options=socket_options)

    def sleep(self, seconds: float) -> None:
        """Delegate backend sleeps unchanged.

        This preserves httpcore's backend contract while keeping the pinning logic scoped to TCP connects.
        """
        self._backend.sleep(seconds)


def _create_ssl_context(*, verify: bool) -> ssl.SSLContext | None:
    """Create the SSL context used by the pinned transport.

    Returning `None` preserves httpcore's normal certificate verification. A custom context is needed only when
    the caller requested the existing `ignore_tls` behavior.
    """
    if verify:
        return None
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _build_pinned_transport(
    *,
    pinned_host: str,
    pinned_ips: tuple[IPv4Address | IPv6Address, ...],
    verify: bool,
) -> httpx.BaseTransport:
    """Build an httpx transport whose TCP connects use the pinned address set.

    httpx does not expose a per-request resolved-IP hook, so this transport keeps normal request/response
    handling while replacing the lower-level httpcore network backend used for connection creation.
    """
    import httpcore  # noqa: PLC0415
    import httpx as httpx_runtime  # noqa: PLC0415

    network_backend = cast(
        "httpcore.NetworkBackend",
        _PinnedNetworkBackend(
            pinned_host=pinned_host,
            pinned_ips=pinned_ips,
            backend=cast("_NetworkBackend", httpcore.SyncBackend()),
        ),
    )

    class _PinnedHTTPTransport(httpx_runtime.BaseTransport):
        """Request-scoped transport bound to a pinned httpcore connection pool."""

        def __init__(self) -> None:
            """Create the pool with the pinned backend.

            The transport is created per fetch, so validated addresses do not leak into unrelated requests.
            """
            self._pool = httpcore.ConnectionPool(
                ssl_context=_create_ssl_context(verify=verify),
                network_backend=network_backend,
            )

        def handle_request(self, request: httpx.Request) -> httpx.Response:
            """Send an httpx request through httpcore and return an httpx response.

            The translation is needed because the pinning hook lives in httpcore. The response body is read
            immediately so callers keep the same simple, text-based response contract.
            """
            req = httpcore.Request(
                method=request.method,
                url=httpcore.URL(
                    scheme=request.url.raw_scheme,
                    host=request.url.raw_host,
                    port=request.url.port,
                    target=request.url.raw_path,
                ),
                headers=request.headers.raw,
                content=request.stream,
                extensions=dict(request.extensions),
            )
            resp = self._pool.handle_request(req)
            stream = cast("_ClosableByteStream", resp.stream)
            try:
                content = b"".join(stream)
            finally:
                stream.close()
            return httpx_runtime.Response(
                status_code=resp.status,
                headers=resp.headers,
                content=content,
                extensions=resp.extensions,
                request=request,
            )

        def close(self) -> None:
            """Close the request-scoped connection pool and release sockets."""
            self._pool.close()

    return _PinnedHTTPTransport()


def _get_http_response(  # noqa: PLR0913
    httpx_module: _HTTPXModule,
    url: str,
    *,
    headers: Sequence[tuple[str, str]] | None,
    verify: bool,
    follow_redirects: bool,
    query_parameters: Sequence[tuple[str, str]] | None,
    timeout: float,
    pinned_host: str | None,
    pinned_ips: tuple[IPv4Address | IPv6Address, ...],
) -> _HTTPResponse:
    """Fetch a URL, using DNS pinning when validation produced public addresses.

    The unpinned path preserves existing httpx behavior for trusted private-network opt-in and tests. The pinned
    path ensures the host resolved during validation is the only host used by the actual TCP connect.
    """
    if pinned_host is None or not pinned_ips:
        return httpx_module.get(
            url,
            headers=headers,
            verify=verify,
            follow_redirects=follow_redirects,
            params=query_parameters,  # ty: ignore
            timeout=timeout,
        )

    transport = _build_pinned_transport(pinned_host=pinned_host, pinned_ips=pinned_ips, verify=verify)
    with httpx_module.Client(transport=transport, timeout=timeout) as client:
        return client.get(
            url,
            headers=headers,
            follow_redirects=follow_redirects,
            params=query_parameters,  # ty: ignore
        )


def _format_private_network_error(
    *,
    url: str,
    hostname: str,
    reason: str,
    resolved_ips: tuple[IPv4Address | IPv6Address, ...] = (),
) -> str:
    """Build an actionable error for blocked network targets.

    The message includes both the security reason and the opt-in path so users with trusted internal schema
    endpoints can fix their invocation without guessing which option is required.
    """
    ip_details = f" Resolved IPs: {', '.join(str(ip) for ip in resolved_ips)}." if resolved_ips else ""
    return (
        f"Blocked unsafe URL host: {hostname}\n"
        f"Reason: {reason}.{ip_details}\n"
        "datamodel-code-generator blocks local, private, link-local, reserved, and otherwise non-public "
        "network targets by default to reduce SSRF risk.\n"
        f"URL: {url}\n"
        "If this is a trusted internal schema endpoint, pass --allow-private-network "
        "or set allow_private_network=True when using the Python API."
    )


def _validate_url_for_fetch(
    url: str,
    *,
    allow_private_network: bool,
) -> tuple[str, tuple[IPv4Address | IPv6Address, ...]] | None:
    """Validate a fetch URL and return DNS pinning data when pinning is required.

    Every initial URL and redirect target passes through this guard before fetching. It rejects unsupported
    schemes, invalid hosts, unresolved names, and non-public addresses unless private-network access is
    explicitly allowed.
    """
    parsed_url = urlparse(url)
    match parsed_url.scheme:
        case "http" | "https":
            pass
        case _:
            msg = f"Unsupported URL scheme for HTTP fetch: {url}"
            raise SchemaFetchError(msg)

    if (hostname := parsed_url.hostname) is None:
        msg = f"Missing URL host for HTTP fetch: {url}"
        raise SchemaFetchError(msg)

    host = _normalize_dns_host(hostname)
    if host is None:
        msg = f"Invalid URL host for HTTP fetch: {hostname}"
        raise SchemaFetchError(msg)

    if allow_private_network:
        return None

    if host in _UNSAFE_HOST_NAMES or host.endswith(".localhost"):
        msg = _format_private_network_error(
            url=url,
            hostname=hostname,
            reason="localhost names resolve to the local machine",
        )
        raise SchemaFetchError(msg)

    ips = _get_ips_from_host(host)
    if not ips:
        msg = _format_private_network_error(
            url=url,
            hostname=hostname,
            reason="the host could not be resolved to a public IP address",
        )
        raise SchemaFetchError(msg)

    if all(_is_safe_ip(ip) for ip in ips):
        return host, ips

    msg = _format_private_network_error(
        url=url,
        hostname=hostname,
        reason="the host resolves to a non-public address",
        resolved_ips=ips,
    )
    raise SchemaFetchError(msg)


def _get_redirect_url(httpx_module: _HTTPXModule, current_url: str, response: _HTTPResponse) -> str | None:
    """Return the absolute redirect target for a redirect response.

    Redirects are handled manually so each target can be revalidated and re-pinned before the next HTTP request
    instead of allowing the client to follow it automatically.
    """
    if response.status_code not in _HTTP_REDIRECT_STATUS_CODES:
        return None
    if not (location := response.headers.get("location")):
        msg = f"Redirect response from {current_url} is missing a Location header"
        raise SchemaFetchError(msg)
    return str(httpx_module.URL(current_url).join(location))


def _get_url_origin(url: str) -> tuple[str, str, int | None] | None:
    """Return the normalized URL origin used to decide whether redirect headers are scoped.

    The origin is represented as scheme, canonical DNS host, and effective port. Default ports are normalized
    so `https://example.com` and `https://example.com:443` are treated as the same scope, and IDN hosts are
    compared in the same ASCII form used by the DNS pinning guard.

    Sensitive headers are safe to keep only when the origin is unchanged. Invalid origins return `None` so
    redirect handling can strip scoped credentials instead of guessing.
    """
    parsed_url = urlparse(url)
    host = _normalize_dns_host(parsed_url.hostname)
    if host is None:
        return None
    try:
        port = parsed_url.port
    except ValueError:
        return None
    return (
        parsed_url.scheme.lower(),
        host,
        port or _DEFAULT_PORTS.get(parsed_url.scheme.lower()),
    )


def _get_redirect_headers(
    headers: Sequence[tuple[str, str]] | None,
    current_url: str,
    redirect_url: str,
) -> Sequence[tuple[str, str]] | None:
    """Drop scoped credentials when a redirect crosses origins.

    The input headers are the headers that would be sent on the next redirect hop. If there are no headers, or
    the redirect target has the same normalized origin, the existing headers are reused unchanged.

    Authorization and cookie headers are scoped to the original origin. Keeping them for a different or
    unparsable redirect target can leak credentials to an attacker-controlled host, so this function fails
    closed and removes those headers unless both origins are valid and equal.
    """
    current_origin = _get_url_origin(current_url)
    redirect_origin = _get_url_origin(redirect_url)
    if not headers or (current_origin is not None and current_origin == redirect_origin):
        return headers
    return [(name, value) for name, value in headers if name.lower() not in _SENSITIVE_REDIRECT_HEADERS]


def get_body(  # noqa: PLR0913
    url: str,
    headers: Sequence[tuple[str, str]] | None = None,
    ignore_tls: bool = False,  # noqa: FBT001, FBT002
    query_parameters: Sequence[tuple[str, str]] | None = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    *,
    allow_private_network: bool = False,
) -> str:
    """Fetch schema content from a URL with redirect validation and DNS pinning.

    The function validates the original URL and each redirect target before connecting. Public DNS results are
    pinned into the transport so a host cannot resolve to a safe address during validation and a private address
    during the actual connection.

    Redirects are followed manually rather than by httpx so each hop can be revalidated and sensitive headers
    can be narrowed before the next request. Once a redirect crosses origins, scoped credentials are removed
    from `current_headers` and are not restored on later hops.
    """
    httpx_module = _get_httpx()
    current_url = url
    current_headers = headers
    for redirect_count in range(MAX_HTTP_REDIRECTS + 1):
        validated_host = _validate_url_for_fetch(current_url, allow_private_network=allow_private_network)
        pinned_host, pinned_ips = validated_host if validated_host is not None else (None, ())
        try:
            response = _get_http_response(
                httpx_module,
                current_url,
                headers=current_headers,
                verify=not ignore_tls,
                follow_redirects=False,
                query_parameters=query_parameters if redirect_count == 0 else None,
                timeout=timeout,
                pinned_host=pinned_host,
                pinned_ips=pinned_ips,
            )
        except Exception as e:
            msg = f"Failed to fetch {current_url}: {e}"
            raise SchemaFetchError(msg) from e
        if (redirect_url := _get_redirect_url(httpx_module, current_url, response)) is None:
            break
        current_headers = _get_redirect_headers(current_headers, current_url, redirect_url)
        current_url = redirect_url
    else:
        msg = f"Too many redirects fetching {url}"
        raise SchemaFetchError(msg)

    if response.status_code >= 400:  # noqa: PLR2004
        msg = f"HTTP {response.status_code} error fetching {current_url}"
        raise SchemaFetchError(msg)
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        msg = (
            f"Unexpected HTML response from {current_url} "
            f"(Content-Type: {content_type}). Expected JSON or YAML schema content."
        )
        raise SchemaFetchError(msg)
    return response.text


def join_url(url: str, ref: str = ".") -> str:  # noqa: PLR0912
    """Join a base URL with a relative reference.

    File URLs need local handling because httpx URL joining is HTTP-oriented. HTTP(S) URLs are delegated to
    httpx so normal web URL semantics stay consistent with the fetch path.
    """
    if url.startswith("file://"):
        from urllib.parse import urlparse  # noqa: PLC0415

        parsed = urlparse(url)

        if ref.startswith("file://"):
            return ref

        ref_path, *frag = ref.split("#", 1)

        # Fragment-only ref: keep the original path
        if not ref_path:
            joined = url.split("#", maxsplit=1)[0]
            if frag:
                joined += f"#{frag[0]}"
            return joined

        if ref_path.startswith("/"):
            joined_path = ref_path
        else:
            base_segments = parsed.path.lstrip("/").split("/")
            if base_segments and not base_segments[0]:
                base_segments = []
            if base_segments:
                base_segments = base_segments[:-1]

            min_depth = 1 if parsed.netloc else 0
            for segment in ref_path.split("/"):
                if segment in {"", "."}:
                    continue
                if segment == "..":
                    if len(base_segments) > min_depth:
                        base_segments.pop()
                    continue
                base_segments.append(segment)

            joined_path = "/" + "/".join(base_segments)
            if ref_path.endswith("/"):
                joined_path += "/"

        joined = f"file://{parsed.netloc}{joined_path}"
        if frag:
            joined += f"#{frag[0]}"
        return joined
    httpx_module = _get_httpx()
    return str(httpx_module.URL(url).join(ref))
