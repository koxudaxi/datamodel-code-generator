"""HTTP utilities for fetching remote schema files.

Provides functions to fetch schema content from URLs and join URL references.
HTTP(S) URLs require the 'http' extra: `pip install 'datamodel-code-generator[http]'`.
file:// URLs are handled without additional dependencies.
"""

from __future__ import annotations

import socket
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from datamodel_code_generator import SchemaFetchError

if TYPE_CHECKING:
    from collections.abc import Sequence


def _get_httpx() -> Any:
    """Lazily import httpx, raising a helpful error if not installed."""
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        msg = "Please run `$pip install 'datamodel-code-generator[http]`' to resolve HTTP(S) URL references"
        raise Exception(msg) from exc  # noqa: TRY002
    return httpx


DEFAULT_HTTP_TIMEOUT = 30.0
MAX_HTTP_REDIRECTS = 20
_HTTP_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_UNSAFE_HOST_NAMES = frozenset({"localhost"})
_IPV4_PART_COUNT = 4
_IPV4_OCTET_MAX = 0xFF
_IPV4_THREE_PART_TAIL_MAX = 0xFFFF
_IPV4_TWO_PART_TAIL_MAX = 0xFFFFFF
_IPV4_ADDRESS_MAX = 0xFFFFFFFF


def _is_safe_ip(ip: IPv4Address | IPv6Address) -> bool:
    return ip.is_global


def _parse_legacy_ipv4_int(value: str) -> int | None:
    try:
        if value.lower().startswith("0x"):
            return int(value, 0)
        if len(value) > 1 and value.startswith("0"):
            return int(value[1:], 8)
        return int(value, 10)
    except ValueError:
        return None


def _parse_legacy_ipv4_address(host: str) -> IPv4Address | None:
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

    return tuple({ip_address(str(addr_info[4][0]).split("%", maxsplit=1)[0]) for addr_info in addr_infos})


def _format_private_network_error(
    *,
    url: str,
    hostname: str,
    reason: str,
    resolved_ips: tuple[IPv4Address | IPv6Address, ...] = (),
) -> str:
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


def _validate_url_for_fetch(url: str, *, allow_private_network: bool) -> None:
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

    host = hostname.rstrip(".").lower()
    if allow_private_network:
        return

    if host in _UNSAFE_HOST_NAMES or host.endswith(".localhost"):
        msg = _format_private_network_error(
            url=url,
            hostname=hostname,
            reason="localhost names resolve to the local machine",
        )
        raise SchemaFetchError(msg)

    ips = _get_ips_from_host(host)
    if not ips:
        return

    if all(_is_safe_ip(ip) for ip in ips):
        return

    msg = _format_private_network_error(
        url=url,
        hostname=hostname,
        reason="the host resolves to a non-public address",
        resolved_ips=ips,
    )
    raise SchemaFetchError(msg)


def _get_redirect_url(httpx: Any, current_url: str, response: Any) -> str | None:
    if response.status_code not in _HTTP_REDIRECT_STATUS_CODES:
        return None
    if not (location := response.headers.get("location")):
        msg = f"Redirect response from {current_url} is missing a Location header"
        raise SchemaFetchError(msg)
    return str(httpx.URL(current_url).join(location))


def get_body(  # noqa: PLR0913
    url: str,
    headers: Sequence[tuple[str, str]] | None = None,
    ignore_tls: bool = False,  # noqa: FBT001, FBT002
    query_parameters: Sequence[tuple[str, str]] | None = None,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    *,
    allow_private_network: bool = False,
) -> str:
    """Fetch content from a URL with optional headers and query parameters."""
    httpx = _get_httpx()
    current_url = url
    for redirect_count in range(MAX_HTTP_REDIRECTS + 1):
        _validate_url_for_fetch(current_url, allow_private_network=allow_private_network)
        try:
            response = httpx.get(
                current_url,
                headers=headers,
                verify=not ignore_tls,
                follow_redirects=False,
                params=query_parameters if redirect_count == 0 else None,  # ty: ignore
                timeout=timeout,
            )
        except Exception as e:
            msg = f"Failed to fetch {current_url}: {e}"
            raise SchemaFetchError(msg) from e
        if (redirect_url := _get_redirect_url(httpx, current_url, response)) is None:
            break
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
    """Join a base URL with a relative reference."""
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
    httpx = _get_httpx()
    return str(httpx.URL(url).join(ref))
